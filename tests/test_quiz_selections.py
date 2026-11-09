from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app import TheoryVaultApp
from quiz_selections import QuizSelections


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'choices.json'
        self.a = ('reid', True, ('Hanham Philidor',))
        self.b = ('reid', True, ('Exchange Philidor',))

    def test_checked_and_unchecked_choices_survive_restart(self):
        prefs = QuizSelections(self.path)
        self.assertEqual({self.a: True, self.b: True}, prefs.values_for([self.a, self.b]))
        prefs.save({self.a: False, self.b: True})
        self.assertEqual({self.a: False, self.b: True}, QuizSelections(self.path).values_for([self.a, self.b]))
        prefs.save({self.a: False, self.b: False})
        self.assertFalse(any(QuizSelections(self.path).values_for([self.a, self.b]).values()))

    def test_scope_new_nodes_and_temporarily_missing_nodes(self):
        QuizSelections(self.path).save({self.a: True, self.b: False})
        prefs = QuizSelections(self.path)
        prefs.save({self.b: True})
        child = ('reid', True, ('Hanham Philidor', 'New child'))
        new = ('reid', True, ('New opening',))
        black = ('reid', False, ('Hanham Philidor',))
        other = ('another', True, ('Hanham Philidor',))
        values = QuizSelections(self.path).values_for([self.a, new, child, black, other])
        self.assertEqual([True, False, False, True, True], list(values.values()))

    def test_ply_limit_preserves_intended_selection(self):
        QuizSelections(self.path).save({self.a: False, self.b: False}, {self.a})
        self.assertEqual({self.a: True, self.b: False}, QuizSelections(self.path).values_for([self.a, self.b]))

    def test_corrupt_file_falls_back_and_failed_save_keeps_existing_file(self):
        self.path.write_text('broken json')
        prefs = QuizSelections(self.path)
        self.assertTrue(prefs.values_for([self.a])[self.a])
        prefs.save({self.a: False})
        original = self.path.read_bytes()
        with patch('quiz_selections.os.replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                prefs.save({self.a: True})
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual([], list(self.path.parent.glob('*.tmp')))

    def test_selector_clear_cancel_and_reopen_retain_unchecked_state(self):
        class Variable:
            def __init__(self, value=None): self.value = value
            def get(self): return self.value
            def set(self, value): self.value = value
            def trace_add(self, *args): pass

        with patch('app.tk') as tk, patch('app.ttk') as ttk, patch('app.QuizSelections', side_effect=lambda: QuizSelections(self.path)):
            tk.StringVar.side_effect = tk.BooleanVar.side_effect = Variable
            dialog = tk.Toplevel.return_value
            dialog.winfo_width.return_value = dialog.winfo_height.return_value = 200
            app = TheoryVaultApp.__new__(TheoryVaultApp)
            app.root = MagicMock()
            app.status = MagicMock()
            app.root.winfo_width.return_value = app.root.winfo_height.return_value = 600
            app.root.winfo_rootx.return_value = app.root.winfo_rooty.return_value = 0
            cards = [dict(pgn='1. e4 c5 2. f4 *', repertoire_id='test', repertoire_color=False,
                          repertoire_name='Test', prompt_id='a')]
            app.show_quiz_selector(cards)
            next(c.kwargs['command'] for c in ttk.Button.call_args_list if c.kwargs.get('text') == 'Clear all')()
            next(c.kwargs['command'] for c in ttk.Button.call_args_list if c.kwargs.get('text') == 'Cancel')()
            ttk.Checkbutton.reset_mock()
            app.show_quiz_selector(cards)
            self.assertTrue(ttk.Checkbutton.call_args_list)
            self.assertTrue(all(not c.kwargs['variable'].get() for c in ttk.Checkbutton.call_args_list))
