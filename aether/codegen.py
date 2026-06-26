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

    def generate(self):
        self.ir[f"{self.current_ns}:load"] = ["scoreboard objectives add ae_int dummy"]
        load_tags = []
        tick_tags = []
        for s in self.ast.statements:
            if isinstance(s, FunctionDecl):
                if s.name in ["main", "load"]: load_tags.append(f"{self.current_ns}:{s.name}")
                elif s.name == "tick": tick_tags.append(f"{self.current_ns}:{s.name}")
        if load_tags: self.ir["minecraft:tags/functions/load.json"] = load_tags
        if tick_tags: self.ir["minecraft:tags/functions/tick.json"] = tick_tags
        
        self.ast.accept(self)
        return self.ir

    def _lookup(self, name): 
        for s in reversed(self.scopes):
            if name in s: return s[name]
        return None
        
    def _alloc_var(self, name, t):
        safe = "".join(c if c.isalnum() else "_" for c in name)
        loc = f"var_{safe}_{self.var_c}"
        self.var_c += 1
        self.scopes[-1][name] = {"type": t, "loc": loc}
        return loc
        
    def _alloc_temp(self, t): 
        loc = f"temp_{self.temp_c}"; self.temp_c += 1
        return loc
        
    def _get_path(self, node):
        if isinstance(node, Identifier):
            v = self._lookup(node.name)
            if not v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared '{node.name}'", node.line, node.col)
                return "unknown"
            return v["loc"]
        self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, "Invalid target", node.line, node.col)
        return "unknown"

    def visit_Program(self, node):
        for s in node.statements: s.accept(self)

    def visit_NamespaceDecl(self, node): self.current_ns = node.name

    def visit_FunctionDecl(self, node):
        full = f"{self.current_ns}:{node.name}"
        p_cmds = self.cmds; self.cmds = []; self.scopes.append({})
        
        for i, p in enumerate(node.params):
            loc = f"param_{p.name}_{i}"
            if p.param_type.name in ["int", "bool"]:
                self.cmds.append(f"scoreboard players operation {loc} ae_int = arg_{i} ae_int")
            else:
                self.cmds.append(f"data modify storage {self.current_ns}:data {loc} set from storage {self.current_ns}:data arg{i}")
            self.scopes[-1][p.name] = {"type": p.param_type.name, "loc": loc}

        node.body.accept(self)
        self.ir[full] = self.cmds
        self.cmds = p_cmds; self.scopes.pop()

    def visit_Block(self, node):
        self.scopes.append({})
        for s in node.statements: s.accept(self)
        self.scopes.pop()

    def visit_VariableDecl(self, node):
        if isinstance(node.value, Literal):
            loc = self._alloc_var(node.name, node.var_type.name)
            if node.var_type.name in ["int", "bool"]:
                v = node.value.value if node.var_type.name == "int" else (1 if node.value.value else 0)
                self.cmds.append(f"scoreboard players set {loc} ae_int {v}")
            else:
                safe = node.value.value.replace('"', '\\"')
                self.cmds.append(f'data modify storage {self.current_ns}:data {loc} set value "{safe}"')
            return
        t, l = node.value.accept(self)
        loc = self._alloc_var(node.name, node.var_type.name)
        if node.var_type.name in ["int", "bool"]:
            self.cmds.append(f"scoreboard players operation {loc} ae_int = {l} ae_int")
        else:
            self.cmds.append(f"data modify storage {self.current_ns}:data {loc} set from storage {self.current_ns}:data {l}")

    def visit_Assignment(self, node):
        path = self._get_path(node.target)
        if isinstance(node.value, Literal):
            t = node.target.inferred_type if hasattr(node.target, 'inferred_type') else "int"
            if t in ["int", "bool"]:
                v = node.value.value if t == "int" else (1 if node.value.value else 0)
                self.cmds.append(f"scoreboard players set {path} ae_int {v}")
            else:
                safe = node.value.value.replace('"', '\\"')
                self.cmds.append(f'data modify storage {self.current_ns}:data {path} set value "{safe}"')
            return
        t, l = node.value.accept(self)
        if t in ["int", "bool"]:
            self.cmds.append(f"scoreboard players operation {path} ae_int = {l} ae_int")
        else:
            self.cmds.append(f"data modify storage {self.current_ns}:data {path} set from storage {self.current_ns}:data {l}")

    def visit_IfStmt(self, node):
        t, l = node.condition.accept(self)
        ifn = f"branch_if_{self.temp_c}"; self.temp_c += 1
        fif = f"{self.current_ns}:{ifn}"
        p = self.cmds; self.cmds = []
        node.then_block.accept(self)
        self.ir[fif] = self.cmds
        self.cmds = p
        self.cmds.append(f"execute if score {l} ae_int matches 1 run function {fif}")
        if node.else_stmt:
            efn = f"branch_else_{self.temp_c}"; self.temp_c += 1
            fel = f"{self.current_ns}:{efn}"
            p = self.cmds; self.cmds = []
            node.else_stmt.accept(self)
            self.ir[fel] = self.cmds
            self.cmds = p
            self.cmds.append(f"execute if score {l} ae_int matches 0 run function {fel}")

    def visit_ForStmt(self, node):
        s = node.start; e = node.end
        if isinstance(s, Literal) and isinstance(e, Literal):
            for i in range(s.value, e.value):
                p = self.scopes; self.scopes.append({})
                loc = f"var_{node.var_name}_{self.var_c}"; self.var_c += 1
                self.scopes[-1][node.var_name] = {"type": "int", "loc": loc}
                self.cmds.append(f"scoreboard players set {loc} ae_int {i}")
                node.body.accept(self)
                self.scopes.pop()
        else: self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "For loop bounds must be compile-time constants", node.line, node.col)

    def visit_ReturnStmt(self, node):
        if node.value:
            if isinstance(node.value, Literal):
                t = node.value.lit_type
                if t in ["int", "bool"]:
                    v = node.value.value if t == "int" else (1 if node.value.value else 0)
                    self.cmds.append(f"scoreboard players set ret ae_int {v}")
                else:
                    safe = node.value.value.replace('"', '\\"')
                    self.cmds.append(f'data modify storage {self.current_ns}:data ret set value "{safe}"')
                self.cmds.append("return 1")
                return
            t, l = node.value.accept(self)
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation ret ae_int = {l} ae_int")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data ret set from storage {self.current_ns}:data {l}")
        self.cmds.append("return 1")

    def visit_RawCommandStmt(self, node: RawCommandStmt):
        cmd_str = node.cmd_str
        matches = re.findall(r'\{([a-zA-Z0-9_]+)\}', cmd_str)
        
        if not matches:
            self.cmds.append(cmd_str)
            return None
            
        macro_id = self.mac_c
        self.mac_c += 1
        macro_name = f"macro_cmd_{macro_id}"
        full_macro_name = f"{self.current_ns}:{macro_name}"
        
        macro_data_str = []
        for var_name in matches:
            v = self._lookup(var_name)
            if not v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{var_name}' in raw command.", node.line, node.col)
                continue
            if v["type"] in ["int", "bool"]:
                self.cmds.append(f"execute store storage {self.current_ns}:data macro_{var_name} int 1 run scoreboard players get {v['loc']} ae_int")
            else:
                self.cmds.append(f"data modify storage {self.current_ns}:data macro_{var_name} set from storage {self.current_ns}:data {v['loc']}")
            macro_data_str.append(f"macro_{var_name}")
            
        args_str = ",".join(macro_data_str)
        self.cmds.append(f"function {full_macro_name} with storage {self.current_ns}:data {{{args_str}}}")
        
        old_cmds = self.cmds
        self.cmds = []
        macro_cmd = cmd_str
        for var_name in matches:
            macro_cmd = macro_cmd.replace('{' + var_name + '}', '$(' + var_name + ')')
        macro_cmd = '$' + macro_cmd[1:] # Replace leading '/' with '$'
        
        self.cmds.append(macro_cmd)
        self.ir[full_macro_name] = self.cmds
        self.cmds = old_cmds

    def visit_ExprStmt(self, node): node.expr.accept(self)

    def visit_Literal(self, node):
        if node.lit_type == "int":
            l = self._alloc_temp("int"); self.cmds.append(f"scoreboard players set {l} ae_int {node.value}"); return ("int", l)
        if node.lit_type == "bool":
            l = self._alloc_temp("bool"); self.cmds.append(f"scoreboard players set {l} ae_int {1 if node.value else 0}"); return ("bool", l)
        if node.lit_type == "string":
            l = self._alloc_temp("string"); safe = node.value.replace('"', '\\"')
            self.cmds.append(f'data modify storage {self.current_ns}:data {l} set value "{safe}"'); return ("string", l)

    def visit_ArrayLiteral(self, node: ArrayLiteral):
        loc = self._alloc_temp("int[]")
        self.cmds.append(f'data modify storage {self.current_ns}:data {loc} set value []')
        for e in node.elements:
            if isinstance(e, Literal):
                if e.lit_type in ["int", "bool"]:
                    val = e.value if e.lit_type == "int" else (1 if e.value else 0)
                    self.cmds.append(f'execute store storage {self.current_ns}:data {loc}[] int 1 run scoreboard players set temp_lit ae_int {val}')
            else:
                et, el = e.accept(self)
                if et in ["int", "bool"]: self.cmds.append(f'execute store storage {self.current_ns}:data {loc}[] int 1 run scoreboard players get {el} ae_int')
        return ("int[]", loc)

    def visit_Identifier(self, node):
        v = self._lookup(node.name)
        if not v:
            self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared '{node.name}'", node.line, node.col)
            return ("unknown", "unknown")
        return (v["type"], v["loc"])

    def visit_IndexAccess(self, node: IndexAccess):
        # MVP: Only literal indices allowed
        if not isinstance(node.index, Literal):
            self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "Array indices must be literal integers for MVP.", node.line, node.col)
            return ("int", "unknown")
            
        arr_type, arr_loc = node.array.accept(self)
        idx = node.index.value
        
        res_loc = self._alloc_temp("int")
        self.cmds.append(f"execute store score {res_loc} ae_int run data get storage {self.current_ns}:data {arr_loc}[{idx}]")
        return ("int", res_loc)

    def visit_BinaryOp(self, node):
        lt, ll = node.left.accept(self); rt, rl = node.right.accept(self)
        res = self._alloc_temp(lt)
        if node.op in ['+', '-', '*', '/', '%']:
            self.cmds.append(f"scoreboard players operation {res} ae_int = {ll} ae_int")
            ops = {'+': '+=', '-': '-=', '*': '*=', '/': '/=', '%': '%='}
            self.cmds.append(f"scoreboard players operation {res} ae_int {ops[node.op]} {rl} ae_int")
            return ("int", res)
        elif node.op in ['==', '!=', '<', '>', '<=', '>=']:
            self.cmds.append(f"scoreboard players set {res} ae_int 0")
            if node.op == '!=': self.cmds.append(f"execute unless score {ll} ae_int = {rl} ae_int run scoreboard players set {res} ae_int 1")
            else: self.cmds.append(f"execute if score {ll} ae_int {node.op} {rl} ae_int run scoreboard players set {res} ae_int 1")
            return ("bool", res)
        elif node.op in ['&&', '||']:
            self.cmds.append(f"scoreboard players operation {res} ae_int = {ll} ae_int")
            if node.op == '&&': self.cmds.append(f"scoreboard players operation {res} ae_int *= {rl} ae_int")
            else:
                self.cmds.append(f"scoreboard players operation {res} ae_int += {rl} ae_int")
                self.cmds.append(f"execute if score {res} ae_int matches 2.. run scoreboard players set {res} ae_int 1")
            return ("bool", res)

    def visit_FunctionCall(self, node):
        args = [a.accept(self) for a in node.args]
        for i, (t, l) in enumerate(args):
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation arg_{i} ae_int = {l} ae_int")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data arg{i} set from storage {self.current_ns}:data {l}")
        self.cmds.append(f"function {self.current_ns}:{node.name}")
        return None