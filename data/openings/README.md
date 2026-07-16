# Bundled opening catalog

This directory contains a pinned snapshot of the CC0
[`lichess-org/chess-openings`](https://github.com/lichess-org/chess-openings)
dataset copied from the adjacent Chess Opening Audit project.

`openings.tsv` maps ECO codes and full opening names to canonical PGN/UCI move
sequences and normalized positions. `metadata.json` records the immutable
upstream commit, checksums, entry count, and generator information. The app
loads this data through `opening_classifier.py`; opening records are not
hard-coded in the UI.
