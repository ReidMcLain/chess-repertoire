from __future__ import annotations

import csv
import hashlib
import io
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import chess
import chess.pgn


OPENING_DATA_DIRECTORY = Path(__file__).with_name("data") / "openings"


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
