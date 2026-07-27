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
                "eco": "B21",
                "opening": "Sicilian Defense",
                "variation": "McDonnell Attack",
                "subvariation": "",
            },
        )

    def test_sicilian_eco_codes_distinguish_old_and_closed_systems(self) -> None:
        old = self.app.classify_opening({"pgn": "1. e4 c5 2. Nf3 Nc6 *"})
        closed = self.app.classify_opening({"pgn": "1. e4 c5 2. Nc3 Nc6 *"})

        self.assertEqual(("B30", "Old Sicilian"), (old["eco"], old["variation"]))
        self.assertEqual(("B23", "Closed"), (closed["eco"], closed["variation"]))
        self.assertEqual(
            "B30 · Sicilian Defense > Old Sicilian",
            self.app.opening_label({"pgn": "1. e4 c5 2. Nf3 Nc6 *"}),
        )

    def test_eco_codes_are_descriptors_not_hierarchy_nodes(self) -> None:
        cards = [
            {"pgn": "1. e4 c5 2. Nf3 Nc6 *"},
            {"pgn": "1. e4 c5 2. Nc3 Nc6 *"},
        ]

        opening_groups = self.app.classification_groups(cards, "opening")

        self.assertEqual(["Sicilian Defense"], list(opening_groups))
        self.assertEqual(
            "Sicilian Defense (2)  ·  ECO B30, B23",
            self.app.hierarchy_label("Sicilian Defense", cards),
        )
        self.assertEqual(
            ("Sicilian Defense", "Old Sicilian"),
            self.app.opening_path(cards[0]),
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
                "eco": "E20",
                "opening": "Nimzo-Indian Defense",
                "variation": "",
                "subvariation": "",
            },
        )

    def assert_accelerated_dragon(self, pgn: str, subvariation: str = "", eco: str = "B32") -> None:
        self.assertEqual(
            self.app.classify_opening({"pgn": pgn}),
            {
                "eco": eco,
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
                "eco": "B27",
                "opening": "Sicilian Defense",
                "variation": "Hyperaccelerated Dragon",
                "subvariation": "",
            },
        )

    def test_accelerated_dragon_english_transposition(self) -> None:
        self.assert_accelerated_dragon(
            "1. Nf3 c5 2. c4 g6 3. d4 cxd4 4. Nxd4 Nc6 5. e4 *",
            "Maróczy Bind",
            "B36",
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

        self.assertEqual("B32 · Sicilian Defense > Accelerated Dragon", label)

    def test_visible_opening_tracks_the_current_history_cursor(self) -> None:
        self.app.move_history = [
            {"move_uci": move}
            for move in ("e2e4", "c7c5", "f2f4")
        ]

        self.app.move_cursor = 3
        self.assertEqual(
            {
                "eco": "B21",
                "opening": "Sicilian Defense",
                "variation": "McDonnell Attack",
                "subvariation": "",
            },
            self.app.visible_opening(),
        )

        self.app.move_cursor = 2
        self.assertEqual(
            ("B20", "Sicilian Defense", "", ""),
            tuple(self.app.visible_opening().values()),
        )

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

    def test_variation_study_includes_sequential_lead_in_quiz_moves(self) -> None:
        cards = [
            {
                "repertoire_id": "white",
                "pgn": "1. e4 *",
                "opening": "King's Pawn Game",
                "variation": "",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "pgn": "1. e4 e6 2. d4 *",
                "opening": "French Defense",
                "variation": "Normal Variation",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "pgn": "1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 *",
                "opening": "French Defense",
                "variation": "Rubinstein Variation",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "pgn": "1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 Nd7 5. Nf3 *",
                "opening": "French Defense",
                "variation": "Rubinstein Variation",
                "subvariation": "Blackburne Defense",
            },
            {
                "repertoire_id": "white",
                "pgn": "1. e4 e6 2. d4 d5 3. Nc3 Nf6 4. Bg5 *",
                "opening": "French Defense",
                "variation": "Classical Variation",
                "subvariation": "",
            },
        ]

        selected = self.app.study_cards_for_path(
            cards,
            "white",
            ("French Defense", "Rubinstein Variation"),
        )

        self.assertEqual(cards[1:4], selected)

    def test_combined_repertoire_keeps_white_and_black_study_trees_separate(self) -> None:
        cards = [
            {
                "repertoire_id": "reid",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 c5 2. Nf3 *",
                "opening": "Sicilian Defense",
                "variation": "Bowdler Attack",
                "subvariation": "",
            },
            {
                "repertoire_id": "reid",
                "repertoire_color": chess.BLACK,
                "pgn": "1. e4 c5 *",
                "opening": "Sicilian Defense",
                "variation": "",
                "subvariation": "",
            },
        ]

        roots = [node for node in self.app.study_nodes(cards) if len(node[2]) == 1]

        self.assertEqual(2, len(roots))
        self.assertEqual({chess.WHITE, chess.BLACK}, {node[1] for node in roots})

    def test_opening_study_keeps_sequential_white_ancestors(self) -> None:
        cards = [
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 *",
                "opening": "King's Pawn Game",
                "variation": "",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 e6 2. d4 *",
                "opening": "French Defense",
                "variation": "Normal Variation",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 e6 2. d4 d5 3. Nc3 *",
                "opening": "French Defense",
                "variation": "Paulsen Variation",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 e6 2. d4 d5 3. Nc3 Nf6 4. Bg5 *",
                "opening": "French Defense",
                "variation": "Classical Variation",
                "subvariation": "",
            },
        ]

        selected = self.app.study_cards_for_path(cards, "white", ("French Defense",))

        self.assertEqual(cards[1:], selected)

    def test_opening_study_keeps_sequential_black_ancestors(self) -> None:
        cards = [
            {
                "repertoire_id": "black",
                "pgn": "1. e4 e6 *",
                "opening": "French Defense",
                "variation": "",
                "subvariation": "",
            },
            {
                "repertoire_id": "black",
                "pgn": "1. e4 e6 2. d4 d5 *",
                "opening": "French Defense",
                "variation": "Normal Variation",
                "subvariation": "",
            },
        ]

        selected = self.app.study_cards_for_path(cards, "black", ("French Defense",))

        self.assertEqual(cards, selected)

    def test_family_tree_preserves_opening_name_transitions(self) -> None:
        cards = [
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 c5 2. Nf3 *",
                "opening": "Sicilian Defense",
                "variation": "",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 c5 2. Nf3 Nc6 3. d4 *",
                "opening": "Sicilian Defense",
                "variation": "Open",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 *",
                "opening": "Sicilian Defense",
                "variation": "Accelerated Dragon",
                "subvariation": "Maróczy Bind",
            },
        ]

        paths = self.app.study_family_paths(cards)
        selected = self.app.study_cards_for_path(
            cards,
            "white",
            ("Sicilian Defense", "Open", "Accelerated Dragon"),
            chess.WHITE,
        )

        self.assertEqual(
            (
                "Sicilian Defense",
                "Open",
                "Accelerated Dragon",
                "Maróczy Bind",
            ),
            paths[-1],
        )
        self.assertEqual(cards, selected)

    def test_family_tree_nests_changed_opening_names_under_their_lead_in(self) -> None:
        cards = [
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 e5 2. Nf3 *",
                "opening": "King's Knight Opening",
                "variation": "",
                "subvariation": "",
            },
            {
                "repertoire_id": "white",
                "repertoire_color": chess.WHITE,
                "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4 *",
                "opening": "Italian Game",
                "variation": "",
                "subvariation": "",
            },
        ]

        self.assertEqual(
            [
                ("King's Knight Opening",),
                ("King's Knight Opening", "Italian Game"),
            ],
            self.app.study_family_paths(cards),
        )

    def test_quiz_setup_transition_reconstructs_the_preceding_move(self) -> None:
        card = {
            "pgn": "1. e4 e5 2. Nf3 Nc6 3. Bc4 *",
            "before_fen": (
                "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/"
                "RNBQKB1R w KQkq - 2 3"
            ),
        }

        transition = self.app.quiz_setup_transition(card)

        self.assertIsNotNone(transition)
        start_fen, move = transition
        self.assertEqual("b8c6", move.uci())
        self.assertEqual(chess.BLACK, chess.Board(start_fen).turn)

    def test_castling_animation_moves_the_king_and_rook_together(self) -> None:
        self.app.board = chess.Board()
        for uci in (
            "e2e4",
            "e7e5",
            "g1f3",
            "g8f6",
            "f1c4",
            "f8e7",
            "d2d3",
        ):
            self.app.board.push_uci(uci)

        parts = self.app.quiz_setup_animation_parts(chess.Move.from_uci("e8g8"))

        self.assertEqual(
            [
                (chess.KING, "e8", "g8"),
                (chess.ROOK, "h8", "f8"),
            ],
            [
                (
                    piece.piece_type,
                    chess.square_name(from_square),
                    chess.square_name(to_square),
                )
                for piece, from_square, to_square in parts
            ],
        )

    def test_long_king_drag_normalizes_to_the_legal_castling_move(self) -> None:
        self.app.board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")

        self.assertEqual(
            "e1g1",
            self.app.normalize_user_move(chess.E1, chess.H1).uci(),
        )
        self.assertEqual(
            "e1c1",
            self.app.normalize_user_move(chess.E1, chess.B1).uci(),
        )
        self.assertEqual(
            "e1c1",
            self.app.normalize_user_move(chess.E1, chess.A1).uci(),
        )

    def test_long_king_drag_is_not_castling_when_castling_is_illegal(self) -> None:
        self.app.board = chess.Board()

        self.assertEqual(
            "e1h1",
            self.app.normalize_user_move(chess.E1, chess.H1).uci(),
        )

    def test_quiz_title_prefers_the_most_specific_variation(self) -> None:
        self.assertEqual(
            "Accelerated Dragon",
            self.app.specific_opening_title(
                {
                    "opening": "Sicilian Defense",
                    "variation": "Accelerated Dragon",
                    "subvariation": "",
                }
            ),
        )
        self.assertEqual(
            "Maróczy Bind",
            self.app.specific_opening_title(
                {
                    "opening": "Sicilian Defense",
                    "variation": "Accelerated Dragon",
                    "subvariation": "Maróczy Bind",
                }
            ),
        )
        self.assertEqual(
            "Evans Gambit — Main Line",
            self.app.specific_opening_title(
                {
                    "opening": "Italian Game",
                    "variation": "Evans Gambit",
                    "subvariation": "Main Line",
                }
            ),
        )

    def test_quiz_cards_keep_tree_order_and_receive_local_progress(self) -> None:
        cards = [
            {"_study_path": ("French Defense", "Rubinstein Variation"), "id": "root"},
            {"_study_path": ("French Defense", "Rubinstein Variation"), "id": "leaf"},
            {"_study_path": ("French Defense", "Classical Variation"), "id": "other"},
        ]

        prepared = self.app.prepare_quiz_cards(cards)

        self.assertEqual(["root", "leaf", "other"], [card["id"] for card in prepared])
        self.assertEqual([1, 2, 1], [card["_study_position"] for card in prepared])
        self.assertEqual([2, 2, 1], [card["_study_total"] for card in prepared])
        self.assertEqual([1, 1, 2], [card["_study_block_index"] for card in prepared])

    def test_quiz_context_does_not_reveal_the_trained_answer(self) -> None:
        label = self.app.quiz_context_label(
            {"pgn": "1. e4 e6 2. d4 d5 3. Nc3 Nf6 4. Bg5 *"}
        )

        self.assertEqual("After 3... Nf6", label)

    def test_french_rubinstein_variation(self) -> None:
        classification = self.app.classify_opening(
            {"pgn": "1. e4 e6 2. d4 d5 3. Nc3 dxe4 4. Nxe4 *"}
        )

        self.assertEqual(
            {
                "eco": "C10",
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
            "Accelerated Dragon (9)  ·  ECO B32",
            state_key,
        )

        self.assertIn(state_key, self.app.repertoire_expanded_sections)
        self.assertEqual("pack", content.winfo_manager())
        restored_header = FakeHeader()
        restored_content = FakeContent()
        self.app.restore_repertoire_section(
            restored_header,
            restored_content,
            "Accelerated Dragon (9)  ·  ECO B32",
            state_key,
        )
        self.assertEqual("pack", restored_content.winfo_manager())
        self.assertEqual("-  Accelerated Dragon (9)  ·  ECO B32", restored_header.text)


if __name__ == "__main__":
    unittest.main()
