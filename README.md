Here is the ultimate, fully extended `README.md` complete with the deep-dive engine breakdown, memory architecture, and OOP mapping details. You can copy and paste this directly into your repository!

***

# ⚡ Aether Programming Language

<p align="center">
  <strong>A modern, strictly-typed, Python-inspired programming language that compiles to Minecraft Java Edition 1.21.11 Datapacks.</strong>
</p>

Aether bridges the gap between modern software development and Minecraft map creation. Stop writing hundreds of repetitive `.mcfunction` files. With Aether, you write clean, object-oriented code with type hints, compile-time math, and native command DSLs, and the compiler translates it into perfectly optimized, vanilla-safe Minecraft datapacks.

## ✨ Features

* **Python-like Syntax:** Indentation-based blocks, `def` functions, `class` OOP, and optional type hints.
* **Zero-Boilerplate Datapacks:** Automatically generates `pack.mcmeta`, `load.json`, and `tick.json`. Just write logic.
* **Lifecycle Functions:** `def main():` runs on load. `def tick():` runs every tick. 
* **Compile-Time Math & Loops:** `for i in range(10):` and `math::sin(i)` are evaluated *at compile time*, outputting raw commands with zero runtime lag.
* **Native Command DSL:** Write readable Minecraft commands using keyword arguments. `particle("flame", at=(0, 10, 0), count=5)`
* **Dynamic `run()` Macros:** Inject variables directly into raw commands: `run("say {message}")` automatically generates 1.21 macro functions.
* **OOP Support:** Create `class` structs with `__init__`, `self`, and methods. Objects map dynamically to NBT storage.
* **Multi-File Projects:** Clean `import "path/file.ae"` syntax. The compiler resolves the dependency graph from `main.ae`.
* **Optimized IR:** Bolt-style Dead Code Elimination (DCE) and unused function removal ensure your datapacks stay lean.

---

## 📦 Installation

Aether is written in pure Python and requires **no external dependencies**. It works natively on Windows, Linux, and macOS.

