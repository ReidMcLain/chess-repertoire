"""Persistent quiz choices, separated by repertoire, side, and opening path."""
import json
import os
from pathlib import Path
import tempfile

from app_paths import user_data_directory


class QuizSelections:
    def __init__(self, path: Path | None = None):
        self.path = path if path is not None else user_data_directory() / 'quiz-selections.json'
        self.choices = {}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or data.get('version') != 1:
                return
            entries = data.get('choices', [])
            if not isinstance(entries, list):
                return
            for row in entries:
                if (isinstance(row, dict) and isinstance(row.get('repertoire'), str)
                        and type(row.get('color')) is bool and type(row.get('checked')) is bool
                        and isinstance(row.get('path'), list) and row['path']
                        and all(isinstance(label, str) for label in row['path'])):
                    self.choices[(row['repertoire'], row['color'], tuple(row['path']))] = row['checked']
        except (OSError, ValueError):
            # Missing or damaged settings should never prevent opening a quiz.
            pass

    def values_for(self, nodes):
        known_scopes = {node[:2] for node in self.choices}
        return {node: self.choices.get(node, len(node[2]) == 1 and node[:2] not in known_scopes)
                for node in nodes}

    def save(self, values, temporarily_disabled=()):
        # A ply limit hides a selection; it does not change the user's choice.
        updated = {**self.choices, **{node: bool(value or node in temporarily_disabled)
                                    for node, value in values.items()}}
        data = {'version': 1, 'choices': [
            {'repertoire': node[0], 'color': node[1], 'path': list(node[2]), 'checked': checked}
            for node, checked in updated.items()
        ]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                             prefix='.quiz-selections-', suffix='.tmp', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.choices = updated
