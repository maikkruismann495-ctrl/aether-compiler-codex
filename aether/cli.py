# aether/cli.py

import argparse, os, sys, re, glob, time
from typing import Dict, List
from .lexer import Lexer
from .parser import Parser
from .semantic import SemanticAnalyzer
from .type_checker import TypeChecker
from .optimizer import Optimizer
from .codegen import CodeGenerator
from .optimizer_ir import IROptimizer
from .datapack_builder import DatapackBuilder
from .diagnostics import DiagnosticEngine
from .errors import AetherError

def preprocess_imports(file_path: str, seen: set) -> str:
    if file_path in seen: return ""
    seen.add(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f: content = f.read()
    except IOError as e:
        print(f"[IOError] {e}", file=sys.stderr); sys.exit(1)
    def rep(m):
        p = os.path.join(os.path.dirname(file_path), m.group(1))
        if os.path.isfile(p):
            return preprocess_imports(p, seen)
        print(f"[Error] Import not found: {p}", file=sys.stderr); sys.exit(1)
    return re.sub(r'^\s*import\s+"([^"]+\.ae)"\s*', rep, content, flags=re.MULTILINE)

def extract_namespace(src: str) -> str:
    m = re.search(r'^\s*namespace\s+([a-zA-Z0-9_]+)', src, re.MULTILINE)
    return m.group(1) if m else "aether"

def run_compilation(sp: str, out: str, mdd: str) -> bool:
    try:
        if os.path.isdir(sp):
            main_file = os.path.join(sp, "main.ae")
            if not os.path.exists(main_file):
                print(f"[Error] Entry point 'main.ae' not found in directory: {sp}", file=sys.stderr)
                return False
            src = preprocess_imports(main_file, set())
        elif os.path.isfile(sp):
            if not sp.endswith("main.ae"):
                print("[Warning] Compiling a file not named 'main.ae'. It will be treated as the entry point.", file=sys.stderr)
            src = preprocess_imports(sp, set())
        else:
            print(f"[Error] Path not found: {sp}", file=sys.stderr)
            return False
            
        ns = extract_namespace(src)
        
        # Initialize the Diagnostics Engine
        filename = os.path.basename(sp if os.path.isfile(sp) else os.path.join(sp, "main.ae"))
        engine = DiagnosticEngine(filename, src)
        
        # Pipeline
        lexer = Lexer(src, engine)
        tokens = lexer.tokenize()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        parser = Parser(tokens, engine)
        ast = parser.parse()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        sem = SemanticAnalyzer(ast, engine)
        ast = sem.analyze()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        tc = TypeChecker(ast, sem.functions, sem.classes, engine)
        ast = tc.check()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        opt = Optimizer(ast, engine)
        ast = opt.optimize()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        cg = CodeGenerator(ast, engine, root_ns=ns)
        ir = cg.generate()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        ir_opt = IROptimizer(ir)
        ir = ir_opt.optimize()
        
        # Print any warnings generated during compilation
        if engine.diagnostics:
            engine.print_diagnostics()
            
        builder = DatapackBuilder(ir, out, ns, mdd)
        builder.build()
        return True
        
    except AetherError as e:
        # This catches hard crashes that bypass the engine (should be rare now)
        print(e.diag.format(), file=sys.stderr)
        return False
    except Exception as e:
        import traceback
        print(f"\n[Internal Compiler Error] {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

def main() -> int:
    p = argparse.ArgumentParser(prog="aether", description="Aether Compiler v2.0 for MC 1.21.11")
    p.add_argument("source", help="Path to main.ae file or project directory")
    p.add_argument("-o", "--output", default=None, help="Output directory for datapack")
    p.add_argument("-w", "--watch", action="store_true", help="Watch for changes and recompile automatically")
    args = p.parse_args()
    
    sp = os.path.abspath(args.source)
    out = os.path.abspath(args.output) if args.output else os.path.abspath("aether_datapack")
    mdd = os.path.join(sp, "data") if os.path.isdir(sp) and os.path.isdir(os.path.join(sp, "data")) else None
    
    if args.watch:
        print("[*] Initial compilation...")
        if run_compilation(sp, out, mdd): print(f"[✓] Datapack generated at: {out}")
        print(f"[*] Watching for changes in '{sp}'... (Press Ctrl+C to stop)")
        
        last_mtimes = {}
        
        def get_files():
            if os.path.isdir(sp): return set(glob.glob(os.path.join(sp, "**", "*.ae"), recursive=True))
            elif os.path.isfile(sp): return {sp}
            return set()
            
        for f in get_files():
            try: last_mtimes[f] = os.path.getmtime(f)
            except: pass
                
        try:
            while True:
                time.sleep(0.5)
                changed = False
                for f in get_files():
                    try:
                        mtime = os.path.getmtime(f)
                        if f not in last_mtimes or last_mtimes[f] != mtime:
                            changed = True; last_mtimes[f] = mtime
                    except: pass
                if changed:
                    print("\n[*] Change detected. Recompiling...")
                    if run_compilation(sp, out, mdd): print(f"[✓] Datapack regenerated at: {out}")
                    print("[*] Watching for changes... (Press Ctrl+C to stop)")
        except KeyboardInterrupt:
            print("\n[*] Stopped watching.")
            return 0
    else:
        print("[*] Compiling Aether source...")
        if run_compilation(sp, out, mdd):
            print(f"[✓] Success! Datapack generated at: {out}")
            return 0
        return 1

if __name__ == "__main__":
    sys.exit(main())