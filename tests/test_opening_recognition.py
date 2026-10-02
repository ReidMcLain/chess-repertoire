import unittest

import chess

from app import TheoryVaultApp
from opening_classifier import OPENING_CLASSIFIER, position_key


class OpeningRecognitionCatalogTests(unittest.TestCase):
    def test_parent_families_are_a_sixty_question_catalog_subset(self) -> None:
        questions = OPENING_CLASSIFIER.recognition_questions("families")
        self.assertEqual(60, len(questions))
        self.assertEqual(60, len({question["answer"] for question in questions}))
        for question in questions:
            self.assertTrue(chess.Board(question["fen"]).is_valid())

    def test_named_variations_have_five_unique_choices_with_the_answer(self) -> None:
        questions = OPENING_CLASSIFIER.recognition_questions("variations")
        self.assertEqual(150, len(questions))
        for index, question in enumerate(questions):
            choices = OPENING_CLASSIFIER.recognition_options(questions, index)
            self.assertEqual(5, len(choices))
            self.assertEqual(5, len(set(choices)))
            self.assertIn(question["answer"], choices)

    def test_named_variations_stop_at_their_defining_move(self) -> None:
        questions = {
            question["answer"]: question
            for question in OPENING_CLASSIFIER.recognition_questions("variations")
        }
        expected_final_moves = {
            "Sicilian Defense: Najdorf Variation": "a7a6",
            "Sicilian Defense: Dragon Variation": "g7g6",
            "Sicilian Defense: Accelerated Dragon": "g7g6",
            "Sicilian Defense: Taimanov Variation": "b8c6",
        }
        for name, final_move in expected_final_moves.items():
            self.assertEqual(final_move, questions[name]["moves"][-1], name)

    def test_question_starts_before_and_can_play_its_defining_move(self) -> None:
        questions = OPENING_CLASSIFIER.recognition_questions("variations")
        najdorf = next(question for question in questions if question["answer"] == "Sicilian Defense: Najdorf Variation")
        self.assertEqual("a7a6", najdorf["defining_move_uci"])
        board = chess.Board(najdorf["before_fen"])
        defining_move = chess.Move.from_uci(najdorf["defining_move_uci"])
        self.assertIn(defining_move, board.legal_moves)
        board.push(defining_move)
        self.assertEqual(position_key(chess.Board(najdorf["fen"])), position_key(board))

    def test_theory_refresher_filters_variations_and_repeats_each_recorded_side(self) -> None:
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        theory_cards = [
            {
                "opening": "Sicilian Defense",
                "variation": "Najdorf Variation",
                "repertoire_color": chess.WHITE,
            },
            {
                "opening": "Sicilian Defense",
                "variation": "Najdorf Variation",
                "repertoire_color": chess.BLACK,
            },
        ]
        cards = app.build_opening_recognition_cards("variations", theory_cards=theory_cards)
        self.assertEqual(2, len(cards))
        self.assertEqual({chess.WHITE, chess.BLACK}, {card["theory_orientation"] for card in cards})
        self.assertEqual(2, len({card["prompt_id"] for card in cards}))
        self.assertTrue(all(card["answer"] == "Sicilian Defense: Najdorf Variation" for card in cards))

    def test_theory_refresher_uses_the_full_variation_level_catalog(self) -> None:
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        medium_names = {question["answer"] for question in OPENING_CLASSIFIER.recognition_questions("variations")}
        all_questions = OPENING_CLASSIFIER.recognition_questions("all_variations")
        self.assertEqual(1306, len(all_questions))
        uncommon_name = next(question["answer"] for question in all_questions if question["answer"] not in medium_names)
        opening, variation = uncommon_name.split(": ", maxsplit=1)
        cards = app.build_opening_recognition_cards(
            "all_variations",
            theory_cards=[
                {"opening": opening, "variation": variation, "repertoire_color": chess.WHITE}
            ],
        )
        self.assertEqual([uncommon_name], [card["answer"] for card in cards])


if __name__ == "__main__":
    unittest.main()
