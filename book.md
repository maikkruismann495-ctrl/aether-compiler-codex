# 📖 The Aether Programming Language: Official Handbook (v2.2)

Welcome to the official handbook for Aether. This document is the complete, authoritative guide to the Aether programming language and its compiler. Whether you are building a simple Hello World script or a massive multiplayer RPG, this book will teach you how to master Aether.

---

# Part 0 — Aether Programming 101 (The Beginner Course)

*Welcome to the grid, dev. You’re about to learn how to bend Minecraft to your absolute will using modern programming techniques. This crash course will take you from absolute beginner to Aether expert. Let’s hack the block.*

## Lesson 1: Hello, Overworld
Programming is just giving a computer a list of instructions. In Aether, you write these instructions in a text file, and the compiler translates them into Minecraft commands.

Create a file named `main.ae` and type this:

```python
# main.ae
namespace my_first_pack

def main():
    say("Hello, Minecraft!")
```

**What did you just write?**
1. `#` makes a comment. The compiler ignores this. It's for you.
2. `namespace my_first_pack` tells Minecraft which folder to put your code in.
3. `def main():` defines a function named `main`. Aether automatically runs `main()` when the datapack loads.
4. `say("Hello, Minecraft!")` is a built-in Aether command that translates to `/tellraw @a`.

Compile it by opening your terminal and running:
`aether main.ae -o my_datapack`

Move `my_datapack` into your world's `datapacks` folder, jump in-game, type `/reload`, and watch the chat. You just wrote code!

## Lesson 2: Variables (The Scoreboard Illusion)
Variables are boxes that hold data. In Minecraft, numbers are stored in "scoreboards" and text in "NBT storage". Aether hides this ugly reality from you.

```python
def main():
    local player_hp: int = 100     # An integer (whole number)
    local player_name = "Steve"    # A string (text). Type is inferred!
    local is_alive: bool = true    # A boolean (true/false)
    
    player_hp = 80                 # You can change variables later
```

