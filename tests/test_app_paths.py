import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app_paths import (
    APPLICATION_DATA_DIRECTORY_NAME,
    LEGACY_APPLICATION_DATA_DIRECTORY_NAME,
    repertoire_directory,
    resource_path,
    user_data_directory,
)


class ApplicationPathTests(unittest.TestCase):
    def test_legacy_data_is_copied_once_without_overwriting_vault_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            legacy = base / LEGACY_APPLICATION_DATA_DIRECTORY_NAME / "repertoire"
            legacy.mkdir(parents=True)
            old_pgn = legacy / "my-lines.pgn"
            old_pgn.write_text('1. e4 {[%crm_quiz 1]} *', encoding="utf-8")
            environment = {"LOCALAPPDATA": str(base)}

            vault = repertoire_directory(frozen=True, environment=environment)

            self.assertEqual(base / "TheoryVault" / "repertoire", vault)
            self.assertEqual(old_pgn.read_bytes(), (vault / old_pgn.name).read_bytes())
            (vault / old_pgn.name).write_text("updated", encoding="utf-8")
            repertoire_directory(frozen=True, environment=environment)
            self.assertEqual("updated", (vault / old_pgn.name).read_text(encoding="utf-8"))
            self.assertIn("crm_quiz", old_pgn.read_text(encoding="utf-8"))
            (vault / old_pgn.name).unlink()
            repertoire_directory(frozen=True, environment=environment)
            self.assertFalse((vault / old_pgn.name).exists())

    def test_failed_legacy_copy_leaves_no_partial_vault_and_can_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            legacy = base / LEGACY_APPLICATION_DATA_DIRECTORY_NAME
            legacy.mkdir()
            (legacy / "saved.txt").write_text("saved", encoding="utf-8")
            environment = {"LOCALAPPDATA": str(base)}
            with patch("app_paths.shutil.copytree", side_effect=OSError("copy interrupted")):
                with self.assertRaises(OSError):
                    user_data_directory(frozen=True, environment=environment)
            self.assertFalse((base / "TheoryVault").exists())
            vault = user_data_directory(frozen=True, environment=environment)
            self.assertEqual("saved", (vault / "saved.txt").read_text(encoding="utf-8"))

    def test_source_resources_resolve_from_source_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            self.assertEqual(
                source / "assets" / "pieces" / "wK.png",
                resource_path(
                    "assets",
                    "pieces",
                    "wK.png",
                    frozen=False,
                    source_directory=source,
                ),
            )

    def test_frozen_resources_resolve_from_bundle_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            self.assertEqual(
                bundle / "data" / "openings" / "metadata.json",
                resource_path(
                    "data",
                    "openings",
                    "metadata.json",
                    frozen=True,
                    bundle_directory=bundle,
                ),
            )

    def test_source_user_data_retains_repository_local_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            self.assertEqual(
                source,
                user_data_directory(frozen=False, source_directory=source),
            )

    def test_frozen_user_data_uses_local_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local_app_data = Path(temporary)
            directory = user_data_directory(
                frozen=True,
                environment={"LOCALAPPDATA": str(local_app_data)},
            )
            self.assertEqual(
                local_app_data / APPLICATION_DATA_DIRECTORY_NAME,
                directory,
            )
            self.assertTrue(directory.is_dir())

    def test_repertoire_directory_is_created_under_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            local_app_data = Path(temporary)
            directory = repertoire_directory(
                frozen=True,
                environment={"LOCALAPPDATA": str(local_app_data)},
            )
            self.assertEqual(
                local_app_data / APPLICATION_DATA_DIRECTORY_NAME / "repertoire",
                directory,
            )
            self.assertTrue(directory.is_dir())


if __name__ == "__main__":
    unittest.main()
