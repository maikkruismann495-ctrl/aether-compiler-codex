# Changelog

## 3.1.0

### Added

- JavaScript/Bolt-style `.ae` syntax: `function`, `let`, `const`, `var`, JS boolean operators, and TypeScript-style annotations.
- Bare Minecraft command lines, with or without a leading slash.
- Command passthrough no longer depends on a hardcoded Minecraft command list.
- Raw `execute` blocks and raw Minecraft condition blocks.
- Compile-time loops with `for (let i = 0; i < n; i++)` and `for (let i of range(start, end))`.
- Regression tests for lexer, parser failure handling, imports, macros, datapack output, data asset copying, and command passthrough.
- Example projects under `examples/`.
- PyPI-ready packaging metadata, publishing guide, manifest, and GitHub Trusted Publishing workflow.

### Changed

- Replaced the stale top-level compiler copy with a wrapper around `aether.cli`.
- Rewrote README and handbook documentation around the current language.
- Updated package metadata to `3.1.0`.
- Watch mode now tracks copied `data/` assets in addition to `.ae` files.
- CI now compiles example projects.
- `.gitignore` now covers common Python build, cache, and test artifacts.

### Fixed

- Semantic analysis now visits the root program.
- `const` reassignment now reports an error.
- Compound assignment now generates scoreboard operations.
- Basic array literals and literal index reads now generate code.
- Compile-time loop values now inline into raw command macros.
- Import failures and circular imports now report clean compiler errors instead of exiting inside helper code.
- Parser recovery no longer loops forever on malformed statements before a closing brace.

## Notes

This repository was adopted with generated files and outdated historical notes checked in. The old changelog entries were removed because they described unsupported Python/OOP-style features that are not present in the current compiler.
