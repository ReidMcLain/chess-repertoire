from __future__ import annotations

import csv
import hashlib
import io
import json
import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import chess
import chess.pgn

from app_paths import resource_path


OPENING_DATA_DIRECTORY = resource_path("data", "openings")


def position_key(board: chess.Board) -> str:
    return " ".join(board.fen(en_passant="legal").split()[:4])


def split_opening_name(name: str) -> tuple[str, str, str]:
    family, separator, detail = name.partition(":")
    opening = family.strip() or "Unclassified position"
    if not separator:
        return opening, "", ""
    parts = [part.strip() for part in detail.split(",") if part.strip()]
    variation = parts[0] if parts else ""
    subvariation = ", ".join(parts[1:]) if len(parts) > 1 else ""
    return opening, variation, subvariation


@dataclass(frozen=True, slots=True)
class OpeningMatch:
    eco: str
    opening: str
    variation: str
    subvariation: str
    deepest_ply: int
    source: str

    def opening_fields(self) -> dict[str, str]:
        return {
            "eco": self.eco,
            "opening": self.opening,
            "variation": self.variation,
            "subvariation": self.subvariation,
        }


@dataclass(frozen=True, slots=True)
class _DatasetEntry:
    eco: str
    name: str
    moves: tuple[str, ...]
    final_position_key: str

    def match(self, ply: int, source: str) -> OpeningMatch:
        hierarchy = split_opening_name(self.name)
        return OpeningMatch(self.eco, *hierarchy, ply, source)


