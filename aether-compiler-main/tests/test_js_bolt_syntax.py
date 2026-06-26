import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Tuple

from aether.cli import run_compilation
from aether.diagnostics import DiagnosticEngine
from aether.lexer import Lexer
from aether.tokens import TokenType


class JavaScriptBoltSyntaxTests(unittest.TestCase):
    def compile_source(self, source: str) -> Tuple[bool, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project = Path(temp_dir.name)
        source_path = project / "main.ae"
        out_dir = project / "out"
        source_path.write_text(source, encoding="utf-8")
        data_dir = project / "data"
        manual_data_dir = str(data_dir) if data_dir.exists() else None
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ok = run_compilation(str(source_path), str(out_dir), manual_data_dir)
        return ok, out_dir

    def compile_project(self, files) -> Tuple[bool, Path]:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        project = Path(temp_dir.name)
        for rel_path, content in files.items():
            path = project / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        out_dir = project / "out"
        data_dir = project / "data"
        manual_data_dir = str(data_dir) if data_dir.exists() else None
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ok = run_compilation(str(project), str(out_dir), manual_data_dir)
        return ok, out_dir

    def test_compiles_js_style_language_with_bolt_style_commands(self):
        ok, out_dir = self.compile_source(
            """
namespace "demo";

function add(x: int, y: int): int {
    return x + y;
}

function main() {
    let hp: int = add(70, 30);
    hp -= 20;

    const scores = [10, 20, 30];
    let first: int = scores[0];

    if (hp > 50 && first == 10) {
        say Healthy
    } else {
        tellraw @a {"text":"HP is {hp}","color":"gold"}
    }

    for (let i = 0; i < 3; i++) {
        summon minecraft:zombie ~{i} ~ ~
    }
}

function tick() {
    execute as @e[type=zombie] at @s {
        particle minecraft:flame ~ ~1 ~ 0 0 0 0 1
    }
}
"""
        )

        self.assertTrue(ok)
        main_file = out_dir / "data" / "demo" / "function" / "main.mcfunction"
        self.assertTrue(main_file.exists())
        generated = "\n".join(p.read_text(encoding="utf-8") for p in (out_dir / "data" / "demo" / "function").glob("*.mcfunction"))
        self.assertIn("say Healthy", generated)
        self.assertIn("summon minecraft:zombie ~0 ~ ~", generated)
        self.assertIn("summon minecraft:zombie ~2 ~ ~", generated)

    def test_rejects_const_reassignment(self):
        ok, _ = self.compile_source(
            """
function main() {
    const hp = 100;
    hp = 80;
}
"""
        )

        self.assertFalse(ok)

    def test_compiles_utf8_bom_source(self):
        ok, out_dir = self.compile_source(
            "\ufeff" + """
namespace "bom";

function main() {
    say Hello
}
"""
        )

        self.assertTrue(ok)
        self.assertTrue((out_dir / "data" / "bom" / "function" / "main.mcfunction").exists())

    def test_passes_minecraft_commands_through_without_wrappers(self):
        ok, out_dir = self.compile_source(
            """
namespace "cmds";

function main() {
    data merge entity @s {Health:20f,Tags:["aether"]}
    execute as @a at @s run tellraw @s {"text":"Hi","color":"green"}
    function cmds:helper
    reload
    future_command added_by_minecraft_later @s {foo:1b}
    return run say Done
}

function helper() {
    say Helper
}
"""
        )

        self.assertTrue(ok)
        main_text = (out_dir / "data" / "cmds" / "function" / "main.mcfunction").read_text(encoding="utf-8")
        self.assertIn('data merge entity @s {Health:20f,Tags:["aether"]}', main_text)
        self.assertIn('execute as @a at @s run tellraw @s {"text":"Hi","color":"green"}', main_text)
        self.assertIn("function cmds:helper", main_text)
        self.assertIn("reload", main_text)
        self.assertIn("future_command added_by_minecraft_later @s {foo:1b}", main_text)
        self.assertIn("return run say Done", main_text)

    def test_lexer_treats_unknown_command_as_raw_command_inside_block(self):
        source = """
function main() {
    future_command @s {foo:1b}
}
"""
        engine = DiagnosticEngine("main.ae", source)
        tokens = Lexer(source, engine).tokenize()
        raw_commands = [t for t in tokens if t.type == TokenType.RAW_CMD]

        self.assertFalse(engine.has_errors)
        self.assertEqual(1, len(raw_commands))
        self.assertEqual("/future_command @s {foo:1b}", raw_commands[0].value)

    def test_macros_generate_storage_and_macro_function(self):
        ok, out_dir = self.compile_source(
            """
namespace "macro";

function main() {
    let hp = 40;
    hp += 2;
    tellraw @a {"text":"HP {hp}"}
}
"""
        )

        self.assertTrue(ok)
        function_dir = out_dir / "data" / "macro" / "function"
        main_text = (function_dir / "main.mcfunction").read_text(encoding="utf-8")
        macro_text = (function_dir / "__macro_0.mcfunction").read_text(encoding="utf-8")
        self.assertIn("execute store storage macro:data macro_hp int 1", main_text)
        self.assertIn("function macro:__macro_0 with storage macro:data {macro_hp}", main_text)
        self.assertIn('$tellraw @a {"text":"HP $(macro_hp)"}', macro_text)

    def test_imports_are_inlined(self):
        ok, out_dir = self.compile_project({
            "main.ae": """
namespace "imports";
import "./shared.ae";

function main() {
    shared();
}
""",
            "shared.ae": """
function shared() {
    say Imported
}
""",
        })

        self.assertTrue(ok)
        function_dir = out_dir / "data" / "imports" / "function"
        self.assertTrue((function_dir / "shared.mcfunction").exists())
        self.assertIn("function imports:shared", (function_dir / "main.mcfunction").read_text(encoding="utf-8"))

    def test_missing_import_fails_without_exiting_process(self):
        ok, _ = self.compile_project({
            "main.ae": """
import "./missing.ae";

function main() {
    say Never
}
""",
        })

        self.assertFalse(ok)

    def test_circular_import_fails_without_exiting_process(self):
        ok, _ = self.compile_project({
            "main.ae": 'import "./a.ae";\nfunction main() { say Never }\n',
            "a.ae": 'import "./b.ae";\n',
            "b.ae": 'import "./a.ae";\n',
        })

        self.assertFalse(ok)

    def test_copies_data_assets_into_datapack(self):
        ok, out_dir = self.compile_project({
            "main.ae": """
namespace "assets";

function main() {
    say Assets
}
""",
            "data/assets/recipe/magic.json": json.dumps({
                "type": "minecraft:crafting_shaped",
                "pattern": ["D"],
                "key": {"D": "minecraft:diamond"},
                "result": {"id": "minecraft:diamond"}
            }),
        })

        self.assertTrue(ok)
        copied = out_dir / "data" / "assets" / "recipe" / "magic.json"
        self.assertTrue(copied.exists())
        self.assertEqual("minecraft:crafting_shaped", json.loads(copied.read_text(encoding="utf-8"))["type"])

    def test_syntax_errors_fail_compilation(self):
        ok, _ = self.compile_source(
            """
function main() {
    let hp = ;
}
"""
        )

        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