### Prerequisites
* [Python 3.8+](https://www.python.org/downloads/)

### Global Installation (Recommended)
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

def main():
    say("Hello, Minecraft!")

def tick():
    # Runs every single tick!
    particle("minecraft:flame", at=(~0, ~1, ~0), count=1, speed=0.1)
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

## 📖 Language Reference

### Project Structure & Imports
Every project must have a `main.ae` file as the entry point. You can organize code into modules and import them using relative paths.

```text
my_project/
├── main.ae
└── lib/
    └── utils.ae
```

```python
# main.ae
namespace my_game
import "lib/utils.ae"

def main():
    utils::do_something()
```

### Variables & Types
Aether is statically typed, but supports type inference.

```python
x: int = 10           # Explicit type
name = "Steve"        # Inferred as string
is_admin = true       # Inferred as bool
```

### Control Flow
Standard Python-like syntax. Conditions must evaluate to `bool`.

```python
if hp <= 0:
    say("Game Over")
elif hp < 50:
    say("Danger")
else:
    say("Safe")
```

**Compile-Time Loops (`for`):**
Bounds *must* be constant integers. Unrolled at compile time (zero runtime cost).
```python
for i in range(5):
    give("@a", "minecraft:arrow", 1)
```

**Runtime Loops (`while`):**
Runs dynamically in Minecraft via recursive functions.
```python
local time = 0
while time < 100:
    time += 1
```

### Object-Oriented Programming (OOP)
Classes map to NBT compounds in storage. Methods map to macro functions.

```python
class Player:
    hp: int
    name: string

    def __init__(self, name: str, hp: int):
        self.name = name
        self.hp = hp

    def take_damage(self, amount: int):
        self.hp -= amount
        if self.hp <= 0:
            say("Player died!")

def main():
    p1 = Player("Steve", 100)
    p1.take_damage(20)
```

---

## ⚙️ Native Command Integration

Aether provides structured wrappers for Minecraft commands using Python-like keyword arguments.

### Structured Commands (DSL)
```python
# Particle
particle("minecraft:flame", at=(0, 10, 0), count=10, speed=0.1, mode="force")

# Summon
summon("minecraft:zombie", at=(~, ~, ~), nbt="{CustomName:'\"Bob\"'}")

# Setblock
setblock("minecraft:diamond_block", at=(0, 0, 0), mode="replace")

# Give
give("@a", "minecraft:apple", count=5)
```

### Inline `run()` Command (With Macros)
Need to write a raw command? Use `run()`. You can inject variables dynamically using `{var}` syntax. The compiler automatically generates a 1.21 macro function for you!

```python
local player_name = "Steve"
local score = 10

run('tellraw @a {"text":"Player {player_name} has {score} points!"}')
```

---

## 🔬 Aether Engine Deep Dive: How It Works

To understand how Aether transforms high-level Python-like code into vanilla Minecraft commands, we have to look at the compiler pipeline. Aether is a **Direct Compiler**. It does not bundle a runtime interpreter into your datapack. Instead, it translates your logic into raw `.mcfunction` commands at compile time.

### The 8 Stages of Compilation

1. **Lexer (`lexer.py`):** Reads your raw text and groups characters into `Token` objects. It handles Python-style indentation by generating `INDENT` and `DEDENT` tokens.
2. **Parser (`parser.py`):** Takes the flat list of tokens and arranges them into a 3D tree structure called an Abstract Syntax Tree (AST) using recursive descent.
3. **Semantic Analyzer (`semantic.py`):** Walks the AST to build symbol tables, check scopes, and validate function calls.
4. **Type Checker (`type_checker.py`):** Enforces strict typing rules and attaches `inferred_type` metadata to AST nodes.
5. **AST Optimizer (`optimizer.py`):** Performs Constant Folding (evaluates `5 + 5` to `10` at compile time), unrolls `for` loops, and evaluates `math::sin()`.
6. **Code Generator (`codegen.py`):** Translates the optimized AST into an Intermediate Representation (IR)—a dictionary mapping function names to lists of command strings.
7. **IR Optimizer (`optimizer_ir.py`):** Cleans up dead scoreboard variables and deletes generated branch functions that ended up not being called.
8. **Datapack Builder (`datapack_builder.py`):** Writes the IR to disk as `.mcfunction` files and generates `pack.mcmeta` and tag JSONs.

### Memory Architecture
Aether maps high-level types directly to Minecraft's native storage systems:
* **`int` and `bool`**: Mapped to the `ae_int` scoreboard objective. Variables are given readable names like `var_hp_0` instead of hidden `#` names, so you can easily debug your game using `/scoreboard objectives setdisplay sidebar ae_int`.
* **`string` and Objects**: Mapped to `storage <namespace>:data`. Strings and class instances are stored as NBT compounds, allowing dynamic manipulation at runtime.

### 🕵️ Microscope: How `run("")` Works

Let's trace exactly what happens when you write this Aether code:

```python
namespace my_game
def main():
    local message: string = "Hello"
    run("say {message}")
```

**1. Lexing & Parsing:**
The Lexer reads `run("say {message}")` and produces an `IDENT` ("run") and a `STRING` ("say {message}"). The Parser sees the function call and creates a `FunctionCall` AST node.

**2. Code Generation (The Magic Happens):**
The Code Generator visits the `FunctionCall` node. It hits the `run` builtin logic. First, it uses a Regex to search for `{var_name}` inside the string. It finds `message`.

Because it found a variable, the compiler knows it **cannot** just output a raw string. In Minecraft 1.21+, you cannot inject a scoreboard or NBT value directly into a `say` or `tellraw` command string at runtime without using **Macros**.

So, the compiler dynamically generates a macro function:
1. It creates a unique macro function name: `macro_run_0`.
2. It copies the variable from its NBT path into a temporary macro path: `data modify storage my_game:data macro_message set from storage my_game:data var_message_0`.
3. It calls the macro function, passing the data: `function my_game:macro_run_0 with storage my_game:data {macro_message}`.
4. It generates the actual `.mcfunction` file for the macro, replacing `{message}` with `$(message)` and prepending `$` (Minecraft's syntax for macros): `$say $(message)`.

**Output `data/my_game/function/main.mcfunction`:**
```mcfunction
# local message: string = "Hello"
data modify storage my_game:data var_message_0 set value "Hello"

# run("say {message}")
data modify storage my_game:data macro_message set from storage my_game:data var_message_0
function my_game:macro_run_0 with storage my_game:data {macro_message}
```

**Output `data/my_game/function/macro_run_0.mcfunction`:**
```mcfunction
$say $(message)
```

### 🧠 OOP to NBT Mapping
When you instantiate `p1 = Player("Steve", 100)`, Aether creates an NBT compound in storage: `storage my_game:data instances.Player_1 {name:"Steve", hp:100}`. 

When you call `p1.take_damage(20)`, Aether passes `Player_1` to the method as a macro argument `$(obj_id)`. Inside the method, `self.hp` is dynamically resolved to `instances.Player_$(obj_id).hp`. This allows multiple objects to share the same method functions without colliding.

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0** - see the [LICENSE](LICENSE) file for details.
