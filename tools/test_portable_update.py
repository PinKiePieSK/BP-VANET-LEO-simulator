"""Check incremental updates against a local Git remote and isolated workspace."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from portable_update import REPOSITORY, adopt_package, copy_runtime, digest, runtime_path, update
import portable_launch
import package_simulator


class PortableUpdateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="bp-update-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.remote = self.root / "remote.git"
        self.workspace = self.root / "workspace"
        self.runtime = self.workspace / "runtime"
        self.runtime.mkdir(parents=True)
        self._git("init", "-b", "main", cwd=self.source)
        self._git("config", "user.name", "Test", cwd=self.source)
        self._git("config", "user.email", "test@example.invalid", cwd=self.source)
        files = {
            "tools/simulator_server.py": "print('old server')\n",
            "tools/simulator_cli.py": "import os\nprint(os.getcwd())\n",
            "viewer/simulator.js": "const version = 'old';\n",
            "config/simulator-example.json": "{}\n",
            "config/scenarios/bundled.json": "{\"bundled\": true}\n",
            "data/inputs/user/bundled/world.json": "{\"bundled\": true}\n",
        }
        for relative, content in files.items():
            target = self.source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            installed = self.runtime / relative
            installed.parent.mkdir(parents=True, exist_ok=True)
            installed.write_text(content)
        (self.runtime / ".venv/bin").mkdir(parents=True)
        (self.runtime / ".venv/bin/python").symlink_to(sys.executable)
        (self.runtime / "results/simulations/old-run").mkdir(parents=True)
        (self.runtime / "results/simulations/old-run/trace.txt").write_text("old trace\n")
        (self.runtime / "vendor").mkdir()
        (self.runtime / "vendor/pinned.txt").write_text("dependency\n")
        self._git("add", ".", cwd=self.source)
        self._git("commit", "-m", "base", cwd=self.source)
        (self.source / ".gitignore").write_text("/config/scenarios/\n/data/inputs/user/\n")
        self._git("add", ".gitignore", cwd=self.source)
        self._git("commit", "-m", "ignore local scenarios", cwd=self.source)
        self.base = self._git("rev-parse", "HEAD", cwd=self.source).strip()
        self._git("clone", "--bare", str(self.source), str(self.remote), cwd=self.root)
        self._git("remote", "add", "origin", str(self.remote), cwd=self.source)
        (self.workspace / "READY").write_text(str(self.runtime) + "\n")
        managed = {relative: digest(self.runtime / relative) for relative in files}
        self.managed = managed
        state = {"schema_version": 1, "repository": REPOSITORY, "branch": "main",
                 "revision": self.base, "active_runtime": "runtime",
                 "versions": {self.base: "runtime"}, "runs": {}, "managed": managed}
        (self.workspace / "UPDATE-STATE.json").write_text(json.dumps(state))

    def _git(self, *args: str, cwd: Path) -> str:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
        return result.stdout

    def commit(self, changes: dict[str, str | None]) -> str:
        for relative, content in changes.items():
            path = self.source / relative
            if content is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
        self._git("add", "-A", cwd=self.source)
        self._git("commit", "-m", "approved change", cwd=self.source)
        self._git("push", "origin", "main", cwd=self.source)
        return self._git("rev-parse", "HEAD", cwd=self.source).strip()

    def test_package_includes_only_four_bundled_scenarios(self) -> None:
        with patch.object(package_simulator, "ROOT", self.source):
            scenarios = self.source / "config/scenarios"
            data = self.source / "data/inputs/user"
            for name in package_simulator.PINNED_SCENARIOS:
                (scenarios / f"{name}.json").write_text("{}\n")
                (data / name).mkdir()
            (scenarios / "my-trip.json").write_text("{}\n")
            (data / "my-trip").mkdir()
            for directory in (scenarios, data):
                entries = [item.name for item in directory.iterdir()]
                included = set(entries) - package_simulator.ignore(str(directory), entries)
                expected = ({name + ".json" for name in package_simulator.PINNED_SCENARIOS}
                            if directory == scenarios else package_simulator.PINNED_SCENARIOS)
                self.assertEqual(included, expected)

    def test_edited_bundled_scenario_remains_local_after_update(self) -> None:
        scenario = self.runtime / "config/scenarios/bundled.json"
        data = self.runtime / "data/inputs/user/bundled/world.json"
        scenario.write_text('{"edited": true}\n')
        data.write_text('{"edited": true}\n')
        self.commit({"tools/simulator_server.py": "print('new server')\n",
                     "config/scenarios/bundled.json": '{"published": true}\n',
                     "data/inputs/user/bundled/world.json": '{"published": true}\n'})
        self.assertEqual(update(self.workspace, str(self.remote), authenticate=False,
                                validate=True)["status"], "UPDATED")
        active = runtime_path(self.workspace)
        self.assertEqual((active / "config/scenarios/bundled.json").read_text(),
                         '{"edited": true}\n')
        self.assertEqual((active / "data/inputs/user/bundled/world.json").read_text(),
                         '{"edited": true}\n')
        state = json.loads((self.workspace / "UPDATE-STATE.json").read_text())
        self.assertNotIn("config/scenarios/bundled.json", state["managed"])
        self.assertNotIn("data/inputs/user/bundled/world.json", state["managed"])

    def test_delta_preserves_saved_scenarios_without_publishing_them(self) -> None:
        saved = self.runtime / "config/scenarios/my-trip.json"
        saved.write_text('{"saved": true}\n')
        saved_data = self.runtime / "data/inputs/user/my-trip/world.json"
        saved_data.parent.mkdir()
        saved_data.write_text('{"roads": []}\n')
        source_saved = self.source / "config/scenarios/my-trip.json"
        source_saved.write_text(saved.read_text())
        source_saved_data = self.source / "data/inputs/user/my-trip/world.json"
        source_saved_data.parent.mkdir()
        source_saved_data.write_text(saved_data.read_text())
        target = self.commit({"tools/simulator_server.py": "print('new server')\n",
                              "viewer/simulator.js": "const version = 'new';\n",
                              "config/added.json": "{\"new\": true}\n",
                              "docs/note.md": "Documentation only.\n"})
        result = update(self.workspace, str(self.remote), authenticate=False, validate=True)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["changed_files"], 3)
        self.assertEqual(result["revision"], target)
        tracked = self._git("ls-tree", "-r", "--name-only", target, cwd=self.source)
        self.assertNotIn("config/scenarios/my-trip.json", tracked)
        self.assertNotIn("data/inputs/user/my-trip/world.json", tracked)
        active = runtime_path(self.workspace)
        self.assertEqual((active / "tools/simulator_server.py").read_text(), "print('new server')\n")
        self.assertEqual((self.runtime / "tools/simulator_server.py").read_text(), "print('old server')\n")
        self.assertEqual((active / "data/inputs/user/bundled/world.json").read_text(),
                         '{"bundled": true}\n')
        self.assertTrue((active / "config/scenarios/bundled.json").is_file())
        self.assertEqual((active / "config/scenarios/my-trip.json").read_text(), saved.read_text())
        self.assertEqual((active / "data/inputs/user/my-trip/world.json").read_text(),
                         saved_data.read_text())
        self.assertTrue(saved.is_file())
        self.assertTrue(saved_data.is_file())
        self.assertFalse((active / "results/simulations/old-run").exists())
        self.assertEqual((self.runtime / "results/simulations/old-run/trace.txt").read_text(), "old trace\n")
        self.assertEqual(runtime_path(self.workspace, "old-run"), self.runtime)
        with self.assertRaisesRegex(RuntimeError, "neexistuje"):
            runtime_path(self.workspace, "missing-run")
        self.assertEqual((active / "vendor/pinned.txt").read_text(), "dependency\n")
        (active / "results/simulations/second-run").mkdir()
        (active / "results/simulations/second-run/trace.txt").write_text("second trace\n")
        self.assertEqual(runtime_path(self.workspace, "second-run"), active)
        (self.runtime / "results/simulations/later-old-run").mkdir()
        self.assertEqual(runtime_path(self.workspace, "later-old-run"), self.runtime)
        (active / "config/scenarios/another-trip.json").write_text('{"saved": true}\n')
        newer = self.commit({"viewer/simulator.js": "const version = 'newer';\n"})
        self.assertEqual(update(self.workspace, str(self.remote), authenticate=False,
                                validate=True)["revision"], newer)
        self.assertEqual(runtime_path(self.workspace, "old-run"), self.runtime)
        self.assertEqual(runtime_path(self.workspace, "second-run"), active)
        self.assertFalse((runtime_path(self.workspace) / "results/simulations/second-run").exists())
        self.assertTrue((runtime_path(self.workspace) / "config/scenarios/another-trip.json").is_file())
        self.assertTrue((runtime_path(self.workspace) / "config/scenarios/my-trip.json").is_file())
        self.assertEqual(update(self.workspace, str(self.remote), authenticate=False,
                                validate=False)["status"], "CURRENT")

    def test_rejects_local_changes_and_preserves_active_version(self) -> None:
        self.commit({"viewer/simulator.js": "const version = 'new';\n"})
        (self.runtime / "tools/simulator_server.py").write_text("local edit\n")
        with self.assertRaisesRegex(RuntimeError, "Lokálne upravený súbor"):
            update(self.workspace, str(self.remote), authenticate=False, validate=False)
        self.assertEqual(runtime_path(self.workspace), self.runtime)

    def test_rejects_package_change_without_switching_version(self) -> None:
        self.commit({"scripts/portable_update.py": "print('different updater')\n"})
        with self.assertRaisesRegex(RuntimeError, "úplné vydanie"):
            update(self.workspace, str(self.remote), authenticate=False, validate=False)
        self.assertEqual(runtime_path(self.workspace), self.runtime)

    def test_failed_preflight_keeps_old_version(self) -> None:
        self.commit({"tools/simulator_cli.py": "raise SystemExit(1)\n"})
        with self.assertRaisesRegex(RuntimeError, "Príkaz zlyhal"):
            update(self.workspace, str(self.remote), authenticate=False, validate=True)
        self.assertEqual(runtime_path(self.workspace), self.runtime)
        self.assertFalse(any((self.workspace / ".versions").iterdir()))

    def test_run_wrapper_verifies_with_the_correct_version(self) -> None:
        package = self.root / "package"
        package.mkdir()
        scripts = Path(__file__).resolve().parents[1] / "scripts"
        shutil.copy2(scripts / "portable_run.sh", package / "run.sh")
        shutil.copy2(scripts / "portable_import.sh", package / "import.sh")
        shutil.copy2(scripts / "portable_update.py", package / "update.py")
        (package / "PACKAGE-MANIFEST.json").write_text("{}\n")
        (self.workspace / "PACKAGE-ID").write_text(digest(package / "PACKAGE-MANIFEST.json"))
        self.commit({"viewer/simulator.js": "const version = 'new';\n"})
        update(self.workspace, str(self.remote), authenticate=False, validate=True)
        active = runtime_path(self.workspace)
        (active / "results/simulations/new-run").mkdir()
        env = {**os.environ, "BP_SIM_WORKSPACE": str(self.workspace)}
        for run_id, expected in (("old-run", self.runtime), ("new-run", active)):
            completed = subprocess.run(["bash", str(package / "run.sh"), "verify", run_id],
                                       env=env, capture_output=True, text=True, check=True)
            self.assertEqual(completed.stdout.strip(), str(expected))
            with patch.object(portable_launch, "PACKAGE", package):
                self.assertEqual(portable_launch.ready_runtime(self.workspace, run_id), expected)
        duplicate = subprocess.run(["bash", str(package / "run.sh"), "run",
                                    "config/simulator-example.json", "old-run"],
                                   env=env, capture_output=True, text=True)
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn("už patrí staršiemu behu", duplicate.stderr)
        imported = self.root / "imported.json"
        imported.write_text('{"local": true}\n')
        subprocess.run(["bash", str(package / "import.sh"), str(imported)],
                       env=env, capture_output=True, text=True, check=True)
        self.assertTrue((active / "data/inputs/user/imported.json").is_file())
        self.assertFalse((self.runtime / "data/inputs/user/imported.json").exists())

    def test_complete_package_upgrade_preserves_previous_runs(self) -> None:
        package = self.root / "new-package"
        package.mkdir()
        (package / "PACKAGE-MANIFEST.json").write_text("{}\n")
        new_revision = "a" * 40
        base = {"schema_version": 1, "repository": REPOSITORY, "branch": "main",
                "revision": new_revision, "active_runtime": "runtime",
                "versions": {new_revision: "runtime"}, "runs": {}, "managed": {}}
        (package / "UPDATE-BASE.json").write_text(json.dumps(base))
        target = self.workspace / ".versions" / new_revision
        target.parent.mkdir()
        copy_runtime(self.runtime, target)
        outcome = adopt_package(self.workspace, package, target)
        self.assertEqual(outcome["status"], "READY")
        self.assertEqual(runtime_path(self.workspace), target)
        self.assertEqual(runtime_path(self.workspace, "old-run"), self.runtime)
        self.assertEqual((self.workspace / "PACKAGE-ID").read_text().strip(),
                         digest(package / "PACKAGE-MANIFEST.json"))
        self.assertEqual((self.runtime / "results/simulations/old-run/trace.txt").read_text(),
                         "old trace\n")

    def test_complete_package_upgrade_from_legacy_workspace(self) -> None:
        (self.workspace / "UPDATE-STATE.json").unlink()
        (self.workspace / "PACKAGE-ID").write_text("b" * 64)
        package = self.root / "new-package"
        package.mkdir()
        (package / "PACKAGE-MANIFEST.json").write_text("{}\n")
        new_revision = "c" * 40
        base = {"schema_version": 1, "repository": REPOSITORY, "branch": "main",
                "revision": new_revision, "active_runtime": "runtime",
                "versions": {new_revision: "runtime"}, "runs": {}, "managed": {}}
        (package / "UPDATE-BASE.json").write_text(json.dumps(base))
        target = self.workspace / ".versions" / new_revision
        target.parent.mkdir()
        copy_runtime(self.runtime, target)
        adopt_package(self.workspace, package, target)
        self.assertEqual(runtime_path(self.workspace, "old-run"), self.runtime)
        self.assertEqual(runtime_path(self.workspace), target)


if __name__ == "__main__":
    unittest.main()
