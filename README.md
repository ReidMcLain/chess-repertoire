# Chess Repertoire MVP

This first MVP is a local Python desktop app, not a browser app.

It shows:

- A playable chess board
- PNG chess piece assets in `assets/pieces`
- A live PGN panel on the right
- `Add move`, `Quiz`, `View repertoire`, and `Reset board` buttons on the left
- Board orientation follows the side to move
- Quiz feedback uses an in-app animated progress indicator for correct answers

## Repertoire Workflow

1. Create or select a named White/Black repertoire.
2. Play a line on the board.
3. Click `Add move` to mark only the final move as a trainable answer; earlier moves remain PGN context.
4. Click `View repertoire` to browse positions by repertoire and opening. Each saved move has `Details`, `Remove`, `View`, and `Edit` actions.
5. Click `Quiz`, choose one or more openings, and practice their saved replies from the starting FEN positions.

`View` opens the saved line at its training position with the repertoire side at the bottom. Use the board arrows or the keyboard Left/Right arrows to move through the line. `Edit` opens the same navigable line in a clearly marked editing mode; branch from any earlier position and use `Save changes` to replace the trained move.

Quiz order is randomized. At the end of a quiz round, missed moves can be replayed as a smaller follow-up round with `Only Replay Missed moves`; the app keeps the prior round scores and attempt counts. The check/X marks under the board can be clicked after the round to replay the saved move.
The quiz selector discovers openings dynamically, separates them into White and Black repertoire sections, shows the number of cards in each opening, and checks every opening by default. Click `Play Selected Openings` to begin; `Restart Quiz` repeats the same selected set.

Named repertoires are standard PGN files in:

```text
repertoire/
```

PGN variations store the complete move tree. Trainable answers are marked in move comments with:

```text
[%crm_quiz 1]
```

The app derives single-position quiz prompts from those marks. Each normalized position has exactly one trained reply; saving or importing a newer reply replaces the previous one. Transpositions within one repertoire are combined by normalized FEN and share that single reply.

Use `Import PGN` to load a local `.pgn` file or pasted PGN text. Ordinary PGNs mark every move by the selected training color; PGNs already containing CRM quiz marks preserve those explicit choices. Import provides a preview before writing and supports merge or replace when a repertoire name already exists.

The app ignores duplicate saves of the same reply and replaces conflicting replies from the same position. Opening names are matched from each prompt's PGN move sequence or normalized transposed position. Positions outside the bundled opening catalog are labeled `Unclassified position` rather than guessed.
Each opening section starts collapsed and displays the number of saved moves it contains.

## Opening Classification

Opening records are data, not hard-coded UI rules. The app loads the pinned,
CC0-licensed Lichess opening catalog from `data/openings/openings.tsv` through
`opening_classifier.py`. The catalog currently contains 3,803 named positions
with ECO codes, canonical PGN/UCI sequences, and normalized positions.
Names and hierarchy are displayed directly from the catalog without app-specific
aliases or naming overrides.

## Install

```powershell
cd C:\Users\reidm\OneDrive\Desktop\codex\chess-repertoire-memorizer
python -m venv .venv
pip install -r requirements.txt
```

## Run

```powershell
python app.py
```

Click a piece, then click a target square to make a legal move. Pawn promotions auto-promote to queen for this MVP.
