# aether/cli.py
import argparse, os, sys, re, glob, time
from typing import Optional, Set
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

IMPORT_RE = re.compile(r'^\s*(?:use|import)\s+["\']([^"\']+\.ae)["\']\s*;?\s*(?://.*)?$')

class ImportResolutionError(Exception):
    def __init__(self, message: str, stack):
        self.message = message
        self.stack = stack
        super().__init__(message)

    def format(self) -> str:
        if not self.stack:
            return f"[ImportError] {self.message}"
        stack = "\n".join(f"  -> {p}" for p in self.stack)
        return f"[ImportError] {self.message}\nImport stack:\n{stack}"

def preprocess_imports(file_path: str, seen: Optional[Set[str]] = None, stack=None) -> str:
    file_path = os.path.abspath(file_path)
    seen = seen if seen is not None else set()
    stack = stack if stack is not None else []

    if file_path in stack:
        raise ImportResolutionError("Circular import detected", stack + [file_path])
    if file_path in seen:
        return ""

    seen.add(file_path)
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f: content = f.read()
    except IOError as e:
        raise ImportResolutionError(str(e), stack + [file_path])

    output = []
    for line in content.splitlines(keepends=True):
        match = IMPORT_RE.match(line)
        if not match:
            output.append(line)
            continue

        import_path = os.path.abspath(os.path.join(os.path.dirname(file_path), match.group(1)))
        if not os.path.isfile(import_path):
            raise ImportResolutionError(f"Import not found: {import_path}", stack + [file_path])

        imported = preprocess_imports(import_path, seen, stack + [file_path])
        output.append(imported)
        if imported and not imported.endswith("\n"):
            output.append("\n")

    return "".join(output)

def extract_namespace(src: str) -> str:
    patterns = [
        r'^\s*namespace\s*\(\s*["\']?([a-zA-Z0-9_\-\.]+)["\']?\s*\)\s*;?',
        r'^\s*namespace\s+["\']?([a-zA-Z0-9_\-\.]+)["\']?\s*;?',
    ]
    for pattern in patterns:
        m = re.search(pattern, src, re.MULTILINE)
        if m:
            return m.group(1)
    return "aether"

def run_compilation(sp: str, out: str, mdd: Optional[str]) -> bool:
    try:
        if os.path.isdir(sp):
            main_file = os.path.join(sp, "main.ae")
            if not os.path.exists(main_file):
                print(f"[Error] Entry point 'main.ae' not found in directory: {sp}", file=sys.stderr)
                return False
            src = preprocess_imports(main_file)
        elif os.path.isfile(sp):
            if not sp.endswith("main.ae"):
                print("[Warning] Compiling a file not named 'main.ae'. It will be treated as the entry point.", file=sys.stderr)
            src = preprocess_imports(sp)
        else:
            print(f"[Error] Path not found: {sp}", file=sys.stderr)
            return False
            
        ns = extract_namespace(src)
        
        filename = os.path.basename(sp if os.path.isfile(sp) else os.path.join(sp, "main.ae"))
        engine = DiagnosticEngine(filename, src)
        
        lexer = Lexer(src, engine)
        tokens = lexer.tokenize()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        parser = Parser(tokens, engine)
        ast = parser.parse()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        sem = SemanticAnalyzer(ast, engine)
        ast = sem.analyze()
        if engine.has_errors: engine.print_diagnostics(); return False
        
        tc = TypeChecker(ast, sem.functions, engine)
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
        
        if engine.diagnostics:
            engine.print_diagnostics()
            
        builder = DatapackBuilder(ir, out, ns, mdd)
        builder.build()
        return True
        
    except ImportResolutionError as e:
        print(e.format(), file=sys.stderr)
        return False
    except AetherError as e:
        print(e.diag.format(), file=sys.stderr)
        return False
    except Exception as e:
        import traceback
        print(f"\n[Internal Compiler Error] {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False

def main() -> int:
    p = argparse.ArgumentParser(prog="aether", description="Aether Compiler v3.1 (JavaScript/Bolt-style) for Minecraft 1.21+ datapacks")
    p.add_argument("source", help="Path to main.ae file or project directory")
    p.add_argument("-o", "--output", default=None, help="Output directory for datapack")
    p.add_argument("-w", "--watch", action="store_true", help="Watch for changes and recompile automatically")
    args = p.parse_args()
    
    sp = os.path.abspath(args.source)
    out = os.path.abspath(args.output) if args.output else os.path.abspath("aether_datapack")
    project_dir = sp if os.path.isdir(sp) else os.path.dirname(sp)
    data_dir = os.path.join(project_dir, "data")
    mdd = data_dir if os.path.isdir(data_dir) else None
    
    if args.watch:
        print("[*] Initial compilation...")
        if run_compilation(sp, out, mdd): print(f"[OK] Datapack generated at: {out}")
        print(f"[*] Watching for changes in '{sp}'... (Press Ctrl+C to stop)")
        
        last_mtimes = {}
        
        def get_files():
            files = set()
            if os.path.isdir(sp):
                files.update(glob.glob(os.path.join(sp, "**", "*.ae"), recursive=True))
            elif os.path.isfile(sp):
                files.update(glob.glob(os.path.join(project_dir, "**", "*.ae"), recursive=True))

            if mdd and os.path.isdir(mdd):
                for root, _, names in os.walk(mdd):
                    for name in names:
                        files.add(os.path.join(root, name))
            return files
            
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
                    if run_compilation(sp, out, mdd): print(f"[OK] Datapack regenerated at: {out}")
                    print("[*] Watching for changes... (Press Ctrl+C to stop)")
        except KeyboardInterrupt:
            print("\n[*] Stopped watching.")
            return 0
    else:
        print("[*] Compiling Aether source...")
        if run_compilation(sp, out, mdd):
            print(f"[OK] Success! Datapack generated at: {out}")
            return 0
        return 1

if __name__ == "__main__":
    sys.exit(main())
