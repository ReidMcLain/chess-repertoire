# Chess Repertoire MVP

This first MVP is a local Python desktop app, not a browser app.

## Download for Windows

1. Open the [GitHub Releases page](https://github.com/ReidMcLain/chess-repertoire/releases).
2. Expand **Assets** for the latest release.
3. Download `Chess-Repertoire-Memorizer-vX.Y-Windows.zip` and extract it.
4. Run `Chess Repertoire Memorizer.exe` from the extracted folder. Keep the
   accompanying `_internal` folder beside the executable. Python and pip are
   not required.

Windows SmartScreen may warn that the application is from an unknown publisher.
The executable is not currently code-signed, so confirm that you downloaded it
from this repository's Releases page before choosing **Run anyway**.

User-created repertoires are stored in:

```text
%LOCALAPPDATA%\ChessRepertoireMemorizer\repertoire\
```

It shows:

- A playable chess board
- PNG chess piece assets in `assets/pieces`
- A live PGN panel on the right
- `Add move`, `Quiz`, `View repertoire`, and `Reset board` buttons on the left
- Board orientation follows the side to move
- Quiz feedback uses an in-app animated progress indicator for correct answers

## Repertoire Workflow

1. Create or select a named repertoire. Each repertoire can contain both White and Black moves.
2. Play a line on the board.
3. Click `Add move` to mark only the final move as a trainable answer; earlier moves remain PGN context.
4. Click `View repertoire` to browse positions by repertoire and opening. Each saved move has `Details`, `Remove`, `View`, and `Edit` actions.
5. Click `Quiz`, choose one or more openings, and practice their saved replies from the starting FEN positions.

`View` opens the saved line at its training position with the repertoire side at the bottom. Use the board arrows or the keyboard Left/Right arrows to move through the line. `Edit` opens the same navigable line in a clearly marked editing mode; branch from any earlier position and use `Save changes` to replace the trained move.

The Saved Repertoire browser starts with collapsed parent openings such as French Defense, Sicilian Defense, and Italian Game. Expanding a parent reveals its ECO groups, followed by variations and named lines.

Quiz order follows the saved PGN tree. Before each prompt, the opponent's preceding move slides into place so the position arrives like it would in an online game; board input unlocks when that short animation finishes. Moves in a selected family are drilled together in branch order instead of being shuffled position by position. The family tree follows actual PGN move-prefix ancestry, so a continuous line remains together when its catalog label or ECO changes—for example, Old Sicilian → Open → Accelerated Dragon. Sequential trained lead-in moves are included automatically without opening-specific move-number rules. At the end of a quiz round, missed moves can be replayed as a smaller follow-up round with `Only Replay Missed moves`; the app keeps the prior round scores and attempt counts. A compact fixed-width counter below the board shows completed versus total quiz moves without expanding the window.

The hierarchical quiz selector discovers families dynamically and separates the White and Black trees inside each repertoire. It starts with a compact, collapsed list of parent families; expand one to follow its opening-name transitions, variations, and exact continuations. A parent selection includes its descendant lines and each continuation includes its trained ancestors in move order. During the drill, a chess title card above the board shows the exact family/context, ECO, tree number, and local move progress. `Restart Quiz` repeats the same selected trees.

Named repertoires are standard PGN files in:

```text
repertoire/
```

PGN variations store the complete move tree. Trainable answers are marked in move comments with:

```text
[%crm_quiz 1]
```

The app derives single-position quiz prompts from those marks. Each normalized position has exactly one trained reply; saving or importing a newer reply replaces the previous one. Transpositions within one repertoire are combined by normalized FEN and share that single reply.

Use `Import PGN` to load a local `.pgn` file or pasted PGN text. Ordinary PGNs can mark White moves, Black moves, or both sides; PGNs already containing CRM quiz marks preserve those explicit choices. Imported repertoire files accept future additions for either side. Import provides a preview before writing and supports merge or replace when a repertoire name already exists.

The app ignores duplicate saves of the same reply and replaces conflicting replies from the same position. Opening names are matched from each prompt's PGN move sequence or normalized transposed position. Positions outside the bundled opening catalog are labeled `Unclassified position` rather than guessed.
Each opening section starts collapsed and displays the number of saved moves it contains.

## Opening Classification

Opening records are data, not hard-coded UI rules. The app loads the pinned,
CC0-licensed Lichess opening catalog from `data/openings/openings.tsv` through
`opening_classifier.py`. The catalog currently contains 3,803 named positions
with ECO codes, canonical PGN/UCI sequences, and normalized positions.
Names and hierarchy are displayed directly from the catalog without app-specific
aliases or naming overrides. ECO codes are shown with opening groups—for example,
`B30 · Sicilian Defense > Old Sicilian` and `B23 · Sicilian Defense > Closed`.

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

## Build the Windows application

On Windows, one PowerShell command creates an isolated build environment,
installs the dependencies, runs the tests, builds the application, checks its
bundled resources, and performs a packaged-app smoke test:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1 -Version v1.0
```

The finished release assets are written to:

```text
release\Chess-Repertoire-Memorizer-v1.0-Windows.zip
```

The ZIP contains a PyInstaller one-folder distribution. This is more reliable
on Windows than a self-extracting one-file build because it does not unpack
runtime DLLs into a temporary directory every time the app starts.

The build intentionally includes only the application code, `assets/`, the
bundled opening catalog in `data/openings/`, the build version, required
runtime libraries, and third-party license metadata. It excludes the
repository's `repertoire/` directory, archived/personal PGNs, the
Chess.com-generated report, tests, caches, virtual environments, and other
development/build output.
