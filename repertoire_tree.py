"""Compact repertoire folders whose ancestry follows exact move prefixes."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from functools import lru_cache

import chess
import chess.pgn

from opening_overrides import classify_repertoire
from repertoire_store import position_key


@dataclass
class MoveFolder:
    key: tuple[str, ...]
    name: str
    eco: str
    move_label: str
    cards: list[dict] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    children: list[MoveFolder] = field(default_factory=list)


@lru_cache(maxsize=4096)
def _line(pgn: str) -> tuple[str, tuple[str, ...]]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        return chess.STARTING_FEN, ()
    return game.board().fen(), tuple(move.uci() for move in game.mainline_moves())


@lru_cache(maxsize=8192)
def _classification(path: tuple[str, ...], repertoire_id=None, color=None) -> tuple[str, str]:
    match = classify_repertoire(path, repertoire_id, color)
    name = match.opening
    if match.variation:
        name += f": {match.variation}"
    if match.subvariation:
        name += f", {match.subvariation}"
    return name, match.eco


@lru_cache(maxsize=4096)
def _positions(fen: str, path: tuple[str, ...]) -> tuple[str, ...]:
    board = chess.Board(fen)
    positions = []
    for uci in path:
        positions.append(position_key(board))
        board.push_uci(uci)
    return tuple(positions)


def _continuation(card: dict, target: str) -> tuple[str, ...] | None:
    """Find a saved route through this position, including alternate contexts."""
    fen, path = _line(card.get("pgn", ""))
    candidates = [(fen, path)]
    answer = card.get("move_uci") or (path[-1] if path else None)
    if answer:
        for context in card.get("contexts", []):
            root, moves = _line(context)
            candidates.append((root, (*moves, answer)))
    for root, moves in candidates:
        positions = _positions(root, moves)
        if target in positions:
            return moves[positions.index(target):]
    return None


def move_folders(cards: list[dict], focus_path: tuple[str, ...] | None = None,
                 root_fen: str = chess.STARTING_FEN) -> list[MoveFolder]:
    """Keep each saved answer once; names annotate rather than define ancestry."""
    focus_board = chess.Board(root_fen)
    focus_label = "Current position"
    if focus_path is not None:
        for uci in focus_path:
            move = chess.Move.from_uci(uci)
            focus_label = f"{focus_board.fullmove_number}{'.' if focus_board.turn else '...'} {focus_board.san(move)}"
            focus_board.push(move)
    target = position_key(focus_board)
    roots: dict[tuple[str, ...], dict] = {}
    for card in cards:
        fen, path = _line(card.get("pgn", ""))
        if focus_path is not None:
            suffix = _continuation(card, target)
            if suffix is None:
                continue
            # Rebase the display only. The original card retains its saved
            # move order for View/Edit/Remove, including transposed contexts.
            fen, path = root_fen, (*focus_path, *suffix)
        scope = (card["repertoire_id"], str(card["repertoire_color"]), fen)
        node = roots.setdefault(scope, {"children": {}, "rows": []})
        for move in path:
            node = node["children"].setdefault(move, {"children": {}, "rows": []})
        node["rows"].append(card)

    def build(node: dict, scope: tuple[str, ...], path: tuple[str, ...],
              board: chess.Board, move_label: str) -> MoveFolder:
        name, eco = (_classification(path, scope[0], scope[1] == str(chess.WHITE)) if scope[2] == chess.STARTING_FEN
                     else ("Custom position", ""))
        folder = MoveFolder((*scope, *path), name, eco, move_label, rows=list(node["rows"]))
        for uci, child in node["children"].items():
            move = chess.Move.from_uci(uci)
            label = f"{board.fullmove_number}{'.' if board.turn else '...'} {board.san(move)}"
            after = board.copy(stack=False)
            after.push(move)
            folder.children.append(build(child, scope, (*path, uci), after, label))
        folder.cards = folder.rows + [card for child in folder.children for card in child.cards]
        # Consecutive moves with the same name share a folder. Retain forks
        # and every name/ECO transition, including transitions without a quiz mark.
        while len(folder.children) == 1:
            child = folder.children[0]
            if (folder.name, folder.eco) != (child.name, child.eco):
                break
            folder.rows.extend(child.rows)
            folder.children = child.children
        return folder

    result = []
    for scope, root in roots.items():
        if focus_path is not None:
            node = root
            for uci in focus_path:
                node = node["children"][uci]
            result.append(build(node, scope, focus_path, focus_board, focus_label))
            continue
        board = chess.Board(scope[2])
        # Normally the root has no trained answer. Retain malformed/empty
        # contexts rather than silently dropping a saved card.
        if root["rows"]:
            result.append(build(root, scope, (), board, "Starting position"))
            continue
        for uci, child in root["children"].items():
            move = chess.Move.from_uci(uci)
            label = f"{board.fullmove_number}{'.' if board.turn else '...'} {board.san(move)}"
            after = board.copy(stack=False)
            after.push(move)
            result.append(build(child, scope, (uci,), after, label))
    return result
