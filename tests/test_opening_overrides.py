import unittest
from unittest.mock import MagicMock

import chess

from app import TheoryVaultApp
from opening_overrides import classify_repertoire
from repertoire_tree import move_folders


def moves(san):
    board = chess.Board()
    for word in san.split():
        board.push_san(word)
    return tuple(move.uci() for move in board.move_stack)


class OverrideTests(unittest.TestCase):
    def test_grand_prix_starts_with_black_response_after_f4(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        cards = [dict(pgn=line, repertoire_id='reid-s-repertoire', repertoire_color=chess.BLACK)
                 for line in ('1. e4 c5 *', '1. e4 c5 2. Nc3 Nc6 *',
                              '1. e4 c5 2. Nc3 Nc6 3. f4 g6 *',
                              '1. e4 c5 2. Nc3 Nc6 3. f4 g6 4. Nf3 Bg7 *')]
        selected = app.study_cards_for_path(cards, 'reid-s-repertoire', ('Grand Prix Attack',), chess.BLACK)
        self.assertEqual(cards[2:], selected)
        self.assertEqual(5, app.study_branch_start(moves('e4 c5 Nc3 Nc6 f4 g6'),
                                                 'reid-s-repertoire', chess.BLACK, ('Grand Prix Attack',)))

    def test_nested_variation_skips_the_move_that_defines_it(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        cards = [dict(pgn=line, repertoire_id='other', repertoire_color=chess.WHITE)
                 for line in ('1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 *',
                              '1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6 5. c4 Bg7 6. Be3 *')]
        paths = app.study_family_paths(cards)
        selected = app.study_cards_for_path(cards, 'other', paths[0], chess.WHITE)
        self.assertEqual(cards[1:], selected)

    def test_first_prompt_shows_saved_position_without_setup_animation(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        board = chess.Board()
        for san in 'e4 c5 Nc3 Nc6 f4'.split():
            board.push_san(san)
        card = dict(before_fen=board.fen(), repertoire_color=chess.BLACK,
                    _study_position=1, _study_path=('Grand Prix Attack',))
        app.quiz_cards = [card]
        app.quiz_index = app.quiz_animation_serial = 0
        for method in ('show_quiz_title_card', 'status', 'show_text', 'draw_board',
                       'quiz_setup_transition', 'animate_quiz_setup_move'):
            setattr(app, method, MagicMock())
        app.load_current_quiz_card()
        self.assertEqual(board.fen(), app.board.fen())
        self.assertTrue(app.quiz_input_enabled)
        app.quiz_setup_transition.assert_not_called()
        app.animate_quiz_setup_move.assert_not_called()

    def test_quiz_roots_are_rules_and_lead_ins_are_excluded(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        def card(pgn, prompt):
            return dict(pgn=pgn, prompt_id=prompt, repertoire_id='reid-s-repertoire', repertoire_color=chess.WHITE)
        cards = [card('1. e4 *', 'a'), card('1. e4 e5 2. Nf3 *', 'b'),
                 card('1. e4 e5 2. Nf3 d6 3. d4 *', 'c'),
                 card('1. e4 e5 2. Nf3 d6 3. d4 Nd7 4. Bc4 *', 'd'),
                 card('1. e4 e5 2. Nf3 d6 3. d4 exd4 4. Nxd4 *', 'e'),
                 card('1. e4 e5 2. Nf3 d6 3. d4 a6 4. Bc4 *', 'f')]
        roots = {node[2][0] for node in app.study_nodes(cards) if len(node[2]) == 1}
        self.assertEqual({'Hanham Philidor', 'Exchange Philidor', 'Other saved lines'}, roots)
        chosen = app.study_cards_for_path(cards, 'reid-s-repertoire', ('Hanham Philidor',), chess.WHITE)
        self.assertEqual(['d'], [c['prompt_id'] for c in chosen])
        self.assertEqual('Other saved lines', app.study_family_paths(cards)[-1][0])

    def test_quiz_selector_combines_transposed_rule_names(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        cards = [dict(pgn=line, repertoire_id='reid-s-repertoire', repertoire_color=chess.BLACK)
                 for line in ('1. e4 c5 2. Nf3 Nc6 3. Nc3 g6 *',
                              '1. e4 c5 2. Nc3 Nc6 3. Nf3 g6 *')]
        roots = [node for node in app.study_nodes(cards) if len(node[2]) == 1]
        self.assertEqual([('reid-s-repertoire', chess.BLACK, ('Nc3 Old Sicilian',))], roots)
        self.assertEqual(cards, app.study_cards_for_path(cards, 'reid-s-repertoire', ('Nc3 Old Sicilian',), chess.BLACK))

    def test_quiz_headline_keeps_custom_parent_over_deeper_catalog_name(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        for attr in ('quiz_title_card', 'quiz_title_name', 'quiz_title_branch', 'quiz_title_kicker', 'quiz_title_progress'):
            setattr(app, attr, MagicMock())
        card = dict(pgn='1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 *',
                    repertoire_id='reid-s-repertoire', repertoire_color=chess.BLACK)
        app.show_quiz_title_card(card)
        app.quiz_title_name.configure.assert_called_with(text='Benoni')
        self.assertIn('Benko', app.quiz_title_branch.configure.call_args.kwargs['text'])

    def test_success_and_failure_feedback_advance_after_half_a_second(self):
        for answer in ('e2e4', 'd2d4'):
            app = TheoryVaultApp.__new__(TheoryVaultApp)
            app.board = chess.Board()
            app.quiz_cards = [dict(prompt_id='example', accepted_uci=['e2e4'], move_san='e4')]
            app.quiz_index = app.quiz_score = 0
            app.quiz_attempt_counts = {}
            for method in ('root', 'status', 'add_quiz_result', 'show_feedback', 'draw_board',
                           'animate_correct_move_square', 'animate_incorrect_move_square'):
                setattr(app, method, MagicMock())
            app.handle_quiz_move(chess.Move.from_uci(answer))
            app.root.after.assert_called_once_with(500, app.advance_quiz)

    def test_shared_sicilian_position_has_one_name(self):
        for line in ('e4 c5 Nf3 Nc6 Nc3', 'e4 c5 Nc3 Nc6 Nf3'):
            match = classify_repertoire(moves(line), 'reid-s-repertoire', chess.BLACK)
            self.assertEqual('Nc3 Old Sicilian', match.opening)

    def test_unlisted_move_order_recognized_by_position(self):
        match = classify_repertoire(moves('Nf3 d5 e4'), 'reid-s-repertoire', chess.WHITE)
        # This is not an override endpoint, so the catalog still applies.
        self.assertNotEqual('reidmate_override', match.source)
        match = classify_repertoire(moves('Nf3 c5 e4 Nc6 Bb5'), 'reid-s-repertoire', chess.BLACK)
        self.assertEqual('Rossolimo', match.opening)

    def test_scope_and_color_are_respected(self):
        line = moves('e4 c5 Nf3 Nc6 Bb5')
        self.assertNotEqual('Rossolimo', classify_repertoire(line, 'other', chess.BLACK).opening)
        self.assertNotEqual('Rossolimo', classify_repertoire(line, 'reid-s-repertoire', chess.WHITE).opening)

    def test_deeper_catalog_branch_stays_below_custom_parent(self):
        match = classify_repertoire(moves('d4 Nf6 c4 c5 d5 b5'), 'reid-s-repertoire', chess.BLACK)
        self.assertEqual('Benoni', match.opening)
        self.assertIn('Benko', match.variation)

    def test_quiz_title_does_not_reveal_the_expected_reply(self):
        app = TheoryVaultApp.__new__(TheoryVaultApp)
        card = dict(pgn='1. e4 c5 2. Nc3 Nc6 3. f4 *', repertoire_id='reid-s-repertoire', repertoire_color=chess.BLACK)
        self.assertEqual('Grand Prix Attack', app.classify_opening(card)['opening'])
        self.assertNotEqual('Grand Prix Attack', app.classify_quiz_position(card)['opening'])

    def test_folder_override_preserves_card_and_move_path(self):
        card = dict(pgn='1. e4 e5 2. Nf3 d6 3. d4 Nd7 4. Bc4 *', repertoire_id='reid-s-repertoire', repertoire_color=chess.WHITE)
        original = dict(card)
        def walk(folders):
            for folder in folders:
                yield folder
                yield from walk(folder.children)
        folders = list(walk(move_folders([card])))
        self.assertTrue(any(f.name == 'Hanham Philidor' for f in folders))
        self.assertEqual([card], [row for f in folders for row in f.rows])
        self.assertEqual(original, card)
