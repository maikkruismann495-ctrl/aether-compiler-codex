# src/aether/optimizer_ir.py

import re
from typing import Dict, List, Set

class IROptimizer:
    def __init__(self, ir: Dict[str, List[str]]):
        self.ir = ir

    def optimize(self) -> Dict[str, List[str]]:
        optimized_ir = {}
        for f, cmds in self.ir.items():
            if "load.json" in f or "tick.json" in f:
                optimized_ir[f] = cmds
                continue
            optimized_ir[f] = self._dce(cmds)
        return self._remove_unused_functions(optimized_ir)

    def _dce(self, cmds: List[str]) -> List[str]:
        used_s: Set[str] = set()
        used_d: Set[str] = set()
        s_re = re.compile(r'[a-zA-Z0-9_]+(?=\s+ae_int)')
        d_re = re.compile(r'[a-zA-Z0-9_\-\.]+:data ([a-zA-Z0-9_\.]+)')
        for c in cmds:
            if c.startswith("scoreboard players set") or (c.startswith("scoreboard players operation") and " = " in c):
                parts = c.split(" = ")
                if len(parts) > 1: used_s.update(s_re.findall(parts[1]))
            elif c.startswith("data modify storage ") and " set " in c:
                if "set from storage" in c:
                    m = d_re.findall(c)
                    if len(m) > 1: used_d.add(m[1])
            else:
                used_s.update(s_re.findall(c))
                used_d.update(d_re.findall(c))
        opt = []
        for c in cmds:
            dead = False
            if c.startswith("scoreboard players set") or c.startswith("scoreboard players operation"):
                m = s_re.match(c.split(" ")[2] if "set" in c else c.split(" ")[3])
                if m and m.group(0) not in used_s: dead = True
            elif c.startswith("data modify storage "):
                m = d_re.match(c)
                if m and m.group(1) not in used_d: dead = True
            if not dead: opt.append(c)
        return opt

    def _remove_unused_functions(self, ir: Dict[str, List[str]]) -> Dict[str, List[str]]:
        called: Set[str] = set()
        if "minecraft:tags/functions/load.json" in ir:
            called.update(ir["minecraft:tags/functions/load.json"])
        if "minecraft:tags/functions/tick.json" in ir:
            called.update(ir["minecraft:tags/functions/tick.json"])
        func_re = re.compile(r'function\s+([a-zA-Z0-9_:\/]+)')
        for f, cmds in ir.items():
            if "load.json" in f or "tick.json" in f: continue
            for c in cmds:
                m = func_re.search(c)
                if m:
                    called_func = m.group(1).split(" with")[0]
                    called.add(called_func)
        macro_call_re = re.compile(r'\$\w+\s+([a-zA-Z0-9_:\/]+)')
        for f, cmds in ir.items():
            if "load.json" in f or "tick.json" in f: continue
            for c in cmds:
                if c.startswith("$"):
                    m = macro_call_re.search(c)
                    if m: called.add(m.group(1))
        final_ir = {}
        for f, cmds in ir.items():
            if "load.json" in f or "tick.json" in f:
                final_ir[f] = [c for c in cmds if c in called]
            elif f in called:
                final_ir[f] = cmds
        return final_ir
