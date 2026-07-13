import json
import tempfile
import unittest
from pathlib import Path

from codex_profile_switcher.core import DEFAULT_ENV_KEY, ProfileStore
from codex_profile_switcher.tui import App


class FakeScreen:
    def clear(self):
        pass

    def refresh(self):
        pass


class DrawScreen(FakeScreen):
    def __init__(self, height: int = 32, width: int = 120) -> None:
        self.height = height
        self.width = width
        self.lines: list[tuple[int, int, str, int]] = []

    def erase(self):
        self.lines.clear()

    def getmaxyx(self):
        return self.height, self.width

    def addstr(self, y, x, text, attr=0):
        self.lines.append((y, x, text, attr))

    def text(self) -> str:
        rows: dict[int, list[tuple[int, str]]] = {}
        for y, x, line, _attr in self.lines:
            rows.setdefault(y, []).append((x, line))
        rendered: list[str] = []
        for y in sorted(rows):
            row = ""
            for x, line in sorted(rows[y]):
                if len(row) < x:
                    row += " " * (x - len(row))
                row = row[:x] + line
            rendered.append(row.rstrip())
        return "\n".join(rendered)


def write_auth(path: Path) -> None:
    path.write_text(json.dumps({"tokens": {"access_token": "redacted"}}), encoding="utf-8")


def backup_count(root: Path) -> int:
    backups = root / "backups"
    if not backups.exists():
        return 0
    return len(list(backups.iterdir()))


class TuiConfirmedApplyTests(unittest.TestCase):
    def test_selecting_gateway_route_stages_then_confirm_applies_with_selected_auth(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            auth = root / "personal"
            route = root / "work"
            auth.mkdir(parents=True)
            route.mkdir(parents=True)
            codex_dir.mkdir()
            write_auth(auth / "auth.json")
            (route / "config.toml").write_text(
                """
model_provider = "custom_gateway"
model = "gpt-5.5"

[model_providers.custom_gateway]
base_url = "https://gateway.example/v1"
env_key = "OPENAI_API_KEY"
requires_openai_auth = false
""",
                encoding="utf-8",
            )

            store = ProfileStore(root=root, codex_dir=codex_dir)
            app = App(FakeScreen(), store)
            app.chosen_auth = "personal"
            app.focus = "route"

            app.choose_current()

            self.assertIsNone(app.pending_apply)
            self.assertFalse((codex_dir / "config.toml").exists())
            self.assertTrue(any("Draft gateway route: work" in line for line in app.history))

            app.request_apply_selection()

            self.assertEqual(app.pending_apply, ("personal", "work"))
            self.assertFalse((codex_dir / "config.toml").exists())

            app.handle_apply_confirmation(ord("y"))

            active = store.active_status()
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertEqual(active.mode, "hybrid")
            self.assertEqual(active.provider, "gateway")
            self.assertIn('base_url = "https://gateway.example/v1"', config)
            self.assertIn("requires_openai_auth = true", config)
            self.assertEqual(
                (codex_dir / "auth.json").read_text(encoding="utf-8"),
                (auth / "auth.json").read_text(encoding="utf-8"),
            )
            self.assertTrue(any("Applied auth=personal gateway=work" in line for line in app.history))

            backups_before = backup_count(root)
            app.request_apply_selection()
            self.assertEqual(backup_count(root), backups_before)
            self.assertTrue(any("already uses auth=personal gateway=work" in line for line in app.history))

    def test_saving_gateway_form_stages_when_auth_is_selected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            auth = root / "personal"
            auth.mkdir(parents=True)
            codex_dir.mkdir()
            write_auth(auth / "auth.json")

            store = ProfileStore(root=root, codex_dir=codex_dir)
            app = App(FakeScreen(), store)
            app.chosen_auth = "personal"
            app.api_form.values.update(
                {
                    "name": "work",
                    "base_url": "https://gateway.example/v1",
                    "model": "gpt-5.5",
                    "env_key": DEFAULT_ENV_KEY,
                    "provider": "gateway",
                    "wire_api": "responses",
                }
            )

            app.save_api_form()

            self.assertEqual(app.mode, "main")
            self.assertEqual(app.chosen_route, "work")
            self.assertIsNone(app.pending_apply)
            self.assertNotEqual(store.active_status().mode, "hybrid")
            self.assertTrue(any("Draft gateway route: work" in line for line in app.history))

            app.request_apply_selection()
            self.assertEqual(app.pending_apply, ("personal", "work"))
            app.handle_apply_confirmation(ord("y"))

            self.assertEqual(store.active_status().mode, "hybrid")
            self.assertEqual(store.active_status().base_url, "https://gateway.example/v1")
            self.assertTrue(any("Applied auth=personal gateway=work" in line for line in app.history))

    def test_main_page_draws_draft_apply_preview(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            auth = root / "personal"
            route = root / "work"
            auth.mkdir(parents=True)
            route.mkdir(parents=True)
            codex_dir.mkdir()
            write_auth(auth / "auth.json")
            (route / "config.toml").write_text(
                """
model_provider = "gateway"
model = "gpt-5.5"

[model_providers.gateway]
base_url = "https://gateway.example/v1"
env_key = "OPENAI_API_KEY"
requires_openai_auth = false
""",
                encoding="utf-8",
            )

            store = ProfileStore(root=root, codex_dir=codex_dir)
            screen = DrawScreen()
            app = App(screen, store)
            app.chosen_auth = "personal"
            app.chosen_route = "work"

            app.draw_main_page(screen.height, screen.width)

            text = screen.text()
            self.assertIn("Apply preview", text)
            self.assertIn("auth.json      <- personal", text)
            self.assertIn("config.toml    <- work", text)
            self.assertIn("request path   -> uses selected auth + gateway", text)
            self.assertIn("Enter: review and confirm before writing", text)
            self.assertIn("Space: change draft only", text)

    def test_compact_main_page_uses_short_logo_and_footer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            root.mkdir(parents=True)
            codex_dir.mkdir()

            store = ProfileStore(root=root, codex_dir=codex_dir)
            screen = DrawScreen(height=24, width=88)
            app = App(screen, store)

            app.draw_main_page(screen.height, screen.width)

            text = screen.text()
            self.assertNotIn("Version:", text)
            self.assertIn("[Space] draft", text)
            self.assertIn("[Enter] apply", text)

    def test_doctor_command_logs_findings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"

            store = ProfileStore(root=root, codex_dir=codex_dir)
            app = App(FakeScreen(), store)

            app.run_command("/doctor")

            self.assertTrue(any("Doctor:" in line for line in app.history))
            self.assertTrue(any("Codex directory does not exist" in line for line in app.history))

    def test_doctor_menu_action_logs_findings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"

            store = ProfileStore(root=root, codex_dir=codex_dir)
            app = App(FakeScreen(), store)

            app.run_menu_action("doctor")

            self.assertEqual(app.mode, "main")
            self.assertTrue(any("Doctor:" in line for line in app.history))


if __name__ == "__main__":
    unittest.main()
