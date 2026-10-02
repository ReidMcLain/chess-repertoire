import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import chess

from app import TheoryVaultApp
from repertoire_store import RepertoireStore, SIDELINED_MARK


class SideliningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = RepertoireStore(Path(self.temp.name))
        self.info = self.store.create("Test")

    def add(self, *moves):
        return self.store.add_line(self.info, [chess.Move.from_uci(move) for move in moves])

    def sideline(self, card, value=True, **kwargs):
        return self.store.set_answers_sidelined(
            self.info, [(card["position_key"], card["move_uci"])], value, **kwargs)

    def test_misclick_replacement_never_creates_sidelined_reply(self):
        self.add("e2e3")
        self.assertEqual("replaced", self.add("e2e4"))
        self.assertNotIn(SIDELINED_MARK, self.info.path.read_text())
        self.assertEqual(["e2e4"], [c["move_uci"] for c in self.store.compile(self.info, True)])

    def test_sidelined_reply_survives_replacements_and_reload(self):
        self.add("e2e4")
        self.sideline(self.store.compile(self.info)[0])
        self.assertEqual([], self.store.compile_all())
        self.add("d2d4")
        self.add("c2c4")
        cards = RepertoireStore(Path(self.temp.name)).compile(self.info, True)
        self.assertEqual({("e2e4", True), ("c2c4", False)},
                         {(c["move_uci"], c["sidelined"]) for c in cards})

    def test_reactivation_conflict_requires_explicit_replacement(self):
        self.add("e2e4")
        old = self.store.compile(self.info)[0]
        self.sideline(old)
        self.add("d2d4")
        before = self.info.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "conflicts"):
            self.sideline(old, False)
        self.assertEqual(before, self.info.path.read_bytes())
        self.sideline(old, False, replace_conflicts=True)
        cards = self.store.compile(self.info, True)
        self.assertEqual(["e2e4"], [c["move_uci"] for c in cards])
        self.assertFalse(cards[0]["sidelined"])

    def test_adding_under_sidelined_move_preserves_status(self):
        self.add("e2e4")
        self.sideline(self.store.compile(self.info)[0])
        self.assertEqual("sidelined", self.add("e2e4", "e7e5", "g1f3"))
        self.assertEqual([], self.store.compile(self.info))
        self.assertEqual(2, len(self.store.compile(self.info, True)))

    def test_merge_and_roundtrip_preserve_sidelined_choices(self):
        self.add("e2e4")
        self.sideline(self.store.compile(self.info)[0])
        preview = self.store.preview_import(self.info.path.read_text(), None)
        self.assertEqual([], preview["errors"])
        restored = self.store.import_preview(preview, "Copy", None, "new")
        self.assertEqual([], self.store.compile(restored))
        self.assertTrue(self.store.compile(restored, True)[0]["sidelined"])
        self.add("d2d4")
        preview = self.store.preview_import('1. e4 *', chess.WHITE)
        self.store.import_preview(preview, "Test", None, "merge")
        self.assertEqual(["d2d4"], [c["move_uci"] for c in self.store.compile(self.info)])
        self.assertEqual(2, len(self.store.compile(self.info, True)))

    def test_editing_sidelined_reply_preserves_active_alternative(self):
        self.add("e2e3")
        old = self.store.compile(self.info)[0]
        self.sideline(old)
        self.add("d2d4")
        self.store.replace_answer(self.info, old["position_key"], "e2e3", [chess.Move.from_uci("e2e4")])
        self.assertEqual({("e2e4", True), ("d2d4", False)},
                         {(c["move_uci"], c["sidelined"]) for c in self.store.compile(self.info, True)})

    def test_editing_sidelined_to_active_reply_does_not_demote_it(self):
        self.add("e2e3")
        old = self.store.compile(self.info)[0]
        self.sideline(old)
        self.add("d2d4")
        before = self.info.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "already active"):
            self.store.replace_answer(self.info, old["position_key"], "e2e3", [chess.Move.from_uci("d2d4")])
        self.assertEqual(before, self.info.path.read_bytes())

    def test_transposition_cannot_accidentally_reactivate_reply(self):
        self.add("g1f3", "d7d5", "d2d4", "g8f6")
        self.sideline(self.store.compile(self.info)[0])
        self.assertEqual("sidelined", self.add("d2d4", "d7d5", "g1f3", "g8f6"))
        self.assertEqual([], self.store.compile(self.info))
        self.assertEqual(1, len(self.store.compile(self.info, True)))

    def test_remove_sidelined_answer_clears_status(self):
        self.add("e2e4")
        card = self.store.compile(self.info)[0]
        self.sideline(card)
        self.store.remove_answer(self.info, card["position_key"], card["move_uci"])
        self.assertNotIn(SIDELINED_MARK, self.info.path.read_text())
        self.assertEqual("added", self.add("e2e4"))

    def test_browser_conflict_cancel_leaves_repertoire_untouched(self):
        self.add("e2e4")
        card = self.store.compile(self.info)[0]
        self.sideline(card)
        self.add("d2d4")
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        app.store = self.store
        app.root = MagicMock()
        before = self.info.path.read_bytes()
        with patch("app.messagebox.askyesno", return_value=False) as ask:
            app.change_sidelined([card], False)
        ask.assert_called_once()
        self.assertEqual(before, self.info.path.read_bytes())

    def test_group_follows_descendants_without_sidelining_shared_lead_in(self):
        self.add("d2d4", "g8f6")
        self.add("d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4")
        self.add("d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4", "e2e3", "e8g8")
        self.add("d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "d7d5")
        cards = self.store.compile(self.info)
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        app.repertoire_explorer_cards = cards
        nimzo = next(card for card in cards if card["move_uci"] == "f8b4")
        group = app.sideline_group_cards([nimzo])
        self.assertEqual({"f8b4", "e8g8"}, {card["move_uci"] for card in group})
        self.store.set_answers_sidelined(self.info,
            [(card["position_key"], card["move_uci"]) for card in group], True)
        self.assertEqual({"g8f6", "d7d5"}, {card["move_uci"] for card in self.store.compile(self.info)})
        self.store.set_answers_sidelined(self.info,
            [(card["position_key"], card["move_uci"]) for card in group], False)
        self.assertEqual(4, len(self.store.compile(self.info)))

    def test_multiple_sidelined_alternatives_cannot_be_bulk_reactivated(self):
        self.add("e2e4")
        first = self.store.compile(self.info)[0]
        self.sideline(first)
        self.add("d2d4")
        second = self.store.compile(self.info)[0]
        self.sideline(second)
        before = self.info.path.read_bytes()
        with self.assertRaisesRegex(ValueError, "individually"):
            self.store.set_answers_sidelined(self.info,
                [(c["position_key"], c["move_uci"]) for c in (first, second)], False)
        self.assertEqual(before, self.info.path.read_bytes())


if __name__ == "__main__":
    unittest.main()
