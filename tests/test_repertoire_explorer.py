import io
import unittest
from unittest.mock import MagicMock

import chess
import chess.pgn

from app import ChessMvpApp


def board_after(pgn: str) -> chess.Board:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise AssertionError("Test PGN could not be parsed")
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board


def continuation_card(name: str, context: str) -> dict:
    return {
        "name": name,
        "before_fen": board_after(context).fen(en_passant="legal"),
        "contexts": [context],
    }


def saved_move_card(pgn: str) -> dict:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise AssertionError("Test PGN could not be parsed")
    board = game.board()
    moves = list(game.mainline_moves())
    for move in moves[:-1]:
        board.push(move)
    return {
        "pgn": pgn,
        "before_fen": board.fen(en_passant="legal"),
        "move_san": board.san(moves[-1]),
    }


class RepertoireExplorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = ChessMvpApp.__new__(ChessMvpApp)

    def test_position_keeps_exact_reply_and_every_later_continuation(self) -> None:
        exact_reply = continuation_card("Nf3", "1. e4 c5 *")
        later_reply = continuation_card("Bb5", "1. e4 c5 2. Nf3 Nc6 *")
        already_played = continuation_card("e4", "*")
        unrelated = continuation_card("c4", "1. d4 d5 *")
        current = board_after("1. e4 c5 *")

        matches = self.app.filter_repertoire_continuations(
            [exact_reply, later_reply, already_played, unrelated],
            current,
        )

        self.assertEqual(["Nf3", "Bb5"], [card["name"] for card in matches])

    def test_transposed_move_order_matches_the_same_resulting_position(self) -> None:
        saved_line = continuation_card("c4", "1. Nf3 d5 2. d4 Nf6 *")
        current = board_after("1. d4 Nf6 2. Nf3 d5 *")

        matches = self.app.filter_repertoire_continuations([saved_line], current)

        self.assertEqual([saved_line], matches)

    def test_show_all_preserves_every_repertoire_before_exploring(self) -> None:
        cards = [
            continuation_card("e4", "*"),
            continuation_card("custom branch", "1. d4 d5 *"),
        ]

        matches = self.app.filter_repertoire_continuations(
            cards,
            chess.Board(),
            show_all=True,
        )

        self.assertEqual(cards, matches)

    def test_explorer_visibly_disables_add_move(self) -> None:
        self.app.add_move_button = MagicMock()

        self.app.set_repertoire_explorer_active(True)

        self.assertTrue(self.app.repertoire_explorer_active)
        self.app.add_move_button.configure.assert_called_once_with(state="disabled")

    def test_unnamed_lines_split_at_the_first_actual_move_divergence(self) -> None:
        trunk = saved_move_card("1. e4 e5 *")
        knight_line = saved_move_card("1. e4 e5 2. Nf3 Nc6 *")
        bishop_line = saved_move_card("1. e4 e5 2. Bc4 Nf6 *")

        shared, branches = self.app.split_repertoire_branches(
            [trunk, knight_line, bishop_line]
        )

        self.assertEqual([trunk], shared)
        self.assertEqual(["2. Nf3", "2. Bc4"], [label for label, _cards in branches])
        self.assertEqual([[knight_line], [bishop_line]], [cards for _label, cards in branches])

    def test_branch_split_finds_a_later_fork_below_a_shared_saved_move(self) -> None:
        shared = saved_move_card("1. e4 e5 2. Nf3 *")
        nc6_line = saved_move_card("1. e4 e5 2. Nf3 Nc6 3. Bb5 *")
        nf6_line = saved_move_card("1. e4 e5 2. Nf3 Nf6 3. Nxe5 *")

        trunk, branches = self.app.split_repertoire_branches([shared, nc6_line, nf6_line])

        self.assertEqual([shared], trunk)
        self.assertEqual(["2... Nc6", "2... Nf6"], [label for label, _cards in branches])

    def test_move_counter_shows_chess_move_and_ply(self) -> None:
        white_move = saved_move_card("1. e4 e5 2. Nf3 Nc6 3. Bb5 *")
        black_move = saved_move_card("1. e4 e5 2. Nf3 Nc6 *")

        self.assertEqual(
            "Move 3  ·  ply 5  ·  3. Bb5",
            self.app.repertoire_move_counter(white_move),
        )
        self.assertEqual(
            "Move 2  ·  ply 4  ·  2... Nc6",
            self.app.repertoire_move_counter(black_move),
        )


if __name__ == "__main__":
    unittest.main()
