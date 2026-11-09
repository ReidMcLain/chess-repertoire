import unittest
import io

import chess
import chess.pgn

from repertoire_tree import move_folders


def card(pgn, repertoire="test", side=False, sidelined=False):
    return dict(pgn=pgn, repertoire_id=repertoire, repertoire_color=side, sidelined=sidelined)


def walk(folders):
    for folder in folders:
        yield folder
        yield from walk(folder.children)


class RepertoireTreeTests(unittest.TestCase):
    def path(self, pgn):
        return tuple(m.uci() for m in chess.pgn.read_game(io.StringIO(pgn)).mainline_moves())

    def test_current_accelerated_dragon_hides_ancestors_and_keeps_future_branches(self):
        prefix = "1. e4 c5 2. Nf3 Nc6 3. d4 cxd4 4. Nxd4 g6"
        cards = [card(prefix + " 5. c4 *"), card(prefix + " 5. Nc3 *")]
        focused = move_folders(cards, self.path(prefix))
        self.assertEqual(1, len(focused))
        self.assertEqual("Sicilian Defense: Accelerated Dragon", focused[0].name)
        self.assertEqual("B32", focused[0].eco)
        self.assertEqual(2, len(focused[0].children))
        self.assertCountEqual(list(map(id, cards)), [id(c) for n in walk(focused) for c in n.rows])
        self.assertEqual("King's Pawn Game", move_folders(cards)[0].name)

    def test_focus_does_not_jump_ahead_to_next_opening(self):
        cards = [card("1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 a6 *")]
        benoni = move_folders(cards, self.path("1. d4 Nf6 2. c4 c5"))
        self.assertEqual("Benoni Defense", benoni[0].name)
        self.assertEqual("Benko Gambit", benoni[0].children[0].name)
        benko = move_folders(cards, self.path("1. d4 Nf6 2. c4 c5 3. d5 b5"))
        self.assertEqual("Benko Gambit", benko[0].name)

    def test_focus_removes_played_moves_and_unrelated_branches(self):
        cards = [card("1. e4 *"), card("1. e4 e5 *"), card("1. d4 d5 *")]
        folders = move_folders(cards, self.path("1. e4"))
        self.assertEqual([cards[1]], folders[0].cards)
        self.assertEqual([], move_folders(cards, self.path("1. e4 e5")))

    def test_transposed_and_alternate_contexts_share_current_folder(self):
        first = card("1. Nf3 d5 2. d4 Nf6 3. c4 *")
        second = card("1. d4 d5 2. Nf3 Nf6 3. e3 *")
        third = card("1. Nf3 Nf6 2. d4 d5 3. g3 *")
        third.update(move_uci="g2g3", contexts=["1. Nf3 Nf6 2. d4 d5 *", "1. d4 d5 2. Nf3 Nf6 *"])
        # This intermediate position exists only in the third card's alternate route.
        folders = move_folders([first, second, third], self.path("1. d4 d5"))
        self.assertEqual(1, len(folders))
        self.assertCountEqual([id(second), id(third)], [id(c) for c in folders[0].cards])
        # Once the transposition is reached, all three saved routes are valid.
        folders = move_folders([first, second, third], self.path("1. d4 d5 2. Nf3 Nf6"))
        self.assertEqual(1, len(folders))
        self.assertEqual(3, len(folders[0].cards))
        self.assertEqual("1. Nf3 d5 2. d4 Nf6 3. c4 *", first["pgn"])

    def test_custom_position_can_be_focused(self):
        fen = "8/8/8/8/8/5k2/8/7K w - - 0 1"
        saved = card(f'[SetUp "1"]\n[FEN "{fen}"]\n\n1. Kh2 Ke2 *')
        folders = move_folders([saved], ("h1h2",), fen)
        self.assertEqual("Custom position", folders[0].name)
        self.assertEqual([saved], folders[0].cards)

    def test_benko_name_changes_nest_under_exact_move_ancestors(self):
        cards = [card("1. d4 Nf6 2. c4 c5 *"),
                 card("1. d4 Nf6 2. c4 c5 3. d5 b5 *"),
                 card("1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 a6 *")]
        folders = move_folders(cards)
        benoni = next(n for n in walk(folders) if n.name == "Benoni Defense")
        benko = next(n for n in benoni.children if n.name == "Benko Gambit")
        accepted = next(n for n in benko.children if n.name == "Benko Gambit Accepted")
        self.assertEqual(["A56", "A57", "A57"], [n.eco for n in (benoni, benko, accepted)])
        self.assertEqual([[cards[0]], [cards[1]], [cards[2]]], [n.rows for n in (benoni, benko, accepted)])
        self.assertEqual(cards, benoni.cards)

    def test_untrained_prefixes_preserve_taxonomy_when_filtering(self):
        accepted = card("1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 a6 *", sidelined=True)
        before = card("1. d4 Nf6 2. c4 c5 *")
        complete = {n.key: n.name for n in walk(move_folders([before, accepted]))}
        filtered = list(walk(move_folders([accepted])))
        self.assertTrue({"Benoni Defense", "Benko Gambit", "Benko Gambit Accepted"}.issubset({n.name for n in filtered}))
        self.assertTrue(all(complete[n.key] == n.name for n in filtered))
        self.assertEqual([accepted], [c for n in filtered for c in n.rows])

    def test_same_names_on_different_move_orders_remain_separate(self):
        cards = [card("1. d4 Nf6 2. c4 c5 *"), card("1. c4 Nf6 2. d4 c5 *")]
        folders = move_folders(cards)
        benonis = [n for n in walk(folders) if n.name == "Benoni Defense"]
        self.assertEqual(2, len(benonis))
        self.assertNotEqual(benonis[0].key, benonis[1].key)
        self.assertEqual([[cards[0]], [cards[1]]], [n.cards for n in benonis])

    def test_forks_keep_shared_lead_in_once_and_each_answer_once(self):
        cards = [card("1. e4 *", side=True),
                 card("1. e4 e5 2. Nf3 *", side=True),
                 card("1. e4 c5 2. Nf3 *", side=True)]
        folders = move_folders(cards)
        self.assertEqual(1, len(folders))
        self.assertEqual([cards[0]], folders[0].rows)
        self.assertEqual(2, len(folders[0].children))
        self.assertCountEqual(list(map(id, cards)), [id(c) for n in walk(folders) for c in n.rows])
        for child in folders[0].children:
            self.assertNotIn(cards[0], child.cards)

    def test_continuous_same_named_moves_share_a_folder(self):
        cards = [card("1. d4 Nf6 2. c4 c5 3. d5 b5 *"),
                 card("1. d4 Nf6 2. c4 c5 3. d5 b5 4. cxb5 *", side=False)]
        benkos = [n for n in walk(move_folders(cards)) if n.name == "Benko Gambit"]
        self.assertEqual(1, len(benkos))
        self.assertEqual(cards, benkos[0].rows)

    def test_repertoires_sides_and_starting_positions_have_distinct_roots(self):
        custom = '[SetUp "1"]\n[FEN "8/8/8/8/8/5k2/8/7K w - - 0 1"]\n\n1. Kh2 *'
        cards = [card("1. e4 *"), card("1. e4 *", repertoire="other"),
                 card("1. e4 *", side=True), card(custom)]
        folders = move_folders(cards)
        self.assertEqual(4, len(folders))
        self.assertEqual(4, len({n.key for n in folders}))
        self.assertEqual("Custom position", folders[-1].name)
        self.assertEqual("1. Kh2", folders[-1].move_label)


if __name__ == "__main__":
    unittest.main()
