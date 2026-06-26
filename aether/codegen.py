# src/aether/codegen.py

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

    def _finalize_function(self, full_name: str, cmds: List[str]) -> List[str]:
        if not any("__WAIT__(" in c for c in cmds):
            return cmds
            
        final_cmds = []
        cont_idx = 0
        current_cmds = cmds
        
        while True:
            wait_idx = -1
            for i, c in enumerate(current_cmds):
                if c.startswith("__WAIT__("):
                    wait_idx = i
                    break
            
            if wait_idx != -1:
                ticks = current_cmds[wait_idx].split("(")[1].split(")")[0]
                final_cmds.extend(current_cmds[:wait_idx])
                final_cmds.append(f"schedule function {full_name}__cont_{cont_idx} {ticks}t")
                final_cmds.append("return 1")
                
                cont_name = f"{full_name}__cont_{cont_idx}"
                current_cmds = current_cmds[wait_idx+1:]
                self.ir[cont_name] = self._finalize_function(cont_name, current_cmds)
                return final_cmds
            else:
                final_cmds.extend(current_cmds)
                return final_cmds

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
            if not v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared '{node.name}'", node.line, node.col)
                return "unknown"
            return v["loc"]
        if isinstance(node, MemberAccess):
            base = "self" if isinstance(node.obj, Identifier) and node.obj.name == "self" else self._get_path(node.obj)
            if isinstance(node.obj, Identifier) and node.obj.name == "self" and self.class_context:
                return f"instances.{self.class_context}_$(obj_id).{node.member}"
            return f"{base}.{node.member}"
        self.engine.report(ErrorCodes.INVALID_OPERATION, Severity.ERROR, "Invalid target", node.line, node.col)
        return "unknown"

    def _get_obj(self, node):
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
        self.ir[full] = self._finalize_function(full, self.cmds)
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
        self.ir[fif] = self._finalize_function(fif, self.cmds)
        self.cmds = p
        self.cmds.append(f"execute if score {l} {obj} matches 1 run function {fif}")
        if node.else_stmt:
            efn = f"branch_else_{self.temp_c}"; self.temp_c += 1
            fel = f"{self.current_ns}:{efn}"
            p = self.cmds; self.cmds = []
            node.else_stmt.accept(self)
            self.ir[fel] = self._finalize_function(fel, self.cmds)
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
        else: self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "For loop bounds must be compile-time constants", node.line, node.col)

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
        self.ir[fw] = self._finalize_function(fw, self.cmds)
        self.cmds = []
        self.scopes.append({})
        node.body.accept(self)
        self.scopes.pop()
        self.ir[fb] = self._finalize_function(fb, self.cmds)
        self.cmds = p

    def visit_ExecuteStmt(self, node: ExecuteStmt):
        chain_str = ""
        for sub, sel_node in node.chain:
            if isinstance(sel_node, Literal):
                chain_str += f"{sub} {sel_node.value} "
            else:
                self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "Dynamic selectors in execute blocks not supported in MVP.", sel_node.line, sel_node.col)
                
        old_cmds = self.cmds
        self.cmds = []
        node.body.accept(self)
        body_cmds = self.cmds
        self.cmds = old_cmds
        
        for cmd in body_cmds:
            self.cmds.append(f"execute {chain_str}run {cmd}")

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

    def visit_DictLiteral(self, node: DictLiteral):
        nbt_str = self._dict_to_nbt(node.elements)
        l = self._alloc_temp("nbt")
        self.cmds.append(f'data modify storage {self.current_ns}:data {l} set value {nbt_str}')
        return ("nbt", l)

    def _dict_to_nbt(self, elements: Dict[str, ASTNode]) -> str:
        parts = []
        for k, v_node in elements.items():
            if isinstance(v_node, Literal):
                if v_node.lit_type == "string":
                    parts.append(f'{k}:"{v_node.value}"')
                elif v_node.lit_type == "int":
                    parts.append(f'{k}:{v_node.value}')
                elif v_node.lit_type == "bool":
                    parts.append(f'{k}:{"1b" if v_node.value else "0b"}')
            elif isinstance(v_node, DictLiteral):
                parts.append(f'{k}:{self._dict_to_nbt(v_node.elements)}')
        return "{" + ",".join(parts) + "}"

    def visit_FormatString(self, node):
        s = ""
        for p in node.parts:
            if isinstance(p, str): s += p
            elif isinstance(p, Literal): s += str(p.value)
            else: self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, "Complex format strings not supported in MVP", node.line, node.col)
        l = self._alloc_temp("string"); safe = s.replace('"', '\\"')
        self.cmds.append(f'data modify storage {self.current_ns}:data {l} set value "{safe}"')
        return ("string", l)

    def visit_Identifier(self, node):
        v = self._lookup(node.name)
        if not v:
            self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared '{node.name}'", node.line, node.col)
            return ("unknown", "unknown")
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
            self.engine.report(ErrorCodes.UNSUPPORTED_FEATURE, Severity.ERROR, f"Command '{name}' requires literal arguments for MVP.", n.line, n.col)
            return ""

        # BOLT-STYLE WAIT COROUTINE
        if name == "wait":
            if not isinstance(node.args[0], Literal) or node.args[0].lit_type != "int":
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "wait() requires a literal integer.", node.line, node.col)
                return None
            self.cmds.append(f"__WAIT__({node.args[0].value})")
            return None

        # BOLT-STYLE ENTITY WRAPPER
        if name == "entity":
            if not isinstance(node.args[0], Literal) or node.args[0].lit_type != "string":
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "entity() requires a literal string selector.", node.line, node.col)
                return None
            loc = self._alloc_var("entity", "Entity")
            self.scopes[-1][loc]["selector"] = node.args[0].value
            self.cmds.append(f'data modify storage {self.current_ns}:data {loc} set value "{node.args[0].value}"')
            return ("Entity", loc)
            
        if name == "say":
            arg = node.args[0]
            if isinstance(arg, FormatString):
                json_parts = []
                for p in arg.parts:
                    if isinstance(p, str):
                        if p: json_parts.append('{"text":"' + p.replace('"', '\\"') + '"}')
                    elif isinstance(p, Literal):
                        if p.lit_type == "bool": json_parts.append('{"text":"' + ("true" if p.value else "false") + '"}')
                        else: json_parts.append('{"text":"' + str(p.value) + '"}')
                    elif isinstance(p, Identifier):
                        v = self._lookup(p.name)
                        if not v:
                            self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{p.name}'", p.line, p.col)
                            continue
                        if v["type"] in ["int", "bool"]:
                            json_parts.append('{"score":{"name":"' + v['loc'] + '","objective":"' + v['objective'] + '"}}')
                        else:
                            json_parts.append('{"storage":"' + self.current_ns + ':data","nbt":"' + v['loc'] + '","interpret":true}')
                tellraw_json = "[" + ",".join(json_parts) + "]"
                self.cmds.append(f"tellraw @a {tellraw_json}")
                return None
                
            elif isinstance(arg, Literal) and arg.lit_type == "string":
                matches = re.findall(r'\{([a-zA-Z0-9_]+)\}', arg.value)
                if matches:
                    parts = re.split(r'\{[a-zA-Z0-9_]+\}', arg.value)
                    json_parts = []
                    for i, part in enumerate(parts):
                        if part: json_parts.append('{"text":"' + part.replace('"', '\\"') + '"}')
                        if i < len(matches):
                            var_name = matches[i]
                            v = self._lookup(var_name)
                            if not v:
                                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{var_name}'", node.line, node.col)
                                continue
                            if v["type"] in ["int", "bool"]:
                                json_parts.append('{"score":{"name":"' + v['loc'] + '","objective":"' + v['objective'] + '"}}')
                            else:
                                json_parts.append('{"storage":"' + self.current_ns + ':data","nbt":"' + v['loc'] + '","interpret":true}')
                    tellraw_json = "[" + ",".join(json_parts) + "]"
                    self.cmds.append(f"tellraw @a {tellraw_json}")
                else:
                    self.cmds.append(f'tellraw @a {{"text":"{arg.value}"}}')
                return None
            else:
                t, l = arg.accept(self)
                if t == "string": self.cmds.append(f'tellraw @a {{"storage":"{self.current_ns}:data","nbt":"{l}","interpret":true}}')
                else: self.cmds.append(f'tellraw @a {{"score":{{"name":"{l}","objective":"ae_int"}}}}')
                return None

        # --- PRODUCTION-READY NATIVE COMMAND DSL ---
        
        if name == "give":
            target = lit_to_str(node.args[0])
            item = lit_to_str(node.args[1])
            count = lit_to_str(get_kwarg("count", 1))
            self.cmds.append(f"give {target} {item} {count}")
            return None

        if name == "summon":
            entity = lit_to_str(node.args[0])
            at = lit_to_str(get_kwarg("at", (0,0,0)))
            nbt_node = get_kwarg("nbt", "")
            if isinstance(nbt_node, DictLiteral): nbt = self._dict_to_nbt(nbt_node.elements)
            else: nbt = lit_to_str(nbt_node)
            cmd = f"summon {entity} {at}"
            if nbt: cmd += f" {nbt}"
            self.cmds.append(cmd)
            return None

        if name == "tp" or name == "teleport":
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
            action = lit_to_str(node.args[0])
            if action == "give":
                target = lit_to_str(node.args[1])
                eff_type = lit_to_str(node.args[2])
                duration = lit_to_str(get_kwarg("duration", 30))
                amplifier = lit_to_str(get_kwarg("amplifier", 0))
                particles = lit_to_str(get_kwarg("particles", True))
                self.cmds.append(f"effect give {target} {eff_type} {duration} {amplifier} {particles}")
            else:
                target = lit_to_str(node.args[1])
                self.cmds.append(f"effect clear {target}")
            return None

        if name == "kill":
            target = lit_to_str(node.args[0]) if node.args else "@e"
            self.cmds.append(f"kill {target}")
            return None

        if name == "damage":
            target = lit_to_str(node.args[0])
            amount = lit_to_str(node.args[1])
            dmg_type = lit_to_str(get_kwarg("type", "minecraft:generic"))
            cmd = f"damage {target} {amount} {dmg_type}"
            if "at" in kwargs: cmd += f" at {lit_to_str(kwargs['at'])}"
            if "by" in kwargs: cmd += f" by {lit_to_str(kwargs['by'])}"
            if "from" in kwargs: cmd += f" from {lit_to_str(kwargs['from'])}"
            self.cmds.append(cmd)
            return None

        if name == "random":
            action = lit_to_str(node.args[0])
            range_ = lit_to_str(node.args[1])
            target = lit_to_str(get_kwarg("target", "@s"))
            self.cmds.append(f"random {action} {range_} {target}")
            return None

        if name == "tag":
            target = lit_to_str(node.args[0])
            action = lit_to_str(node.args[1])
            tag_name = lit_to_str(node.args[2])
            self.cmds.append(f"tag {target} {action} {tag_name}")
            return None

        if name == "team":
            action = lit_to_str(node.args[0])
            team_name = lit_to_str(node.args[1])
            members = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            self.cmds.append(f"team {action} {team_name} {members}".strip())
            return None

        if name == "time":
            action = lit_to_str(node.args[0])
            value = lit_to_str(node.args[1])
            self.cmds.append(f"time {action} {value}")
            return None

        if name == "weather":
            action = lit_to_str(node.args[0])
            duration = lit_to_str(get_kwarg("duration", 600))
            self.cmds.append(f"weather {action} {duration}")
            return None

        if name == "xp" or name == "experience":
            target = lit_to_str(node.args[0])
            amount = lit_to_str(node.args[1])
            type_ = lit_to_str(get_kwarg("type", "levels"))
            self.cmds.append(f"xp add {target} {amount} {type_}")
            return None

        if name == "title":
            target = lit_to_str(node.args[0])
            action = lit_to_str(node.args[1])
            if action in ["title", "subtitle", "actionbar"]:
                text = lit_to_str(node.args[2])
                self.cmds.append(f'title {target} {action} {{"text":"{text}"}}')
            else:
                self.cmds.append(f"title {target} {action}")
            return None

        if name == "enchant":
            target = lit_to_str(node.args[0])
            ench = lit_to_str(node.args[1])
            level = lit_to_str(get_kwarg("level", 1))
            self.cmds.append(f"enchant {target} {ench} {level}")
            return None

        if name == "attribute":
            target = lit_to_str(node.args[0])
            attr = lit_to_str(node.args[1])
            action = lit_to_str(node.args[2])
            value = lit_to_str(node.args[3]) if len(node.args) > 3 else ""
            self.cmds.append(f"attribute {target} {attr} {action} {value}".strip())
            return None

        if name == "clear":
            target = lit_to_str(node.args[0]) if node.args else "@a"
            item = lit_to_str(node.args[1]) if len(node.args) > 1 else ""
            count = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            self.cmds.append(f"clear {target} {item} {count}".strip())
            return None

        if name == "clone":
            from_ = lit_to_str(get_kwarg("from", (0,0,0)))
            to = lit_to_str(get_kwarg("to", (0,0,0)))
            dest = lit_to_str(get_kwarg("dest", (0,0,0)))
            mode = lit_to_str(get_kwarg("mode", "replace"))
            self.cmds.append(f"clone {from_} {to} {dest} {mode}")
            return None

        if name == "bossbar":
            action = lit_to_str(node.args[0])
            id_ = lit_to_str(node.args[1])
            extra = " ".join([lit_to_str(a) for a in node.args[2:]])
            self.cmds.append(f"bossbar {action} {id_} {extra}".strip())
            return None

        if name == "advancement":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1])
            criterion = lit_to_str(node.args[2])
            adv = lit_to_str(node.args[3]) if len(node.args) > 3 else ""
            self.cmds.append(f"advancement {action} {target} {criterion} {adv}".strip())
            return None

        if name == "gamemode":
            mode = lit_to_str(node.args[0])
            target = lit_to_str(get_kwarg("target", "@s"))
            self.cmds.append(f"gamemode {mode} {target}")
            return None

        if name == "gamerule":
            rule = lit_to_str(node.args[0])
            value = lit_to_str(node.args[1]) if len(node.args) > 1 else ""
            self.cmds.append(f"gamerule {rule} {value}".strip())
            return None

        if name == "item":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1])
            slot = lit_to_str(node.args[2])
            item = lit_to_str(node.args[3]) if len(node.args) > 3 else ""
            count = lit_to_str(get_kwarg("count", 1))
            self.cmds.append(f"item {action} {target} {slot} {item} {count}".strip())
            return None

        if name == "schedule":
            action = lit_to_str(node.args[0])
            func = lit_to_str(node.args[1])
            time = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            mode = lit_to_str(get_kwarg("mode", "replace"))
            self.cmds.append(f"schedule {action} {func} {time} {mode}".strip())
            return None

        if name == "scoreboard":
            action = lit_to_str(node.args[0])
            sub = lit_to_str(node.args[1])
            extra = " ".join([lit_to_str(a) for a in node.args[2:]])
            self.cmds.append(f"scoreboard {action} {sub} {extra}".strip())
            return None

        if name == "spreadplayers":
            center = lit_to_str(get_kwarg("center", (0, 0)))
            spread = lit_to_str(get_kwarg("spread", (0, 0)))
            max_height = lit_to_str(get_kwarg("max_height", 256))
            respect_teams = lit_to_str(get_kwarg("respect_teams", True))
            target = lit_to_str(node.args[0])
            self.cmds.append(f"spreadplayers {center} {spread} {max_height} {respect_teams} {target}")
            return None

        if name == "stopsound":
            target = lit_to_str(node.args[0])
            sound = lit_to_str(node.args[1]) if len(node.args) > 1 else ""
            self.cmds.append(f"stopsound {target} * {sound}".strip())
            return None

        if name == "worldborder":
            action = lit_to_str(node.args[0])
            extra = " ".join([lit_to_str(a) for a in node.args[1:]])
            self.cmds.append(f"worldborder {action} {extra}".strip())
            return None

        if name == "recipe":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1])
            recipe = lit_to_str(node.args[2]) if len(node.args) > 2 else "*"
            self.cmds.append(f"recipe {action} {target} {recipe}")
            return None

        if name == "forceload":
            action = lit_to_str(node.args[0])
            pos = lit_to_str(node.args[1]) if len(node.args) > 1 else ""
            self.cmds.append(f"forceload {action} {pos}".strip())
            return None

        if name == "setworldspawn":
            pos = lit_to_str(get_kwarg("pos", (0, 0, 0)))
            self.cmds.append(f"setworldspawn {pos}")
            return None

        if name == "spawnpoint":
            target = lit_to_str(node.args[0]) if node.args else "@s"
            pos = lit_to_str(get_kwarg("pos", (0, 0, 0)))
            self.cmds.append(f"spawnpoint {target} {pos}")
            return None

        if name == "spectate":
            target = lit_to_str(node.args[0]) if node.args else "@s"
            player = lit_to_str(get_kwarg("player", "@s"))
            self.cmds.append(f"spectate {target} {player}")
            return None

        if name == "data":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1])
            path = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            self.cmds.append(f"data {action} {target} {path}".strip())
            return None

        if name == "ride":
            target = lit_to_str(node.args[0])
            action = lit_to_str(node.args[1])
            vehicle = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            self.cmds.append(f"ride {target} {action} {vehicle}".strip())
            return None

        if name == "loot":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1])
            source = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            self.cmds.append(f"loot {action} {target} {source}".strip())
            return None

        if name == "locate":
            structure = lit_to_str(node.args[0])
            self.cmds.append(f"locate structure {structure}")
            return None

        if name == "fillbiome":
            from_ = lit_to_str(get_kwarg("from", (0,0,0)))
            to = lit_to_str(get_kwarg("to", (0,0,0)))
            biome = lit_to_str(node.args[0])
            self.cmds.append(f"fillbiome {from_} {to} {biome}")
            return None

        if name == "place":
            feature = lit_to_str(node.args[0])
            pos = lit_to_str(get_kwarg("pos", (0, 0, 0)))
            self.cmds.append(f"place feature {feature} {pos}")
            return None

        if name == "trigger":
            objective = lit_to_str(node.args[0])
            action = lit_to_str(get_kwarg("action", "set"))
            value = lit_to_str(get_kwarg("value", 0))
            self.cmds.append(f"trigger {objective} {action} {value}")
            return None

        if name == "defaultgamemode":
            mode = lit_to_str(node.args[0])
            self.cmds.append(f"defaultgamemode {mode}")
            return None

        if name == "difficulty":
            level = lit_to_str(node.args[0])
            self.cmds.append(f"difficulty {level}")
            return None

        if name == "dialog":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1])
            body = lit_to_str(node.args[2]) if len(node.args) > 2 else ""
            self.cmds.append(f"dialog {action} {target} {body}".strip())
            return None

        if name == "transfer":
            server = lit_to_str(node.args[0])
            port = lit_to_str(get_kwarg("port", 25565))
            self.cmds.append(f"transfer {server} {port}")
            return None

        if name == "setidletimeout":
            minutes = lit_to_str(node.args[0])
            self.cmds.append(f"setidletimeout {minutes}")
            return None

        if name == "whitelist":
            action = lit_to_str(node.args[0])
            target = lit_to_str(node.args[1]) if len(node.args) > 1 else ""
            self.cmds.append(f"whitelist {action} {target}".strip())
            return None

        if name == "ban" or name == "ban-ip" or name == "pardon" or name == "pardon-ip" or name == "kick" or name == "op" or name == "deop":
            target = lit_to_str(node.args[0])
            reason = lit_to_str(node.args[1]) if len(node.args) > 1 else ""
            self.cmds.append(f"{name} {target} {reason}".strip())
            return None

        if name == "list" or name == "banlist" or name == "seed" or name == "reload" or name == "stop" or name == "publish" or name == "debug" or name == "perf" or name == "jfr" or name == "help" or name == "version" or name == "test" or name == "tick" or name == "me" or name == "teammsg" or name == "tm" or name == "tell" or name == "msg" or name == "w" or name == "waypoint":
            extra = " ".join([lit_to_str(a) for a in node.args])
            self.cmds.append(f"{name} {extra}".strip())
            return None

        if name == "run":
            cmd_str_node = node.args[0]
            if not isinstance(cmd_str_node, Literal) or cmd_str_node.lit_type != "string":
                self.engine.report(ErrorCodes.TYPE_MISMATCH, Severity.ERROR, "run() expects a string literal.", node.line, node.col)
                return None
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
                if not v:
                    self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, f"Undeclared variable '{var_name}' in run() string.", node.line, node.col)
                    continue
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
            
        # UNIVERSAL NATIVE COMMAND FALLBACK
        if f"{self.current_ns}:{node.name}" not in self.ir:
            vals = [lit_to_str(arg) for arg in node.args]
            self.cmds.append(f"{name} {' '.join(vals)}".strip())
            return None
            
        # USER FUNCTION CALL
        args = [a.accept(self) for a in node.args]
        for i, (t, l) in enumerate(args):
            obj = self._get_obj(node.args[i])
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation arg_{i} ae_int = {l} {obj}")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data arg{i} set from storage {self.current_ns}:data {l}")
        self.cmds.append(f"function {self.current_ns}:{node.name}")
        return None

    def visit_MethodCall(self, node: MethodCall):
        obj_type = node.obj.inferred_type if hasattr(node.obj, 'inferred_type') else "Entity"
        
        # BOLT-STYLE ENTITY OBJECT METHODS
        if obj_type == "Entity":
            v = self._lookup(node.obj.name)
            if not v or "selector" not in v:
                self.engine.report(ErrorCodes.UNDECLARED_VARIABLE, Severity.ERROR, "Entity variable not found or invalid.", node.line, node.col)
                return None
            sel = v["selector"]
            
            if node.method == "kill":
                self.cmds.append(f"kill {sel}")
            elif node.method == "tp":
                x = node.args[0].value if isinstance(node.args[0], Literal) else "~"
                y = node.args[1].value if isinstance(node.args[1], Literal) else "~"
                z = node.args[2].value if isinstance(node.args[2], Literal) else "~"
                self.cmds.append(f"tp {sel} {x} {y} {z}")
            elif node.method == "say":
                if isinstance(node.args[0], Literal):
                    self.cmds.append(f'tellraw @a {{"text":"[{sel}] {node.args[0].value}"}}')
            elif node.method == "set_nbt":
                if isinstance(node.args[0], DictLiteral):
                    nbt = self._dict_to_nbt(node.args[0].elements)
                    self.cmds.append(f"data merge entity {sel} {nbt}")
                elif isinstance(node.args[0], Literal):
                    self.cmds.append(f"data merge entity {sel} {node.args[0].value}")
            return None

        # Standard OOP method call
        obj_path = self._get_path(node.obj)
        self.cmds.append(f'data modify storage {self.current_ns}:data macro_obj_path set value "{obj_path}"')
        args = [a.accept(self) for a in node.args]
        for i, (t, l) in enumerate(args):
            obj = self._get_obj(node.args[i])
            if t in ["int", "bool"]: self.cmds.append(f"scoreboard players operation arg_{i} ae_int = {l} {obj}")
            else: self.cmds.append(f"data modify storage {self.current_ns}:data arg{i} set from storage {self.current_ns}:data {l}")
            
        self.cmds.append(f"function {self.current_ns}:{obj_type}_{node.method} with storage {self.current_ns}:data {{macro_obj_path:'{obj_path}'}}")
        return None