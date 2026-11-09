import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import chess.pgn

from app import TheoryVaultApp
from repertoire_store import RepertoireStore


class BranchRemovalTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = RepertoireStore(Path(temp.name))
        self.info = self.store.create("Branches")

    def add(self, pgn):
        game = chess.pgn.read_game(io.StringIO(pgn))
        self.store.add_line(self.info, list(game.mainline_moves()))

    def make_tree(self):
        for pgn in ("1. e4", "1. e4 e5", "1. e4 e5 2. Nf3",
                    "1. e4 e5 2. Nf3 Nc6", "1. e4 e5 2. Nf3 Nf6 3. Nxe5",
                    "1. e4 c5 2. Nf3"):
            self.add(pgn)
        return next(c for c in self.store.compile(self.info) if c["move_uci"] == "e7e5")

    def test_removes_subtree_for_both_colors_preserving_ancestor_and_sibling(self):
        selected = self.make_tree()
        self.assertEqual(4, self.store.remove_branch(self.info, selected["pgn"]))
        remaining = self.store.compile(self.info)
        self.assertEqual(["e2e4", "g1f3"], [c["move_uci"] for c in remaining])
        game = self.store.read_games(self.info)[0]
        self.assertEqual(["c7c5"], [n.move.uci() for n in game.variations[0].variations])

    def test_single_move_removal_keeps_continuations(self):
        selected = self.make_tree()
        self.store.remove_answer(self.info, selected["position_key"], selected["move_uci"])
        self.assertEqual(5, len(self.store.compile(self.info)))
        self.assertIn("b8c6", {c["move_uci"] for c in self.store.compile(self.info)})

    def test_other_transposed_move_order_and_notes_survive(self):
        self.add("1. Nf3 d5 2. d4 Nf6")
        self.add("1. d4 d5 2. Nf3 Nf6")
        games = self.store.read_games(self.info)
        games[0].comment = "Keep this note"
        self.store._atomic_write(self.info.path, games)
        self.store.remove_branch(self.info, "1. Nf3 d5 2. d4 Nf6 *")
        cards = self.store.compile(self.info)
        self.assertEqual(1, len(cards))
        self.assertTrue(cards[0]["pgn"].startswith("1. d4"))
        self.assertEqual("Keep this note", self.store.read_games(self.info)[0].comment)

    def test_custom_starting_position_and_whole_tree_removal(self):
        text = '[SetUp "1"]\n[FEN "8/P7/8/8/8/8/7k/4K3 w - - 0 1"]\n\n1. a8=Q *'
        preview = self.store.preview_import(text, chess.WHITE)
        info = self.store.import_preview(preview, "Custom", chess.WHITE, "new")
        selected = self.store.compile(info)[0]
        self.assertEqual(1, self.store.remove_branch(info, selected["pgn"]))
        self.assertEqual([], self.store.compile(info))
        self.assertEqual([], self.store.read_games(info)[0].variations)

    def test_missing_branch_and_invalid_path_do_not_write(self):
        self.make_tree()
        before = self.info.path.read_bytes()
        for pgn in ("*", "1. d4 *", "1. d4 d5 2. c4 *"):
            with self.subTest(pgn=pgn), self.assertRaises(ValueError):
                self.store.remove_branch(self.info, pgn)
            self.assertEqual(before, self.info.path.read_bytes())

    def make_app(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        app.root = object()
        app.store = self.store
        app.status = MagicMock()
        app.view_repertoire = MagicMock()
        app.show_toast = MagicMock()
        return app

    def test_remove_dialog_routes_branch_choice_to_actual_deletion(self):
        selected = self.make_tree()
        app = self.make_app()
        with patch.object(app, "ask_remove_scope", return_value=True):
            app.remove_card_answer(selected)
        self.assertEqual(2, len(self.store.compile(self.info)))
        app.view_repertoire.assert_called_once_with()

    def test_remove_dialog_cancel_leaves_file_and_browser_untouched(self):
        selected = self.make_tree()
        before = self.info.path.read_bytes()
        app = self.make_app()
        with patch.object(app, "ask_remove_scope", return_value=None):
            app.remove_card_answer(selected)
        self.assertEqual(before, self.info.path.read_bytes())
        app.view_repertoire.assert_not_called()
        app.show_toast.assert_not_called()


if __name__ == "__main__":
    unittest.main()
