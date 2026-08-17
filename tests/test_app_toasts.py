import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import chess

from app import ChessMvpApp, DESTRUCTIVE, SUCCESS


class AppToastTests(unittest.TestCase):
    def make_save_app(self, outcome: str, before_fen: str) -> ChessMvpApp:
        app = ChessMvpApp.__new__(ChessMvpApp)
        app.mode = "play"
        app.move_cursor = 1
        app.move_history = [
            {
                "before_fen": before_fen,
                "move_uci": "e2e4" if chess.Board(before_fen).turn == chess.WHITE else "e7e5",
                "move_san": "e4" if chess.Board(before_fen).turn == chess.WHITE else "e5",
            }
        ]
        app.status = MagicMock()
        app.store = MagicMock()
        app.store.add_line.return_value = outcome
        app.current_repertoire = lambda: SimpleNamespace(name="Main Lines")
        app.show_toast = MagicMock()
        return app

    def test_added_move_toast_names_white_side_move_and_repertoire(self) -> None:
        app = self.make_save_app("added", chess.Board().fen())

        app.save_last_move()

        app.show_toast.assert_called_once_with(
            "Added to White repertoire",
            "e4 · Main Lines",
            SUCCESS,
        )

    def test_replaced_move_toast_uses_the_actual_black_side(self) -> None:
        board = chess.Board()
        board.push_uci("e2e4")
        app = self.make_save_app("replaced", board.fen())

        app.save_last_move()

        app.show_toast.assert_called_once_with(
            "Added to Black repertoire",
            "e5 · Main Lines",
            SUCCESS,
        )

    def test_duplicate_move_does_not_show_an_addition_toast(self) -> None:
        app = self.make_save_app("duplicate", chess.Board().fen())

        app.save_last_move()

        app.show_toast.assert_not_called()

    @patch("app.messagebox.askyesno", return_value=True)
    def test_removed_move_toast_is_red_and_names_the_move(self, _askyesno: MagicMock) -> None:
        app = ChessMvpApp.__new__(ChessMvpApp)
        info = SimpleNamespace(name="French Defense")
        app.root = object()
        app.store = MagicMock()
        app.store.get.return_value = info
        app.store.remove_answer.return_value = 1
        app.status = MagicMock()
        app.view_repertoire = MagicMock()
        app.show_toast = MagicMock()
        card = {
            "repertoire_id": "french-defense",
            "repertoire_color": chess.BLACK,
            "position_key": "position",
            "accepted_moves": [{"move_san": "e6", "move_uci": "e7e6"}],
        }

        app.remove_card_answer(card)

        app.show_toast.assert_called_once_with(
            "Deleted from Black repertoire",
            "e6 · French Defense",
            DESTRUCTIVE,
        )


if __name__ == "__main__":
    unittest.main()
