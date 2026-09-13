from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from agent_workstation.context import ancestors, discover, safe_file
from agent_workstation.integrations import Catalog

SKILL = (
    "---\nname: incident\ndescription: >\n  Diagnose a local service\n  using CLI evidence.\n---\nFull body\n"
)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, name, content="rules"):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return p

    def test_direct_children_not_recursive(self):
        self.write("repo/AGENTS.md")
        self.write("repo/deep/AGENTS.md")
        self.assertEqual(discover(self.root, Mock(), []), ["repo/AGENTS.md"])

    def test_git_metadata_only_for_real_repository_roots(self):
        self.write(".git", "gitdir: ignored-in-this-mock")
        self.write("deep/AGENTS.md")
        git = Mock(return_value=["deep/AGENTS.md"])
        self.assertEqual(discover(self.root, git, []), ["deep/AGENTS.md"])
        git.assert_called_once_with(self.root)

    def test_git_failure_falls_back_to_root_rules(self):
        self.write(".git")
        self.write("AGENTS.md")
        self.assertEqual(discover(self.root, Mock(return_value=None), []), ["AGENTS.md"])

    def test_generated_directories_skipped(self):
        for name in (".worktrees", ".codex-worktrees", ".validation", "node_modules"):
            self.write(name + "/AGENTS.md")
        self.assertEqual(discover(self.root, Mock(), []), [])

    def test_target_inside_skipped_tree_still_loads_rules(self):
        self.write("AGENTS.md")
        self.write(".worktrees/feature/AGENTS.md")
        self.write(".worktrees/feature/src/main.py")
        result = Catalog(self.root).guide(".worktrees/feature/src/main.py")
        self.assertEqual([r["path"] for r in result["rules"]], ["AGENTS.md", ".worktrees/feature/AGENTS.md"])

    def test_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "AGENTS.md"
            target.write_text("private")
            (self.root / "AGENTS.md").symlink_to(target)
            self.assertFalse(safe_file(self.root / "AGENTS.md", self.root))
            self.assertEqual(discover(self.root, Mock(), []), [])

    def test_internal_alias_deduplicated(self):
        target = self.write("AGENTS.md")
        (self.root / "CLAUDE.md").symlink_to(target)
        self.assertEqual(discover(self.root, Mock(), []), ["AGENTS.md"])

    def test_cyclic_and_broken_symlinks(self):
        (self.root / "cycle").symlink_to(self.root / "cycle")
        (self.root / "broken").symlink_to(self.root / "missing")
        self.assertFalse(safe_file(self.root / "cycle", self.root))
        self.assertFalse(safe_file(self.root / "broken", self.root))

    def test_directory_symlinks_not_followed_at_startup(self):
        self.write("real/AGENTS.md")
        (self.root / "alias").symlink_to(self.root / "real", target_is_directory=True)
        self.assertEqual(discover(self.root, Mock(), []), ["real/AGENTS.md"])

    def test_limits_are_reported(self):
        self.write("one/AGENTS.md")
        self.write("two/AGENTS.md")
        warnings = []
        self.assertEqual(len(discover(self.root, Mock(), warnings, max_children=1)), 1)
        self.assertTrue(warnings)

    def test_unsafe_git_paths_rejected(self):
        self.write(".git")
        self.write("AGENTS.md")
        result = discover(self.root, Mock(return_value=["../AGENTS.md", "/tmp/AGENTS.md", "AGENTS.md"]), [])
        self.assertEqual(result, ["AGENTS.md"])

    def test_ancestor_order_and_target_validation(self):
        self.write("repo/src/file.py")
        self.assertEqual(
            ancestors(self.root, "repo/src/file.py"), [self.root, self.root / "repo", self.root / "repo/src"]
        )
        for target in ("../anything", str(self.root)):
            with self.assertRaises(ValueError):
                ancestors(self.root, target)

    def test_skill_metadata_supports_multiline_yaml(self):
        self.write("repo/.agents/skills/incident/SKILL.md", SKILL)
        result = Catalog(self.root).guide("repo")
        self.assertEqual(result["skills"][0]["name"], "incident")
        self.assertIn("using CLI evidence", result["skills"][0]["description"])
        self.assertNotIn("Full body", str(result))
        self.assertEqual(len(result["skills"][0]["sha256"]), 64)

    def test_duplicate_skill_names_keep_paths(self):
        self.write(".agents/skills/incident/SKILL.md", SKILL)
        self.write("repo/.agents/skills/incident/SKILL.md", SKILL)
        result = Catalog(self.root).guide("repo")
        self.assertEqual(len(result["skills"]), 2)
        self.assertNotEqual(result["skills"][0]["path"], result["skills"][1]["path"])

    def test_oversized_or_invalid_skill_warns(self):
        self.write(".agents/skills/large/SKILL.md", "x" * 33000)
        self.write(".agents/skills/bad/SKILL.md", "invalid")
        result = Catalog(self.root).guide()
        self.assertFalse(result["skills"])
        self.assertEqual(len(result["warnings"]), 2)

    def test_external_auto_skill_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as out:
            p = Path(out) / "incident"
            p.mkdir()
            (p / "SKILL.md").write_text(SKILL)
            (self.root / ".agents").mkdir()
            (self.root / ".agents/skills").symlink_to(out, target_is_directory=True)
            result = Catalog(self.root).guide()
            self.assertFalse(result["skills"])
            self.assertTrue(result["warnings"])

    def test_config_is_explicit_not_autoloaded(self):
        self.write("agent-workstation.local.toml", "invalid [ TOML")
        self.assertTrue(Catalog(self.root).guide()["ok"])

    def test_recipe_metadata_never_executes(self):
        self.write("skills/incident/SKILL.md", SKILL)
        conf = self.write(
            "workstation.toml",
            'skill_roots=["skills"]\n[recipes.incident]\ndescription="Local incident"\nskill="skills/incident/SKILL.md"\n',
        )
        result = Catalog(self.root, conf).guide()
        self.assertEqual(result["recipes"][0]["name"], "incident")
        self.assertEqual(len(result["skills"]), 1)

    def test_recipe_executable_fields_rejected(self):
        conf = self.write("workstation.toml", '[recipes.test]\ndescription="Bad"\ncommand="touch unwanted"\n')
        with self.assertRaises(ValueError):
            Catalog(self.root, conf)
        self.assertFalse((self.root / "unwanted").exists())

    def test_external_explicit_roots_require_trusted_mode(self):
        with tempfile.TemporaryDirectory() as out:
            conf = self.write("workstation.toml", "skill_roots=[" + repr(out) + "]")
            with self.assertRaises(ValueError):
                Catalog(self.root, conf)
            self.assertTrue(Catalog(self.root, conf, trusted=True).guide()["ok"])

    def test_unknown_config_keys_rejected(self):
        with self.assertRaises(ValueError):
            Catalog(self.root, self.write("workstation.toml", 'shell="anything"'))

    def test_recipe_cannot_reference_unapproved_external_path(self):
        with tempfile.TemporaryDirectory() as out:
            p = Path(out) / "SKILL.md"
            p.write_text(SKILL)
            conf = self.write(
                "workstation.toml", '[recipes.incident]\ndescription="test"\nskill=' + repr(str(p))
            )
            with self.assertRaises(ValueError):
                Catalog(self.root, conf, trusted=True)
