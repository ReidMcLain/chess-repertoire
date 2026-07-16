from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import chess
import chess.pgn


QUIZ_MARK = "[%crm_quiz 1]"
QUIZ_MARK_RE = re.compile(r"(?:\s*\[%crm_quiz\s+1\]\s*)")


@dataclass(frozen=True)
class RepertoireInfo:
    path: Path
    name: str
    color: bool

    @property
    def id(self) -> str:
        return self.path.stem


def position_key(board_or_fen: chess.Board | str) -> str:
    board = chess.Board(board_or_fen) if isinstance(board_or_fen, str) else board_or_fen
    return " ".join(board.fen(en_passant="legal").split()[:4])


def is_quiz_node(node: chess.pgn.ChildNode) -> bool:
    return bool(QUIZ_MARK_RE.search(node.comment or ""))


def mark_quiz_node(node: chess.pgn.ChildNode) -> None:
    if not is_quiz_node(node):
        node.comment = f"{node.comment.strip()} {QUIZ_MARK}".strip()


def unmark_quiz_node(node: chess.pgn.ChildNode) -> None:
    node.comment = QUIZ_MARK_RE.sub(" ", node.comment or "").strip()


def parse_pgn(text: str) -> tuple[list[chess.pgn.Game], list[str]]:
    stream = io.StringIO(text)
    games: list[chess.pgn.Game] = []
    errors: list[str] = []
    while True:
        try:
            game = chess.pgn.read_game(stream)
        except (ValueError, IndexError) as exc:
            errors.append(str(exc))
            break
        if game is None:
            break
        games.append(game)
        errors.extend(str(error) for error in game.errors)
    if not games and not errors:
        errors.append("No PGN games were found")
    return games, errors


def export_games(games: list[chess.pgn.Game]) -> str:
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
    return "\n\n".join(game.accept(exporter).strip() for game in games) + "\n"


def _merge_comment(existing: str, incoming: str) -> str:
    existing = existing.strip()
    incoming = incoming.strip()
    if not incoming or incoming == existing or incoming in existing:
        return existing
    if not existing:
        return incoming
    return f"{existing} {incoming}"


def merge_nodes(target: chess.pgn.GameNode, source: chess.pgn.GameNode) -> None:
    for source_child in source.variations:
        target_child = next((child for child in target.variations if child.move == source_child.move), None)
        if target_child is None:
            target_child = target.add_variation(source_child.move)
        target_child.comment = _merge_comment(target_child.comment, source_child.comment)
        target_child.starting_comment = _merge_comment(target_child.starting_comment, source_child.starting_comment)
        target_child.nags.update(source_child.nags)
        merge_nodes(target_child, source_child)


def merge_game_into(games: list[chess.pgn.Game], incoming: chess.pgn.Game) -> chess.pgn.Game:
    incoming_key = position_key(incoming.board())
    target = next((game for game in games if position_key(game.board()) == incoming_key), None)
    if target is None:
        target = chess.pgn.Game()
        target.headers.clear()
        target.headers.update(incoming.headers)
        merge_nodes(target, incoming)
        games.append(target)
        return target
    merge_nodes(target, incoming)
    return target


def trained_answer_choices(games: list[chess.pgn.Game]) -> dict[str, str]:
    selected: dict[str, str] = {}

    def collect(node: chess.pgn.GameNode, board: chess.Board) -> None:
        key = position_key(board)
        for child in node.variations:
            if is_quiz_node(child):
                selected[key] = child.move.uci()
            next_board = board.copy(stack=False)
            next_board.push(child.move)
            collect(child, next_board)

    for game in games:
        collect(game, game.board())
    return selected


def enforce_single_answers(
    games: list[chess.pgn.Game],
    preferred: dict[str, str] | None = None,
) -> int:
    """Keep one trained move per normalized position; the latest move wins."""
    selected = trained_answer_choices(games)
    if preferred:
        selected.update(preferred)

    removed = 0

    def remove_others(node: chess.pgn.GameNode, board: chess.Board) -> None:
        nonlocal removed
        key = position_key(board)
        chosen_move = selected.get(key)
        for child in node.variations:
            if is_quiz_node(child) and child.move.uci() != chosen_move:
                unmark_quiz_node(child)
                removed += 1
            next_board = board.copy(stack=False)
            next_board.push(child.move)
            remove_others(child, next_board)

    for game in games:
        remove_others(game, game.board())
    return removed


