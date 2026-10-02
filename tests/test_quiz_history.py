import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import chess

from app import TheoryVaultApp
from quiz_history import QuizHistory


def card(name: str, pgn: str = "1. e4 e5 *", repertoire: str = "main") -> dict:
    return {
        "prompt_id": f"{repertoire}:{name}",
        "repertoire_id": repertoire,
        "move_uci": "e7e5",
        "before_fen": chess.Board().fen(),
        "pgn": pgn,
    }


def node(name: str, *branches: str, repertoire: str = "main", side: bool = chess.BLACK) -> tuple:
    return repertoire, side, (name, *branches)


class QuizHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "quiz-history.sqlite3"
        self.history = QuizHistory(self.path)
        self.app = TheoryVaultApp.__new__(TheoryVaultApp)
        self.app.quiz_history = self.history

    def record(self, position: dict, correct: int, incorrect: int = 0) -> None:
        for _ in range(correct):
            self.history.record(position, True)
        for _ in range(incorrect):
            self.history.record(position, False)

    def test_answer_counts_persist_and_use_smoothed_score(self) -> None:
        position = card("position")
        self.record(position, 2, 8)
        reopened = QuizHistory(self.path)
        self.assertEqual(0.25, reopened.scores()[reopened.key(position)])
        reopened.record(position, True)
        self.assertEqual(4 / 13, self.history.scores()[self.history.key(position)])

    def test_changed_reply_and_other_repertoires_have_separate_history(self) -> None:
        original = card("position")
        self.record(original, 10)
        changed = {**original, "move_uci": "c7c5"}
        other = card("position", repertoire="other")
        self.assertNotIn(self.history.key(changed), self.history.scores())
        self.assertNotIn(self.history.key(other), self.history.scores())

    def test_weak_new_and_consistently_correct_families_order_by_score(self) -> None:
        strong, new, weak, once = [node(name) for name in ("Strong", "New", "Weak", "Once")]
        cards = {item: [card(item[2][0])] for item in (strong, new, weak, once)}
        self.record(cards[strong][0], 10)
        self.record(cards[weak][0], 2, 8)
        self.record(cards[once][0], 1)
        self.assertEqual(
            [weak, new, once, strong],
            self.app.order_quiz_families([strong, new, weak, once], cards, 100),
        )

    def test_unseen_and_equal_score_families_keep_original_order(self) -> None:
        nodes = [node("B"), node("A")]
        cards = {item: [card(item[2][0])] for item in nodes}
        self.assertEqual(nodes, self.app.order_quiz_families(nodes, cards, 100))
        for group in cards.values():
            self.record(group[0], 1, 1)
        self.assertEqual(nodes, self.app.order_quiz_families(nodes, cards, 100))

    def test_positions_have_equal_weight_and_shared_ancestors_count_once(self) -> None:
        first = node("Mixed", "First")
        second = node("Mixed", "Second")
        other = node("Other")
        easy, hard, comparison = card("easy"), card("hard"), card("comparison")
        self.record(easy, 100)
        self.record(hard, 0, 10)
        self.record(comparison, 2, 1)  # 0.6; Mixed's mean is about 0.54.
        cards = {first: [easy, hard], second: [easy], other: [comparison]}
        self.assertEqual(
            [first, second, other],
            self.app.order_quiz_families([other, first, second], cards, 100),
        )

    def test_depth_limit_excludes_unselected_positions_from_score(self) -> None:
        mixed, unseen = node("Mixed"), node("Unseen")
        easy = card("easy")
        hard = card("hard", "1. e4 e5 2. Nf3 Nc6 *")
        self.record(easy, 1)
        self.record(hard, 0, 10)
        cards = {mixed: [easy, hard], unseen: [card("unseen")]}
        self.assertEqual([mixed, unseen], self.app.order_quiz_families([mixed, unseen], cards, 4))
        self.assertEqual([unseen, mixed], self.app.order_quiz_families([mixed, unseen], cards, 2))

    def test_same_family_label_in_other_side_or_repertoire_is_independent(self) -> None:
        nodes = [node("French"), node("French", side=chess.WHITE), node("French", repertoire="other")]
        cards = {item: [card(str(index))] for index, item in enumerate(nodes)}
        self.record(cards[nodes[0]][0], 10)
        self.record(cards[nodes[2]][0], 0, 10)
        self.assertEqual(list(reversed(nodes)), self.app.order_quiz_families(nodes, cards, 100))

    def test_reordered_quiz_preserves_all_moves_branch_order_and_deduplication(self) -> None:
        strong, first, second = node("Strong"), node("Weak", "First"), node("Weak", "Second")
        shared, strong_leaf, first_leaf, second_leaf = [card(name) for name in ("shared", "strong", "first", "second")]
        cards = {
            strong: [shared, strong_leaf],
            first: [shared, first_leaf],
            second: [shared, second_leaf],
        }
        for position in (shared, strong_leaf):
            self.record(position, 10)
        for position in (first_leaf, second_leaf):
            self.record(position, 0, 10)
        family_paths = {id(position): ("Original",) for group in cards.values() for position in group}
        original_nodes = [strong, first, second]
        ordered = self.app.order_quiz_families(original_nodes, cards, 100)
        before = self.app.study_cards_for_nodes(original_nodes, cards, family_paths, 100)
        after = self.app.study_cards_for_nodes(ordered, cards, family_paths, 100)
        self.assertEqual([first, second, strong], ordered)
        self.assertEqual(["main:shared", "main:first", "main:second", "main:strong"], [p["prompt_id"] for p in after])
        self.assertCountEqual([p["prompt_id"] for p in before], [p["prompt_id"] for p in after])
        self.assertEqual([strong, first, second], original_nodes)
        self.assertNotIn("_study_path", shared)
        prepared = self.app.prepare_quiz_cards(after)
        self.assertEqual([2, 2, 1, 1], [p["_study_total"] for p in prepared])

    def test_quiz_result_records_history_without_changing_round_results(self) -> None:
        position = card("position")
        self.app.quiz_results = []
        self.app.update_quiz_counter = MagicMock()
        self.app.add_quiz_result(position, False)
        self.app.add_quiz_result(position, True)
        self.assertEqual(
            [{"card": position, "correct": False}, {"card": position, "correct": True}],
            self.app.quiz_results,
        )
        self.assertEqual(0.5, self.history.scores()[self.history.key(position)])
        self.assertEqual(2, self.app.update_quiz_counter.call_count)

    def test_quiz_counter_shows_live_score_accuracy_and_progress(self) -> None:
        self.app.quiz_cards = [card("one"), card("two"), card("three"), card("four")]
        self.app.quiz_results = [{"card": self.app.quiz_cards[0], "correct": True}, {"card": self.app.quiz_cards[1], "correct": False}]
        self.app.quiz_score = 1
        self.app.quiz_counter = MagicMock()

        self.app.update_quiz_counter()

        self.app.quiz_counter.set.assert_called_once_with("Score: 1/2 correct (50%)  •  2/4 answered")

    def test_card_key_supports_theory_and_recognition_card_schemas(self) -> None:
        theory = card("theory")
        recognition = {
            "prompt_id": "opening-recognition:families:position",
            "move_uci": "recognition-answer-id",
            "fen": chess.Board().fen(),
            "answer": "Sicilian Defense",
            "quiz_kind": "recognition",
        }
        self.assertEqual(theory["prompt_id"], self.app.card_key(theory))
        theory_without_prompt = {key: value for key, value in theory.items() if key != "prompt_id"}
        self.assertEqual("main:" + theory["before_fen"], self.app.card_key(theory_without_prompt))
        self.assertEqual(recognition["prompt_id"], self.app.card_key(recognition))

    def test_incorrect_recognition_answer_records_and_replays_as_recognition(self) -> None:
        recognition = {
            "prompt_id": "opening-recognition:families:position",
            "move_uci": "recognition-answer-id",
            "fen": chess.Board().fen(),
            "answer": "Sicilian Defense",
            "quiz_kind": "recognition",
        }
        self.app.quiz_results = []
        self.app.update_quiz_counter = MagicMock()
        self.app.add_quiz_result(recognition, False)
        self.assertEqual(1 / 3, self.history.scores()[self.history.key(recognition)])

        self.app.last_missed_cards = [recognition]
        self.app.begin_opening_recognition = MagicMock()
        self.app.begin_quiz = MagicMock()
        self.app.replay_missed_moves()
        self.app.begin_opening_recognition.assert_called_once_with([recognition])
        self.app.begin_quiz.assert_not_called()

    def test_missed_theory_move_replays_as_theory(self) -> None:
        theory = card("theory")
        self.app.last_missed_cards = [theory]
        self.app.begin_opening_recognition = MagicMock()
        self.app.begin_quiz = MagicMock()
        self.app.replay_missed_moves()
        self.app.begin_quiz.assert_called_once_with([theory])
        self.app.begin_opening_recognition.assert_not_called()

    def test_recognition_orientation_faces_the_defining_move_from_the_opponent(self) -> None:
        # The Najdorf defining move ...a6 is Black's, so Recognition should
        # face White (the player recognizing Black's system).
        self.app.mode = "recognition_quiz"
        self.app.board = chess.Board()
        self.app.board.push_san("e4")
        self.app.orientation_turn = not self.app.board.turn
        self.assertEqual(chess.WHITE, self.app.current_orientation())


if __name__ == "__main__":
    unittest.main()
