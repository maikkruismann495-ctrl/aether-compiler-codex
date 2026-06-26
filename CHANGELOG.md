# Changelog

All notable changes to the Aether programming language and compiler are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] - Production-Ready Command DSL

This release focuses on making Aether feel like writing raw Minecraft code by providing clean, typed wrappers for almost every command in the game.

### Added
- **Comprehensive Native Command DSL:** Added structured, keyword-argument wrappers for almost every vanilla Minecraft command, including `bossbar`, `attribute`, `damage`, `random`, `data`, `scoreboard`, `recipe`, `tag`, `team`, `time`, `weather`, `xp`, `ride`, `loot`, `place`, `fillbiome`, and many more.
- **Universal Fallback:** Any command without an explicit wrapper automatically formats function arguments into a raw vanilla command string, ensuring 100% game coverage.

### Fixed
- Fixed a critical `TypeError` in Python 3.14+ caused by a missing parenthesis on `auto` in the `TokenType` enum.

---

## [2.1.0] - The Bolt-Style Update

This release introduces massive quality-of-life features to Aether, bringing it closer to the "supercharged command language" feel of Bolt/Beet.

### Added
- **Execute Blocks:** Added native `execute as "@e" at "@s":` syntax that cleanly scopes commands to entities without raw `run()` strings.
- **Entity Wrapper:** Added the `Entity` type and `entity()` constructor. Selectors can now be manipulated as native objects (e.g., `target.tp(0, 100, 0)`, `target.kill()`).
- **Dict Literals (NBT):** Added `{}` syntax for NBT compounds. The compiler automatically serializes them to Minecraft NBT format for `summon()` etc.
- **`wait()` Coroutine:** Added the `wait(ticks)` function. It splits the current function into multiple `.mcfunction` files and uses `/schedule` to pause execution seamlessly.

### Changed
- Updated Lexer and Parser to handle the new `execute` blocks, `{}` dict literals, and `entity()` wrapper syntax.
- Updated Codegen with `_finalize_function` to handle `wait()` function splitting and `_dict_to_nbt` for serialization.
- Updated Semantic Analyzer and Type Checker to validate the new constructs and track the `Entity` class natively.

---

## [2.0.0] - The Professional Refactor

This release represents a complete architectural overhaul of the Aether compiler, transitioning it from a functional prototype into a professionally engineered compiler pipeline. 

### Phase 1: Architecture & Decoupling
- **Added:** `DiagnosticEngine` module to decouple error reporting from the exception system.
- **Changed:** The compiler pipeline no longer crashes on the first error. It collects diagnostics across all stages before halting.
- **Changed:** Frontend (Lexer, Parser, AST) is fully decoupled from the backend (Codegen, IR, Datapack Builder).

### Phase 2: Diagnostics & Error Recovery
- **Added:** Rust/Clang style error formatting.
  - Errors now include Error Codes (e.g., `E201`).
  - Errors print the source file name, line, and column.
  - Errors print a snippet of the source code with `^` underlines.
  - Errors include helpful hints (e.g., "Did you forget a ':'?").
  - Terminal color output implemented (auto-disables if piped).
- **Added:** Parser Error Recovery. When a syntax error is encountered, the parser logs it, synchronizes to the next statement boundary (newline), and continues parsing so you can see multiple syntax errors at once.

### Phase 3: Semantic Analysis
- **Added:** Formal `SymbolTable` and `Scope` classes to replace basic dictionaries.
- **Added:** Detection for duplicate variable declarations in the same scope (`E303`).
- **Added:** Semantic warnings for unused variables (`E304`).
- **Added:** Semantic warnings for variables that shadow outer scope variables (`E305`).

### Phase 4: Type Checker
- **Changed:** Type checker now accepts the `DiagnosticEngine` to report type mismatches cleanly without stack traces.
- **Added:** Strict type checking for return statements to ensure they match the function's declared return type (`E403`).

### Phase 5 & 6: IR & Optimizer
- **Changed:** AST Optimizer now uses the `DiagnosticEngine` to report unsupported features (like dynamic `for` loop bounds).
- **Maintained:** Dead Code Elimination (DCE) and Unused Function Pruning in the IR Optimizer.

### Phase 7: Datapack Backend
- **Changed:** Datapack Builder now correctly generates singular `function` folders (required for Minecraft 1.21+).
- **Maintained:** Automatic generation of `pack.mcmeta`, `load.json`, and `tick.json`.

### Phase 9: Formal Specification
- **Added:** `SPEC.md` containing the formal Lexical Structure, Type System, Memory Model, and EBNF Grammar.

### Phase 11: Continuous Integration
- **Added:** GitHub Actions workflow (`.github/workflows/ci.yml`).
  - Runs Flake8 linting.
  - Runs compilation integration tests on Python 3.8 through 3.11.

### Phase 12: Code Quality
- **Changed:** Refactored entire codebase to reduce file coupling.
- **Added:** Rigorous, professional docstrings and architectural comments to all modules.

---

## [1.0.0] - The MVP Release

The initial, feature-complete Minimum Viable Product of the Aether language.

### Added
- **Language Syntax:** Python-like indentation, `def` functions, `class` OOP, and optional type hints.
- **Types:** `int` (mapped to scoreboards), `string` and Objects (mapped to NBT storage), `bool`.
- **Control Flow:** `if`/`elif`/`else` (translated to branch functions), `for` loops (compile-time unrolled), `while` loops (recursive runtime functions).
- **OOP Support:** Classes, `__init__`, `self`, and methods. Objects mapped to NBT compounds with dynamic macro routing.
- **Native Command DSL:** Structured wrappers for `particle`, `summon`, `give`, `setblock`, etc., using Python-like keyword arguments.
- **Dynamic `run()` (Macros):** Ability to inject variables into raw commands using `{var}` syntax, automatically generating 1.21 macro functions.
- **Dynamic `say()`:** Automatically builds valid, wiki-compliant `tellraw` JSON arrays from `{var}` string interpolation.
- **External Objectives:** `@objective("name")` decorator to bridge Aether variables with vanilla Minecraft scoreboards.
- **Modules:** `import "path/file.ae"` syntax with depth-first dependency resolution and circular import prevention.
- **CLI Tools:** `-o` output directory flag, `-w` watch mode for rapid development.
- **Lifecycle Hooks:** `def main():` hooked into `#minecraft:load`, `def tick():` hooked into `#minecraft:tick`.