def _line_pgn(moves: list[chess.Move], root_board: chess.Board) -> str:
    game = chess.pgn.Game()
    if root_board.fen() != chess.Board().fen():
        game.setup(root_board)
    node: chess.pgn.GameNode = game
    for move in moves:
        node = node.add_variation(move)
    exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False, columns=None)
    return game.accept(exporter).strip()


def _headers(name: str, color: bool) -> dict[str, str]:
    return {
        "Event": name,
        "Site": "Chess Repertoire Memorizer",
        "Date": datetime.now().strftime("%Y.%m.%d"),
        "Round": "-",
        "White": "?",
        "Black": "?",
        "Result": "*",
        "RepertoireColor": "White" if color else "Black",
        "CRMVersion": "1",
    }


def _apply_headers(games: list[chess.pgn.Game], name: str, color: bool) -> None:
    for game in games:
        preserved = dict(game.headers)
        game.headers.clear()
        game.headers.update(_headers(name, color))
        for key, value in preserved.items():
            if key not in game.headers and key not in {"RepertoireColor", "CRMVersion"}:
                game.headers[key] = value


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "repertoire"


class RepertoireStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def list_repertoires(self) -> list[RepertoireInfo]:
        infos: list[RepertoireInfo] = []
        if not self.directory.exists():
            return infos
        for path in sorted(self.directory.glob("*.pgn")):
            games, errors = parse_pgn(path.read_text(encoding="utf-8"))
            if not games or errors:
                continue
            color_text = games[0].headers.get("RepertoireColor", "White").lower()
            color = color_text != "black"
            name = games[0].headers.get("Event", path.stem.replace("-", " ").title())
            infos.append(RepertoireInfo(path, name, color))
        return infos

    def get(self, repertoire_id: str) -> RepertoireInfo | None:
        return next((info for info in self.list_repertoires() if info.id == repertoire_id), None)

    def read_games(self, info: RepertoireInfo) -> list[chess.pgn.Game]:
        games, errors = parse_pgn(info.path.read_text(encoding="utf-8"))
        if errors:
            raise ValueError("; ".join(errors))
        enforce_single_answers(games)
        return games

    def _available_path(self, name: str, current: Path | None = None) -> Path:
        base = self.directory / f"{slugify(name)}.pgn"
        if not base.exists() or (current and base == current):
            return base
        index = 2
        while True:
            candidate = self.directory / f"{slugify(name)}-{index}.pgn"
            if not candidate.exists() or (current and candidate == current):
                return candidate
            index += 1

    def _atomic_write(self, path: Path, games: list[chess.pgn.Game]) -> None:
        enforce_single_answers(games)
        self.directory.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(prefix=f".{path.stem}-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(export_games(games))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            temp_path = Path(temp_name)
            if temp_path.exists():
                temp_path.unlink()

    def create(self, name: str, color: bool) -> RepertoireInfo:
        path = self._available_path(name)
        game = chess.pgn.Game()
        game.headers.clear()
        game.headers.update(_headers(name, color))
        self._atomic_write(path, [game])
        return RepertoireInfo(path, name, color)

    def rename(self, info: RepertoireInfo, name: str) -> RepertoireInfo:
        games = self.read_games(info)
        _apply_headers(games, name, info.color)
        new_path = self._available_path(name, current=info.path)
        self._atomic_write(new_path, games)
        if new_path != info.path:
            info.path.unlink()
        return RepertoireInfo(new_path, name, info.color)

    def add_line(self, info: RepertoireInfo, moves: list[chess.Move]) -> str:
        if not moves:
            raise ValueError("Play a move first")
        board = chess.Board()
        for move in moves:
            if move not in board.legal_moves:
                raise ValueError(f"Illegal move in played line: {move.uci()}")
            board.push(move)
        final_color = not board.turn
        if final_color != info.color:
            raise ValueError(f"The final move is not a {'White' if info.color else 'Black'} repertoire move")

        games = self.read_games(info)
        game = next((item for item in games if position_key(item.board()) == position_key(chess.Board())), None)
        if game is None:
            game = chess.pgn.Game()
            game.headers.clear()
            game.headers.update(_headers(info.name, info.color))
            games.append(game)
        node: chess.pgn.GameNode = game
        for move in moves:
            child = next((variation for variation in node.variations if variation.move == move), None)
            node = child if child is not None else node.add_variation(move)
        already_marked = is_quiz_node(node)
        mark_quiz_node(node)
        target_board = chess.Board()
        for move in moves[:-1]:
            target_board.push(move)
        replaced = enforce_single_answers(
            games,
            {position_key(target_board): moves[-1].uci()},
        )
        self._atomic_write(info.path, games)
        if replaced:
            return "replaced"
        return "duplicate" if already_marked else "added"

    def normalize(self, info: RepertoireInfo) -> int:
        games, errors = parse_pgn(info.path.read_text(encoding="utf-8"))
        if errors:
            raise ValueError("; ".join(errors))
        removed = enforce_single_answers(games)
        if removed:
            self._atomic_write(info.path, games)
        return removed

    def compile(self, info: RepertoireInfo) -> list[dict]:
        grouped: dict[str, dict] = {}
        for game_index, game in enumerate(self.read_games(info)):
            root_board = game.board()

            def visit(node: chess.pgn.GameNode, board: chess.Board, moves: list[chess.Move]) -> None:
                key = position_key(board)
                marked_children = [child for child in node.variations if is_quiz_node(child)]
                if marked_children:
                    prompt = grouped.setdefault(
                        key,
                        {
                            "prompt_id": f"{info.id}:{key}",
                            "repertoire_id": info.id,
                            "repertoire_name": info.name,
                            "repertoire_color": info.color,
                            "file": info.path.name,
                            "path": str(info.path),
                            "position_key": key,
                            "before_fen": board.fen(en_passant="legal"),
                            "answers": {},
                            "contexts": [],
                        },
                    )
                    context = _line_pgn(moves, root_board)
                    if context not in prompt["contexts"]:
                        prompt["contexts"].append(context)
                    for child in marked_children:
                        after = board.copy(stack=False)
                        san = after.san(child.move)
                        after.push(child.move)
                        full_line = _line_pgn(moves + [child.move], root_board)
                        prompt["answers"].setdefault(
                            child.move.uci(),
                            {
                                "move_uci": child.move.uci(),
                                "move_san": san,
                                "after_fen": after.fen(en_passant="legal"),
                                "pgn": full_line,
                                "game_index": game_index,
                            },
                        )
                for child in node.variations:
                    next_board = board.copy(stack=False)
                    next_board.push(child.move)
                    visit(child, next_board, moves + [child.move])

            visit(game, root_board, [])

        prompts: list[dict] = []
        for prompt in grouped.values():
            answers = list(prompt["answers"].values())
            answers.sort(key=lambda item: item["move_san"])
            prompt["accepted_moves"] = answers
            prompt["accepted_uci"] = {item["move_uci"] for item in answers}
            primary = answers[0]
            prompt.update(primary)
            prompt["move_san"] = " / ".join(item["move_san"] for item in answers)
            prompt["pgn"] = primary["pgn"]
            del prompt["answers"]
            prompts.append(prompt)
        return prompts

    def compile_all(self) -> list[dict]:
        prompts: list[dict] = []
        for info in self.list_repertoires():
            prompts.extend(self.compile(info))
        return prompts

    def remove_answer(self, info: RepertoireInfo, key: str, move_uci: str) -> int:
        games = self.read_games(info)
        removed = 0
        for game in games:
            def visit(node: chess.pgn.GameNode, board: chess.Board) -> None:
                nonlocal removed
                if position_key(board) == key:
                    for child in node.variations:
                        if child.move.uci() == move_uci and is_quiz_node(child):
                            unmark_quiz_node(child)
                            removed += 1
                for child in node.variations:
                    next_board = board.copy(stack=False)
                    next_board.push(child.move)
                    visit(child, next_board)
            visit(game, game.board())
        if removed:
            self._atomic_write(info.path, games)
        return removed

    def replace_answer(
        self,
        info: RepertoireInfo,
        key: str,
        old_move_uci: str,
        moves: list[chess.Move],
    ) -> int:
        if not moves:
            raise ValueError("The edited line must contain at least one move")

        board = chess.Board()
        for move in moves:
            if move not in board.legal_moves:
                raise ValueError(f"Illegal move in edited line: {move.uci()}")
            board.push(move)
        final_color = not board.turn
        if final_color != info.color:
            raise ValueError(
                f"The edited line must end with a {'White' if info.color else 'Black'} repertoire move"
            )

        games = self.read_games(info)
        removed = 0
        for game in games:
            def visit(node: chess.pgn.GameNode, position: chess.Board) -> None:
                nonlocal removed
                if position_key(position) == key:
                    for child in node.variations:
                        if child.move.uci() == old_move_uci and is_quiz_node(child):
                            unmark_quiz_node(child)
                            removed += 1
                for child in node.variations:
                    next_position = position.copy(stack=False)
                    next_position.push(child.move)
                    visit(child, next_position)

            visit(game, game.board())

        if not removed:
            raise ValueError("The saved repertoire move could not be found")

        game = next((item for item in games if position_key(item.board()) == position_key(chess.Board())), None)
        if game is None:
            game = chess.pgn.Game()
            game.headers.clear()
            game.headers.update(_headers(info.name, info.color))
            games.append(game)
        node: chess.pgn.GameNode = game
        for move in moves:
            child = next((variation for variation in node.variations if variation.move == move), None)
            node = child if child is not None else node.add_variation(move)
        mark_quiz_node(node)
        target_board = chess.Board()
        for move in moves[:-1]:
            target_board.push(move)
        enforce_single_answers(
            games,
            {position_key(target_board): moves[-1].uci()},
        )
        self._atomic_write(info.path, games)
        return removed

    def preview_import(self, text: str, color: bool) -> dict:
        games, errors = parse_pgn(text)
        has_marks = any(
            is_quiz_node(child)
            for game in games
            for node in _walk_nodes(game)
            for child in node.variations
        )
        if not errors and not has_marks:
            for game in games:
                for node in _walk_nodes(game):
                    for child in node.variations:
                        if child.parent.board().turn == color:
                            mark_quiz_node(child)
        merged: list[chess.pgn.Game] = []
        for game in games:
            merge_game_into(merged, game)
        enforce_single_answers(merged)
        if games:
            temp_info = RepertoireInfo(Path("preview.pgn"), "Preview", color)
            prompts = _compile_games_for_preview(merged, temp_info)
        else:
            prompts = []
        if games and not prompts and not errors:
            errors.append("The PGN contains no trainable moves for the selected color")
        return {
            "games": merged,
            "errors": errors,
            "game_count": len(games),
            "root_count": len(merged),
            "prompt_count": len(prompts),
            "answer_count": sum(len(prompt["accepted_moves"]) for prompt in prompts),
            "used_existing_marks": has_marks,
        }

    def import_preview(self, preview: dict, name: str, color: bool, mode: str) -> RepertoireInfo:
        if preview["errors"] or not preview["games"]:
            raise ValueError("Cannot import invalid PGN")
        existing = next((info for info in self.list_repertoires() if info.name.casefold() == name.casefold()), None)
        incoming = preview["games"]
        incoming_choices = trained_answer_choices(incoming)
        if existing and mode == "cancel":
            raise ValueError("Import cancelled")
        if existing and mode == "merge":
            games = self.read_games(existing)
            for game in incoming:
                merge_game_into(games, game)
            path = existing.path
        elif existing and mode == "replace":
            games = incoming
            path = existing.path
        else:
            games = incoming
            path = self._available_path(name)
        enforce_single_answers(games, incoming_choices)
        _apply_headers(games, name, color)
        self._atomic_write(path, games)
        return RepertoireInfo(path, name, color)

def _walk_nodes(root: chess.pgn.GameNode):
    yield root
    for child in root.variations:
        yield from _walk_nodes(child)


def _compile_games_for_preview(games: list[chess.pgn.Game], info: RepertoireInfo) -> list[dict]:
    directory = Path(tempfile.mkdtemp(prefix="crm-preview-"))
    try:
        store = RepertoireStore(directory)
        path = directory / "preview.pgn"
        store._atomic_write(path, games)
        return store.compile(RepertoireInfo(path, info.name, info.color))
    finally:
        shutil.rmtree(directory, ignore_errors=True)
