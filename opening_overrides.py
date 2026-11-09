"""ReidMate display names, matched by position without rewriting PGNs."""
from functools import lru_cache
import json

import chess

from app_paths import resource_path
from opening_classifier import OPENING_CLASSIFIER, OpeningMatch, position_key


def _full_name(match):
    name = match.opening
    if match.variation:
        name += ': ' + match.variation
    if match.subvariation:
        name += ', ' + match.subvariation
    return name


@lru_cache(maxsize=1)
def _rules():
    data = json.loads(resource_path('data', 'openings', 'reidmate_overrides.json').read_text(encoding='utf-8'))
    positions = {}
    for rule in data['rules']:
        board = chess.Board()
        for san in rule['moves']:
            board.push_san(san)
        name = data['position_aliases'].get(rule['name'], rule['name'])
        for color in rule.get('colors', ['White']):
            key = (color == 'White', position_key(board))
            previous = positions.setdefault(key, name)
            if previous != name:
                raise ValueError(f'Conflicting opening overrides: {previous} and {name}')
    return frozenset(data['repertoire_ids']), positions


def classify_repertoire(moves, repertoire_id=None, color=None):
    return _classify(tuple(moves), repertoire_id, color)


def uses_reidmate_rules(repertoire_id):
    return repertoire_id in _rules()[0]


@lru_cache(maxsize=8192)
def _classify(moves, repertoire_id, color):
    base = OPENING_CLASSIFIER.classify(moves)
    scopes, positions = _rules()
    if repertoire_id not in scopes or color is None:
        return base
    board = chess.Board()
    anchor = None
    for ply, uci in enumerate(moves, 1):
        try:
            board.push_uci(uci)
        except ValueError:
            break
        name = positions.get((color, position_key(board)))
        if name:
            anchor = (ply, name)
    if anchor is None:
        return base
    ply, name = anchor
    # Keep later catalog discoveries as descendants of the user's named parent.
    at_anchor = OPENING_CLASSIFIER.classify(moves[:ply])
    detail = (_full_name(base) if base.deepest_ply > ply
              and _full_name(base) != _full_name(at_anchor) else '')
    return OpeningMatch(base.eco, name, detail, '', max(ply, base.deepest_ply), 'reidmate_override')