* **`int`**: Numbers like `10`, `-5`, `1000`. No decimals allowed! (Minecraft doesn't support floats natively).
* **`string`**: Text wrapped in quotes. `"Alex"`.
* **`bool`**: `true` or `false`. Used for logic.

## Lesson 3: Math & Logic
You can do math and compare things, just like in school.

```python
def main():
    local a = 10
    local b = 3
    
    local sum = a + b      # 13
    local diff = a - b     # 7
    local prod = a * b     # 30
    local quot = a / b     # 3 (Divides and drops the decimal)
    
    # Comparisons return bools
    local is_greater = a > b   # true
    local is_equal = a == b    # false
```

## Lesson 4: Control Flow (Making Decisions)
You need your code to make decisions. Use `if`, `elif`, and `else`.

```python
def main():
    local hp = 40
    
    if hp <= 0:
        say("Game Over!")
    elif hp < 50:
        say("Danger! Low health!")
    else:
        say("Healthy and ready to fight!")
```
*Note: Aether forces you to use `bool` types in `if` statements. You can't say `if hp:` because `hp` is an `int`, not a `bool`. You must explicitly compare it, like `if hp > 0:`.*

## Lesson 5: Loops & Coroutines
Loops let you run code multiple times. Aether has `for` (compile-time) and `while` (runtime) loops. 
Aether also features `wait()`, a coroutine that pauses your function for a set number of ticks!

```python
def main():
    # Compile-time loop (unrolled into flat commands)
    for i in range(5):
        give("@a", "minecraft:arrow", 1)
        
    # Coroutine
    say("Waiting 1 second...")
    wait(20) # 20 ticks = 1 second
    say("Done!")
```
*Warning: If a `while` loop never ends, Minecraft will crash (hit the 65536 command limit). Always ensure it breaks!*

## Lesson 6: Functions
Functions are reusable blocks of code. You pass data in, they do work, and they can pass data back.

```python
def calculate_damage(base: int, armor: int) -> int:
    local final_damage = base - armor
    if final_damage < 0:
        return 0
    return final_damage

def main():
    local hit = calculate_damage(50, 20)
    say("You took {hit} damage!") # String interpolation!
```

## Lesson 7: Classes & OOP
Object-Oriented Programming (OOP) lets you group data and functions together. Think of a `Player` having `hp` and a `take_damage` function.

```python
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
    p1.take_damage(30)
```
Under the hood, Aether saves `p1` as an NBT compound in Minecraft storage and dynamically routes the `take_damage` function to modify `p1`'s specific `hp` value.

## Lesson 8: Native Minecraft Commands (The Bolt Magic)
Aether gives you clean syntax for Minecraft commands using "Keyword Arguments". It also lets you use native `execute` blocks and `Entity` wrapper objects!

```python
def main():
    # Dict Literals (NBT)
    local gear = {"id": "minecraft:diamond_sword", "Count": 1}
    
    # Execute Blocks
    execute as "@e[type=zombie]" at "@s":
        run("data merge entity @s {HurtTime:10}")
        particle("minecraft:cloud", at=(~, ~1, ~), count=2)
        
    # Entity Objects
    local target = entity("@p")
    target.say("I am the target!")
    target.tp(0, 100, 0)
```

*Congratulations, you now know the basics of Aether! The rest of this book is the deep-dive reference manual. Keep it open while you build.*

---

# Part 1 — Introduction

### What the language is
Aether is a strictly-typed, high-level programming language that compiles directly into Minecraft Java Edition 1.21.11 datapacks. It uses Python-like indentation and syntax, supports Object-Oriented Programming (OOP), and abstracts away the tedium of scoreboards, NBT data manipulation, and recursive function loops.

### Design Philosophy
Aether is built on three core pillars:
1. **Readability over boilerplate:** You write logic, not `execute if score` commands. The syntax is designed to be instantly familiar to Python developers while enforcing strict safety rules.
2. **Zero-cost abstractions:** A `for` loop that calculates math compiles down to raw, flat commands, adding zero runtime lag. Object-Oriented Programming (OOP) compiles down to macro-driven NBT manipulation.
3. **Strictness prevents bugs:** Types are checked at compile time. If you try to subtract a `string` from an `int`, Aether refuses to compile. This prevents runtime crashes in Minecraft.

### Differences from Python, Java, C#, and Minecraft Commands
* **vs Python:** Aether looks like Python, but it is strictly typed. You cannot change a variable's type at runtime, and you cannot use implicit truthiness in `if` statements.
* **vs Java/C#:** No garbage collector, no threads. Execution is bound by Minecraft's single-threaded tick system (65536 commands per tick limit).
* **vs Minecraft Commands:** You don't manually manage `data modify storage` or `scoreboard players operation`. Aether handles allocation automatically and safely.

---

# Part 2 — Installation & Pipeline

### Installation
Install globally via GitHub:
```bash
pip install git+https://github.com/torbenn211/aether-compiler.git
```

### CLI Usage & Flags
```bash
aether <source> [options]
```
* `-o, --output <dir>`: Output directory for the datapack.
* `-w, --watch`: Watch for changes and recompile instantly (like Bolt/Beet).
* `--debug`: Dumps `ir_debug.json` showing the exact generated commands.

### Compilation Pipeline
Aether behaves like a real compiler (Direct Compiler model). The Intermediate Representation (IR) is temporary scaffolding. The final output is optimized, native `.mcfunction` files.

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

---

# Part 3 — Language Basics

Aether uses indentation (spaces) to define blocks. Semicolons are optional.

### Keywords
`namespace`, `class`, `def`, `if`, `elif`, `else`, `for`, `while`, `return`, `local`, `import`, `in`, `range`, `self`, `and`, `or`, `not`, `true`, `false`, `int`, `string`, `bool`, `execute`.

### Formatting
```python
namespace my_game

def main():
    local x: int = 10
    if x > 5:
        say("X is big")
```

---

# Part 4 — Types

Aether is statically typed. Type inference is supported.

### 1. `int` (Integer)
* **Purpose:** 32-bit signed integer.
* **Memory Model:** Stored in the `ae_int` scoreboard objective.
* **Limitations:** Cannot hold decimals. Division truncates towards zero like Java, not down like Python.

### 2. `string`
* **Purpose:** UTF-8 text.
* **Memory Model:** Stored in `storage <namespace>:data` as NBT strings.
* **Limitations:** Cannot be dynamically concatenated at runtime in MVP. Use compile-time interpolation or `say()` dynamic JSON generation.

### 3. `bool`
* **Purpose:** `true` or `false`.
* **Memory Model:** Stored in `ae_int` scoreboard as `1` or `0`.

### 4. `nbt` (Dict Literal)
* **Purpose:** NBT compound data.
* **Memory Model:** Stored in `storage <namespace>:data` as NBT compounds.
* **Limitations:** Keys must be string literals. Values can be strings, ints, bools, or nested dicts.

---

# Part 5 — Variables

### Declaration & Mutability
Variables are declared using `local`. They must be initialized. All variables are mutable by default.
```python
local score = 0       # Inferred as int
local name: string = "Alex"
name = "Bob"          # Allowed
```

### Scope and Lifetime
Variables exist only within the `def` block they were created in. When a function ends, its local variables are conceptually discarded (their scoreboard/NBT locations will be overwritten by future function calls).

### External Objectives (`@objective` decorator)
By default, Aether maps all `int` and `bool` variables to its internal `ae_int` scoreboard objective. This is by design: it keeps the generated datapacks clean, makes debugging easy (`/scoreboard objectives setdisplay sidebar ae_int`), and avoids boilerplate `scoreboard objectives add` commands.

However, sometimes you need to read or write to a **vanilla objective** (like `deathCount` or `food`) or an objective created by an external datapack. Aether provides the `@objective("name")` decorator for this.

**Syntax:**
```python
@objective("objective_name")
local var_name: int = value
```

**Example:**
```python
def main():
    @objective("deathCount")
    local deaths: int = 0
    
    @objective("currency")
    local gold: int = 100
    
    if deaths > 0:
        gold -= 10 * deaths
```

**Compiler Implementation:**
When Aether sees `@objective`, it skips allocating the variable on `ae_int`. Instead, it uses the provided objective name for all subsequent `scoreboard players operation` and `scoreboard players set` commands.

> **Warning:** Aether assumes the external objective already exists. You must create it via a `run("scoreboard objectives add ...")` command or a manual JSON file in your `data/` folder.

---

# Part 6 — Expressions

### Arithmetic Operators
`+`, `-`, `*`, `/`, `%` (Modulo follows Java semantics: result takes sign of dividend).

### Comparison Operators
`==`, `!=`, `<`, `>`, `<=`, `>=`

### Logical Operators
`and`, `or`, `not`

### Precedence (Highest to Lowest)
1. `()`, `[]`, `.` (Member access)
2. `-` (Unary minus), `not`
3. `*`, `/`, `%`
4. `+`, `-`
5. `<`, `>`, `<=`, `>=`
6. `==`, `!=`
7. `and`
8. `or`

---

# Part 7 — Control Flow

### If / Elif / Else
Conditions **must** evaluate to `bool`. There is no implicit truthiness.
**Compiler Translation:** Generates separate `.mcfunction` files for branches (`branch_if_0.mcfunction`) and calls them via `execute if score #temp_0 ae_int matches 1 run function...`.

### Compile-Time Loops (`for`)
**Compiler Translation:** The optimizer unrolls this completely at compile time into flat commands. Zero runtime overhead.

### Runtime Loops (`while`)
**Compiler Translation:** Generates a recursive function. `loop_0.mcfunction` checks the condition, calls `loop_body_0.mcfunction`, then calls itself.

### The `wait()` Coroutine (New!)
Pauses the execution of the current function for a specified number of ticks.
```python
def main():
    say("Explosion in 3...")
    wait(20) # Pauses execution for 20 ticks (1 second)
    say("2...")
    wait(20)
    say("1...")
    wait(20)
    summon("minecraft:tnt", at=(0, 5, 0))
```
**Compiler Translation:** Aether splits the function into multiple `.mcfunction` files and uses `/schedule` to chain them.

---

# Part 8 — Functions

### Syntax & Parameters
```python
def add(a: int, b: int) -> int:
    return a + b
```
Functions support explicit types. Recursion is fully supported, but beware of Minecraft's command chain limit.

### Namespaces
Group functions into datapack folders.
```python
namespace math_lib
def square(n: int) -> int:
    return n * n
```

---

# Part 9 & 10 — Classes & Objects

Aether supports Rust/Python-style OOP. Classes map to NBT compounds.

```python
class Player:
    hp: int
    name: string

    def __init__(self, name: str, hp: int):
        self.name = name
        self.hp = hp

    def take_damage(self, amount: int):
        self.hp -= amount
```

### How OOP is implemented in Minecraft
When you instantiate `p1 = Player("Steve", 100)`, Aether creates an NBT compound in `storage my_game:data instances.Player_1 {name:"Steve", hp:100}`. When you call `p1.take_damage(20)`, Aether generates a macro function call passing `1` as the `obj_id`. `self.hp` is dynamically resolved to `instances.Player_$(obj_id).hp`.

---

# Part 11 — Collections

### Arrays
Arrays map to Minecraft NBT lists. All elements must be the same type.
```python
local scores: int[] = [10, 20, 30]
local first = scores[0]
```
**Limitation:** Dynamic indexing (`scores[i]` where `i` is a variable) is not supported in the current MVP. Indices must be compile-time constants.

### Dict Literals (NBT Compounds) (New!)
Dict literals map directly to Minecraft NBT compounds. This is perfect for summoning entities with custom data.
```python
def main():
    local gear = {
        "id": "minecraft:diamond_sword",
        "Count": 1,
        "tag": {"Enchantments": [{"id": "minecraft:sharpness", "lvl": 5}]}
    }
    summon("minecraft:zombie", at=(0, 0, 0), nbt=gear)
```

---

# Part 12 — Modules

### Imports
Use `import` with relative paths. The compiler resolves this depth-first, starting from `main.ae`. Circular imports are automatically detected and prevented.
```python
import "lib/utils.ae"
```

---

# Part 13 — Standard Library

### Math (Compile-Time)
* `math::sin(degrees)` -> Returns `int` scaled by 1000.
* `math::cos(degrees)` -> Returns `int` scaled by 1000.
* `math::sqrt(val)` -> Returns `int`.

### Time
* `wait(ticks)` -> Schedules the rest of the function for later using `/schedule`. (Replaces `time.sleep`)

---

# Part 14 — Minecraft API

Aether provides structured, typed wrappers for almost every Minecraft command. You no longer need to remember exact string formatting or quote escaping.

### Dynamic `say()` (Wiki-Compliant `tellraw` JSON)
When you use `say()` with a string containing `{var}`, Aether does **not** just use macros. It dynamically builds a valid, wiki-compliant `tellraw` JSON array. It reads directly from scoreboards and NBT storage at runtime!

```python
@objective("deathCount")
local deaths: int = 0
local gold: int = 100

say("You have lost {gold} gold to {deaths} deaths.")
```

**Generated `.mcfunction`:**
```mcfunction
tellraw @a [{"text":"You have lost "},{"score":{"name":"var_gold_0","objective":"ae_int"}},{"text":" gold to "},{"score":{"name":"var_deaths_0","objective":"deathCount"}},{"text":" deaths."}]
```

### Dynamic `run()` (Macros)
For raw commands that aren't `say`, you can use `run()` and inject variables using `{var}`.
```python
local target = "@p"
run("kill {target}")
```
**Compiler Translation:** Generates a 1.21 macro function: `$kill $(target)`.

### Native `execute` Blocks (New!)
Instead of writing raw `run("execute as @e...")` strings, you can use Aether's clean block syntax to scope commands to entities.
```python
def cast_aoe():
    execute as "@e[type=zombie, distance=..5]":
        run("data merge entity @s {HurtTime:10}")
        particle("minecraft:cloud", at=(~, ~1, ~), count=5)
```
**Compiler Translation:**
```mcfunction
execute as @e[type=zombie, distance=..5] run data merge entity @s {HurtTime:10}
execute as @e[type=zombie, distance=..5] run particle minecraft:cloud ~ ~1 ~ 0 0 0 0 5 normal
```

### `Entity` Wrapper Objects (New!)
In Aether, selectors can be manipulated as native objects using the `entity()` constructor.
```python
def main():
    local target = entity("@p")
    
    # Call methods directly on the entity!
    target.say("I am the target!")
    target.tp(0, 100, 0)
    
    # Modify NBT data directly using Dict literals
    target.set_nbt({"CustomName":'"Bessie"'})
```

### Production-Ready Command DSL (New!)
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

### Lifecycle Hooks
* `def main():` -> Hooked into `#minecraft:load`
* `def tick():` -> Hooked into `#minecraft:tick`

---

# Part 15 & 16 — Compiler Internals & Optimizations

### The Diagnostic Engine (New in v2.0)
Aether v2.0 introduces a decoupled `DiagnosticEngine`. Instead of throwing exceptions and crashing on the first error, the Lexer, Parser, and Semantic Analyzer log diagnostics. 
* **Error Recovery:** If the parser encounters a missing `:`, it reports the error, skips tokens until the next newline, and continues parsing the rest of the file.
* **Symbol Table:** The semantic analyzer uses a formal `SymbolTable` to track scopes. It will now log warnings for unused variables and variables that shadow outer scopes.

### Optimizations
1. **AST Optimizer:** Constant folding, loop unrolling.
2. **IR Optimizer:** Dead Code Elimination. If a scoreboard variable is set but never read, the compiler deletes it. Unused generated branch functions are pruned.

---

# Part 17 — Error Messages & Diagnostics

Aether v2.0 features Rust/Clang style error formatting. Errors include line/column, source snippets, underlines, and helpful hints.

```text
error[E202]: Expected ':' (Got NEWLINE)
 --> main.ae:4:24
  |
4 |     if hp > 0
  |                        ^ Expected ':' (Got NEWLINE)
  |
  = hint: Did you forget a ':' at the end of the statement?
```

### Warning Codes (300s)
* **E304 (Unused Variable):** Logged when a variable is declared but never used in its scope.
* **E305 (Shadowed Variable):** Logged when a variable name hides an outer variable.

---

# Part 18 & 19 — Architecture & Best Practices

* **Small:** One `main.ae` file.
* **Medium:** `main.ae` + `lib/` folder for utilities.
* **Large:** Split by domain (`combat.ae`, `economy.ae`, `ui.ae`), all imported into `main.ae`.
* **Name variables clearly:** The compiler uses them in scoreboards (`var_player_hp_0`).
* **Prefer `for` over `while`:** `for` loops are compile-time unrolled and have zero lag cost.

---

# Part 20 — Advanced Topics

### Interoperability with Vanilla Systems
By using the `@objective("name")` decorator, you can seamlessly bridge Aether's internal memory management with vanilla Minecraft systems. This is highly useful for reading vanilla stats (like `deathCount`), interacting with the `food` objective, or integrating with external datapacks that rely on specific scoreboard objectives.

### Compile-Time Execution
Because the optimizer evaluates math and loops at compile time, you can use Aether to generate massive structures (like a sphere) without any runtime lag.
```python
for phi in range(0, 360, 30):
    local x = math::cos(phi) / 1000
    setblock("stone", at=(x, 0, 0))
```

---

# Part 21 — Complete Examples

### Snowball Trail
```python
namespace trail_pack

def main():
    run("scoreboard objectives add trail_timer dummy")

def tick():
    run("execute as @e[type=snowball] at @s run function trail_pack:place_trail")
    run("execute as @e[type=marker,tag=trail_block] at @s run function trail_pack:update_trail")

def place_trail():
    run("setblock ~ ~ ~ minecraft:cobblestone")
    run('summon marker ~ ~ ~ {Tags:["trail_block"]}')

def update_trail():
    run("execute unless score @s trail_timer matches 0.. run scoreboard players set @s trail_timer 0")
    run("scoreboard players add @s trail_timer 1")
    run("execute if score @s trail_timer matches 200.. run function trail_pack:remove_trail")

def remove_trail():
    run("setblock ~ ~ ~ air")
    run("kill @s")
```

### Dynamic Entity Manipulation (New!)
```python
# main.ae
namespace my_game

def main():
    say("Starting script...")
    
    # Dict Literals (NBT Compounds)
    local zombie_gear = {
        "id": "minecraft:diamond_sword",
        "Count": 1,
        "tag": {"Enchantments": [{"id": "minecraft:sharpness", "lvl": 5}]}
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

---

# Part 22 — Language Reference

* **Keywords:** `namespace`, `class`, `def`, `if`, `elif`, `else`, `for`, `while`, `return`, `local`, `import`, `in`, `range`, `self`, `and`, `or`, `not`, `true`, `false`, `int`, `string`, `bool`, `execute`.
* **Decorators:** `@objective("name")`.
* **Builtins:** `say`, `give`, `summon`, `tp`, `setblock`, `fill`, `effect`, `particle`, `playsound`, `clear`, `title`, `kill`, `run`, `wait`, `entity`.
* **Math:** `math::sin`, `math::cos`, `math::sqrt`.

---

# Part 23 — Appendix

### Datapack Folder Layout
```text
my_datapack/
├── pack.mcmeta
└── data/
    ├── minecraft/
    │   └── tags/
    │       └── function/
    │           ├── load.json
    │           └── tick.json
    └── my_game/
        └── function/
            ├── main.mcfunction
            └── ...
```

### FAQ
**Q: Can I use floats?**
A: No, Minecraft scoreboards are integers. Use scaled integers (e.g., `1000` = `1.0`).

**Q: How do I debug?**
A: Run `/scoreboard objectives setdisplay sidebar ae_int` in Minecraft to see all your internal variables on screen!

**Q: How do I read vanilla death counts?**
A: Use the `@objective("deathCount")` decorator on an `int` variable.