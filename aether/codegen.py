# src/aether/codegen.py

import re
from typing import Dict, List, Optional, Tuple, Any
from .ast_nodes import *
from .errors import CodegenError

class CodeGenerator(Visitor):
    def __init__(self, ast: Program, root_ns: str = "aether"):
        self.ast = ast
        self.ir: Dict[str, List[str]] = {}
        self.current_ns = root_ns
        self.cmds: List[str] = []
        self.var_c = 0
        self.temp_c = 0
        self.mac_c = 0
        self.scopes: List[Dict[str, Dict[str, str]]] = [{}]
        self.class_context: Optional[str] = None

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
        
    def _alloc_var(self, name, t, objective="ae_int"):
        safe = "".join(c if c.isalnum() else "_" for c in name)
        loc = f"var_{safe}_{self.var_c}"
        self.var_c += 1
        self.scopes[-1][name] = {"type": t, "loc": loc, "objective": objective}
        return loc
        
    def _alloc_temp(self, t, objective="ae_int"): 
        loc = f"temp_{self.temp_c}"; self.temp_c += 1
        return loc
        
    def _get_path(self, node):
        if isinstance(node, Identifier):
            v = self._lookup(node.name)
            if not v: raise CodegenError(f"Undeclared '{node.name}'", node.line, node.col)
            return v["loc"]
        if isinstance(node, MemberAccess):
            base = "self" if isinstance(node.obj, Identifier) and node.obj.name == "self" else self._get_path(node.obj)
            if isinstance(node.obj, Identifier) and node.obj.name == "self" and self.class_context:
                return f"instances.{self.class_context}_$(obj_id).{node.member}"
            return f"{base}.{node.member}"
        raise CodegenError("Invalid target", node.line, node.col)

    def _get_obj(self, node):
        """Returns the scoreboard objective for a given AST node."""
        if isinstance(node, Identifier):
            v = self._lookup(node.name)
            return v["objective"] if v else "ae_int"
        return "ae_int"

    def visit_Program(self, node):
        for s in node.statements: s.accept(self)

    def visit_NamespaceDecl(self, node): self.current_ns = node.name
    def visit_ClassDecl(self, node): pass

    def visit_FunctionDecl(self, node):
        full = f"{self.current_ns}:{node.name}"
        p_cmds = self.cmds; self.cmds = []; self.scopes.append({})
        
        if node.is_method and node.params and node.params[0].name == "self":
            self.class_context = node.name.rsplit("_", 1)[0] if "_" in node.name else None
            self.scopes[-1]["self"] = {"type": self.class_context, "loc": "self", "objective": "ae_int"}
            for i, p in enumerate(node.params[1:]):
                loc = f"param_{p.name}_{i}"
                if p.param_type.name in ["int", "bool"]:
                    self.cmds.append(f"scoreboard players operation {loc} ae_int = arg_{i} ae_int")
                else:
                    self.cmds.append(f"data modify storage {self.current_ns}:data {loc} set from storage {self.current_ns}:data arg{i}")
                self.scopes[-1][p.name] = {"type": p.param_type.name, "loc": loc, "objective": "ae_int"}
            self.cmds.insert(0, "$")
        else:
            for i, p in enumerate(node.params):
                loc = f"param_{p.name}_{i}"
                if p.param_type.name in ["int", "bool"]:
                    self.cmds.append(f"scoreboard players operation {loc} ae_int = arg_{i} ae_int")
                else:
                    self.cmds.append(f"data modify storage {self.current_ns}:data {loc} set from storage {self.current_ns}:data arg{i}")
                self.scopes[-1][p.name] = {"type": p.param_type.name, "loc": loc, "objective": "ae_int"}

        node.body.accept(self)
        self.ir[full] = self.cmds
        self.cmds = p_cmds; self.scopes.pop()
        self.class_context = None

    def visit_Block(self, node):
        self.scopes.append({})
        for s in node.statements: s.accept(self)
        self.scopes.pop()

    def visit_VariableDecl(self, node):
        obj_name = node.decorator if node.decorator else "ae_int"
        
        if isinstance(node.value, Literal):
            loc = self._alloc_var(node.name, node.var_type.name, obj_name)
            if node.var_type.name in ["int", "bool"]:
                v = node.value.value if node.var_type.name == "int" else (1 if node.value.value else 0)
                self.cmds.append(f"scoreboard players set {loc} {obj_name} {v}")
            else:
                safe = node.value.value.replace('"', '\\"')
                self.cmds.append(f'data modify storage {self.current_ns}:data {loc} set value "{safe}"')
            return
        t, l = node.value.accept(self)
        loc = self._alloc_var(node.name, node.var_type.name, obj_name)
        if node.var_type.name in ["int", "bool"]:
            self.cmds.append(f"scoreboard players operation {loc} {obj_name} = {l} ae_int")
        else:
            self.cmds.append(f"data modify storage {self.current_ns}:data {loc} set from storage {self.current_ns}:data {l}")

    def visit_Assignment(self, node):
        path = self._get_path(node.target)
        obj = self._get_obj(node.target)
        
        if isinstance(node.value, Literal):
            t = node.target.inferred_type if hasattr(node.target, 'inferred_type') else "int"
            if t in ["int", "bool"]:
                v = node.value.value if t == "int" else (1 if node.value.value else 0)
                self.cmds.append(f"scoreboard players set {path} {obj} {v}")
            else:
                safe = node.value.value.replace('"', '\\"')
                self.cmds.append(f'data modify storage {self.current_ns}:data {path} set value "{safe}"')
            return
        t, l = node.value.accept(self)
        val_obj = self._get_obj(node.value)
        if t in ["int", "bool"]:
            self.cmds.append(f"scoreboard players operation {path} {obj} = {l} {val_obj}")
        else:
            self.cmds.append(f"data modify storage {self.current_ns}:data {path} set from storage {self.current_ns}:data {l}")

    def visit_IfStmt(self, node):
        t, l = node.condition.accept(self)
        obj = self._get_obj(node.condition)
        ifn = f"branch_if_{self.temp_c}"; self.temp_c += 1
        fif = f"{self.current_ns}:{ifn}"
        p = self.cmds; self.cmds = []
        node.then_block.accept(self)
        self.ir[fif] = self.cmds
        self.cmds = p
        self.cmds.append(f"execute if score {l} {obj} matches 1 run function {fif}")
        if node.else_stmt:
            efn = f"branch_else_{self.temp_c}"; self.temp_c += 1
            fel = f"{self.current_ns}:{efn}"
            p = self.cmds; self.cmds = []
            node.else_stmt.accept(self)
            self.ir[fel] = self.cmds
            self.cmds = p
            self.cmds.append(f"execute if score {l} {obj} matches 0 run function {fel}")

    def visit_ForStmt(self, node):
        s = node.start; e = node.end
        if isinstance(s, Literal) and isinstance(e, Literal):
            for i in range(s.value, e.value):
                p = self.scopes; self.scopes.append({})
                loc = f"var_{node.var_name}_{self.var_c}"; self.var_c += 1
                self.scopes[-1][node.var_name] = {"type": "int", "loc": loc, "objective": "ae_int"}
                self.cmds.append(f"scoreboard players set {loc} ae_int {i}")
                node.body.accept(self)
                self.scopes.pop()
        else: raise CodegenError("For loop bounds must be compile-time constants", node.line, node.col)

    def visit_WhileStmt(self, node):
        wf = f"loop_{self.temp_c}"; bf = f"loop_body_{self.temp_c}"; self.temp_c += 1
        fw = f"{self.current_ns}:{wf}"; fb = f"{self.current_ns}:{bf}"
        self.cmds.append(f"function {fw}")
        p = self.cmds; self.cmds = []
        t, l = node.condition.accept(self)
        obj = self._get_obj(node.condition)
        self.cmds.append(f"execute unless score {l} {obj} matches 1 run return 1")
        self.cmds.append(f"function {fb}")
        self.cmds.append(f"function {fw}")
        self.ir[fw] = self.cmds
        self.cmds = []
        self.scopes.append({})
        node.body.accept(self)
        self.scopes.pop()
        self.ir[fb] = self.cmds
        self.cmds = p

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
            obj = self._get_obj(node.value)
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation ret ae_int = {l} {obj}")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data ret set from storage {self.current_ns}:data {l}")
        self.cmds.append("return 1")

    def visit_ExprStmt(self, node): node.expr.accept(self)

    def visit_Literal(self, node):
        if node.lit_type == "int":
            l = self._alloc_temp("int"); self.cmds.append(f"scoreboard players set {l} ae_int {node.value}"); return ("int", l)
        if node.lit_type == "bool":
            l = self._alloc_temp("bool"); self.cmds.append(f"scoreboard players set {l} ae_int {1 if node.value else 0}"); return ("bool", l)
        if node.lit_type == "string":
            l = self._alloc_temp("string"); safe = node.value.replace('"', '\\"')
            self.cmds.append(f'data modify storage {self.current_ns}:data {l} set value "{safe}"'); return ("string", l)

    def visit_FormatString(self, node):
        s = ""
        for p in node.parts:
            if isinstance(p, str): s += p
            elif isinstance(p, Literal): s += str(p.value)
            else: raise CodegenError("Complex format strings not supported in MVP", node.line, node.col)
        l = self._alloc_temp("string"); safe = s.replace('"', '\\"')
        self.cmds.append(f'data modify storage {self.current_ns}:data {l} set value "{safe}"')
        return ("string", l)

    def visit_Identifier(self, node):
        v = self._lookup(node.name)
        if not v: raise CodegenError(f"Undeclared '{node.name}'", node.line, node.col)
        return (v["type"], v["loc"])

    def visit_BinaryOp(self, node):
        lt, ll = node.left.accept(self); rt, rl = node.right.accept(self)
        l_obj = self._get_obj(node.left)
        r_obj = self._get_obj(node.right)
        res = self._alloc_temp(lt)
        if node.op in ['+', '-', '*', '/', '%']:
            self.cmds.append(f"scoreboard players operation {res} ae_int = {ll} {l_obj}")
            ops = {'+': '+=', '-': '-=', '*': '*=', '/': '/=', '%': '%='}
            self.cmds.append(f"scoreboard players operation {res} ae_int {ops[node.op]} {rl} {r_obj}")
            return ("int", res)
        elif node.op in ['==', '!=', '<', '>', '<=', '>=']:
            self.cmds.append(f"scoreboard players set {res} ae_int 0")
            if node.op == '!=': self.cmds.append(f"execute unless score {ll} {l_obj} = {rl} {r_obj} run scoreboard players set {res} ae_int 1")
            else: self.cmds.append(f"execute if score {ll} {l_obj} {node.op} {rl} {r_obj} run scoreboard players set {res} ae_int 1")
            return ("bool", res)
        elif node.op in ['&&', '||']:
            self.cmds.append(f"scoreboard players operation {res} ae_int = {ll} {l_obj}")
            if node.op == '&&': self.cmds.append(f"scoreboard players operation {res} ae_int *= {rl} {r_obj}")
            else:
                self.cmds.append(f"scoreboard players operation {res} ae_int += {rl} {r_obj}")
                self.cmds.append(f"execute if score {res} ae_int matches 2.. run scoreboard players set {res} ae_int 1")
            return ("bool", res)

    def visit_FunctionCall(self, node):
        name = node.name
        kwargs = node.kwargs
        
        def get_kwarg(key, default):
            if key in kwargs: return kwargs[key]
            if isinstance(default, tuple): return TupleLiteral(0, 0, [Literal(0,0,v,"int") for v in default])
            if isinstance(default, str): return Literal(0,0,default,"string")
            if isinstance(default, bool): return Literal(0,0,default,"bool")
            if isinstance(default, int): return Literal(0,0,default,"int")
            
        def lit_to_str(n):
            if isinstance(n, Literal): 
                if n.lit_type == "bool": return "true" if n.value else "false"
                return str(n.value)
            if isinstance(n, TupleLiteral): return " ".join(lit_to_str(e) for e in n.elements)
            raise CodegenError(f"Command '{name}' requires literal arguments for MVP.", n.line, n.col)
            
        if name == "say":
            if isinstance(node.args[0], Literal):
                self.cmds.append(f'tellraw @a {{"text":"{node.args[0].value}"}}')
            else:
                t, l = node.args[0].accept(self)
                if t == "string": self.cmds.append(f'tellraw @a {{"storage":"{self.current_ns}:data","nbt":"{l}","interpret":true}}')
                else: self.cmds.append(f'tellraw @a {{"score":{{"name":"{l}","objective":"ae_int"}}}}')
            return None
            
        if name == "give":
            target = lit_to_str(node.args[0])
            item = lit_to_str(node.args[1])
            count = lit_to_str(get_kwarg("count", 1))
            self.cmds.append(f"give {target} {item} {count}")
            return None
            
        if name == "summon":
            entity = lit_to_str(node.args[0])
            at = lit_to_str(get_kwarg("at", (0,0,0)))
            nbt = lit_to_str(get_kwarg("nbt", ""))
            cmd = f"summon {entity} {at}"
            if nbt: cmd += f" {nbt}"
            self.cmds.append(cmd)
            return None
            
        if name == "tp":
            target = lit_to_str(node.args[0])
            at = lit_to_str(get_kwarg("at", (0,0,0)))
            self.cmds.append(f"tp {target} {at}")
            return None
            
        if name == "particle":
            p_type = lit_to_str(node.args[0])
            at = lit_to_str(get_kwarg("at", (0,0,0)))
            delta = lit_to_str(get_kwarg("delta", (0,0,0)))
            speed = lit_to_str(get_kwarg("speed", 0))
            count = lit_to_str(get_kwarg("count", 1))
            mode = lit_to_str(get_kwarg("mode", "normal"))
            self.cmds.append(f"particle {p_type} {at} {delta} {speed} {count} {mode}")
            return None
            
        if name == "setblock":
            at = lit_to_str(get_kwarg("at", (0,0,0)))
            block = lit_to_str(node.args[0])
            mode = lit_to_str(get_kwarg("mode", "replace"))
            self.cmds.append(f"setblock {at} {block} {mode}")
            return None
            
        if name == "fill":
            from_ = lit_to_str(get_kwarg("from", (0,0,0)))
            to = lit_to_str(get_kwarg("to", (0,0,0)))
            block = lit_to_str(node.args[0])
            mode = lit_to_str(get_kwarg("mode", "replace"))
            self.cmds.append(f"fill {from_} {to} {block} {mode}")
            return None
            
        if name == "effect":
            target = lit_to_str(node.args[0])
            eff_type = lit_to_str(node.args[1])
            duration = lit_to_str(get_kwarg("duration", 30))
            amplifier = lit_to_str(get_kwarg("amplifier", 0))
            particles = lit_to_str(get_kwarg("particles", True))
            self.cmds.append(f"effect give {target} {eff_type} {duration} {amplifier} {particles}")
            return None
            
        if name == "kill":
            target = lit_to_str(node.args[0]) if node.args else "@e"
            self.cmds.append(f"kill {target}")
            return None
            
        if name == "run":
            cmd_str_node = node.args[0]
            if not isinstance(cmd_str_node, Literal) or cmd_str_node.lit_type != "string":
                raise CodegenError("run() expects a string literal.", node.line, node.col)
                
            cmd_str = cmd_str_node.value
            matches = re.findall(r'\{([a-zA-Z0-9_]+)\}', cmd_str)
            
            if not matches:
                self.cmds.append(cmd_str)
                return None
                
            macro_id = self.mac_c
            self.mac_c += 1
            macro_name = f"macro_run_{macro_id}"
            full_macro_name = f"{self.current_ns}:{macro_name}"
            
            macro_data_str = []
            
            for var_name in matches:
                v = self._lookup(var_name)
                if not v: raise CodegenError(f"Undeclared variable '{var_name}' in run() string.", node.line, node.col)
                
                if v["type"] in ["int", "bool"]:
                    self.cmds.append(f"execute store storage {self.current_ns}:data macro_{var_name} int 1 run scoreboard players get {v['loc']} {v['objective']}")
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
            macro_cmd = '$' + macro_cmd
            
            self.cmds.append(macro_cmd)
            self.ir[full_macro_name] = self.cmds
            self.cmds = old_cmds
            return None
            
        args = [a.accept(self) for a in node.args]
        for i, (t, l) in enumerate(args):
            obj = self._get_obj(node.args[i])
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation arg_{i} ae_int = {l} {obj}")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data arg{i} set from storage {self.current_ns}:data {l}")
        
        self.cmds.append(f"function {self.current_ns}:{node.name}")
        return None

    def visit_MethodCall(self, node):
        obj_path = self._get_path(node.obj)
        obj_type = node.obj.inferred_type if hasattr(node.obj, 'inferred_type') else "Entity"
        
        self.cmds.append(f'data modify storage {self.current_ns}:data macro_obj_path set value "{obj_path}"')
        args = [a.accept(self) for a in node.args]
        for i, (t, l) in enumerate(args):
            obj = self._get_obj(node.args[i])
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation arg_{i} ae_int = {l} {obj}")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data arg{i} set from storage {self.current_ns}:data {l}")
            
        self.cmds.append(f"function {self.current_ns}:{obj_type}_{node.method} with storage {self.current_ns}:data {{macro_obj_path:'{obj_path}'}}")
        return None