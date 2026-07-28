import tempfile
import unittest
from pathlib import Path

from app_paths import (
    APPLICATION_DATA_DIRECTORY_NAME,
    repertoire_directory,
    resource_path,
    user_data_directory,
)


class ApplicationPathTests(unittest.TestCase):
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
