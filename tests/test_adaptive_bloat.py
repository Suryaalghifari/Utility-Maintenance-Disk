from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from disktools import commands, platform_linux
from disktools.core import Area, Drive

MB = 1024 * 1024


def make_large_dir(root: Path, relative: str, size_mb: int = 1100) -> Path:
    path = root / relative
    path.mkdir(parents=True, exist_ok=True)
    with (path / "payload.bin").open("wb") as handle:
        handle.truncate(size_mb * MB)
    return path


class AdaptiveBloatAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        make_large_dir(self.home, ".npm/_npx")
        make_large_dir(self.home, ".npm/_cacache")
        make_large_dir(self.home, "snap/firefox/common/.cache")
        make_large_dir(self.home, ".local/share/pnpm/store/v3")
        make_large_dir(self.home, ".local/share/pnpm/store/v11")
        make_large_dir(self.home, "src/retired-app/node_modules")
        make_large_dir(self.home, ".local/share/nvim")
        make_large_dir(self.home, ".local/share/uv")

        self.bin = self.home / "bin"
        self.bin.mkdir()
        pnpm = self.bin / "pnpm"
        pnpm.write_text(
            "#!/bin/sh\n"
            "if [ \"$1 $2\" = \"store path\" ]; then\n"
            f"  printf '%s\\n' '{self.home}/.local/share/pnpm/store/v11'\n"
            "fi\n"
        )
        pnpm.chmod(0o755)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{self.bin}:{os.environ.get('PATH', '')}",
            "NO_COLOR": "1",
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def assert_acceptance_output(self, output: str) -> None:
        expected = {
            ".npm/_cacache": "SAFE CLEAN",
            ".npm/_npx": "PRUNE",
            "snap/firefox/common/.cache": "SAFE CLEAN",
            "pnpm/store/v3": "PRUNE",
            "pnpm/store/v11": "INSPECT",
            "retired-app/node_modules": "PRUNE",
            ".local/share/nvim": "INSPECT",
            ".local/share/uv": "INSPECT",
        }
        for path_fragment, classification in expected.items():
            matching = [line for line in output.splitlines() if path_fragment in line]
            self.assertTrue(matching, f"missing {path_fragment!r}\n{output}")
            self.assertTrue(
                any(classification in line for line in matching),
                f"{path_fragment!r} was not {classification}\n" + "\n".join(matching),
            )
        self.assertIn("alasan:", output)
        self.assertIn("threshold adaptif", output.lower())

    def test_bash_scan_classifies_real_linux_cases(self) -> None:
        result = subprocess.run(
            ["bash", "scripts/bloat-scan"],
            cwd=Path(__file__).parents[1],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assert_acceptance_output(result.stdout)

    def test_firefox_clean_dry_run_reports_candidate_without_deleting(self) -> None:
        cache = self.home / "snap/firefox/common/.cache"
        payload = cache / "payload.bin"
        result = subprocess.run(
            ["bash", "scripts/firefox-clean", "--dry-run", "--yes"],
            cwd=Path(__file__).parents[1], env=self.env, text=True,
            capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload.exists())
        self.assertIn("Would free approximately", result.stdout)
        self.assertIn("nothing deleted", result.stdout)
        self.assertNotIn("Freed -", result.stdout)

    def test_python_scan_classifies_real_linux_cases(self) -> None:
        with mock.patch.dict(os.environ, self.env, clear=True):
            areas = platform_linux.bloat_locations()
            backend = mock.Mock()
            backend.bloat_locations.return_value = areas
            backend.big_files.return_value = []
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                commands.bloat_scan(backend)
        self.assert_acceptance_output(output.getvalue())

    def test_cleanup_native_command_respects_dry_run_and_confirmation(self) -> None:
        drive = Drive(id="/", label="", media="SSD", size=10, free=5, is_system=True)
        area = Area("Dev caches", ["/cache"], recommend="node-clean",
                    bytes=1024, existing=["/cache"])
        backend = mock.Mock()
        backend.cleanable_areas.return_value = [area]
        backend.browser_running.return_value = False
        backend.clean_native.return_value = 1024

        commands.clean(backend, [drive], "node-clean", dry_run=True,
                       assume_yes=False)
        backend.clean_native.assert_not_called()

        with mock.patch("disktools.core.confirm", return_value=False):
            commands.clean(backend, [drive], "node-clean", dry_run=False,
                           assume_yes=False)
        backend.clean_native.assert_not_called()

        commands.clean(backend, [drive], "node-clean", dry_run=False,
                       assume_yes=True)
        backend.clean_native.assert_called_once_with("node-clean", ["/cache"])


if __name__ == "__main__":
    unittest.main()
