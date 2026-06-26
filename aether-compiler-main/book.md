# Aether Handbook

Aether is a small `.ae` to datapack compiler. The syntax is JavaScript-like for program structure and Bolt-like for raw Minecraft commands.

Current working surface: source imports, functions, variables, simple arrays, raw commands, command macros, execute blocks, compile-time loops, datapack generation, and copied `data/` assets.

## Files

```js
namespace "my_game";
import "./shared.ae";
```

`main.ae` is the entry point. `main()` runs on datapack load; `tick()` runs every tick.

## Functions

```js
function add(a: int, b: int): int {
    return a + b;
}

function main() {
    say Loaded
}
```

Parameter types default to `int` when omitted.

## Values

```js
let hp: int = 100;
const alive: bool = true;
const name: string = "Aether";
const scores = [10, 20, 30];

hp -= 20;
let first: int = scores[0];
```

Supported operators:

- Math: `+`, `-`, `*`, `/`, `%`
- Assignment: `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `++`, `--`
- Compare: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Boolean: `&&`, `||`, `!`

## Commands

Inside functions and blocks, any line that is not Aether syntax is emitted as a Minecraft command. Aether does not validate command names or arguments.

```js
say Hello
/give @s minecraft:diamond 1
tellraw @a {"text":"HP is {hp}","color":"gold"}
data merge entity @s {Health:20f,Tags:["aether"]}
execute as @a at @s run say Hi
```

`{name}` injects an Aether value. Runtime values compile through Minecraft macro storage; compile-time loop values are inlined.

Use a leading `/` when a command conflicts with Aether syntax, for example `/return 1`.

## Control Flow

```js
if (hp > 50) {
    say Healthy
} else {
    say Hurt
}

if score @s kills matches 10.. {
    give @s minecraft:diamond 1
}
```

`execute` blocks compile the body into a helper function and run it through the execute chain:

```js
execute as @e[type=zombie] at @s {
    particle minecraft:flame ~ ~1 ~ 0 0 0 0 1
}
```

## Compile-Time Loops

```js
for (let i = 0; i < 5; i++) {
    summon minecraft:zombie ~{i} ~ ~
}

for (let i of range(0, 5)) {
    say Index {i}
}
```

Loop bounds must be constant integers. The current step is `1`.

## Limits

- JavaScript syntax is only the source language shape; Aether does not run JavaScript.
- Runtime values are scoreboard-backed.
- Function calls are practical for `int` and `bool` values.
- Array indices must be literal integers in generated code.
- Legacy `fn`, `let mut`, `use "file.ae";`, and `0..5` syntax may parse, but new code should use the forms above.
- No formatter, language server, standard library, project initializer, command autocomplete, or `--debug` flag is implemented yet.
