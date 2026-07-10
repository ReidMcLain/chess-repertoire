import tempfile
import unittest
from pathlib import Path

import chess

from repertoire_store import QUIZ_MARK, RepertoireStore, parse_pgn


class RepertoireStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.store = RepertoireStore(self.directory)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_add_line_marks_only_final_move(self) -> None:
        info = self.store.create("Caro-Kann", chess.WHITE)
        moves = [chess.Move.from_uci(uci) for uci in ("e2e4", "c7c6", "g1f3")]

        self.assertTrue(self.store.add_line(info, moves))
        self.assertFalse(self.store.add_line(info, moves))

        prompts = self.store.compile(info)
        self.assertEqual(1, len(prompts))
        self.assertEqual({"g1f3"}, prompts[0]["accepted_uci"])
        self.assertNotIn(QUIZ_MARK, info.path.read_text(encoding="utf-8").split("1. e4", 1)[0])

    def test_multiple_marked_children_become_one_prompt(self) -> None:
        info = self.store.create("First Moves", chess.WHITE)
        self.store.add_line(info, [chess.Move.from_uci("e2e4")])
        self.store.add_line(info, [chess.Move.from_uci("d2d4")])

        prompts = self.store.compile(info)

        self.assertEqual(1, len(prompts))
        self.assertEqual({"e2e4", "d2d4"}, prompts[0]["accepted_uci"])
        self.assertEqual(2, len(prompts[0]["accepted_moves"]))

    def test_generic_import_marks_every_selected_side_move(self) -> None:
        text = "[Event \"Imported\"]\n\n1. e4 c5 (1... e5) 2. Nf3 *\n"

        preview = self.store.preview_import(text, chess.WHITE)

        self.assertEqual([], preview["errors"])
        self.assertFalse(preview["used_existing_marks"])
        self.assertEqual(2, preview["prompt_count"])
        self.assertEqual(2, preview["answer_count"])
        info = self.store.import_preview(preview, "Imported", chess.WHITE, "new")
        self.assertEqual(2, len(self.store.compile(info)))

    def test_import_with_crm_marks_does_not_mark_other_moves(self) -> None:
        text = f"[Event \"Imported\"]\n\n1. e4 {{ {QUIZ_MARK} }} e5 2. Nf3 *\n"

        preview = self.store.preview_import(text, chess.WHITE)

        self.assertTrue(preview["used_existing_marks"])
        self.assertEqual(1, preview["prompt_count"])
        self.assertEqual(1, preview["answer_count"])

    def test_remove_answer_unmarks_without_deleting_context(self) -> None:
        info = self.store.create("First Moves", chess.WHITE)
        self.store.add_line(info, [chess.Move.from_uci("e2e4")])

        prompt = self.store.compile(info)[0]
        removed = self.store.remove_answer(info, prompt["position_key"], "e2e4")

        self.assertEqual(1, removed)
        self.assertEqual([], self.store.compile(info))
        games, errors = parse_pgn(info.path.read_text(encoding="utf-8"))
        self.assertEqual([], errors)
        self.assertEqual(["e2e4"], [move.uci() for move in games[0].mainline_moves()])

    def test_transposed_paths_compile_to_one_position(self) -> None:
        info = self.store.create("Transpositions", chess.BLACK)
        first = [chess.Move.from_uci(uci) for uci in ("g1f3", "d7d5", "g2g3", "g8f6")]
        second = [chess.Move.from_uci(uci) for uci in ("g2g3", "d7d5", "g1f3", "g8f6")]
        self.store.add_line(info, first)
        self.store.add_line(info, second)

        prompts = self.store.compile(info)

        self.assertEqual(1, len(prompts))
        self.assertEqual({"g8f6"}, prompts[0]["accepted_uci"])
        self.assertEqual(2, len(prompts[0]["contexts"]))

    def test_custom_fen_comments_nags_and_promotion_round_trip(self) -> None:
        text = """[Event "Promotion"]
[SetUp "1"]
[FEN "8/P7/8/8/8/8/7k/4K3 w - - 0 1"]

1. a8=Q $1 {Promote now} *
"""

        preview = self.store.preview_import(text, chess.WHITE)
        self.assertEqual([], preview["errors"])
        info = self.store.import_preview(preview, "Promotion", chess.WHITE, "new")
        exported = info.path.read_text(encoding="utf-8")
        prompts = self.store.compile(info)

        self.assertIn('[FEN "8/P7/8/8/8/8/7k/4K3 w - - 0 1"]', exported)
        self.assertIn("$1", exported)
        self.assertIn("Promote now", exported)
        self.assertEqual({"a7a8q"}, prompts[0]["accepted_uci"])

    def test_invalid_or_empty_pgn_cannot_be_imported(self) -> None:
        preview = self.store.preview_import("[Event \"Empty\"]\n\n*", chess.WHITE)
        self.assertTrue(preview["errors"])
        with self.assertRaises(ValueError):
            self.store.import_preview(preview, "Empty", chess.WHITE, "new")

if __name__ == "__main__":
    unittest.main()
