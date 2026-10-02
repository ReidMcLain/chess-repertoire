"""Persistent answer counts used only to order quiz families."""

import sqlite3
from contextlib import closing
from pathlib import Path


class QuizHistory:
    def __init__(self, path: Path) -> None:
        self.path = path
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS answers (
                    prompt_id TEXT NOT NULL,
                    move_uci TEXT NOT NULL,
                    correct INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (prompt_id, move_uci)
                )"""
            )

    @staticmethod
    def key(card: dict) -> tuple[str, str]:
        # A replacement repertoire reply starts with its own answer history.
        return card["prompt_id"], card["move_uci"]

    def record(self, card: dict, correct: bool) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                """INSERT INTO answers (prompt_id, move_uci, correct, attempts)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT (prompt_id, move_uci) DO UPDATE SET
                       correct = answers.correct + excluded.correct,
                       attempts = answers.attempts + 1""",
                (*self.key(card), int(correct)),
            )

    def scores(self) -> dict[tuple[str, str], float]:
        with closing(sqlite3.connect(self.path)) as connection:
            return {
                (prompt_id, move_uci): (correct + 1) / (attempts + 2)
                for prompt_id, move_uci, correct, attempts in connection.execute(
                    "SELECT prompt_id, move_uci, correct, attempts FROM answers"
                )
            }
