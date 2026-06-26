# 📖 The Aether Programming Language: Official Handbook (v3.0)

Welcome to the official handbook for Aether. Aether is a strictly-typed, Rust-inspired programming language that compiles directly into Minecraft Java Edition 1.21+ datapacks. It combines the raw execution power of vanilla commands with clean, readable syntax, and uses a pure, lightning-fast scoreboard architecture for all variables.

---

## Part 1 — Introduction

### What is Aether?
Aether bridges the gap between modern software development and Minecraft map creation. Stop writing hundreds of repetitive `.mcfunction` files, dealing with messy `execute if` chains, or fighting with NBT boilerplate. 

With Aether, you write pure logic and raw commands side-by-side. The compiler handles variable allocation, macro generation, and datapack bundling automatically.

### Design Philosophy
1. **Raw Command Native:** Any line starting with `/` is a vanilla command. No string wrapping.
2. **Pure Scoreboard Architecture:** Every `let` variable gets its own scoreboard objective. Arrays are mapped to single objectives using indices as fake player names. Zero NBT lag.
3. **Zero-Cost Abstractions:** `for` loops and math are evaluated *at compile time*, unrolling into flat commands.
4. **Clean Syntax:** Rust/Bolt hybrid syntax with `fn`, `let mut`, `if`, and `execute` blocks. No semicolons required.

---

## Part 2 — Installation & CLI

### Installation
Install globally via pip:
```bash
pip install git+https://github.com/torbenn211/aether-compiler.git
```

### CLI Usage
```bash
aether <source> [options]
```
* `-o, --output <dir>`: Output directory for the datapack.
* `-w, --watch`: Watch for changes and recompile instantly.
* `--debug`: Dumps the intermediate representation (IR) JSON.

---

## Part 3 — Language Basics

Aether uses `{}` for blocks. Semicolons are optional.

### Keywords
`namespace`, `fn`, `let`, `mut`, `if`, `else`, `for`, `in`, `return`, `execute`, `true`, `false`, `int`, `string`, `bool`.

### Formatting
```rust
namespace my_game

fn main() {
    let mut hp: int = 100
    if hp > 50 {
        /say Healthy!
    }
}
```

---

## Part 4 — Variables & Memory Architecture

Variables are declared using `let`. Use `let mut` if you want to change the variable later.

```rust
fn main() {
    let mut score = 0       // Inferred as int, mutable
    let max_score: int = 10 // Explicit type, immutable
    score = score + 5
}
```

### The Scoreboard Architecture
In Aether, **every variable is its own scoreboard objective.** 
When you write `let hp = 100`, Aether creates a custom objective `var_hp_0` and stores the value under the fake player `#val`.

**Generated `load.mcfunction`:**
```mcfunction
scoreboard objectives add var_hp_0 dummy
```

**Generated `main.mcfunction`:**
```mcfunction
scoreboard players set #val var_hp_0 100
```

This makes debugging in-game trivial. Just type `/scoreboard objectives setdisplay sidebar var_hp_0` to watch your variable update in real-time!

---

## Part 5 — Arrays

Arrays in Aether are mapped to **single scoreboard objectives**. The array index becomes the fake player name! This means array operations are lightning-fast, with zero NBT data lag.

```rust
fn main() {
    let scores = [10, 20, 30]
    let first = scores[0]
}
```

**Generated `main.mcfunction`:**
```mcfunction
# 1. Create the array objective (registered in load.mcfunction)
scoreboard objectives add var_arr_0 dummy

# 2. Populate the array
scoreboard players set 0 var_arr_0 10
scoreboard players set 1 var_arr_0 20
scoreboard players set 2 var_arr_0 30

# 3. Access the array
scoreboard players operation #temp_0 ae_int = 0 var_arr_0
```
*Note: In the current MVP, array indices must be compile-time constants (e.g., `0`, `1`, `2`).*

---

## Part 6 — Control Flow

### If Statements
You can use Aether's native math conditions, or raw Minecraft conditions!

```rust
fn check_hp() {
    let hp = 80
    
    // Aether native condition
    if hp > 50 {
        /say Healthy!
    } else {
        /say Hurt!
    }
    
    // Bolt-style raw condition
    if score @s kills matches 10.. {
        /say You killed 10 mobs!
    }
}
```

### Execute Blocks
Stop copy-pasting `execute as @e at @s run...` on every line. Write it once, open a `{ block`, and put all your commands inside!

```rust
fn tick() {
    execute as @e[type=zombie] at @s {
        /particle minecraft:flame ~ ~1 ~ 0 0 0 0 1
        /effect give @s minecraft:speed 1 0 true
    }
}
```

### Compile-Time Loops (`for`)
`for` loops are unrolled completely at compile time into flat commands. Zero runtime overhead.

```rust
fn main() {
    for i in 0..5 {
        /summon minecraft:zombie ~{i} ~ ~
    }
}
```

---

## Part 7 — Raw Commands & Macros

### Raw Commands
Any line starting with `/` is treated as a vanilla command. Aether strips the leading `/` automatically, as `.mcfunction` files do not allow them.

```rust
fn main() {
    /give @s minecraft:diamond 1
}
```
Compiles to: `give @s minecraft:diamond 1`

### Dynamic `{var}` Macros
You can inject Aether variables directly into raw commands using `{curly brackets}`. Aether automatically generates the 1.21 macro functions under the hood!

```rust
fn main() {
    let hp = 100
    /tellraw @a {"text":"Game Started! HP is {hp}","color":"gold"}
}
```

**How it compiles:**
Aether creates a hidden macro file and handles the storage injection perfectly.

*`main.mcfunction`:*
```mcfunction
# 1. Copy the 'hp' scoreboard value into macro storage
execute store storage my_game:data macro_hp int 1 run scoreboard players get #val var_hp_0

# 2. Call the macro function, passing the stored data
function my_game:macro_cmd_0 with storage my_game:data {macro_hp}
```

*`macro_cmd_0.mcfunction`:*
```mcfunction
# The macro variable is $(macro_hp) to match the storage key!
$tellraw @a {"text":"Game Started! HP is $(macro_hp)","color":"gold"}
```

---

## Part 8 — Custom JSON Assets (Recipes, Dimensions)

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

## Part 9 — Functions & Lifecycle

A function is a way to group commands together. 

* `fn main()` runs automatically when the datapack loads.
* `fn tick()` runs automatically every single game tick (20 times a second).

```rust
// Runs on load!
fn main() {
    /say Game Started!
}

// Runs every tick!
fn tick() {
    /weather clear
}
```

---

## Part 10 — Compiler Architecture

Aether behaves like a real, professionally engineered compiler (Direct Compiler model).

1. **Lexer:** Tokenizes source code, recognizes raw commands.
2. **Parser:** Recursive descent. Builds an AST. Features error recovery.
3. **Semantic Analyzer:** Validates scopes and function calls using a formal Symbol Table.
4. **Type Checker:** Validates types and attaches metadata to AST nodes.
5. **AST Optimizer:** Constant folding, loop unrolling.
6. **Code Generator:** Translates AST to command strings (IR). Maps `let mut` to scoreboards, generates 1.21 macros.
7. **IR Optimizer:** Dead Code Elimination (DCE).
8. **Datapack Builder:** Writes `pack.mcmeta`, `load/tick.json`, merges `data/` folder. Enforces 1.21+ singular `function` folder structures.