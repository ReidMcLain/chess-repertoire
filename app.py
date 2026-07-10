import tkinter as tk
import io
import random
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import chess
import chess.pgn

from repertoire_store import RepertoireInfo, RepertoireStore


SQUARE_SIZE = 72
BOARD_SIZE = SQUARE_SIZE * 8
LIGHT = "#eeeed2"
DARK = "#769656"
SELECTED = "#f6f669"
LEGAL_DOT = "#4a6f28"
BG = "#f6f7f9"
PANEL = "#ffffff"
TEXT = "#1f2937"
MUTED = "#6b7280"
SUCCESS = "#15803d"
ASSET_DIR = Path(__file__).with_name("assets") / "pieces"
CHECK_SUCCESS_LOTTIE = Path(__file__).with_name("assets") / "check_success.json"
REPERTOIRE_DIR = Path(__file__).with_name("repertoire")

# Ordered from broad openings to specific branches. The longest match wins.
OPENING_RULES = [
    (("e2e4", "c7c5"), "Sicilian Defense", "", ""),
    (("e2e4", "e7e5"), "Open Game", "", ""),
    (("e2e4", "e7e5", "g1f3", "g8f6"), "Petrov's Defense", "", ""),
    (("e2e4", "e7e5", "g1f3", "g8f6", "d2d4"), "Petrov's Defense", "Steinitz Attack", ""),
    (("e2e4", "e7e5", "g1f3", "b8c6", "f1c4"), "Italian Game", "", ""),
    (("e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"), "Italian Game", "Giuoco Piano", ""),
    (("e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b2b4"), "Italian Game", "Evans Gambit", ""),
    (("e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b2b4", "c5b4"), "Italian Game", "Evans Gambit", "Accepted"),
    (("e2e4", "d7d5"), "Scandinavian Defense", "", ""),
    (("e2e4", "d7d5", "e4d5"), "Scandinavian Defense", "Main Line", ""),
    (("e2e4", "e7e6"), "French Defense", "", ""),
    (("e2e4", "e7e6", "e4e5"), "French Defense", "Advance Variation", ""),
    (("e2e4", "c7c6"), "Caro-Kann Defense", "", ""),
    (("e2e4", "c7c6", "g1f3", "d7d5", "b1c3"), "Caro-Kann Defense", "Two Knights Attack", ""),
    (("e2e4", "c7c6", "g1f3", "d7d5", "b1c3", "d5e4", "c3e4"), "Caro-Kann Defense", "Two Knights Attack", "3...dxe4"),
    (("e2e4", "c7c6", "g1f3", "d7d5", "b1c3", "c8g4"), "Caro-Kann Defense", "Two Knights Attack", "3...Bg4"),
    (("e2e4", "c7c6", "g1f3", "d7d5", "b1c3", "d5d4"), "Caro-Kann Defense", "Two Knights Attack", "3...d4"),
    (("d2d4", "g8f6"), "Indian Game", "", ""),
]

PIECES = {
    chess.PAWN: ("P", "p"),
    chess.KNIGHT: ("N", "n"),
    chess.BISHOP: ("B", "b"),
    chess.ROOK: ("R", "r"),
    chess.QUEEN: ("Q", "q"),
    chess.KING: ("K", "k"),
}


class ChessMvpApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Chess Repertoire MVP")
        self.root.configure(bg=BG)
        self.configure_style()

        self.board = chess.Board()
        self.game = chess.pgn.Game()
        self.current_node = self.game
        self.mode = "play"
        self.move_history: list[dict[str, str]] = []
        self.move_cursor = 0
        self.quiz_cards: list[dict] = []
        self.quiz_source_cards: list[dict] = []
        self.quiz_dialog: tk.Toplevel | None = None
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_marks: list[dict] = []
        self.quiz_results: list[dict] = []
        self.quiz_round_summaries: list[tuple[int, int]] = []
        self.quiz_attempt_counts: dict[str, int] = {}
        self.last_missed_cards: list[dict] = []
        self.manual_orientation = chess.WHITE
        self.orientation_turn: bool | None = None
        self.selected_square: chess.Square | None = None
        self.dragging_square: chess.Square | None = None
        self.drag_item: int | None = None
        self.piece_images = self.load_piece_images()
        self.store = RepertoireStore(REPERTOIRE_DIR)
        self.repertoire_by_label: dict[str, RepertoireInfo] = {}
        self.active_repertoire = tk.StringVar(value="")

        left_panel = ttk.Frame(root, padding=16, style="Panel.TFrame")
        left_panel.grid(row=0, column=0, sticky="ns", padx=(12, 6), pady=12)

        ttk.Label(left_panel, text="Repertoire", style="Title.TLabel").pack(anchor="w", pady=(0, 14))
        ttk.Label(left_panel, text="Active repertoire", style="TLabel").pack(anchor="w", pady=(0, 4))
        self.repertoire_combo = ttk.Combobox(
            left_panel,
            textvariable=self.active_repertoire,
            state="readonly",
            width=24,
        )
        self.repertoire_combo.pack(fill="x", pady=(0, 6))
        repertoire_actions = ttk.Frame(left_panel, style="Panel.TFrame")
        repertoire_actions.pack(fill="x", pady=(0, 8))
        ttk.Button(repertoire_actions, text="New", width=8, command=self.create_repertoire).pack(side="left")
        ttk.Button(repertoire_actions, text="Rename", width=8, command=self.rename_repertoire).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(left_panel, text="Add move", command=self.save_last_move).pack(fill="x", pady=(0, 8))
        ttk.Button(left_panel, text="Import PGN", command=self.show_import_dialog).pack(fill="x", pady=(0, 8))
        ttk.Button(left_panel, text="Quiz", command=self.start_quiz).pack(fill="x", pady=(0, 8))
        ttk.Button(left_panel, text="View repertoire", command=self.view_repertoire).pack(fill="x", pady=(0, 8))
        ttk.Button(left_panel, text="Reset board", command=self.reset_board).pack(fill="x")

        board_frame = ttk.Frame(root, padding=8, style="Panel.TFrame")
        board_frame.grid(row=0, column=1, padx=6, pady=12)
        self.canvas = tk.Canvas(board_frame, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0, bg=PANEL)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        board_controls = ttk.Frame(board_frame, style="Panel.TFrame")
        board_controls.pack(pady=(8, 0))
        self.back_button = ttk.Button(board_controls, text="←", width=3, command=self.back_move)
        self.back_button.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(board_controls, text="⇄", width=3, command=self.flip_board).grid(row=0, column=1)
        self.forward_button = ttk.Button(board_controls, text="→", width=3, command=self.forward_move)
        self.forward_button.grid(row=0, column=2, padx=(6, 0))

        self.right_panel = ttk.Frame(root, padding=16, style="Panel.TFrame")
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(6, 12), pady=12)
        root.columnconfigure(2, weight=1)
        root.rowconfigure(0, weight=1)

        self.right_title = ttk.Label(self.right_panel, text="Live PGN", style="Title.TLabel")
        self.right_title.pack(anchor="w")
        self.right_body = ttk.Frame(self.right_panel, style="Panel.TFrame")
        self.right_body.pack(fill="both", expand=True, pady=(10, 0))

        feedback_frame = tk.Frame(root, bg=BG)
        feedback_frame.grid(row=1, column=0, columnspan=3, pady=(0, 2))
        self.feedback = tk.StringVar(value="")
        self.feedback_label = tk.Label(
            feedback_frame,
            textvariable=self.feedback,
            font=("Segoe UI", 13, "bold"),
            bg=BG,
            fg=TEXT,
        )
        self.feedback_label.pack()
        self.quiz_marks_frame = tk.Frame(
            feedback_frame,
            bg=BG,
        )
        self.quiz_marks_frame.pack(pady=(2, 0))
        self.quiz_actions_frame = tk.Frame(feedback_frame, bg=BG)
        self.quiz_actions_frame.pack(pady=(8, 0))

        self.status = tk.StringVar(value="White to move")
        tk.Label(root, textvariable=self.status, anchor="w", padx=16, bg=BG, fg=MUTED).grid(
            row=2, column=0, columnspan=3, sticky="ew", pady=(0, 10)
        )

        self.draw_board()
        self.update_pgn()
        self.refresh_repertoire_selector()

    def configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL, relief="flat")
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 10),
            background=SUCCESS,
            foreground="#ffffff",
        )
        style.map("Primary.TButton", background=[("active", "#166534"), ("disabled", "#9ca3af")])
        style.configure("Accordion.TButton", font=("Segoe UI", 11, "bold"), padding=(10, 9), anchor="w")
        style.configure("TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 15, "bold"))

    def event_to_square(self, event: tk.Event) -> chess.Square | None:
        display_file = event.x // SQUARE_SIZE
        display_rank = event.y // SQUARE_SIZE
        if not 0 <= display_file <= 7 or not 0 <= display_rank <= 7:
            return None
        return self.display_to_square(display_file, display_rank)

    def display_to_square(self, display_file: int, display_rank: int) -> chess.Square:
        orientation_turn = self.current_orientation()
        if orientation_turn == chess.WHITE:
            file_index = display_file
            rank = 7 - display_rank
        else:
            file_index = 7 - display_file
            rank = display_rank
        return chess.square(file_index, rank)

    def square_to_display(self, square: chess.Square) -> tuple[int, int]:
        file_index = chess.square_file(square)
        rank = chess.square_rank(square)
        orientation_turn = self.current_orientation()
        if orientation_turn == chess.WHITE:
            return file_index, 7 - rank
        return 7 - file_index, rank

    def current_orientation(self) -> bool:
        if self.mode in {"quiz", "replay"}:
            return self.orientation_turn if self.orientation_turn is not None else self.board.turn
        return self.manual_orientation

    def flip_board(self) -> None:
        if self.mode == "quiz":
            self.orientation_turn = not self.current_orientation()
        else:
            self.manual_orientation = not self.manual_orientation
        self.selected_square = None
        self.dragging_square = None
        if self.drag_item is not None:
            self.canvas.delete(self.drag_item)
            self.drag_item = None
        self.draw_board()

    def on_mouse_down(self, event: tk.Event) -> None:
        clicked_square = self.event_to_square(event)
        if clicked_square is None:
            return
        clicked_piece = self.board.piece_at(clicked_square)

        if clicked_piece and clicked_piece.color == self.board.turn:
            self.selected_square = clicked_square
            self.dragging_square = clicked_square
            self.draw_board()
            self.create_drag_item(clicked_piece, event.x, event.y)

    def on_mouse_drag(self, event: tk.Event) -> None:
        if self.dragging_square is None or self.drag_item is None:
            return
        self.canvas.coords(self.drag_item, event.x, event.y)

    def on_mouse_up(self, event: tk.Event) -> None:
        released_square = self.event_to_square(event)

        if self.drag_item is not None:
            self.canvas.delete(self.drag_item)
            self.drag_item = None

        if self.dragging_square is not None:
            from_square = self.dragging_square
            self.dragging_square = None

            if released_square is not None and released_square != from_square:
                self.try_move(from_square, released_square)
            else:
                self.draw_board()
            return

        if self.selected_square is not None and released_square is not None:
            self.try_move(self.selected_square, released_square)

    def create_drag_item(self, piece: chess.Piece, x: int, y: int) -> None:
        image = self.piece_images.get(piece.symbol())
        if image:
            self.drag_item = self.canvas.create_image(x, y, image=image)
            return

        white_symbol, black_symbol = PIECES[piece.piece_type]
        symbol = white_symbol if piece.color == chess.WHITE else black_symbol
        self.drag_item = self.canvas.create_text(x, y, text=symbol, font=("Segoe UI", 36, "bold"))

    def try_move(self, from_square: chess.Square, to_square: chess.Square) -> None:
        if self.mode not in {"play", "quiz"}:
            return

        move = chess.Move(from_square, to_square)
        if self.is_promotion_move(move):
            move = chess.Move(from_square, to_square, promotion=chess.QUEEN)

        if move not in self.board.legal_moves:
            self.status.set("Illegal move")
            self.draw_board()
            return

        if self.mode == "quiz":
            self.handle_quiz_move(move)
            return

        if self.move_cursor < len(self.move_history):
            self.move_history = self.move_history[: self.move_cursor]
            self.restore_board_to_cursor()

        before_fen = self.board.fen()
        san = self.board.san(move)
        self.board.push(move)
        after_fen = self.board.fen()
        self.current_node = self.current_node.add_variation(move)
        self.move_history.append(
            {
                "before_fen": before_fen,
                "after_fen": after_fen,
                "move_uci": move.uci(),
                "move_san": san,
                "pgn": self.current_pgn(),
            }
        )
        self.move_cursor = len(self.move_history)
        self.clear_feedback()
        self.status.set(f"Played {san}. {'White' if self.board.turn else 'Black'} to move")
        self.selected_square = None
        self.draw_board()
        self.update_pgn()

    def back_move(self) -> None:
        if self.mode != "play" or self.move_cursor == 0:
            return
        self.move_cursor -= 1
        self.restore_board_to_cursor()

    def forward_move(self) -> None:
        if self.mode != "play" or self.move_cursor >= len(self.move_history):
            return
        self.move_cursor += 1
        self.restore_board_to_cursor()

    def restore_board_to_cursor(self) -> None:
        if self.move_cursor == 0:
            self.board.reset()
        else:
            self.board = chess.Board(self.move_history[self.move_cursor - 1]["after_fen"])
        self.rebuild_game_from_history()
        self.selected_square = None
        self.dragging_square = None
        self.status.set(f"Move {self.move_cursor}/{len(self.move_history)}")
        self.draw_board()
        self.update_pgn()

    def rebuild_game_from_history(self) -> None:
        self.game = chess.pgn.Game()
        self.current_node = self.game
        board = chess.Board()
        for entry in self.move_history[: self.move_cursor]:
            move = chess.Move.from_uci(entry["move_uci"])
            if move not in board.legal_moves:
                break
            board.push(move)
            self.current_node = self.current_node.add_variation(move)

    def is_promotion_move(self, move: chess.Move) -> bool:
        piece = self.board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        return chess.square_rank(move.to_square) in {0, 7}

    def draw_board(self) -> None:
        self.update_navigation_buttons()
        self.canvas.delete("all")
        legal_targets = self.legal_targets_from_selected()

        for display_rank in range(8):
            for display_file in range(8):
                square = self.display_to_square(display_file, display_rank)
                x1 = display_file * SQUARE_SIZE
                y1 = display_rank * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                color = LIGHT if (chess.square_rank(square) + chess.square_file(square)) % 2 == 0 else DARK
                if square == self.selected_square:
                    color = SELECTED
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

                if square in legal_targets:
                    center_x = x1 + SQUARE_SIZE / 2
                    center_y = y1 + SQUARE_SIZE / 2
                    self.canvas.create_oval(
                        center_x - 8,
                        center_y - 8,
                        center_x + 8,
                        center_y + 8,
                        fill=LEGAL_DOT,
                        outline=LEGAL_DOT,
                    )

                piece = None if square == self.dragging_square else self.board.piece_at(square)
                if piece:
                    center_x = x1 + SQUARE_SIZE / 2
                    center_y = y1 + SQUARE_SIZE / 2
                    image = self.piece_images.get(piece.symbol())
                    if image:
                        self.canvas.create_image(center_x, center_y, image=image, tags=("piece",))
                    else:
                        white_symbol, black_symbol = PIECES[piece.piece_type]
                        symbol = white_symbol if piece.color == chess.WHITE else black_symbol
                        self.canvas.create_text(
                            center_x,
                            center_y,
                            text=symbol,
                            font=("Segoe UI", 36, "bold"),
                            tags=("piece",),
                        )

    def update_navigation_buttons(self) -> None:
        if self.mode == "play":
            self.back_button.grid()
            self.forward_button.grid()
        else:
            self.back_button.grid_remove()
            self.forward_button.grid_remove()

    def load_piece_images(self) -> dict[str, tk.PhotoImage]:
        images = {}
        for symbol in ["K", "Q", "R", "B", "N", "P", "k", "q", "r", "b", "n", "p"]:
            color = "w" if symbol.isupper() else "b"
            filename = f"{color}{symbol.upper()}.png"
            path = ASSET_DIR / filename
            if path.exists():
                images[symbol] = tk.PhotoImage(file=path)
        return images

    def refresh_repertoire_selector(self, select_id: str | None = None) -> None:
        previous = self.current_repertoire()
        self.repertoire_by_label = {}
        for info in self.store.list_repertoires():
            side = "White" if info.color else "Black"
            label = f"{info.name} ({side})"
            self.repertoire_by_label[label] = info
        labels = list(self.repertoire_by_label)
        self.repertoire_combo.configure(values=labels)
        selected = next(
            (
                label
                for label, info in self.repertoire_by_label.items()
                if info.id == select_id or (select_id is None and previous and info.id == previous.id)
            ),
            labels[0] if labels else "",
        )
        self.active_repertoire.set(selected)

    def current_repertoire(self) -> RepertoireInfo | None:
        return self.repertoire_by_label.get(self.active_repertoire.get())

    def create_repertoire(self) -> None:
        name = simpledialog.askstring("New repertoire", "Repertoire name:", parent=self.root)
        if not name or not name.strip():
            return
        white = messagebox.askyesnocancel(
            "Repertoire color",
            "Train White moves?\n\nYes = White, No = Black",
            parent=self.root,
        )
        if white is None:
            return
        info = self.store.create(name.strip(), white)
        self.refresh_repertoire_selector(info.id)
        self.status.set(f"Created {info.name}")

    def rename_repertoire(self) -> None:
        info = self.current_repertoire()
        if info is None:
            self.status.set("Create or select a PGN repertoire first")
            return
        name = simpledialog.askstring(
            "Rename repertoire",
            "New repertoire name:",
            initialvalue=info.name,
            parent=self.root,
        )
        if not name or not name.strip() or name.strip() == info.name:
            return
        renamed = self.store.rename(info, name.strip())
        self.refresh_repertoire_selector(renamed.id)
        self.status.set(f"Renamed repertoire to {renamed.name}")

    def show_import_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Import PGN")
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.geometry("700x560")

        shell = ttk.Frame(dialog, style="Panel.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Import PGN", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        fields = ttk.Frame(shell, style="Panel.TFrame")
        fields.pack(fill="x", pady=(0, 8))
        ttk.Label(fields, text="Name").grid(row=0, column=0, sticky="w", padx=(0, 6))
        name_var = tk.StringVar(value="Imported Repertoire")
        ttk.Entry(fields, textvariable=name_var).grid(row=0, column=1, sticky="ew", padx=(0, 12))
        ttk.Label(fields, text="Train").grid(row=0, column=2, sticky="w", padx=(0, 6))
        color_var = tk.StringVar(value="White")
        ttk.Combobox(fields, textvariable=color_var, values=("White", "Black"), state="readonly", width=8).grid(
            row=0, column=3
        )
        fields.columnconfigure(1, weight=1)

        text_box = tk.Text(shell, wrap="none", height=20, font=("Consolas", 9), undo=True)
        text_box.pack(fill="both", expand=True)
        summary_var = tk.StringVar(value="Load a PGN file or paste PGN text, then preview it.")
        ttk.Label(shell, textvariable=summary_var, wraplength=650).pack(anchor="w", pady=(8, 8))

        preview_state: dict[str, object] = {"preview": None, "source": "", "color": ""}
        import_button = ttk.Button(shell, text="Import", style="Primary.TButton", state="disabled")

        def load_file() -> None:
            filename = filedialog.askopenfilename(
                parent=dialog,
                title="Choose PGN",
                filetypes=(("PGN files", "*.pgn"), ("Text files", "*.txt"), ("All files", "*.*")),
            )
            if not filename:
                return
            try:
                content = Path(filename).read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                messagebox.showerror("Could not read PGN", str(exc), parent=dialog)
                return
            text_box.delete("1.0", "end")
            text_box.insert("1.0", content)
            name_var.set(Path(filename).stem.replace("-", " ").replace("_", " ").title())
            preview_state["preview"] = None
            import_button.configure(state="disabled")
            summary_var.set(f"Loaded {Path(filename).name}. Click Preview.")

        def preview() -> None:
            content = text_box.get("1.0", "end").strip()
            if not content:
                summary_var.set("Paste or load PGN text first.")
                return
            result = self.store.preview_import(content, color_var.get() == "White")
            preview_state["preview"] = result
            preview_state["source"] = content
            preview_state["color"] = color_var.get()
            if result["errors"]:
                summary_var.set("Cannot import: " + "; ".join(result["errors"][:3]))
                import_button.configure(state="disabled")
                return
            mark_note = "existing CRM quiz marks" if result["used_existing_marks"] else f"all {color_var.get()} moves"
            summary_var.set(
                f"{result['game_count']} game(s), {result['root_count']} root tree(s), "
                f"{result['prompt_count']} prompts, {result['answer_count']} answers; using {mark_note}."
            )
            import_button.configure(state="normal")

        def perform_import() -> None:
            result = preview_state.get("preview")
            name = name_var.get().strip()
            if not isinstance(result, dict) or not name:
                return
            current_source = text_box.get("1.0", "end").strip()
            if current_source != preview_state.get("source") or color_var.get() != preview_state.get("color"):
                summary_var.set("The PGN text or training color changed. Preview it again before importing.")
                import_button.configure(state="disabled")
                return
            existing = next(
                (info for info in self.store.list_repertoires() if info.name.casefold() == name.casefold()),
                None,
            )
            mode = "new"
            if existing:
                choice = messagebox.askyesnocancel(
                    "Repertoire already exists",
                    f"{existing.name} already exists.\n\nYes = merge\nNo = replace\nCancel = do nothing",
                    parent=dialog,
                )
                if choice is None:
                    return
                mode = "merge" if choice else "replace"
            try:
                info = self.store.import_preview(result, name, color_var.get() == "White", mode)
            except (ValueError, OSError) as exc:
                messagebox.showerror("Import failed", str(exc), parent=dialog)
                return
            self.refresh_repertoire_selector(info.id)
            self.status.set(
                f"Imported {result['prompt_count']} prompts and {result['answer_count']} answers into {info.name}"
            )
            dialog.destroy()

        actions = ttk.Frame(shell, style="Panel.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Load file", command=load_file).pack(side="left")
        ttk.Button(actions, text="Preview", command=preview).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
        import_button.configure(command=perform_import)
        import_button.pack(fill="x", pady=(10, 0))
        dialog.grab_set()
        dialog.focus_force()

    def save_last_move(self) -> None:
        if self.mode != "play":
            self.status.set("Leave quiz mode before saving moves")
            return
        if self.move_cursor == 0:
            self.status.set("Play a move first, then click Add move")
            return

        info = self.current_repertoire()
        if info is None:
            self.status.set("Create, migrate, or select a PGN repertoire before adding moves")
            return
        moves = [chess.Move.from_uci(entry["move_uci"]) for entry in self.move_history[: self.move_cursor]]
        try:
            added = self.store.add_line(info, moves)
        except (ValueError, OSError) as exc:
            self.status.set(str(exc))
            return
        card = self.move_history[self.move_cursor - 1]
        if added:
            self.status.set(f"Saved {card['move_san']} in {info.name}")
        else:
            self.status.set(f"Duplicate ignored: {card['move_san']} is already trainable in {info.name}")

    def reset_board(self) -> None:
        self.board.reset()
        self.game = chess.pgn.Game()
        self.current_node = self.game
        self.mode = "play"
        self.move_history = []
        self.move_cursor = 0
        self.quiz_cards = []
        self.quiz_source_cards = []
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_marks = []
        self.quiz_results = []
        self.quiz_round_summaries = []
        self.quiz_attempt_counts = {}
        self.last_missed_cards = []
        self.update_quiz_marks()
        self.clear_quiz_actions()
        self.orientation_turn = None
        self.selected_square = None
        self.dragging_square = None
        if self.drag_item is not None:
            self.canvas.delete(self.drag_item)
            self.drag_item = None
        self.clear_feedback()
        self.status.set("Board reset. White to move")
        self.draw_board()
        self.update_pgn()

    def card_key(self, card: dict) -> str:
        return card.get("prompt_id", f"{card.get('repertoire_id', 'unknown')}:{card['before_fen']}")

    def classify_opening(self, card: dict[str, str]) -> dict[str, str]:
        fields = ("opening", "variation", "subvariation")
        stored = {key: card.get(key, "") for key in fields}
        if stored["opening"]:
            return stored

        moves = self.pgn_uci_moves(card.get("pgn", ""))
        best = ("Unclassified position", "", "")
        for sequence, opening, variation, subvariation in OPENING_RULES:
            if len(sequence) <= len(moves) and tuple(moves[: len(sequence)]) == sequence:
                best = (opening, variation, subvariation)
        return dict(zip(fields, best))

    def pgn_uci_moves(self, pgn: str) -> list[str]:
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
            return [move.uci() for move in game.mainline_moves()] if game else []
        except (ValueError, IndexError):
            return []

    def opening_label(self, card: dict[str, str]) -> str:
        classification = self.classify_opening(card)
        return " > ".join(value for value in classification.values() if value)

    def repertoire_sort_key(self, card: dict[str, str]) -> tuple[str, str, str, int, str]:
        classification = self.classify_opening(card)
        return (
            classification["opening"],
            classification["variation"],
            classification["subvariation"],
            len(self.pgn_uci_moves(card.get("pgn", ""))),
            card.get("created_at", ""),
        )

    def load_repertoire(self) -> list[dict]:
        try:
            cards = self.store.compile_all()
        except (ValueError, OSError) as exc:
            self.status.set(f"Could not load repertoire: {exc}")
            return []
        for card in cards:
            card.update(self.classify_opening(card))
        return cards

    def start_quiz(self) -> None:
        cards = self.load_repertoire()
        if not cards:
            self.status.set("No saved repertoire moves yet")
            self.show_text("No repertoire saved yet.\n\nPlay a move, then click Add move.")
            return

        if self.quiz_dialog is not None and self.quiz_dialog.winfo_exists():
            self.quiz_dialog.lift()
            self.quiz_dialog.focus_force()
            return

        self.show_quiz_selector(cards)

    def show_quiz_selector(self, cards: list[dict]) -> None:
        opening_groups: dict[tuple[str, str], list[dict]] = {}
        for card in cards:
            opening_groups.setdefault((card["repertoire_id"], card["opening"]), []).append(card)

        dialog = tk.Toplevel(self.root)
        self.quiz_dialog = dialog
        dialog.title("Choose Quiz Openings")
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.resizable(False, True)

        shell = ttk.Frame(dialog, style="Panel.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Choose Quiz Openings", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        list_container = ttk.Frame(shell, style="Panel.TFrame")
        list_container.pack(fill="both", expand=True)
        canvas = tk.Canvas(list_container, width=360, height=280, bg=PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        choices = ttk.Frame(canvas, style="Panel.TFrame")
        window_id = canvas.create_window((0, 0), window=choices, anchor="nw")
        choices.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        variables: dict[tuple[str, str], tk.BooleanVar] = {}
        start_button = ttk.Button(shell, style="Primary.TButton")

        def update_start_button() -> None:
            count = sum(len(opening_groups[key]) for key, variable in variables.items() if variable.get())
            start_button.configure(
                text=f"Play Selected Openings ({count})",
                state="normal" if count else "disabled",
            )

        repertoire_ids = list(dict.fromkeys(card["repertoire_id"] for card in cards))
        for repertoire_id in repertoire_ids:
            side_keys = sorted((key for key in opening_groups if key[0] == repertoire_id), key=lambda key: key[1])
            representative = opening_groups[side_keys[0]][0]
            heading = representative["repertoire_name"]
            side = "White" if representative["repertoire_color"] else "Black"
            side_count = sum(len(opening_groups[key]) for key in side_keys)
            ttk.Label(
                choices,
                text=f"{heading} — {side} ({side_count})",
                style="TLabel",
                font=("Segoe UI", 11, "bold"),
            ).pack(fill="x", anchor="w", pady=(8, 4))
            for key in side_keys:
                opening = key[1]
                variable = tk.BooleanVar(value=True)
                variables[key] = variable
                ttk.Checkbutton(
                    choices,
                    text=f"{opening} ({len(opening_groups[key])})",
                    variable=variable,
                    command=update_start_button,
                ).pack(fill="x", anchor="w", padx=(10, 0), pady=3)

        def set_all(selected: bool) -> None:
            for variable in variables.values():
                variable.set(selected)
            update_start_button()

        def close_dialog() -> None:
            self.quiz_dialog = None
            dialog.destroy()

        def launch_quiz() -> None:
            selected = {
                key
                for key, variable in variables.items()
                if variable.get()
            }
            selected_cards = [
                card
                for card in cards
                if (card["repertoire_id"], card["opening"]) in selected
            ]
            if not selected_cards:
                return
            self.quiz_source_cards = selected_cards[:]
            close_dialog()
            self.quiz_round_summaries = []
            self.quiz_attempt_counts = {}
            self.begin_quiz(selected_cards)

        selection_actions = ttk.Frame(shell, style="Panel.TFrame")
        selection_actions.pack(fill="x", pady=(12, 8))
        ttk.Button(selection_actions, text="Select all", command=lambda: set_all(True)).pack(side="left")
        ttk.Button(selection_actions, text="Clear all", command=lambda: set_all(False)).pack(side="left", padx=(8, 0))

        start_button.configure(command=launch_quiz)
        start_button.pack(fill="x", pady=(0, 8))

        footer = ttk.Frame(shell, style="Panel.TFrame")
        footer.pack(fill="x")
        ttk.Button(footer, text="Cancel", command=close_dialog).pack(side="right")
        update_start_button()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dialog.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dialog.winfo_height()) // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        dialog.focus_force()

    def restart_quiz(self) -> None:
        cards = self.quiz_source_cards[:]
        if not cards:
            cards = self.load_repertoire()
            self.quiz_source_cards = cards[:]
        if cards:
            self.quiz_round_summaries = []
            self.quiz_attempt_counts = {}
            self.begin_quiz(cards)

    def replay_missed_moves(self) -> None:
        if self.last_missed_cards:
            self.begin_quiz(self.last_missed_cards)

    def begin_quiz(self, cards: list[dict]) -> None:
        self.mode = "quiz"
        self.quiz_cards = cards[:]
        random.shuffle(self.quiz_cards)
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_marks = []
        self.quiz_results = []
        self.last_missed_cards = []
        self.update_quiz_marks()
        self.clear_quiz_actions()
        self.clear_feedback()
        self.load_current_quiz_card()

    def load_current_quiz_card(self) -> None:
        self.selected_square = None
        self.dragging_square = None
        self.drag_item = None

        if self.quiz_index >= len(self.quiz_cards):
            total = len(self.quiz_cards)
            missed_results = [result for result in self.quiz_results if not result["correct"]]
            self.last_missed_cards = [result["card"] for result in missed_results]
            self.quiz_round_summaries.append((self.quiz_score, total))
            self.mode = "play"
            self.show_feedback("✓", f"Quiz complete: {self.quiz_score}/{total}", SUCCESS)
            self.status.set(f"Quiz complete: {self.quiz_score}/{total}")
            self.update_quiz_marks()
            self.show_quiz_summary()
            self.show_quiz_end_actions(has_misses=bool(self.last_missed_cards))
            self.board.reset()
            self.game = chess.pgn.Game()
            self.current_node = self.game
            self.move_history = []
            self.move_cursor = 0
            self.draw_board()
            return

        card = self.quiz_cards[self.quiz_index]
        self.orientation_turn = None
        self.board = chess.Board(card["before_fen"])
        self.status.set(f"Quiz {self.quiz_index + 1}/{len(self.quiz_cards)}: find a repertoire move")
        self.show_text(
            "\n".join(
                [
                    "Quiz mode",
                    "",
                    f"Position {self.quiz_index + 1} of {len(self.quiz_cards)}",
                    "",
                    "Find an accepted repertoire move on the board.",
                ]
            )
        )
        self.draw_board()

    def handle_quiz_move(self, move: chess.Move) -> None:
        card = self.quiz_cards[self.quiz_index]
        self.selected_square = None
        self.quiz_attempt_counts[self.card_key(card)] = self.quiz_attempt_counts.get(self.card_key(card), 0) + 1

        if move.uci() in card["accepted_uci"]:
            self.quiz_score += 1
            self.add_quiz_result("✓", card, True, move.uci())
            orientation_before_move = self.board.turn
            san = self.board.san(move)
            self.board.push(move)
            self.orientation_turn = orientation_before_move
            self.show_feedback("✓", f"Correct: {san}", SUCCESS)
            self.status.set(f"Correct: {san}")
            self.draw_board()
            self.animate_correct_move_square(move.to_square)
            self.root.after(1000, self.advance_quiz)
            return

        orientation_before_move = self.board.turn
        self.board.push(move)
        self.orientation_turn = orientation_before_move
        self.add_quiz_result("✕", card, False, move.uci())
        self.show_feedback("✕", f"Wrong. Correct move: {card['move_san']}", "#dc2626")
        self.status.set(f"Wrong. Correct move: {card['move_san']}")
        self.draw_board()
        self.animate_incorrect_move_square(move.to_square)
        self.root.after(1000, self.advance_quiz)

    def advance_quiz(self) -> None:
        self.clear_feedback()
        self.orientation_turn = None
        self.quiz_index += 1
        self.load_current_quiz_card()

    def animate_correct_move_square(self, square: chess.Square) -> None:
        display_file, display_rank = self.square_to_display(square)
        x1 = display_file * SQUARE_SIZE
        y1 = display_rank * SQUARE_SIZE
        x2 = x1 + SQUARE_SIZE
        y2 = y1 + SQUARE_SIZE
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2
        item = self.canvas.create_rectangle(
            center_x,
            center_y,
            center_x,
            center_y,
            fill="#22c55e",
            outline="",
            tags=("correct-move-square",),
        )
        self.canvas.tag_raise("piece")
        self.run_scale_in_center(item, center_x, center_y, SQUARE_SIZE, duration_ms=500)

    def animate_incorrect_move_square(self, square: chess.Square) -> None:
        display_file, display_rank = self.square_to_display(square)
        x1 = display_file * SQUARE_SIZE
        y1 = display_rank * SQUARE_SIZE
        center_x = x1 + SQUARE_SIZE / 2
        center_y = y1 + SQUARE_SIZE / 2
        line_a = self.canvas.create_line(
            center_x,
            center_y,
            center_x,
            center_y,
            fill="#dc2626",
            width=7,
            capstyle=tk.ROUND,
            tags=("incorrect-move-square",),
        )
        line_b = self.canvas.create_line(
            center_x,
            center_y,
            center_x,
            center_y,
            fill="#dc2626",
            width=7,
            capstyle=tk.ROUND,
            tags=("incorrect-move-square",),
        )
        self.canvas.tag_raise("incorrect-move-square")
        self.run_x_scale_in_center(line_a, line_b, center_x, center_y, SQUARE_SIZE, duration_ms=500)

    def run_scale_in_center(self, item: int, center_x: float, center_y: float, size: int, duration_ms: int) -> None:
        frame_ms = 16
        frames = max(1, duration_ms // frame_ms)

        def animate(frame: int) -> None:
            if frame > frames:
                self.canvas.delete("correct-move-square")
                return

            progress = frame / frames
            eased = self.cubic_bezier_y(progress, 0.250, 0.460, 0.450, 0.940)
            half_size = (size * eased) / 2
            self.canvas.coords(
                item,
                center_x - half_size,
                center_y - half_size,
                center_x + half_size,
                center_y + half_size,
            )
            self.root.after(frame_ms, lambda: animate(frame + 1))

        animate(0)

    def run_x_scale_in_center(
        self,
        line_a: int,
        line_b: int,
        center_x: float,
        center_y: float,
        size: int,
        duration_ms: int,
    ) -> None:
        frame_ms = 16
        frames = max(1, duration_ms // frame_ms)

        def animate(frame: int) -> None:
            if frame > frames:
                self.canvas.delete("incorrect-move-square")
                return

            progress = frame / frames
            eased = self.cubic_bezier_y(progress, 0.250, 0.460, 0.450, 0.940)
            half_size = (size * 0.32 * eased)
            self.canvas.coords(
                line_a,
                center_x - half_size,
                center_y - half_size,
                center_x + half_size,
                center_y + half_size,
            )
            self.canvas.coords(
                line_b,
                center_x - half_size,
                center_y + half_size,
                center_x + half_size,
                center_y - half_size,
            )
            self.root.after(frame_ms, lambda: animate(frame + 1))

        animate(0)

    def cubic_bezier_y(self, t: float, x1: float, y1: float, x2: float, y2: float) -> float:
        # CSS cubic-bezier approximation for Animista's scale-in-center easing.
        inv = 1 - t
        return (3 * inv * inv * t * y1) + (3 * inv * t * t * y2) + (t * t * t)

    def show_feedback(self, symbol: str, message: str, color: str) -> None:
        self.feedback_label.configure(fg=color, font=("Segoe UI", 16, "bold"))
        self.feedback.set(f"{symbol} {message}")

    def add_quiz_result(self, mark: str, card: dict, correct: bool, attempted_uci: str) -> None:
        result = {
            "mark": mark,
            "card": card,
            "correct": correct,
            "attempted_uci": attempted_uci,
            "replay_uci": attempted_uci if correct else card["move_uci"],
        }
        self.quiz_results.append(result)
        self.quiz_marks.append(result)
        self.update_quiz_marks()

    def update_quiz_marks(self) -> None:
        for child in self.quiz_marks_frame.winfo_children():
            child.destroy()
        for result in self.quiz_marks:
            mark = result["mark"]
            color = SUCCESS if mark == "✓" else "#dc2626"
            label = tk.Label(
                self.quiz_marks_frame,
                text=mark,
                font=("Segoe UI", 18, "bold"),
                bg=BG,
                fg=color,
                cursor="hand2" if self.mode != "quiz" else "",
            )
            label.pack(side="left", padx=3)
            if self.mode != "quiz":
                label.bind("<Button-1>", lambda _event, r=result: self.replay_quiz_result(r))

    def clear_feedback(self) -> None:
        self.feedback_label.configure(fg=TEXT, font=("Segoe UI", 13, "bold"))
        self.feedback.set("")

    def clear_quiz_actions(self) -> None:
        for child in self.quiz_actions_frame.winfo_children():
            child.destroy()

    def show_quiz_end_actions(self, has_misses: bool) -> None:
        self.clear_quiz_actions()
        ttk.Button(self.quiz_actions_frame, text="Restart Quiz", command=self.restart_quiz).pack(side="left", padx=(0, 8))
        if has_misses:
            ttk.Button(
                self.quiz_actions_frame,
                text="Only Replay Missed moves",
                command=self.replay_missed_moves,
            ).pack(side="left")

    def show_quiz_summary(self) -> None:
        total = len(self.quiz_cards)
        lines = [
            "Quiz complete",
            "",
            f"Score: {self.quiz_score}/{total}",
            "",
            "Round scores:",
        ]
        for index, (score, round_total) in enumerate(self.quiz_round_summaries, start=1):
            lines.append(f"{index}. {score}/{round_total}")

        lines.extend(["", "Attempts per move:"])
        for card in self.quiz_cards:
            attempts = self.quiz_attempt_counts.get(self.card_key(card), 0)
            lines.append(f"- {card['move_san']}: {attempts} attempt(s)")

        lines.extend(["", "Click any check or X below to replay that saved move."])
        self.show_text("\n".join(lines))

    def replay_quiz_result(self, result: dict) -> None:
        card = result["card"]
        self.mode = "replay"
        self.clear_feedback()
        self.clear_quiz_actions()
        self.selected_square = None
        self.dragging_square = None
        self.board = chess.Board(card["before_fen"])
        self.orientation_turn = self.board.turn
        self.status.set(f"Replay: {card['move_san']}")
        self.draw_board()
        self.root.after(400, lambda c=card, u=result["replay_uci"]: self.finish_replay(c, u))

    def finish_replay(self, card: dict, move_uci: str) -> None:
        move = chess.Move.from_uci(move_uci)
        if move not in self.board.legal_moves:
            self.status.set("Replay failed: saved move is not legal from this FEN")
            return
        orientation_before_move = self.board.turn
        self.board.push(move)
        self.orientation_turn = orientation_before_move
        self.draw_board()
        self.animate_correct_move_square(move.to_square)

    def view_repertoire(self) -> None:
        cards = self.load_repertoire()
        self.clear_right_body()
        self.right_title.configure(text="Saved Repertoire")

        if not cards:
            self.show_text("No repertoire saved yet.\n\nPlay a move, then click Add move.", title="Saved Repertoire")
            self.status.set("No saved repertoire moves yet")
            return

        list_frame = self.create_scrollable_right_body()
        index = 1
        opening_count = 0
        repertoire_ids = list(dict.fromkeys(card["repertoire_id"] for card in cards))
        for repertoire_id in repertoire_ids:
            repertoire_cards = sorted(
                (card for card in cards if card["repertoire_id"] == repertoire_id), key=self.repertoire_sort_key
            )
            representative = repertoire_cards[0]
            side = "White" if representative["repertoire_color"] else "Black"
            ttk.Label(
                list_frame,
                text=f"{representative['repertoire_name']} — {side} ({len(repertoire_cards)})",
                style="Title.TLabel",
            ).pack(
                anchor="w", pady=(8 if index > 1 else 0, 10)
            )
            opening_groups: dict[str, list[dict]] = {}
            for card in repertoire_cards:
                opening_groups.setdefault(card["opening"], []).append(card)
            for opening, opening_cards in opening_groups.items():
                index = self.render_opening_section(list_frame, opening, opening_cards, index)
                opening_count += 1

        self.status.set(f"Viewing {len(cards)} moves in {opening_count} collapsed opening(s)")

    def render_opening_section(
        self,
        parent: ttk.Frame,
        opening: str,
        cards: list[dict[str, str]],
        start_index: int,
    ) -> int:
        section = ttk.Frame(parent, style="Panel.TFrame")
        section.pack(fill="x", pady=(0, 8))

        content = ttk.Frame(section, style="Panel.TFrame", padding=(10, 8, 0, 0))
        header = ttk.Button(section, style="Accordion.TButton")
        header.configure(
            text=f"+  {opening} ({len(cards)})",
            command=lambda: self.toggle_opening_section(header, content, opening, len(cards)),
        )
        header.pack(fill="x")

        index = start_index
        for card in cards:
            self.render_repertoire_row(content, index, card)
            index += 1
        return index

    def toggle_opening_section(
        self,
        header: ttk.Button,
        content: ttk.Frame,
        opening: str,
        count: int,
    ) -> None:
        if content.winfo_manager():
            content.pack_forget()
            header.configure(text=f"+  {opening} ({count})")
        else:
            content.pack(fill="x")
            header.configure(text=f"-  {opening} ({count})")

    def render_repertoire_row(self, parent: ttk.Frame, index: int, card: dict[str, str]) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame", padding=(0, 0, 0, 8))
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(0, weight=1)

        context = card.get("contexts", [""])[0] or "Starting position"
        classification = self.classify_opening(card)
        branch = " > ".join(
            value for value in (classification["variation"], classification["subvariation"]) if value
        ) or "Main line"
        summary = self.ellipsize(f"{index}. {branch}", 58)
        move_line = self.ellipsize(f"{context} → {card['move_san']}", 62)

        ttk.Label(row, text=summary, style="TLabel", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(row, text=move_line, style="TLabel", foreground=MUTED).grid(
            row=1, column=0, sticky="ew", padx=(0, 8), pady=(2, 0)
        )
        ttk.Button(row, text="Details", width=8, command=lambda r=row, c=card: self.toggle_repertoire_details(r, c)).grid(
            row=0, column=1, rowspan=2, padx=(0, 6)
        )
        ttk.Button(row, text="Remove", width=7, command=lambda c=card: self.remove_card_answer(c)).grid(
            row=0, column=2, rowspan=2
        )

    def toggle_repertoire_details(self, row: ttk.Frame, card: dict[str, str]) -> None:
        existing = getattr(row, "details_frame", None)
        if existing and existing.winfo_exists():
            existing.destroy()
            row.details_frame = None
            return

        details = ttk.Frame(row, style="Panel.TFrame", padding=(0, 6, 0, 0))
        details.grid(row=2, column=0, columnspan=3, sticky="ew")
        classification = self.classify_opening(card)
        accepted_text = ", ".join(
            f"{answer['move_san']} ({answer['move_uci']})" for answer in card["accepted_moves"]
        )
        detail_text = "\n".join(
            [
                f"Opening: {classification['opening']}",
                f"Variation: {classification['variation'] or '(none identified)'}",
                f"Subvariation: {classification['subvariation'] or '(none identified)'}",
                f"Accepted: {accepted_text}",
                f"Context: {card.get('contexts', ['Starting position'])[0] or 'Starting position'}",
                f"Before FEN: {card['before_fen']}",
                f"Repertoire: {card['repertoire_name']}",
                f"File: {card['file']}",
            ]
        )
        ttk.Label(details, text=detail_text, style="TLabel", wraplength=380, justify="left").pack(anchor="w")
        row.details_frame = details

    def ellipsize(self, text: str, max_chars: int) -> str:
        return text if len(text) <= max_chars else f"{text[: max_chars - 1]}…"

    def remove_card_answer(self, card: dict) -> None:
        info = self.store.get(card["repertoire_id"])
        if info is None:
            messagebox.showinfo(
                "Migrate first",
                "The PGN repertoire for this entry could not be found.",
                parent=self.root,
            )
            return

        def remove(answer: dict, parent: tk.Misc = self.root) -> None:
            if not messagebox.askyesno(
                "Remove answer",
                f"Stop training {answer['move_san']} from this position?\n\n"
                "The move remains in the PGN when it is needed as context.",
                parent=parent,
            ):
                return
            removed = self.store.remove_answer(info, card["position_key"], answer["move_uci"])
            self.status.set(f"Removed {answer['move_san']} from {removed} PGN path(s)")
            if isinstance(parent, tk.Toplevel):
                parent.destroy()
            self.view_repertoire()

        answers = card["accepted_moves"]
        if len(answers) == 1:
            remove(answers[0])
            return
        chooser = tk.Toplevel(self.root)
        chooser.title("Choose answer to remove")
        chooser.configure(bg=PANEL)
        chooser.transient(self.root)
        shell = ttk.Frame(chooser, style="Panel.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Choose answer to remove", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        for answer in answers:
            ttk.Button(
                shell,
                text=f"{answer['move_san']} ({answer['move_uci']})",
                command=lambda a=answer: remove(a, chooser),
            ).pack(fill="x", pady=3)
        ttk.Button(shell, text="Cancel", command=chooser.destroy).pack(fill="x", pady=(10, 0))
        chooser.grab_set()

    def legal_targets_from_selected(self) -> set[chess.Square]:
        if self.selected_square is None:
            return set()
        return {
            move.to_square
            for move in self.board.legal_moves
            if move.from_square == self.selected_square
        }

    def update_pgn(self) -> None:
        self.show_text(self.current_pgn() or "Moves will appear here.", title="Live PGN")

    def current_pgn(self) -> str:
        exporter = chess.pgn.StringExporter(headers=False, variations=False, comments=False, columns=None)
        return self.game.accept(exporter).strip()

    def clear_right_body(self) -> None:
        for child in self.right_body.winfo_children():
            child.destroy()

    def create_scrollable_right_body(self) -> ttk.Frame:
        container = ttk.Frame(self.right_body, style="Panel.TFrame")
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, bg=PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="Panel.TFrame")
        window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def update_scroll_region(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def update_window_width(event: tk.Event) -> None:
            canvas.itemconfigure(window_id, width=event.width)

        scroll_frame.bind("<Configure>", update_scroll_region)
        canvas.bind("<Configure>", update_window_width)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        return scroll_frame

    def show_text(self, text: str, title: str | None = None) -> None:
        if title:
            self.right_title.configure(text=title)
        self.clear_right_body()
        text_box = tk.Text(
            self.right_body,
            width=42,
            height=28,
            wrap="word",
            bg=PANEL,
            fg=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            padx=4,
            pady=4,
        )
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", text)
        text_box.configure(state="disabled")


def run_desktop_mvp() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        messagebox.showerror("Startup error", str(exc))
        return
    ChessMvpApp(root)
    root.mainloop()


if __name__ == "__main__":
    run_desktop_mvp()

