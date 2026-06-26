# aether/codegen.py
import re
from typing import Dict, List, Optional, Tuple, Any
from .ast_nodes import *
from .diagnostics import DiagnosticEngine, Severity, ErrorCodes

class CodeGenerator(Visitor):
    def __init__(self, ast: Program, engine: DiagnosticEngine, root_ns: str = "aether"):
        self.ast = ast
        self.engine = engine
        self.ir: Dict[str, List[str]] = {}
        self.current_ns = root_ns
        self.cmds: List[str] = []
        self.var_c = 0
        self.temp_c = 0
        self.mac_c = 0
        self.scopes: List[Dict[str, Dict[str, str]]] = [{}]
        self.objectives: set = set()

    def generate(self):
        self.ast.accept(self) # Visit AST first to collect all objectives and functions
        
        # Generate load.mcfunction
        load_cmds = ["scoreboard objectives add ae_int dummy"]
        for obj in self.objectives:
            load_cmds.append(f"scoreboard objectives add {obj} dummy")
            
        # Call main() if it exists
        if f"{self.current_ns}:main" in self.ir:
            load_cmds.append(f"function {self.current_ns}:main")
            
        self.ir[f"{self.current_ns}:load"] = load_cmds
        
        load_tags = [f"{self.current_ns}:load"]
        tick_tags = []
        if f"{self.current_ns}:tick" in self.ir:
            tick_tags.append(f"{self.current_ns}:tick")
            
        if load_tags: self.ir["minecraft:tags/functions/load.json"] = load_tags
        if tick_tags: self.ir["minecraft:tags/functions/tick.json"] = tick_tags
        
        return self.ir

    def _lookup(self, name): 
        for s in reversed(self.scopes):
            if name in s: return s[name]
        return None
        
    def _alloc_var(self, name, t):
        safe = "".join(c if c.isalnum() else "_" for c in name)
        obj_name = f"var_{safe}_{self.var_c}"
        self.var_c += 1
        self.objectives.add(obj_name)
        self.scopes[-1][name] = {"type": t, "player": "#val", "obj": obj_name}
        return f"#val {obj_name}"
        
    def _alloc_temp(self, t): 
        loc = f"#temp_{self.temp_c}"
        self.temp_c += 1
        return f"{loc} ae_int"
        
    def _get_path(self, node):
        if isinstance(node, Identifier):
            v = self._lookup(node.name)
            if not v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared '{node.name}'", node.line, node.col)
                return "#err err"
            return f"{v['player']} {v['obj']}"
        self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, "Invalid target", node.line, node.col)
        return "#err err"

    def visit_Program(self, node):
        for s in node.statements: s.accept(self)

    def visit_NamespaceDecl(self, node): self.current_ns = node.name

    def visit_FunctionDecl(self, node):
        full = f"{self.current_ns}:{node.name}"
        p_cmds = self.cmds; self.cmds = []; self.scopes.append({})
        
        for i, p in enumerate(node.params):
            p_loc = self._alloc_var(p.name, p.param_type.name)
            player, obj = p_loc.split(" ")
            if p.param_type.name in ["int", "bool"]:
                self.cmds.append(f"scoreboard players operation {player} {obj} = #arg_{i} ae_int")
            self.scopes[-1][p.name] = {"type": p.param_type.name, "player": player, "obj": obj}

        node.body.accept(self)
        self.ir[full] = self.cmds
        self.cmds = p_cmds; self.scopes.pop()

    def visit_Block(self, node):
        self.scopes.append({})
        for s in node.statements: s.accept(self)
        self.scopes.pop()

    def visit_VariableDecl(self, node):
        if isinstance(node.value, Literal):
            p_loc = self._alloc_var(node.name, node.var_type.name)
            if node.var_type.name in ["int", "bool"]:
                v = node.value.value if node.var_type.name == "int" else (1 if node.value.value else 0)
                self.cmds.append(f"scoreboard players set {p_loc} {v}")
            else:
                safe = node.value.value.replace('"', '\\"')
                self.cmds.append(f'data modify storage {self.current_ns}:data var_{node.name}_{self.var_c-1} set value "{safe}"')
            return
        t, l = self._eval_expr(node.value)
        p_loc = self._alloc_var(node.name, node.var_type.name)
        if node.var_type.name in ["int", "bool"]:
            self.cmds.append(f"scoreboard players operation {p_loc} = {l}")

    def visit_Assignment(self, node):
        p_loc = self._get_path(node.target)
        if isinstance(node.value, Literal):
            t = node.target.inferred_type if hasattr(node.target, 'inferred_type') else "int"
            if t in ["int", "bool"]:
                v = node.value.value if t == "int" else (1 if node.value.value else 0)
                self.cmds.append(f"scoreboard players set {p_loc} {v}")
            return
        t, l = self._eval_expr(node.value)
        if t in ["int", "bool"]:
            self.cmds.append(f"scoreboard players operation {p_loc} = {l}")

    def visit_IfStmt(self, node):
        ifn = f"__if_{self.temp_c}"; self.temp_c += 1
        fif = f"{self.current_ns}:{ifn}"
        p = self.cmds; self.cmds = []
        node.then_block.accept(self)
        self.ir[fif] = self.cmds
        self.cmds = p
        
        if node.raw_condition:
            self.cmds.append(f"execute if {node.raw_condition} run function {fif}")
            if node.else_stmt:
                efn = f"__else_{self.temp_c}"; self.temp_c += 1
                fel = f"{self.current_ns}:{efn}"
                p = self.cmds; self.cmds = []
                node.else_stmt.accept(self)
                self.ir[fel] = self.cmds
                self.cmds = p
                self.cmds.append(f"execute unless {node.raw_condition} run function {fel}")
        else:
            t, l = self._eval_expr(node.condition)
            self.cmds.append(f"execute if score {l} matches 1 run function {fif}")
            if node.else_stmt:
                efn = f"__else_{self.temp_c}"; self.temp_c += 1
                fel = f"{self.current_ns}:{efn}"
                p = self.cmds; self.cmds = []
                node.else_stmt.accept(self)
                self.ir[fel] = self.cmds
                self.cmds = p
                self.cmds.append(f"execute if score {l} matches 0 run function {fel}")

    def visit_ExecuteStmt(self, node: ExecuteStmt):
        efn = f"__exec_{self.temp_c}"; self.temp_c += 1
        fex = f"{self.current_ns}:{efn}"
        
        p = self.cmds; self.cmds = []
        node.body.accept(self)
        self.ir[fex] = self.cmds
        self.cmds = p
        
        self.cmds.append(f"execute {node.chain} run function {fex}")

    def visit_ForStmt(self, node):
        s = node.start; e = node.end
        if isinstance(s, Literal) and isinstance(e, Literal):
            for i in range(s.value, e.value):
                p = self.scopes; self.scopes.append({})
                p_loc = self._alloc_var(node.var_name, "int")
                self.cmds.append(f"scoreboard players set {p_loc} {i}")
                node.body.accept(self)
                self.scopes.pop()
        else: self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "For loop bounds must be compile-time constants", node.line, node.col)

    def visit_ReturnStmt(self, node):
        if node.value:
            if isinstance(node.value, Literal):
                t = node.value.lit_type
                if t in ["int", "bool"]:
                    v = node.value.value if t == "int" else (1 if node.value.value else 0)
                    self.cmds.append(f"scoreboard players set #ret ae_int {v}")
                self.cmds.append("return 1")
                return
            t, l = self._eval_expr(node.value)
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation #ret ae_int = {l}")
        self.cmds.append("return 1")

    def visit_RawCommandStmt(self, node: RawCommandStmt):
        cmd_str = node.cmd_str
        matches = re.findall(r'\{([a-zA-Z0-9_]+)\}', cmd_str)
        
        if not matches:
            clean_cmd = cmd_str[1:].strip()
            self.cmds.append(clean_cmd)
            return None
            
        macro_id = self.mac_c
        self.mac_c += 1
        macro_name = f"__macro_{macro_id}"
        full_macro_name = f"{self.current_ns}:{macro_name}"
        
        macro_data_str = []
        for var_name in matches:
            v = self._lookup(var_name)
            if not v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{var_name}' in raw command.", node.line, node.col)
                continue
            
            storage_key = f"macro_{var_name}"
            
            if v["type"] in ["int", "bool"]:
                self.cmds.append(f"execute store storage {self.current_ns}:data {storage_key} int 1 run scoreboard players get {v['player']} {v['obj']}")
            else:
                self.cmds.append(f"data modify storage {self.current_ns}:data {storage_key} set from storage {self.current_ns}:data {v['obj']}")
            
            macro_data_str.append(storage_key)
            
        args_str = ",".join(macro_data_str)
        self.cmds.append(f"function {full_macro_name} with storage {self.current_ns}:data {{{args_str}}}")
        
        old_cmds = self.cmds
        self.cmds = []
        macro_cmd = cmd_str[1:]
        for var_name in matches:
            macro_cmd = macro_cmd.replace('{' + var_name + '}', '$(macro_' + var_name + ')')
        macro_cmd = '$' + macro_cmd.strip()
        
        self.cmds.append(macro_cmd)
        self.ir[full_macro_name] = self.cmds
        self.cmds = old_cmds

    def visit_ExprStmt(self, node): self._eval_expr(node.expr)

    def _eval_expr(self, node) -> Tuple[str, str]:
        if isinstance(node, Literal):
            if node.lit_type in ["int", "bool"]:
                l = self._alloc_temp("int")
                v = node.value if node.lit_type == "int" else (1 if node.value else 0)
                self.cmds.append(f"scoreboard players set {l} {v}")
                return ("int", l)
        elif isinstance(node, Identifier):
            v = self._lookup(node.name)
            if not v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared '{node.name}'", node.line, node.col)
                return ("unknown", "#err err")
            return (v["type"], f"{v['player']} {v['obj']}")
        elif isinstance(node, BinaryOp):
            lt, ll = self._eval_expr(node.left); rt, rl = self._eval_expr(node.right)
            res = self._alloc_temp(lt)
            if node.op in ['+', '-', '*', '/', '%']:
                self.cmds.append(f"scoreboard players operation {res} = {ll}")
                ops = {'+': '+=', '-': '-=', '*': '*=', '/': '/=', '%': '%='}
                self.cmds.append(f"scoreboard players operation {res} {ops[node.op]} {rl}")
                return ("int", res)
            elif node.op in ['==', '!=', '<', '>', '<=', '>=']:
                self.cmds.append(f"scoreboard players set {res} 0")
                if node.op == '!=': self.cmds.append(f"execute unless score {ll} = {rl} run scoreboard players set {res} 1")
                else: self.cmds.append(f"execute if score {ll} {node.op} {rl} run scoreboard players set {res} 1")
                return ("bool", res)
        elif isinstance(node, FunctionCall):
            args = [self._eval_expr(a) for a in node.args]
            for i, (t, l) in enumerate(args):
                if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation #arg_{i} ae_int = {l}")
            self.cmds.append(f"function {self.current_ns}:{node.name}")
            return ("int", "#ret ae_int")
        return ("unknown", "#err err")

    def visit_ArrayLiteral(self, node: ArrayLiteral):
        arr_obj = f"var_arr_{self.var_c}"
        self.var_c += 1
        self.objectives.add(arr_obj)
        
        for i, e in enumerate(node.elements):
            if isinstance(e, Literal):
                if e.lit_type in ["int", "bool"]:
                    val = e.value if e.lit_type == "int" else (1 if e.value else 0)
                    self.cmds.append(f"scoreboard players set {i} {arr_obj} {val}")
            else:
                et, el = self._eval_expr(e)
                if et in ["int", "bool"]: self.cmds.append(f"scoreboard players operation {i} {arr_obj} = {el}")
        
        self.scopes[-1][f"__arr_{arr_obj}"] = {"type": "int[]", "player": "#elem", "obj": arr_obj}
        return ("int[]", arr_obj)

    def visit_IndexAccess(self, node: IndexAccess):
        if not isinstance(node.index, Literal):
            self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "Array indices must be literal integers for MVP.", node.line, node.col)
            return ("int", "#err err")
            
        arr_type, arr_loc = self._eval_expr(node.array)
        idx = node.index.value
        
        res_loc = self._alloc_temp("int")
        self.cmds.append(f"scoreboard players operation {res_loc} = {idx} {arr_loc}")
        return ("int", res_loc)