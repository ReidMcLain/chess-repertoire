import hashlib
import json
import unittest
from pathlib import Path


OPENING_DATA_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "openings"


class OpeningDatasetIntegrityTests(unittest.TestCase):
    def test_runtime_dataset_matches_metadata_using_lf_bytes(self) -> None:
        metadata = json.loads(
            (OPENING_DATA_DIRECTORY / "metadata.json").read_text(encoding="utf-8")
        )
        dataset = (OPENING_DATA_DIRECTORY / "openings.tsv").read_bytes()
        expected = metadata["runtime_sha256"]
        actual = hashlib.sha256(dataset).hexdigest()

        self.assertNotIn(
            b"\r\n",
            dataset,
            "openings.tsv must retain LF line endings; check .gitattributes",
        )
        self.assertEqual(
            expected,
            actual,
            "openings.tsv bytes do not match metadata.json runtime_sha256",
        )


if __name__ == "__main__":
    unittest.main()
