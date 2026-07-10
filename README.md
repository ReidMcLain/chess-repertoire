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
4. Click `View repertoire` to browse positions by repertoire and opening, inspect accepted answers, or stop training an answer.
5. Click `Quiz`, choose one or more openings, and practice their saved replies from the starting FEN positions.

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

The app derives single-position quiz prompts from those marks. If a position has multiple marked moves, any of them is accepted. Transpositions within one repertoire are combined by normalized FEN.

Use `Import PGN` to load a local `.pgn` file or pasted PGN text. Ordinary PGNs mark every move by the selected training color; PGNs already containing CRM quiz marks preserve those explicit choices. Import provides a preview before writing and supports merge or replace when a repertoire name already exists.

The app prevents duplicate trainable moves from the same position. Opening names are matched from each prompt's PGN move sequence. Positions outside the built-in opening table are labeled `Unclassified position` rather than guessed.
Each opening section starts collapsed and displays the number of saved moves it contains.

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
