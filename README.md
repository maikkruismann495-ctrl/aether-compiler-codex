# ⚡ Aether Programming Language

<p align="center">
  <strong>A modern, strictly-typed, Python-inspired programming language that compiles to Minecraft Java Edition 1.21+ Datapacks.</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+"></a>
  <a href="https://github.com/torbenn211/aether-compiler/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-green.svg" alt="License: GPL-3.0"></a>
  <a href="https://minecraft.wiki/w/Data_pack"><img src="https://img.shields.io/badge/Minecraft-1.21%2B-purple.svg" alt="Minecraft 1.21+"></a>
</p>

Aether bridges the gap between modern software development and Minecraft map creation. Stop writing hundreds of repetitive `.mcfunction` files. With Aether, you write clean, object-oriented code with type hints, compile-time math, and a massive native command DSL, and the compiler translates it into perfectly optimized, vanilla-safe Minecraft datapacks.

## ✨ Features

* **Python-like Syntax:** Indentation-based blocks, `def` functions, `class` OOP, and optional type hints.
* **Production-Ready Command DSL:** Clean, typed function wrappers for almost **every command in the game** (`bossbar`, `attribute`, `damage`, `recipe`, `data`, etc.). No more raw string formatting!
* **Bolt-Style `execute` Blocks:** Scope commands to entities natively without raw `run()` strings.
* **`Entity` Wrappers:** Treat selectors as native objects. Call methods like `target.tp(0, 100, 0)` directly!
* **Dict Literals (NBT):** Use `{}` syntax to create NBT compounds. The compiler handles serialization automatically.
* **`wait()` Coroutines:** Pause function execution for a set number of ticks. The compiler automatically splits functions and handles `/schedule`.
* **Zero-Cost Abstractions:** `for` loops and `math::` functions are evaluated *at compile time*, outputting raw commands with zero runtime lag.
* **Professional Diagnostics:** Rust/Clang-style error reporting with source snippets, underlines, and helpful hints. Features error recovery to report multiple errors at once.
* **Vanilla Interoperability:** Use the `@objective("deathCount")` decorator to seamlessly read/write vanilla scoreboard objectives.

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

```python
# main.ae
namespace my_game

class Player:
    hp: int
    name: string

    def __init__(self, name: str, hp: int):
        self.name = name
        self.hp = hp

    def take_damage(self, amount: int):
        self.hp -= amount
        say("{self.name} took {amount} damage!")

def main():
    local p1 = Player("Steve", 100)
    p1.take_damage(20)
    
    # Native Command DSL
    particle("minecraft:flame", at=(0, 10, 0), count=10, speed=0.1, mode="force")
    
    # Dict Literals (NBT Compounds)
    local zombie_gear = {
        "id": "minecraft:diamond_sword",
        "Count": 1
    }
    
    # Native execute blocks
    execute as "@e[type=zombie]" at "@s":
        run("data merge entity @s {HurtTime:10}")
        particle("minecraft:cloud", at=(~, ~1, ~), count=2)
        
    # Entity wrapper objects
    local target = entity("@p")
    target.say("I am the target!")
    target.tp(0, 100, 0)
    
    # wait() coroutine
    say("Falling in 3...")
    wait(20)
    say("2...")
    wait(20)
    say("1...")
    wait(20)
    summon("minecraft:tnt", at=(0, 0, 0), nbt={"Fuse": 20})
    say("Boom!")
```

3. Compile it into a datapack:
```bash
aether main.ae -o my_datapack
```

4. Move the generated `my_datapack` folder into your Minecraft world's `datapacks/` folder and run `/reload` in-game!

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

## 🎮 Native Command DSL

Aether provides structured, typed wrappers for almost every Minecraft command. You no longer need to remember exact string formatting or quote escaping.

```python
def main():
    # Effects & Damage
    effect("give", "@p", "minecraft:speed", duration=30, amplifier=2, particles=false)
    damage("@e[type=zombie]", 50, type="minecraft:fire", by="@p")
    
    # World & Environment
    setblock(at=(0, 0, 0), "minecraft:diamond_block", mode="replace")
    fill(from=(0,0,0), to=(5,5,5), "minecraft:stone", mode="hollow")
    time("set", "day")
    weather("rain", duration=600)
    
    # Entities & Stats
    attribute("@p", "minecraft:generic.max_health", "base", "set", 20)
    tag("@e[type=cow]", "add", "my_cow")
    xp("@p", 10, type="levels")
    
    # Server & Admin
    bossbar("add", "my_boss", "Boss Health")
    gamerule("doDaylightCycle", "false")
    recipe("give", "@a", "minecraft:diamond_sword")
```

If a command doesn't have an explicit wrapper, the **Universal Fallback** automatically formats the function call into a raw vanilla command, meaning *every* command in the game is supported.

---

## 🏗️ Architecture

Aether v2.0 behaves like a real, professionally engineered compiler (Direct Compiler model). The Intermediate Representation (IR) is temporary scaffolding. The final output is optimized, native `.mcfunction` files.

```ascii
[ .ae Source File ]
       |
       v
+------------------+  Injects DiagnosticEngine (Tracks all errors/warnings)
|     Lexer        |  Tokenizes source, handles Python-style INDENT/DEDENT
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
| AST Optimizer    |  evaluates math:: functions at compile time.
+------------------+
       |
       v
+------------------+  Translates AST to command strings (IR).
| Code Generator   |  Maps int/bool -> scoreboards, string/objects -> NBT.
+------------------+  Generates 1.21 macros for dynamic commands.
       |
       v
+------------------+  Dead Code Elimination (DCE). Prunes unused branch
|  IR Optimizer    |  functions and unused scoreboard variables.
+------------------+
       |
       v
+------------------+
| Datapack Builder |  Writes pack.mcmeta, load/tick JSON tags, .mcfunction
+------------------+
```

### Error Recovery & Diagnostics
Instead of crashing on the first syntax error, Aether logs diagnostics and attempts to recover. This allows the compiler to report multiple errors at once, saving you time.

```text
error[E202]: Expected ':' (Got NEWLINE)
 --> main.ae:4:24
  |
4 |     if hp > 0
  |                        ^ Expected ':' (Got NEWLINE)
  |
  = hint: Did you forget a ':' at the end of the statement?
```

---

## 📖 Documentation

For the complete language specification, grammar, and deep-dive tutorials, read the [**Aether Handbook**].

For a detailed breakdown of compiler changes, see the [**Changelog**](.

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
