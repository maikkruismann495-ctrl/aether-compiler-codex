# ⚡ Aether Programming Language

<p align="center">
  <strong>A modern, strictly-typed, Rust-inspired programming language that compiles to Minecraft Java Edition 1.21+ Datapacks.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="https://github.com/torbenn211/aether-compiler/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-green.svg" alt="License: GPL-3.0"></a>
  <a href="https://minecraft.wiki/w/Data_pack"><img src="https://img.shields.io/badge/Minecraft-1.21%2B-purple.svg" alt="Minecraft 1.21+"></a>
</p>

Aether combines the raw execution power of vanilla commands with the clean, readable syntax of Rust and Bolt. Stop writing hundreds of repetitive `.mcfunction` files, dealing with messy `execute if` chains, or fighting with scoreboard boilerplate. 

With Aether, you write pure logic and raw commands side-by-side. The compiler handles variable allocation, macro generation, and datapack bundling automatically.

## ✨ Features

* **Rust/Bolt Hybrid Syntax:** Clean `fn`, `let mut`, `if`, and `for` blocks. No semicolons required.
* **Raw Command Native:** Any line starting with `/` is treated as a vanilla command. No string wrapping needed.
* **Dynamic `{var}` Macros:** Inject Aether variables directly into raw commands. Aether automatically generates the 1.21 macro functions under the hood.
* **`execute` Blocks:** Stop copy-pasting `execute as @e at @s run...` on every line. Write it once, open a `{ block`, and put all your commands inside!
* **Seamless JSON Merging:** Drop a `data/` folder into your project to instantly add custom recipes, dimensions, advancements, and loot tables. Aether merges them perfectly into the final datapack.
* **Zero-Boilerplate:** Automatically generates `pack.mcmeta`, `load.json`, and `tick.json`.
* **Zero-Cost Abstractions:** `for` loops and math are evaluated *at compile time*, unrolling into flat commands with zero runtime lag.
* **Professional Diagnostics:** Rust/Clang-style error reporting with source snippets and helpful hints.

---

## 📦 Installation

Aether is written in pure Python and requires **no external dependencies**. It works natively on Windows, Linux, and macOS.

### Prerequisites
* [Python 3.8+](https://www.python.org/downloads/)

### Global Installation
Install the `aether` command globally so you can use it from any terminal.

**Via GitHub:**
```bash
pip install git+https://github.com/torbenn211/aether-compiler.git
```

**Via Local Clone (For Development):**
```bash
git clone https://github.com/torbenn211/aether-compiler.git
cd aether-compiler
pip install -e .
```

### Verifying Installation
Open a new terminal and run:
```bash
aether --help
```

---

## 🚀 Quick Start

1. Create a folder for your project and add a file named `main.ae`.
2. Write your first Aether program:

```rust
// main.ae
namespace my_game

fn main() {
    let mut hp = 100
    hp = hp - 20

    /tellraw @a {"text":"Game Started! HP is {hp}","color":"gold"}
}

fn tick() {
    // Stop copy-pasting execute! Just open a block.
    execute as @e[type=zombie] at @s {
        /particle minecraft:flame ~ ~1 ~ 0 0 0 0 1
        /effect give @s minecraft:speed 1 0 true
    }
}
```

3. Compile it into a datapack:
```bash
aether main.ae -o my_datapack
```

4. Move the generated `my_datapack` folder into your Minecraft world's `datapacks/` folder and run `/reload` in-game!

---

## 📂 Custom Recipes, Dimensions & JSON Assets

Aether doesn't force you to learn a new JSON syntax. If you want to add custom recipes, dimensions, or loot tables, just create a `data/` folder in your project directory! 

Aether will automatically merge your vanilla JSON files into the final compiled datapack.

**Project Structure:**
```text
my_project/
├── main.ae                 <-- Your Aether code
└── data/                   <-- Your vanilla JSON files
    └── my_game/
        └── recipe/
            └── magic_sword.json
```

When you run `aether my_project/ -o output/`, Aether compiles your `.ae` files AND copies your `data/` folder, creating a perfect, ready-to-play datapack.

---

## 💻 CLI Usage

The Aether CLI is designed for fast, modern development.

```bash
aether <source> [options]
```

**Arguments:**
* `source`: Path to your `main.ae` file or your project directory. If a directory is passed, Aether looks for `main.ae` inside it.

**Options:**
* `-o, --output <dir>`: Specify the output directory for the datapack. Defaults to `./aether_datapack`.
* `-w, --watch`: Watch for file changes and automatically recompile in real-time.
* `--debug`: Dumps the intermediate representation (IR) JSON for advanced debugging.

**Example (Watch Mode):**
```bash
aether ./my_project/ -w -o ./my_world/datapacks/my_game
```

---

## 🏗️ Architecture

Aether behaves like a real, professionally engineered compiler (Direct Compiler model). The Intermediate Representation (IR) is temporary scaffolding. The final output is optimized, native `.mcfunction` files.

```ascii
[ .ae Source File ]
       |
       v
+------------------+  Injects DiagnosticEngine (Tracks all errors/warnings)
|     Lexer        |  Tokenizes source, recognizes raw commands
+------------------+
       |
       v
+------------------+  Features Error Recovery: skips to next line on error
|     Parser       |  Recursive descent. Builds Abstract Syntax Tree (AST)
+------------------+
       |
       v
+-------------------+  Uses formal SymbolTable. Checks for shadowing,
| Semantic Analyzer |  unused vars, and duplicate declarations.
+-------------------+
       |
       v
+------------------+  Validates types and attaches metadata to AST nodes.
|  Type Checker    |  Reports precise type mismatch errors.
+------------------+
       |
       v
+------------------+  Constant folding (5+5 -> 10), unrolls `for` loops,
| AST Optimizer    |  evaluates math at compile time.
+------------------+
       |
       v
+------------------+  Translates AST to command strings (IR).
| Code Generator   |  Maps let mut -> scoreboards, generates 1.21 macros.
+------------------+  Formats raw execute blocks.
       |
       v
+------------------+  Dead Code Elimination (DCE). Prunes unused branch
|  IR Optimizer    |  functions and unused scoreboard variables.
+------------------+
       |
       v
+------------------+
| Datapack Builder |  Writes pack.mcmeta, load/tick JSONs, merges data/ folder
+------------------+
```

---

## 📖 Documentation

For the complete language specification, grammar, and deep-dive tutorials, read the [**Aether Handbook**](https://github.com/torbenn211/aether-compiler/blob/main/HANDBOOK.md).

For a detailed breakdown of compiler changes, see the [**Changelog**](https://github.com/torbenn211/aether-compiler/blob/main/CHANGELOG.md).

---

## 🤝 Contributing

Contributions are welcome! Please ensure you have Python 3.8+ installed.
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add some amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

Please run `flake8` and ensure all tests pass before submitting a PR.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.