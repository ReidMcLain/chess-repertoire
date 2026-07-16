import unittest

from opening_classifier import OPENING_CLASSIFIER


class BundledOpeningClassifierTests(unittest.TestCase):
    def test_loads_the_complete_pinned_catalog(self) -> None:
        self.assertEqual(3803, OPENING_CLASSIFIER.entry_count)
        self.assertIn("lichess-chess-openings@git-", OPENING_CLASSIFIER.dataset_version)

    def test_deep_catalog_branch_is_classified(self) -> None:
        result = OPENING_CLASSIFIER.classify(
            "e2e4 c7c6 g1f3 d7d5 b1c3 c8g4 h2h3 g4h5 e4d5 c6d5 g2g4 h5g6 f3e5".split()
        )

        self.assertEqual("Caro-Kann Defense", result.opening)
        self.assertEqual("Two Knights Attack", result.variation)
        self.assertTrue(result.subvariation)

    def test_position_index_recognizes_an_accelerated_dragon_transposition(self) -> None:
        result = OPENING_CLASSIFIER.classify(
            "g1f3 c7c5 c2c4 g7g6 d2d4 c5d4 f3d4 b8c6 e2e4".split()
        )

        self.assertEqual("Sicilian Defense", result.opening)
        self.assertEqual("Accelerated Dragon", result.variation)
        self.assertEqual("Maróczy Bind", result.subvariation)
        self.assertEqual("dataset_position", result.source)

    def test_catalog_names_are_used_without_display_aliases(self) -> None:
        rossolimo = OPENING_CLASSIFIER.classify(
            "e2e4 c7c5 g1f3 b8c6 f1b5".split()
        )
        nimzo = OPENING_CLASSIFIER.classify(
            "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4".split()
        )

        self.assertEqual("Nyezhmetdinov-Rossolimo Attack", rossolimo.variation)
        self.assertEqual("Nimzo-Indian Defense", nimzo.opening)
        self.assertEqual("", nimzo.variation)

        indian = OPENING_CLASSIFIER.classify("d2d4 g8f6".split())
        self.assertEqual("Indian Defense", indian.opening)


if __name__ == "__main__":
    unittest.main()
