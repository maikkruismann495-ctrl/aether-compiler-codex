Yes, the syntax of Aether v3 is already incredibly simple, but to make it *truly* 3-year-old friendly, we are making one final tweak: **We have completely removed semicolons (`;`).** You never have to think about them again.

Here is the final, simplified Aether v3 handbook. If you can read this, you can write Aether.

***

# 📘 The Aether Handbook (v3.0)

Aether is designed to be as easy as writing plain English. If you know how to type a Minecraft command (like `/give @s diamond`), you already know 90% of Aether. The other 10% is just a few easy rules to make your code clean and smart.

Here is the entire language, explained in 5 simple rules.

---

## Rule 1: It's Just Minecraft Commands
Any line that starts with a `/` is just a normal Minecraft command. Aether doesn't change it, it just sends it straight to the game.

```rust
fn main() {
    /give @s minecraft:diamond 1
    /say Hello World!
    /particle minecraft:flame ~ ~ ~ 0 0 0 0 10
}
```
*See? You already know how to do this.*

---

## Rule 2: Smart Variables (Boxes for Data)
Instead of dealing with ugly scoreboards, you just use `let` to create a box, put a number in it, and give it a name.

* Use `let mut` if you want to be able to change the number later.
* Use `let` if you want it to stay the same forever.

```rust
fn main() {
    let mut hp = 100  // Create a box named 'hp', put 100 in it. We can change this later.
    let max_hp = 100  // Create a box named 'max_hp'. It stays 100 forever.

    hp = hp - 20      // Take 20 away from hp. Now hp is 80.
}
```

### The Magic Trick: `{var}` in Commands
This is the best part. You can put your variables directly inside your commands using `{curly brackets}`. Aether does all the hard work behind the scenes to make Minecraft understand it!

```rust
fn main() {
    let mut score = 5
    score = score + 1

    // Aether automatically injects the number into your command!
    /tellraw @a {"text":"Your score is {score}!"}
}
```

---

## Rule 3: Easy "If" Statements
Want to do something *only* if a player has enough points? Just use `if`.

You can use Aether's smart math: `if score > 10 {`
Or, you can just use raw Minecraft commands: `if score @s points matches 10.. {`

```rust
fn check_door() {
    let mut keys = 3

    // If we have more than 0 keys...
    if keys > 0 {
        keys = keys - 1
        /say The door opens!
    } else {
        /say You need a key!
    }
}
```

---

## Rule 4: "Execute" Blocks (No more messy chains)
In vanilla Minecraft, you have to write `execute as @e at @s run...` on *every single line*. 

In Aether, you just write it once, open a `{ bracket`, and put all your commands inside!

```rust
fn tick() {
    // Do this to ALL zombies, at their own location:
    execute as @e[type=zombie] at @s {
        /particle minecraft:flame ~ ~1 ~ 0 0 0 0 1
        /effect give @s minecraft:speed 1 0 true
    }
}
```
*That’s it. No more copying and pasting `execute` 50 times.*

---

## Rule 5: Functions (Grouping Commands)
A function is just a way to group commands together and give them a name. 

* `fn main()` runs automatically when the datapack loads.
* `fn tick()` runs automatically every single game tick (20 times a second).

```rust
// This runs when the datapack loads!
fn main() {
    /say Game Started!
}

// This runs every tick!
fn tick() {
    /weather clear
}

// You can make your own functions too!
fn give_sword() {
    /give @s minecraft:diamond_sword 1
}
```

---

## Bonus Rule: Loops (Doing things multiple times)
If you want to do something 5 times, you don't have to copy-paste it 5 times. Just use `for`.

```rust
fn main() {
    // Do this 5 times (0, 1, 2, 3, 4)
    for i in 0..5 {
        /summon minecraft:zombie ~{i} ~ ~
    }
}
```
*This spawns 5 zombies in a perfect line. Aether does the math for you at compile time, so it causes zero lag!*

---

## You Now Know Aether.
That is the entire language. No complex classes, no massive JSON files, no copy-pasting execute chains, and **no semicolons**. 

Just write your commands, use `let` for numbers, and let Aether do the heavy lifting.

### Quick Example: The Magic Wand
Here is a complete, working Aether program. It gives you an item, and when you use it, it shoots fireballs.

```rust
namespace my_wand

fn main() {
    /give @s minecraft:blaze_rod 1
    /say You got the Fire Wand!
}

fn tick() {
    // If a player is holding a blaze rod and sneaking...
    execute as @a at @s if entity @s[nbt={SelectedItem:{id:"minecraft:blaze_rod"}}] {
        // Shoot a fireball from their eyes!
        /summon minecraft:fireball ^ ^1 ^2 {Motion:[0.0,0.0,2.0]}
        /particle minecraft:flame ^ ^1 ^2 0 0 0 0 10
    }
}
```

Compile it with `aether main.ae -o my_datapack` and you're ready to play. You are now an Aether dev!