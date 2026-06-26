# Aether Compiler

Aether compiles JavaScript/Bolt-style `.ae` files into Minecraft Java Edition 1.21+ datapacks.

Requires Python 3.9+.

## Status

Aether is an early, lightweight compiler. The core path works: JS-style functions and variables, raw Minecraft command passthrough, compile-time loops, imports, macro interpolation, datapack output, and copied `data/` assets. It does not currently include a formatter, language server, standard library, project initializer, or command autocomplete.

```js
namespace "my_game";

function main() {
    let hp: int = 100;
    hp -= 20;

    tellraw @a {"text":"HP is {hp}","color":"gold"}

    for (let i = 0; i < 3; i++) {
        summon minecraft:zombie ~{i} ~ ~
    }
}

function tick() {
    execute as @e[type=zombie] at @s {
        particle minecraft:flame ~ ~1 ~ 0 0 0 0 1
    }
}
```

## Install

From PyPI after the package is published:

```bash
pip install aether-compiler
```

From a local checkout:

```bash
pip install -e .
```

## Use

```bash
aether main.ae -o my_datapack
aether ./project -w -o ./world/datapacks/my_pack
```

If the source is a directory, Aether looks for `main.ae`. Any `data/` folder beside it is copied into the generated datapack.

There is no `--debug` flag yet.

## Language

- `namespace "name";`
- `import "./file.ae";`
- `function main() { ... }` runs on load.
- `function tick() { ... }` runs every tick.
- `let` / `var` are mutable; `const` is immutable.
- Types: `int`, `bool`, `string`, plus simple arrays.
- Inside functions and blocks, any line that is not Aether syntax is emitted as a Minecraft command.
- Commands can be written directly: `say Hi`, `give @s minecraft:diamond`, or `/say Hi`.
- Aether does not validate command names or arguments; it passes them through so new Minecraft commands keep working.
- Use a leading `/` when a command conflicts with Aether syntax, for example `/return 1`.
- `{name}` inside commands injects variables or compile-time loop values.
- Compile-time loops: `for (let i = 0; i < 5; i++)` and `for (let i of range(0, 5))`.

## Development

```bash
python -m unittest discover -s tests
```

Compile every example:

```bash
for dir in examples/*; do aether "$dir" -o "dist/$(basename "$dir")"; done
```

## Examples

- `examples/basic`
- `examples/combat_system`
- `examples/custom_recipe`
- `examples/execute_blocks`

Input:

```js
function main() {
    say Hello
}
```

Generated `main.mcfunction`:

```mcfunction
say Hello
```

More syntax detail lives in [book.md](book.md). Changes are tracked in [CHANGELOG.md](CHANGELOG.md).
Release and PyPI upload steps live in [docs/PUBLISHING.md](docs/PUBLISHING.md).
