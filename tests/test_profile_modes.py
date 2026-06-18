import json
import tempfile
import unittest
from pathlib import Path

from codex_profile_switcher.core import ProfileStore, detect_mode


def write_auth(path: Path) -> None:
    path.write_text(json.dumps({"tokens": {"access_token": "redacted"}}), encoding="utf-8")


class ProfileModeTests(unittest.TestCase):
    def test_env_key_route_is_api_even_when_auth_json_exists(self):
        config = """
model_provider = "custom_gateway"

[model_providers.custom_gateway]
base_url = "https://gateway.example/v1"
env_key = "OPENAI_API_KEY"
requires_openai_auth = false
"""

        self.assertEqual(detect_mode(config, {"tokens": {"access_token": "redacted"}}, "custom_gateway"), "api")


    def test_auth_required_custom_route_is_hybrid(self):
        config = """
model_provider = "custom"

[model_providers.custom]
base_url = "https://gateway.example/v1"
requires_openai_auth = true
wire_api = "responses"
"""

        self.assertEqual(detect_mode(config, {"tokens": {"access_token": "redacted"}}, "custom"), "hybrid")


    def test_mix_api_route_reports_auth_ignored_and_pins_stable_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            andy = root / "andy"
            work = root / "work"
            andy.mkdir(parents=True)
            work.mkdir(parents=True)
            codex_dir.mkdir()

            write_auth(andy / "auth.json")
            (andy / "config.toml").write_text(
                """
[model_providers.OpenAI]
requires_openai_auth = true
""",
                encoding="utf-8",
            )
            (work / "config.toml").write_text(
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
            (codex_dir / "config.toml").write_text("", encoding="utf-8")

            store = ProfileStore(root=root, codex_dir=codex_dir)
            store.mix_profiles("andy", "work")
            active = store.active_status()
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(active.mode, "api")
            self.assertTrue(active.auth_is_ignored)
            # Provider is pinned to the stable, non-reserved name (not the route
            # profile name) so Codex Desktop keeps one conversation-history bucket.
            self.assertEqual(active.provider, "gateway")
            self.assertIn('model_provider = "gateway"', config)
            self.assertIn("[model_providers.gateway]", config)
            self.assertNotIn('model_provider = "work"', config)
            # Never emit a reserved built-in id that Codex refuses to load.
            self.assertNotIn("[model_providers.openai]", config.lower())
            # Route keys survive the rename.
            self.assertIn('base_url = "https://gateway.example/v1"', config)
            self.assertIn('env_key = "OPENAI_API_KEY"', config)
            self.assertIn("requires_openai_auth = false", config)
            self.assertEqual(
                (codex_dir / "auth.json").read_text(encoding="utf-8"),
                (andy / "auth.json").read_text(encoding="utf-8"),
            )


    def test_use_profile_keeps_embedded_codex_home_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            work = root / "work"
            work.mkdir(parents=True)
            codex_dir.mkdir()

            (work / "config.toml").write_text(
                f"""
[mcp_servers.node_repl.env]
NODE_REPL_TRUSTED_CODE_PATHS = "{work}"
CODEX_HOME = "{work}"
""",
                encoding="utf-8",
            )

            store = ProfileStore(root=root, codex_dir=codex_dir)
            store.use_profile("work")

            config = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn(f'CODEX_HOME = "{codex_dir}"', config)
            self.assertIn(f'NODE_REPL_TRUSTED_CODE_PATHS = "{codex_dir}"', config)
            self.assertNotIn(str(work), config)


    def test_mix_profiles_keeps_embedded_codex_home_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            andy = root / "andy"
            work = root / "work"
            andy.mkdir(parents=True)
            work.mkdir(parents=True)
            codex_dir.mkdir()

            write_auth(andy / "auth.json")
            (work / "config.toml").write_text(
                f"""
model_provider = "custom_gateway"
model = "gpt-5.5"

[model_providers.custom_gateway]
base_url = "https://gateway.example/v1"
env_key = "OPENAI_API_KEY"

[mcp_servers.node_repl.env]
NODE_REPL_TRUSTED_CODE_PATHS = "{work}"
CODEX_HOME = "{work}"
""",
                encoding="utf-8",
            )

            store = ProfileStore(root=root, codex_dir=codex_dir)
            store.mix_profiles("andy", "work")

            config = (codex_dir / "config.toml").read_text(encoding="utf-8")
            self.assertIn(f'CODEX_HOME = "{codex_dir}"', config)
            self.assertIn(f'NODE_REPL_TRUSTED_CODE_PATHS = "{codex_dir}"', config)
            self.assertNotIn(str(work), config)


class ProviderStabilityTests(unittest.TestCase):
    """Switching between routes must keep one stable, Codex-valid provider name so
    Codex Desktop keeps the conversation-history bucket and the config still loads."""

    def _make_store(self, temp_dir):
        root = Path(temp_dir) / "profiles"
        codex_dir = Path(temp_dir) / "active"
        codex_dir.mkdir(parents=True)
        return ProfileStore(root=root, codex_dir=codex_dir), root, codex_dir

    def test_api_routes_share_one_stable_bucket(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, root, _codex_dir = self._make_store(temp_dir)
            personal = root / "personal"
            personal.mkdir(parents=True)
            write_auth(personal / "auth.json")
            (personal / "config.toml").write_text(
                "[model_providers.OpenAI]\nrequires_openai_auth = true\n",
                encoding="utf-8",
            )
            for name, gateway in (("work", "https://a.example/v1"), ("alt", "https://b.example/v1")):
                route = root / name
                route.mkdir(parents=True)
                write_auth(route / "auth.json")
                (route / "config.toml").write_text(
                    f'model_provider = "{name}_p"\nmodel = "gpt-5.5"\n\n'
                    f'[model_providers.{name}_p]\nbase_url = "{gateway}"\n'
                    'env_key = "OPENAI_API_KEY"\nrequires_openai_auth = false\n',
                    encoding="utf-8",
                )

            store.mix_profiles("personal", "work")
            self.assertEqual(store.active_status().provider, "gateway")
            store.mix_profiles("personal", "alt")
            self.assertEqual(store.active_status().provider, "gateway")

    def test_account_uses_gateway_auth_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, root, codex_dir = self._make_store(temp_dir)
            personal = root / "personal"
            personal.mkdir(parents=True)
            write_auth(personal / "auth.json")
            # Legacy auth profile carrying the now-illegal reserved section.
            (personal / "config.toml").write_text(
                "[model_providers.OpenAI]\nname = \"OpenAI\"\nrequires_openai_auth = true\n",
                encoding="utf-8",
            )

            store.mix_profiles("personal", "personal")
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(store.active_status().provider, "gateway")
            self.assertIn('model_provider = "gateway"', config)
            self.assertIn("[model_providers.gateway]", config)
            self.assertIn("requires_openai_auth = true", config)
            # The illegal reserved override section must be gone.
            self.assertNotIn("[model_providers.openai]", config.lower())

    def test_route_custom_pins_provider_and_keeps_hybrid_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, _root, codex_dir = self._make_store(temp_dir)
            (codex_dir / "config.toml").write_text("", encoding="utf-8")

            store.route_custom(
                base_url="https://gateway.example/v1",
                model="gpt-5.5",
                api_key="sk-secret-key",
                provider="gateway",
            )
            active = store.active_status()
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(active.provider, "gateway")
            self.assertEqual(active.mode, "hybrid")
            self.assertIn('model_provider = "gateway"', config)
            self.assertIn("[model_providers.gateway]", config)
            self.assertNotIn("[model_providers.openai]", config.lower())
            self.assertIn("requires_openai_auth = true", config)
            self.assertIn('experimental_bearer_token = "sk-secret-key"', config)
            self.assertIn('base_url = "https://gateway.example/v1"', config)

    def test_route_custom_defaults_to_env_key_api_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, _root, codex_dir = self._make_store(temp_dir)
            (codex_dir / "config.toml").write_text("", encoding="utf-8")

            store.route_custom(
                base_url="https://gateway.example/v1",
                model="gpt-5.5",
                provider="gateway",
            )
            active = store.active_status()
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(active.provider, "gateway")
            self.assertEqual(active.mode, "api")
            self.assertIn('model_provider = "gateway"', config)
            self.assertIn("[model_providers.gateway]", config)
            self.assertIn('base_url = "https://gateway.example/v1"', config)
            self.assertIn('env_key = "OPENAI_API_KEY"', config)
            self.assertIn("requires_openai_auth = false", config)
            self.assertNotIn("experimental_bearer_token", config)

    def test_create_route_profile_defaults_to_env_key_api_route(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, root, _codex_dir = self._make_store(temp_dir)

            path = store.create_route_profile(
                "work",
                base_url="https://gateway.example/v1",
                model="gpt-5.5",
            )
            config = (path / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(path, root / "work")
            self.assertIn('model_provider = "gateway"', config)
            self.assertIn("[model_providers.gateway]", config)
            self.assertIn('base_url = "https://gateway.example/v1"', config)
            self.assertIn('env_key = "OPENAI_API_KEY"', config)
            self.assertIn("requires_openai_auth = false", config)
            self.assertNotIn("experimental_bearer_token", config)

    def test_route_official_uses_gateway_auth_section(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, _root, codex_dir = self._make_store(temp_dir)
            (codex_dir / "config.toml").write_text(
                'model_provider = "gateway"\n\n[model_providers.gateway]\n'
                'base_url = "https://gateway.example/v1"\n',
                encoding="utf-8",
            )

            store.route_official(model="gpt-5.5")
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(store.active_status().provider, "gateway")
            self.assertIn('model_provider = "gateway"', config)
            self.assertIn("[model_providers.gateway]", config)
            self.assertIn("requires_openai_auth = true", config)
            self.assertNotIn('base_url = "https://gateway.example/v1"', config)

    def test_custom_active_provider_name_is_respected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store, _root, codex_dir = self._make_store(temp_dir)
            store.active_provider = "codex"
            (codex_dir / "config.toml").write_text("", encoding="utf-8")

            store.route_custom(
                base_url="https://gateway.example/v1",
                model="gpt-5.5",
                api_key="sk-secret-key",
                provider="gateway",
            )
            config = (codex_dir / "config.toml").read_text(encoding="utf-8")

            self.assertEqual(store.active_status().provider, "codex")
            self.assertIn('model_provider = "codex"', config)
            self.assertIn("[model_providers.codex]", config)
            self.assertIn('experimental_bearer_token = "sk-secret-key"', config)

    def test_reserved_name_is_never_used_even_if_configured(self):
        import os

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "profiles"
            codex_dir = Path(temp_dir) / "active"
            codex_dir.mkdir(parents=True)
            os.environ["CODEX_ACTIVE_PROVIDER"] = "openai"
            try:
                store = ProfileStore(root=root, codex_dir=codex_dir)
            finally:
                del os.environ["CODEX_ACTIVE_PROVIDER"]
            self.assertNotEqual(store.active_provider.lower(), "openai")


class NormalizeProviderConfigTests(unittest.TestCase):
    def test_route_section_renamed_and_keys_preserved(self):
        from codex_profile_switcher.core import normalize_active_provider_config

        config = """model_provider = "custom_gateway"
preferred_auth_method = "chatgpt"

[model_providers.custom_gateway]
name = "custom_gateway"
base_url = "https://gateway.example/v1"
requires_openai_auth = true
experimental_bearer_token = "sk-keep-me"
"""
        out = normalize_active_provider_config(config, canonical="gateway")
        self.assertIn('model_provider = "gateway"', out)
        self.assertIn("[model_providers.gateway]", out)
        self.assertIn('name = "gateway"', out)
        self.assertIn("requires_openai_auth = true", out)
        self.assertIn('experimental_bearer_token = "sk-keep-me"', out)
        self.assertNotIn("[model_providers.custom_gateway]", out)

    def test_reserved_override_sections_are_dropped(self):
        from codex_profile_switcher.core import normalize_active_provider_config

        config = """model_provider = "openai"

[model_providers.OpenAI]
name = "OpenAI"
requires_openai_auth = true
"""
        out = normalize_active_provider_config(config, canonical="gateway")
        self.assertIn('model_provider = "gateway"', out)
        self.assertIn("[model_providers.gateway]", out)
        self.assertIn("requires_openai_auth = true", out)
        self.assertNotIn("[model_providers.openai]", out.lower())

    def test_misnamed_reserved_route_is_promoted_to_canonical(self):
        from codex_profile_switcher.core import normalize_active_provider_config

        # A gateway route that illegally lived under the reserved "OpenAI" id.
        config = """model_provider = "OpenAI"

[model_providers.OpenAI]
name = "OpenAI"
base_url = "https://gateway.example/v1"
env_key = "OPENAI_API_KEY"
"""
        out = normalize_active_provider_config(config, canonical="gateway")
        self.assertIn('model_provider = "gateway"', out)
        self.assertIn("[model_providers.gateway]", out)
        self.assertIn('base_url = "https://gateway.example/v1"', out)
        self.assertIn('env_key = "OPENAI_API_KEY"', out)
        self.assertNotIn("[model_providers.openai]", out.lower())


if __name__ == "__main__":
    unittest.main()
