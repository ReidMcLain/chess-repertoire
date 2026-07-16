import unittest

import chess

from app import ChessMvpApp


class OpeningClassificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = ChessMvpApp.__new__(ChessMvpApp)

    def test_sicilian_mcdonnell_attack(self) -> None:
        classification = self.app.classify_opening({"pgn": "1. e4 c5 2. f4 *"})

        self.assertEqual(
            classification,
            {
                "opening": "Sicilian Defense",
                "variation": "McDonnell Attack",
                "subvariation": "",
            },
        )

    def test_sicilian_nyezhmetdinov_rossolimo_attack(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 c5 2. Nf3 Nc6 3. Bb5 *"}
        )

        self.assertEqual("Sicilian Defense", classification["opening"])
        self.assertEqual("Nyezhmetdinov-Rossolimo Attack", classification["variation"])
        self.assertEqual("", classification["subvariation"])

    def test_sicilian_nyezhmetdinov_rossolimo_response_stays_in_parent(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 c5 2. Nf3 Nc6 3. Bb5 e6 4. O-O Nge7 *"}
        )

        self.assertEqual("Nyezhmetdinov-Rossolimo Attack", classification["variation"])
        self.assertEqual("", classification["subvariation"])

    def test_nimzo_indian_defense(self) -> None:
        classification = self.app.classify_opening({"pgn": "1. d4 Nf6 2. c4 e6 3. Nc3 Bb4 *"})

        self.assertEqual(
            classification,
            {
                "opening": "Nimzo-Indian Defense",
                "variation": "",
                "subvariation": "",
            },
        )

    def assert_accelerated_dragon(self, pgn: str, subvariation: str = "") -> None:
        self.assertEqual(
            self.app.classify_opening({"pgn": pgn}),
            {
                "opening": "Sicilian Defense",
                "variation": "Accelerated Dragon",
                "subvariation": subvariation,
            },
        )

    def test_accelerated_dragon_standard_move_order(self) -> None:
        self.assert_accelerated_dragon(
            "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 *"
        )

    def test_accelerated_dragon_hyperaccelerated_move_order(self) -> None:
        self.assert_accelerated_dragon(
            "1. e4 c5 2. Nf3 g6 3. d4 cxd4 4. Nxd4 Nc6 *"
        )

    def test_accelerated_dragon_with_intervening_development(self) -> None:
        self.assertEqual(
            self.app.classify_opening(
                {"pgn": "1. e4 c5 2. Nf3 g6 3. d4 cxd4 4. Nxd4 Bg7 5. Nc3 Nc6 *"}
            ),
            {
                "opening": "Sicilian Defense",
                "variation": "Hyperaccelerated Dragon",
                "subvariation": "",
            },
        )

    def test_accelerated_dragon_english_transposition(self) -> None:
        self.assert_accelerated_dragon(
            "1. Nf3 c5 2. c4 g6 3. d4 cxd4 4. Nxd4 Nc6 5. e4 *",
            "Maróczy Bind",
        )

    def test_regular_dragon_is_not_mislabeled_accelerated(self) -> None:
        classification = self.app.classify_opening(
            {
                "pgn": (
                    "1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 "
                    "5. Nc3 g6 6. Be3 Nc6 *"
                )
            }
        )

        self.assertEqual("Sicilian Defense", classification["opening"])
        self.assertNotEqual("Accelerated Dragon", classification["variation"])

    def test_opening_label_includes_accelerated_dragon(self) -> None:
        label = self.app.opening_label(
            {"pgn": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 *"}
        )

        self.assertEqual("Sicilian Defense > Accelerated Dragon", label)

    def test_variations_group_below_their_opening_with_main_line(self) -> None:
        cards = [
            {"pgn": "1. e4 c5 *"},
            {"pgn": "1. e4 c5 2. f4 *"},
            {"pgn": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 *"},
        ]

        groups = self.app.classification_groups(cards, "variation")

        self.assertEqual(
            ["Main line", "McDonnell Attack", "Accelerated Dragon"],
            list(groups),
        )
        self.assertEqual(1, len(groups["Main line"]))
        self.assertEqual(1, len(groups["Accelerated Dragon"]))

    def test_named_subvariations_group_below_their_variation(self) -> None:
        cards = [
            {
                "opening": "Sicilian Defense",
                "variation": "Accelerated Dragon",
                "subvariation": "",
            },
            {
                "opening": "Sicilian Defense",
                "variation": "Accelerated Dragon",
                "subvariation": "Maroczy Bind",
            },
        ]

        groups = self.app.classification_groups(cards, "subvariation")

        self.assertEqual(["Main line", "Maroczy Bind"], list(groups))

    def test_french_rubinstein_variation(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 *"}
        )

        self.assertEqual(
            {
                "opening": "French Defense",
                "variation": "Rubinstein Variation",
                "subvariation": "",
            },
            classification,
        )

    def test_french_rubinstein_blackburne_defense(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Nd7 5. Nf3 *"}
        )

        self.assertEqual("Rubinstein Variation", classification["variation"])
        self.assertEqual("Blackburne Defense", classification["subvariation"])

    def test_french_rubinstein_be7_remains_in_the_parent_variation(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Be7 5. Nf3 *"}
        )

        self.assertEqual("Rubinstein Variation", classification["variation"])
        self.assertEqual("", classification["subvariation"])

    def test_french_classical_steinitz_variation(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. d4 d5 3. Nc3 Nf6 4. e5 Nfd7 5. f4 *"}
        )

        self.assertEqual("Classical Variation", classification["variation"])
        self.assertEqual("Steinitz Variation", classification["subvariation"])

    def test_french_advance_and_steinitz_attack_are_distinct(self) -> None:
        advance = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. d4 d5 3. e5 *"}
        )
        steinitz_attack = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. e5 *"}
        )

        self.assertEqual("Advance Variation", advance["variation"])
        self.assertEqual("Steinitz Attack", steinitz_attack["variation"])

    def test_saved_pgn_builds_navigable_move_history(self) -> None:
        root_fen, history = self.app.pgn_move_history(
            "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 *"
        )

        self.assertEqual(chess.Board().fen(), root_fen)
        self.assertEqual(8, len(history))
        self.assertEqual("e2e4", history[0]["move_uci"])
        self.assertEqual("g7g6", history[-1]["move_uci"])
        self.assertEqual(
            history[-1]["before_fen"],
            history[-2]["after_fen"],
        )

    def test_view_starts_after_move_while_edit_starts_before_it(self) -> None:
        self.assertEqual(8, self.app.repertoire_line_start_cursor("view", 8))
        self.assertEqual(7, self.app.repertoire_line_start_cursor("edit", 8))

    def test_repertoire_section_expansion_state_is_preserved(self) -> None:
        class FakeHeader:
            def __init__(self) -> None:
                self.text = ""

            def configure(self, **kwargs) -> None:
                self.text = kwargs.get("text", self.text)

        class FakeContent:
            def __init__(self) -> None:
                self.manager = ""

            def winfo_manager(self) -> str:
                return self.manager

            def pack(self, **_kwargs) -> None:
                self.manager = "pack"

            def pack_forget(self) -> None:
                self.manager = ""

        self.app.repertoire_expanded_sections = set()
        state_key = ("my-black-repertoire", "Sicilian Defense", "Accelerated Dragon")
        header = FakeHeader()
        content = FakeContent()

        self.app.toggle_opening_section(
            header,
            content,
            "Accelerated Dragon",
            9,
            state_key,
        )

        self.assertIn(state_key, self.app.repertoire_expanded_sections)
        self.assertEqual("pack", content.winfo_manager())
        restored_header = FakeHeader()
        restored_content = FakeContent()
        self.app.restore_repertoire_section(
            restored_header,
            restored_content,
            "Accelerated Dragon",
            9,
            state_key,
        )
        self.assertEqual("pack", restored_content.winfo_manager())
        self.assertEqual("-  Accelerated Dragon (9)", restored_header.text)


if __name__ == "__main__":
    unittest.main()