class BundledOpeningClassifier:
    """Classify move sequences from a replaceable TSV opening catalog."""

    def __init__(self, data_directory: Path = OPENING_DATA_DIRECTORY) -> None:
        self.data_directory = data_directory
        metadata_path = data_directory / "metadata.json"
        if not metadata_path.is_file():
            raise ValueError(f"Opening dataset metadata is missing: {metadata_path}")
        try:
            self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Cannot read opening dataset metadata: {exc}") from exc

        self.dataset_version = str(self.metadata.get("version", "unknown"))
        filenames = self.metadata.get("files") or ["openings.tsv"]
        runtime_hash = self.metadata.get("runtime_sha256")
        if filenames == ["openings.tsv"] and runtime_hash:
            runtime_path = data_directory / "openings.tsv"
            if not runtime_path.is_file():
                raise ValueError(f"Opening dataset file is missing: {runtime_path}")
            if hashlib.sha256(runtime_path.read_bytes()).hexdigest() != runtime_hash:
                raise ValueError("Opening dataset checksum does not match metadata")

        self._prefixes: dict[tuple[str, ...], tuple[_DatasetEntry, ...]] = {}
        self._positions: dict[str, tuple[_DatasetEntry, ...]] = {}
        self._load([data_directory / str(filename) for filename in filenames])
        expected_count = self.metadata.get("entry_count")
        if expected_count is not None and self.entry_count != int(expected_count):
            raise ValueError(
                f"Opening dataset entry count mismatch: expected {expected_count}, loaded {self.entry_count}"
            )

    @property
    def entry_count(self) -> int:
        return sum(len(entries) for entries in self._prefixes.values())

    def _load(self, paths: Iterable[Path]) -> None:
        prefixes: dict[tuple[str, ...], list[_DatasetEntry]] = defaultdict(list)
        positions: dict[str, list[_DatasetEntry]] = defaultdict(list)
        for path in paths:
            if not path.is_file():
                raise ValueError(f"Opening dataset file is missing: {path}")
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, delimiter="\t")
                if not reader.fieldnames or not {"eco", "name"}.issubset(reader.fieldnames):
                    raise ValueError(f"Opening dataset has invalid columns: {path}")
                for line_number, row in enumerate(reader, 2):
                    try:
                        moves, final_key = self._moves_and_position(row)
                    except ValueError as exc:
                        raise ValueError(f"Invalid opening row {path.name}:{line_number}: {exc}") from exc
                    name = (row.get("name") or "").strip()
                    if not moves or not name:
                        continue
                    entry = _DatasetEntry(
                        eco=(row.get("eco") or "").strip(),
                        name=name,
                        moves=moves,
                        final_position_key=final_key,
                    )
                    prefixes[moves].append(entry)
                    positions[final_key].append(entry)
        if not prefixes:
            raise ValueError("Opening dataset contains no usable entries")
        self._prefixes = {key: tuple(entries) for key, entries in prefixes.items()}
        self._positions = {key: tuple(entries) for key, entries in positions.items()}

    @staticmethod
    def _moves_and_position(row: Mapping[str, str]) -> tuple[tuple[str, ...], str]:
        uci = (row.get("uci") or "").strip()
        if uci:
            moves = tuple(uci.split())
            board = chess.Board()
            for text in moves:
                try:
                    move = chess.Move.from_uci(text)
                except ValueError as exc:
                    raise ValueError(f"invalid UCI move {text!r}") from exc
                if move not in board.legal_moves:
                    raise ValueError(f"illegal UCI move {text!r}")
                board.push(move)
            return moves, position_key(board)

        pgn = (row.get("pgn") or "").strip()
        game = chess.pgn.read_game(io.StringIO(pgn)) if pgn else None
        if game is None or game.errors:
            raise ValueError("missing or malformed PGN line")
        board = game.board()
        moves_list: list[str] = []
        for move in game.mainline_moves():
            moves_list.append(move.uci())
            board.push(move)
        return tuple(moves_list), position_key(board)

    @staticmethod
    def _unique_entry(entries: tuple[_DatasetEntry, ...] | None) -> _DatasetEntry | None:
        if not entries:
            return None
        if len({(entry.eco, entry.name) for entry in entries}) != 1:
            return None
        return min(entries, key=lambda entry: (entry.eco, entry.name, entry.moves))

    def classify(
        self,
        moves_uci: Iterable[str],
        headers: Mapping[str, str] | None = None,
    ) -> OpeningMatch:
        board = chess.Board()
        prefix: list[str] = []
        best: OpeningMatch | None = None
        for ply, text in enumerate(moves_uci, 1):
            try:
                move = chess.Move.from_uci(text)
            except ValueError:
                break
            if move not in board.legal_moves:
                break
            prefix.append(move.uci())
            board.push(move)

            exact = self._unique_entry(self._prefixes.get(tuple(prefix)))
            if exact is not None:
                best = exact.match(ply, "dataset_prefix")
                continue
            transposed = self._unique_entry(self._positions.get(position_key(board)))
            if transposed is not None:
                best = transposed.match(ply, "dataset_position")

        if best is not None:
            return best
        return self._header_fallback(headers or {})

    def recognition_questions(self, level: str) -> list[dict[str, str | list[str]]]:
        """Return representative, named catalog positions for a recognition quiz.

        This deliberately derives questions from the same bundled TSV used for
        normal classification.  The catalog's breadth is also a useful proxy
        for which names are worth learning first: a family/variation with many
        catalog continuations gets a representative position before an obscure
        one-off name.
        """
        if level not in {"families", "variations", "all_variations", "deep_eco"}:
            raise ValueError(f"Unknown recognition level: {level}")

        entries = [entry for group in self._prefixes.values() for entry in group]
        grouped: dict[str, list[_DatasetEntry]] = defaultdict(list)

        def label_for(entry: _DatasetEntry) -> str | None:
            opening, variation, _subvariation = split_opening_name(entry.name)
            if level == "families":
                return opening
            if level in {"variations", "all_variations"}:
                return f"{opening}: {variation}" if variation else None
            return f"{entry.eco} · {entry.name}"

        def is_base_entry(entry: _DatasetEntry) -> bool:
            opening, variation, subvariation = split_opening_name(entry.name)
            return (
                (level == "families" and entry.name == opening)
                or (level in {"variations", "all_variations"} and bool(variation) and not subvariation)
                or level == "deep_eco"
            )

        for entry in entries:
            if (key := label_for(entry)) is not None:
                grouped[key].append(entry)

        # A position identifies a name only when every catalog line that
        # reaches that exact position belongs to that same name at this quiz
        # level.  Indexing every prefix (and not just final ECO positions)
        # lets a Najdorf stop at ...a6, for example, rather than at a later
        # theoretical continuation in its source line.
        labels_with_base = {
            label
            for entry in entries
            if (label := label_for(entry)) is not None and is_base_entry(entry)
        }
        position_labels: dict[str, set[str]] = defaultdict(set)
        for entry in entries:
            label = label_for(entry)
            if label is None or (label in labels_with_base and not is_base_entry(entry)):
                continue
            board = chess.Board()
            for move_uci in entry.moves:
                board.push_uci(move_uci)
                position_labels[position_key(board)].add(label)

        limits = {"families": 60, "variations": 150, "all_variations": None, "deep_eco": None}
        # Prefer well-represented names.  A middling-depth position is more
        # recognizable than the first move, without turning this into a deep
        # theory drill.
        ranked = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
        if limits[level] is not None:
            ranked = ranked[: limits[level]]

        def identifies(label: str, labels_at_position: set[str]) -> bool:
            if labels_at_position == {label}:
                return True
            if label not in labels_at_position:
                return False
            # Some ECO names are aliases for the same setup (not genuinely
            # different board positions).  Let the catalog's more established
            # identity claim that setup, while the smaller alias continues to
            # its next distinguishing move.  This keeps Taimanov at its
            # ...e6/...Nc6 setup instead of needlessly waiting for ...a6.
            return all(
                len(grouped[label]) > len(grouped[other])
                for other in labels_at_position
                if other != label
            )

        questions: list[dict[str, str | list[str]]] = []
        for label, group in ranked:
            # A catalog row whose name stops at this quiz identity is its
            # defining line: `... a6` for Najdorf, `... g6` for Accelerated
            # Dragon, and so on.  Do not let a child line's sparse prefix make
            # an identity appear to start earlier than the catalog says it
            # does.  If the defining position is genuinely shared, an
            # extension is used only until it becomes unique.
            base_entries = []
            for entry in group:
                if is_base_entry(entry):
                    base_entries.append(entry)
            base_entries.sort(key=lambda entry: (len(entry.moves), entry.eco, entry.name, entry.moves))

            defining: list[tuple[int, _DatasetEntry, tuple[str, ...], str]] = []
            candidates = base_entries or group
            for base in candidates:
                extensions = [
                    entry
                    for entry in group
                    if entry.moves[: len(base.moves)] == base.moves
                ] or [base]
                for entry in extensions:
                    minimum_ply = len(base.moves)
                    board = chess.Board()
                    prefix: list[str] = []
                    for ply, move_uci in enumerate(entry.moves, start=1):
                        board.push_uci(move_uci)
                        prefix.append(move_uci)
                        if ply < minimum_ply:
                            continue
                        if identifies(label, position_labels[position_key(board)]):
                            defining.append((ply, entry, tuple(prefix), board.fen(en_passant="legal")))
                            break
            # Every usable catalog identity should resolve at its complete
            # line. Keep a defensive fallback for a catalog ambiguity while
            # still preferring the shortest available representative.
            if defining:
                _ply, representative, moves, fen = min(
                    defining,
                    key=lambda item: (item[0], item[1].eco, item[1].name, item[2]),
                )
            else:
                representative = min(group, key=lambda entry: (len(entry.moves), entry.eco, entry.name))
                moves = representative.moves
                fen = self._fen_for_moves(moves)
            before_board = chess.Board()
            for move_uci in moves[:-1]:
                before_board.push_uci(move_uci)
            prompt_id = f"opening-recognition:{level}:{position_key(chess.Board(fen))}:{label}"
            questions.append(
                {
                    "prompt_id": prompt_id,
                    "move_uci": hashlib.sha1(label.encode("utf-8")).hexdigest(),
                    "answer": label,
                    "eco": representative.eco,
                    "fen": fen,
                    "before_fen": before_board.fen(en_passant="legal"),
                    "defining_move_uci": moves[-1],
                    "moves": list(moves),
                }
            )
        return questions

    @staticmethod
    def _fen_for_moves(moves: tuple[str, ...]) -> str:
        board = chess.Board()
        for text in moves:
            board.push_uci(text)
        return board.fen(en_passant="legal")

    def recognition_options(self, questions: list[dict[str, str | list[str]]], index: int) -> list[str]:
        """Create one correct answer plus four catalog-near distractors."""
        question = questions[index]
        answer = str(question["answer"])
        eco_prefix = str(question["eco"])[:1]
        moves = tuple(question["moves"])

        def closeness(other: dict[str, str | list[str]]) -> tuple[int, int, str]:
            other_moves = tuple(other["moves"])
            shared = sum(a == b for a, b in zip(moves, other_moves))
            eco_match = int(str(other["eco"])[:1] == eco_prefix)
            return (-eco_match, -shared, str(other["answer"]))

        alternatives = sorted(
            (item for item in questions if str(item["answer"]) != answer), key=closeness
        )
        choices = [answer] + [str(item["answer"]) for item in alternatives[:4]]
        seed = int(hashlib.sha1(str(question["prompt_id"]).encode("utf-8")).hexdigest()[:16], 16)
        random.Random(seed).shuffle(choices)
        return choices

    @staticmethod
    def _header_fallback(headers: Mapping[str, str]) -> OpeningMatch:
        opening = (headers.get("Opening") or "").strip()
        if opening:
            hierarchy = (
                opening,
                (headers.get("Variation") or "").strip(),
                (headers.get("SubVariation") or headers.get("Subvariation") or "").strip(),
            )
            return OpeningMatch((headers.get("ECO") or "").strip(), *hierarchy, 0, "pgn_headers")
        return OpeningMatch(
            (headers.get("ECO") or "").strip(),
            "Unclassified position",
            "",
            "",
            0,
            "unknown",
        )


OPENING_CLASSIFIER = BundledOpeningClassifier()
