import tkinter as tk
import io
import sys
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import chess
import chess.pgn

from app_paths import repertoire_directory, resource_directory, resource_path
from opening_classifier import OPENING_CLASSIFIER
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
ASSET_DIR = resource_path("assets", "pieces")
CHECK_SUCCESS_LOTTIE = resource_path("assets", "check_success.json")
REPERTOIRE_DIR = repertoire_directory()

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
        self.root.title("Chess Repertoire Memorizer")
        self.root.configure(bg=BG)
        self.configure_style()

        self.board = chess.Board()
        self.game = chess.pgn.Game()
        self.current_node = self.game
        self.mode = "play"
        self.move_history: list[dict[str, str]] = []
        self.move_cursor = 0
        self.history_root_fen = chess.Board().fen()
        self.active_line_card: dict | None = None
        self.editing_card: dict | None = None
        self.edit_dirty = False
        self.repertoire_expanded_sections: set[tuple[str, ...]] = set()
        self.repertoire_scroll_fraction = 0.0
        self.repertoire_scroll_canvas: tk.Canvas | None = None
        self.quiz_cards: list[dict] = []
        self.quiz_source_cards: list[dict] = []
        self.quiz_dialog: tk.Toplevel | None = None
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_results: list[dict] = []
        self.quiz_round_summaries: list[tuple[int, int]] = []
        self.quiz_attempt_counts: dict[str, int] = {}
        self.last_missed_cards: list[dict] = []
        self.quiz_input_enabled = False
        self.quiz_animation_serial = 0
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
        self.quiz_title_card = tk.Frame(
            board_frame,
            width=BOARD_SIZE,
            height=106,
            bg="#111827",
            highlightthickness=1,
            highlightbackground="#c9a227",
        )
        self.quiz_title_card.pack_propagate(False)
        tk.Frame(self.quiz_title_card, width=5, bg="#c9a227").pack(side="left", fill="y")
        title_copy = tk.Frame(self.quiz_title_card, bg="#111827", padx=16, pady=10)
        title_copy.pack(side="left", fill="both", expand=True)
        self.quiz_title_kicker = tk.Label(
            title_copy,
            text="OPENING STUDY",
            font=("Segoe UI", 8, "bold"),
            bg="#111827",
            fg="#d6b84b",
            anchor="w",
        )
        self.quiz_title_kicker.pack(fill="x")
        self.quiz_title_name = tk.Label(
            title_copy,
            text="",
            font=("Georgia", 17, "bold"),
            bg="#111827",
            fg="#f9fafb",
            anchor="w",
        )
        self.quiz_title_name.pack(fill="x", pady=(1, 0))
        self.quiz_title_branch = tk.Label(
            title_copy,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#111827",
            fg="#d1d5db",
            anchor="w",
        )
        self.quiz_title_branch.pack(fill="x", pady=(2, 0))
        self.quiz_title_progress = tk.Label(
            self.quiz_title_card,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#111827",
            fg="#9ca3af",
            padx=14,
            justify="right",
        )
        self.quiz_title_progress.pack(side="right", fill="y")
        self.canvas = tk.Canvas(board_frame, width=BOARD_SIZE, height=BOARD_SIZE, highlightthickness=0, bg=PANEL)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.root.bind("<Left>", lambda _event: self.back_move())
        self.root.bind("<Right>", lambda _event: self.forward_move())
        self.mode_banner = tk.StringVar(value="")
        self.mode_banner_label = tk.Label(
            board_frame,
            textvariable=self.mode_banner,
            font=("Segoe UI", 12, "bold"),
            bg=PANEL,
            fg=TEXT,
        )
        self.mode_banner_label.pack(pady=(8, 0))
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
        self.quiz_counter = tk.StringVar(value="")
        self.quiz_counter_label = tk.Label(
            feedback_frame,
            textvariable=self.quiz_counter,
            width=14,
            font=("Segoe UI", 10, "bold"),
            bg=BG,
            fg=MUTED,
        )
        self.quiz_counter_label.pack(pady=(2, 0))
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
        if self.mode == "quiz":
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
        if self.mode == "quiz" and not self.quiz_input_enabled:
            return
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
        if self.mode not in {"play", "edit", "quiz"}:
            return
        if self.mode == "quiz" and not self.quiz_input_enabled:
            return

        move = self.normalize_user_move(from_square, to_square)
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
        if self.mode == "edit":
            self.edit_dirty = True
        self.clear_feedback()
        self.status.set(f"Played {san}. {'White' if self.board.turn else 'Black'} to move")
        self.selected_square = None
        self.draw_board()
        self.update_pgn()

    def normalize_user_move(
        self,
        from_square: chess.Square,
        to_square: chess.Square,
    ) -> chess.Move:
        """Resolve a clear castling gesture to chess's exact king destination."""
        move = chess.Move(from_square, to_square)
        piece = self.board.piece_at(from_square)
        if (
            piece is None
            or piece.piece_type != chess.KING
            or piece.color != self.board.turn
            or chess.square_rank(from_square) != chess.square_rank(to_square)
            or abs(chess.square_file(to_square) - chess.square_file(from_square)) < 2
        ):
            return move

        gesture_direction = 1 if to_square > from_square else -1
        for legal_move in self.board.legal_moves:
            if (
                legal_move.from_square == from_square
                and self.board.is_castling(legal_move)
                and (
                    1 if chess.square_file(legal_move.to_square) > chess.square_file(from_square) else -1
                )
                == gesture_direction
            ):
                return legal_move
        return move

    def back_move(self) -> None:
        if self.mode not in {"play", "view", "edit"} or self.move_cursor == 0:
            return
        self.move_cursor -= 1
        self.restore_board_to_cursor()

    def forward_move(self) -> None:
        if self.mode not in {"play", "view", "edit"} or self.move_cursor >= len(self.move_history):
            return
        self.move_cursor += 1
        self.restore_board_to_cursor()

    def restore_board_to_cursor(self) -> None:
        if self.move_cursor == 0:
            self.board = chess.Board(self.history_root_fen)
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
        board = chess.Board(self.history_root_fen)
        if board.fen() != chess.Board().fen():
            self.game.setup(board)
        self.current_node = self.game
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
        self.update_mode_banner()
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
                        self.canvas.create_image(
                            center_x,
                            center_y,
                            image=image,
                            tags=("piece", f"piece-{square}"),
                        )
                    else:
                        white_symbol, black_symbol = PIECES[piece.piece_type]
                        symbol = white_symbol if piece.color == chess.WHITE else black_symbol
                        self.canvas.create_text(
                            center_x,
                            center_y,
                            text=symbol,
                            font=("Segoe UI", 36, "bold"),
                            tags=("piece", f"piece-{square}"),
                        )

    def update_navigation_buttons(self) -> None:
        if self.mode in {"play", "view", "edit"}:
            self.back_button.grid()
            self.forward_button.grid()
        else:
            self.back_button.grid_remove()
            self.forward_button.grid_remove()

    def update_mode_banner(self) -> None:
        labels = {
            "view": "VIEWING SAVED MOVE",
            "edit": "EDITING SAVED MOVE",
        }
        colors = {
            "view": "#1d4ed8",
            "edit": "#b45309",
        }
        self.mode_banner.set(labels.get(self.mode, ""))
        self.mode_banner_label.configure(fg=colors.get(self.mode, TEXT))

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
            side = "Both sides" if info.color is None else ("White" if info.color else "Black")
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
        info = self.store.create(name.strip())
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
        ttk.Combobox(
            fields,
            textvariable=color_var,
            values=("White", "Black", "Both"),
            state="readonly",
            width=8,
        ).grid(
            row=0, column=3
        )
        fields.columnconfigure(1, weight=1)

        text_box = tk.Text(shell, wrap="none", height=20, font=("Consolas", 9), undo=True)
        text_box.pack(fill="both", expand=True)
        summary_var = tk.StringVar(value="Load a PGN file or paste PGN text, then preview it.")
        ttk.Label(shell, textvariable=summary_var, wraplength=650).pack(anchor="w", pady=(8, 8))

        preview_state: dict[str, object] = {"preview": None, "source": "", "color": ""}
        import_button = ttk.Button(shell, text="Import", style="Primary.TButton", state="disabled")

        def selected_training_color() -> bool | None:
            if color_var.get() == "Both":
                return None
            return color_var.get() == "White"

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
            result = self.store.preview_import(content, selected_training_color())
            preview_state["preview"] = result
            preview_state["source"] = content
            preview_state["color"] = color_var.get()
            if result["errors"]:
                summary_var.set("Cannot import: " + "; ".join(result["errors"][:3]))
                import_button.configure(state="disabled")
                return
            if result["used_existing_marks"]:
                mark_note = "existing CRM quiz marks"
            elif color_var.get() == "Both":
                mark_note = "all moves for both sides"
            else:
                mark_note = f"all {color_var.get()} moves"
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
                info = self.store.import_preview(result, name, selected_training_color(), mode)
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
            outcome = self.store.add_line(info, moves)
        except (ValueError, OSError) as exc:
            self.status.set(str(exc))
            return
        card = self.move_history[self.move_cursor - 1]
        if outcome == "replaced":
            self.status.set(f"Replaced the previous reply with {card['move_san']} in {info.name}")
        elif outcome == "added":
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
        self.history_root_fen = chess.Board().fen()
        self.active_line_card = None
        self.editing_card = None
        self.edit_dirty = False
        self.quiz_cards = []
        self.quiz_source_cards = []
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_results = []
        self.quiz_round_summaries = []
        self.quiz_attempt_counts = {}
        self.last_missed_cards = []
        self.quiz_input_enabled = False
        self.quiz_animation_serial += 1
        self.update_quiz_counter()
        self.clear_quiz_actions()
        self.hide_quiz_title_card()
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
        fields = ("eco", "opening", "variation", "subvariation")
        stored = {key: card.get(key, "") for key in fields}
        if stored["opening"]:
            return stored

        moves = self.pgn_uci_moves(card.get("pgn", ""))
        return OPENING_CLASSIFIER.classify(moves).opening_fields()

    def pgn_uci_moves(self, pgn: str) -> list[str]:
        try:
            game = chess.pgn.read_game(io.StringIO(pgn))
            return [move.uci() for move in game.mainline_moves()] if game else []
        except (ValueError, IndexError):
            return []

    def opening_label(self, card: dict[str, str]) -> str:
        classification = self.classify_opening(card)
        opening = classification["opening"]
        if classification["eco"]:
            opening = f"{classification['eco']} · {opening}"
        return " > ".join(
            value
            for value in (opening, classification["variation"], classification["subvariation"])
            if value
        )

    def opening_path(self, card: dict[str, str]) -> tuple[str, ...]:
        classification = self.classify_opening(card)
        return tuple(
            value
            for value in (
                classification["opening"],
                classification["variation"],
                classification["subvariation"],
            )
            if value
        )

    @staticmethod
    def path_is_within(path: tuple[str, ...], parent: tuple[str, ...]) -> bool:
        return len(path) >= len(parent) and path[: len(parent)] == parent

    @staticmethod
    def path_contains_labels(path: tuple[str, ...], labels: tuple[str, ...]) -> bool:
        """Return whether labels occur in order, allowing catalog transitions between them."""
        if not labels:
            return True
        label_index = 0
        for value in path:
            if value == labels[label_index]:
                label_index += 1
                if label_index == len(labels):
                    return True
        return False

    def study_nodes(
        self,
        cards: list[dict],
        family_paths: list[tuple[str, ...]] | None = None,
        move_paths: list[tuple[str, ...]] | None = None,
    ) -> list[tuple[str, bool, tuple[str, ...]]]:
        """Return move-prefix family nodes in repertoire/PGN encounter order."""
        nodes: list[tuple[str, bool, tuple[str, ...]]] = []
        seen: set[tuple[str, bool, tuple[str, ...]]] = set()
        if move_paths is None:
            move_paths = [tuple(self.pgn_uci_moves(card.get("pgn", ""))) for card in cards]
        if family_paths is None:
            family_paths = self.study_family_paths(cards, move_paths)
        for index, (card, path) in enumerate(zip(cards, family_paths)):
            if not self.study_card_is_eligible(cards, move_paths, index):
                continue
            for depth in range(1, len(path) + 1):
                node = (card["repertoire_id"], card["repertoire_color"], path[:depth])
                if node not in seen:
                    seen.add(node)
                    nodes.append(node)
        return nodes

    @staticmethod
    def study_card_is_eligible(
        cards: list[dict],
        move_paths: list[tuple[str, ...]],
        index: int,
    ) -> bool:
        """Keep prompts that have context, plus true standalone first-move studies."""
        if len(move_paths[index]) >= 2:
            return True
        card = cards[index]
        scope = (card.get("repertoire_id"), card.get("repertoire_color"))
        return not any(
            other_index != index
            and (other.get("repertoire_id"), other.get("repertoire_color")) == scope
            and len(move_paths[other_index]) > len(move_paths[index])
            and move_paths[other_index][: len(move_paths[index])] == move_paths[index]
            for other_index, other in enumerate(cards)
        )

    def study_family_paths(
        self,
        cards: list[dict],
        move_paths: list[tuple[str, ...]] | None = None,
    ) -> list[tuple[str, ...]]:
        """Build opening lineages from saved-move ancestry, not ECO equality.

        Opening catalogs rename positions as a line develops. A move can be
        classified as Old Sicilian, for example, immediately before the same
        PGN branch becomes the Open Sicilian and then the Accelerated Dragon.
        Prefix ancestry preserves that real sequence in the study tree.
        """
        if move_paths is None:
            move_paths = [
                tuple(self.pgn_uci_moves(card.get("pgn", "")))
                for card in cards
            ]
        family_paths: list[tuple[str, ...]] = []
        for index, card in enumerate(cards):
            scope = (card.get("repertoire_id"), card.get("repertoire_color"))
            ancestors = [
                other_index
                for other_index, other in enumerate(cards)
                if other_index != index
                and (other.get("repertoire_id"), other.get("repertoire_color")) == scope
                and len(move_paths[other_index]) >= 2
                and len(move_paths[other_index]) < len(move_paths[index])
                and move_paths[index][: len(move_paths[other_index])] == move_paths[other_index]
            ]
            ancestors.sort(key=lambda other_index: (len(move_paths[other_index]), other_index))

            lineage: list[str] = []
            for relative_index in ancestors + [index]:
                for label in self.opening_path(cards[relative_index]):
                    if label not in lineage:
                        lineage.append(label)
            family_paths.append(tuple(lineage))
        return family_paths

    def study_cards_for_path(
        self,
        cards: list[dict],
        repertoire_id: str,
        study_path: tuple[str, ...],
        repertoire_color: bool | None = None,
        family_paths: list[tuple[str, ...]] | None = None,
        move_paths: list[tuple[str, ...]] | None = None,
    ) -> list[dict]:
        """Return the sequential ancestor/descendant moves for a family branch."""
        if move_paths is None:
            move_paths = [
                tuple(self.pgn_uci_moves(card.get("pgn", "")))
                for card in cards
            ]
        if family_paths is None:
            family_paths = self.study_family_paths(cards, move_paths)
        eligible_indexes = {
            index
            for index in range(len(cards))
            if self.study_card_is_eligible(cards, move_paths, index)
        }
        target_indexes = {
            index
            for index, (card, family_path) in enumerate(zip(cards, family_paths))
            if card["repertoire_id"] == repertoire_id
            and (repertoire_color is None or card["repertoire_color"] == repertoire_color)
            and index in eligible_indexes
            and (
                self.path_is_within(family_path, study_path)
                or self.path_contains_labels(family_path, study_path)
            )
        }
        return [
            card
            for index, card in enumerate(cards)
            if card["repertoire_id"] == repertoire_id
            and (repertoire_color is None or card["repertoire_color"] == repertoire_color)
            and (
                index in target_indexes
                or any(
                    index in eligible_indexes
                    and
                    len(move_paths[index]) < len(move_paths[target_index])
                    and move_paths[target_index][: len(move_paths[index])] == move_paths[index]
                    for target_index in target_indexes
                )
            )
        ]

    def prepare_quiz_cards(self, cards: list[dict]) -> list[dict]:
        prepared = [dict(card) for card in cards]
        block_paths: list[tuple[str, ...]] = []
        for card in prepared:
            path = tuple(card["_study_path"]) if "_study_path" in card else self.opening_path(card)
            card["_study_path"] = path
            if not block_paths or block_paths[-1] != path:
                block_paths.append(path)

        block_count = len(block_paths)
        cursor = 0
        for block_index, path in enumerate(block_paths, 1):
            start = cursor
            while cursor < len(prepared) and tuple(prepared[cursor]["_study_path"]) == path:
                cursor += 1
            block_total = cursor - start
            for local_index in range(start, cursor):
                prepared[local_index]["_study_block_index"] = block_index
                prepared[local_index]["_study_block_count"] = block_count
                prepared[local_index]["_study_position"] = local_index - start + 1
                prepared[local_index]["_study_total"] = block_total
        return prepared

    def quiz_context_label(self, card: dict) -> str:
        moves = self.pgn_uci_moves(card.get("pgn", ""))[:-1]
        if not moves:
            return "Starting position"
        board = chess.Board()
        label = ""
        for text in moves:
            move = chess.Move.from_uci(text)
            if move not in board.legal_moves:
                return "Saved position"
            san = board.san(move)
            label = f"{board.fullmove_number}. {san}" if board.turn else f"{board.fullmove_number}... {san}"
            board.push(move)
        return f"After {label}"

    def show_quiz_title_card(self, card: dict) -> None:
        classification = self.classify_opening(card)
        title = self.specific_opening_title(classification)
        hierarchy = "  ›  ".join(
            value
            for value in (
                classification["opening"],
                classification["variation"],
                classification["subvariation"],
            )
            if value
        )
        side = "WHITE" if card.get("repertoire_color") else "BLACK"
        context = self.quiz_context_label(card)
        eco = classification["eco"] or "—"
        self.quiz_title_kicker.configure(text=f"♞  {side} REPERTOIRE  •  ECO {eco}  •  {context.upper()}")
        self.quiz_title_name.configure(text=self.ellipsize(title, 34))
        self.quiz_title_branch.configure(
            text=self.ellipsize(f"Opening family: {hierarchy or 'Unclassified position'}", 58)
        )
        self.quiz_title_progress.configure(
            text=(
                f"TREE {card.get('_study_block_index', 1)} / {card.get('_study_block_count', 1)}\n"
                f"MOVE {card.get('_study_position', 1)} / {card.get('_study_total', 1)}"
            )
        )
        if not self.quiz_title_card.winfo_manager():
            self.quiz_title_card.pack(fill="x", pady=(0, 8), before=self.canvas)

    @staticmethod
    def specific_opening_title(classification: dict[str, str]) -> str:
        """Choose the deepest useful opening name for the prominent headline."""
        opening = classification.get("opening", "")
        variation = classification.get("variation", "")
        subvariation = classification.get("subvariation", "")
        specific = subvariation or variation or opening or "Opening study"
        if specific.casefold() in {"main line", "main variation"}:
            parent = variation if subvariation else opening
            if parent:
                return f"{parent} — {specific}"
        return specific

    def hide_quiz_title_card(self) -> None:
        self.show_live_opening_title_card()

    def visible_opening(self) -> dict[str, str]:
        moves = [entry["move_uci"] for entry in self.move_history[: self.move_cursor]]
        return OPENING_CLASSIFIER.classify(moves).opening_fields()

    def show_live_opening_title_card(self) -> None:
        classification = self.visible_opening()
        title = self.specific_opening_title(classification)
        hierarchy = "  ›  ".join(
            value
            for value in (
                classification["opening"],
                classification["variation"],
                classification["subvariation"],
            )
            if value
        )
        eco = classification["eco"] or "—"
        turn = "WHITE" if self.board.turn else "BLACK"

        self.quiz_title_kicker.configure(text=f"♞  LIVE OPENING  •  ECO {eco}")
        self.quiz_title_name.configure(text=self.ellipsize(title, 34))
        self.quiz_title_branch.configure(
            text=self.ellipsize(f"Opening family: {hierarchy or 'Unclassified position'}", 58)
        )
        self.quiz_title_progress.configure(
            text=f"MOVE {self.board.fullmove_number}\n{turn} TO MOVE"
        )
        if not self.quiz_title_card.winfo_manager():
            self.quiz_title_card.pack(fill="x", pady=(0, 8), before=self.canvas)

    def classification_groups(
        self,
        cards: list[dict[str, str]],
        field: str,
    ) -> dict[str, list[dict[str, str]]]:
        groups: dict[str, list[dict[str, str]]] = {}
        for card in cards:
            label = self.classify_opening(card)[field] or "Main line"
            groups.setdefault(label, []).append(card)
        return groups

    def eco_descriptor(self, cards: list[dict[str, str]]) -> str:
        codes = list(
            dict.fromkeys(
                classification["eco"]
                for card in cards
                if (classification := self.classify_opening(card))["eco"]
            )
        )
        return f"ECO {', '.join(codes)}" if codes else "ECO not identified"

    def hierarchy_label(
        self,
        name: str,
        cards: list[dict[str, str]],
        count: int | None = None,
    ) -> str:
        return f"{name} ({len(cards) if count is None else count})  ·  {self.eco_descriptor(cards)}"

    def repertoire_sort_key(self, card: dict[str, str]) -> tuple[str, str, str, str, int, str]:
        classification = self.classify_opening(card)
        return (
            classification["eco"],
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
        move_paths = [
            tuple(self.pgn_uci_moves(card.get("pgn", "")))
            for card in cards
        ]
        family_paths = self.study_family_paths(cards, move_paths)
        family_path_by_card = {
            id(card): family_path
            for card, family_path in zip(cards, family_paths)
        }
        nodes = self.study_nodes(cards, family_paths, move_paths)
        node_cards = {
            node: self.study_cards_for_path(
                cards,
                node[0],
                node[2],
                node[1],
                family_paths,
                move_paths,
            )
            for node in nodes
        }
        node_label_cards = {
            node: [
                card
                for card, family_path in zip(cards, family_paths)
                if card["repertoire_id"] == node[0]
                and card["repertoire_color"] == node[1]
                and self.path_is_within(family_path, node[2])
            ]
            for node in nodes
        }

        dialog = tk.Toplevel(self.root)
        self.quiz_dialog = dialog
        dialog.title("Choose Opening Trees")
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.resizable(False, True)

        shell = ttk.Frame(dialog, style="Panel.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="Choose Opening Trees", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            shell,
            text=(
                "Parent families start collapsed. Expand one to follow the actual saved "
                "move sequence across ECO and opening-name changes; selecting a parent "
                "includes every continuation below it."
            ),
            style="TLabel",
            foreground=MUTED,
            wraplength=440,
        ).pack(anchor="w", pady=(4, 12))

        list_container = ttk.Frame(shell, style="Panel.TFrame")
        list_container.pack(fill="both", expand=True)
        canvas = tk.Canvas(list_container, width=460, height=340, bg=PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        choices = ttk.Frame(canvas, style="Panel.TFrame")
        window_id = canvas.create_window((0, 0), window=choices, anchor="nw")
        choices.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        variables: dict[tuple[str, bool, tuple[str, ...]], tk.BooleanVar] = {
            node: tk.BooleanVar(value=len(node[2]) == 1)
            for node in nodes
        }
        start_button = ttk.Button(shell, style="Primary.TButton")

        def selected_nodes() -> list[tuple[str, bool, tuple[str, ...]]]:
            selected = [node for node in nodes if variables[node].get()]
            return [
                node
                for node in selected
                if not any(
                    other[:2] == node[:2]
                    and len(other[2]) < len(node[2])
                    and self.path_is_within(node[2], other[2])
                    for other in selected
                )
            ]

        def update_start_button() -> None:
            chosen = selected_nodes()
            count = sum(len(node_cards[node]) for node in chosen)
            start_button.configure(
                text=f"Study Selected Trees ({count} moves)",
                state="normal" if count else "disabled",
            )

        def toggle_node(chosen: tuple[str, bool, tuple[str, ...]]) -> None:
            if variables[chosen].get():
                chosen_repertoire, chosen_color, chosen_path = chosen
                for other in nodes:
                    if other == chosen or other[:2] != (chosen_repertoire, chosen_color):
                        continue
                    other_path = other[2]
                    if self.path_is_within(other_path, chosen_path) or self.path_is_within(chosen_path, other_path):
                        variables[other].set(False)
            update_start_button()

        repertoire_sides = list(
            dict.fromkeys((card["repertoire_id"], card["repertoire_color"]) for card in cards)
        )
        for repertoire_id, repertoire_color in repertoire_sides:
            side_nodes = [node for node in nodes if node[:2] == (repertoire_id, repertoire_color)]
            representative = next(
                card
                for card in cards
                if (card["repertoire_id"], card["repertoire_color"])
                == (repertoire_id, repertoire_color)
            )
            heading = representative["repertoire_name"]
            side = "White" if repertoire_color else "Black"
            side_count = len(
                [
                    card
                    for card in cards
                    if (card["repertoire_id"], card["repertoire_color"])
                    == (repertoire_id, repertoire_color)
                ]
            )
            ttk.Label(
                choices,
                text=f"{heading} — {side} ({side_count})",
                style="TLabel",
                font=("Segoe UI", 11, "bold"),
            ).pack(fill="x", anchor="w", pady=(8, 4))
            opening_roots = [node for node in side_nodes if len(node[2]) == 1]
            for root_node in opening_roots:
                root_path = root_node[2]
                descendants = [
                    node
                    for node in side_nodes
                    if len(node[2]) > 1 and self.path_is_within(node[2], root_path)
                ]
                root_row = ttk.Frame(choices, style="Panel.TFrame")
                root_row.pack(fill="x", padx=(8, 0), pady=2)
                child_frame = ttk.Frame(choices, style="Panel.TFrame")

                if descendants:
                    expand_button = ttk.Button(root_row, text="+", width=3)
                    expand_button.pack(side="left", padx=(0, 4))

                    def toggle_folder(
                        row: ttk.Frame = root_row,
                        folder: ttk.Frame = child_frame,
                        button: ttk.Button = expand_button,
                    ) -> None:
                        if folder.winfo_manager():
                            folder.pack_forget()
                            button.configure(text="+")
                        else:
                            folder.pack(fill="x", after=row)
                            button.configure(text="−")

                    expand_button.configure(command=toggle_folder)
                else:
                    ttk.Label(root_row, text="", width=3, style="TLabel").pack(side="left", padx=(0, 4))

                ttk.Checkbutton(
                    root_row,
                    text=self.hierarchy_label(
                        root_path[0],
                        node_label_cards[root_node],
                        len(node_cards[root_node]),
                    ),
                    variable=variables[root_node],
                    command=lambda n=root_node: toggle_node(n),
                ).pack(side="left", fill="x", expand=True)

                for node in descendants:
                    path = node[2]
                    depth = len(path)
                    label = (
                        f"Next family  ·  {path[-1]}"
                        if depth == 2
                        else f"Continuation  ·  {path[-1]}"
                    )
                    ttk.Checkbutton(
                        child_frame,
                        text=self.hierarchy_label(
                            label,
                            node_label_cards[node],
                            len(node_cards[node]),
                        ),
                        variable=variables[node],
                        command=lambda n=node: toggle_node(n),
                    ).pack(
                        fill="x",
                        anchor="w",
                        padx=(42 + ((depth - 2) * 22), 0),
                        pady=3,
                    )

        def set_all(selected: bool) -> None:
            for node, variable in variables.items():
                variable.set(selected and len(node[2]) == 1)
            update_start_button()

        def close_dialog() -> None:
            self.quiz_dialog = None
            dialog.destroy()

        def launch_quiz() -> None:
            selected = selected_nodes()
            selected_cards: list[dict] = []
            for node in selected:
                for card in node_cards[node]:
                    study_card = dict(card)
                    study_card["_study_path"] = node[2]
                    study_card["_family_path"] = family_path_by_card[id(card)]
                    selected_cards.append(study_card)
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
        # Cards arrive in PGN traversal order. Keeping that order makes every
        # selected opening/variation play as one coherent tree instead of a
        # shuffled stack of unrelated positions.
        self.quiz_cards = self.prepare_quiz_cards(cards)
        self.quiz_index = 0
        self.quiz_score = 0
        self.quiz_results = []
        self.last_missed_cards = []
        self.quiz_input_enabled = False
        self.quiz_animation_serial += 1
        self.update_quiz_counter()
        self.clear_quiz_actions()
        self.clear_feedback()
        self.load_current_quiz_card()

    def load_current_quiz_card(self) -> None:
        self.selected_square = None
        self.dragging_square = None
        self.drag_item = None

        if self.quiz_index >= len(self.quiz_cards):
            self.quiz_input_enabled = False
            self.quiz_animation_serial += 1
            total = len(self.quiz_cards)
            missed_results = [result for result in self.quiz_results if not result["correct"]]
            self.last_missed_cards = [result["card"] for result in missed_results]
            self.quiz_round_summaries.append((self.quiz_score, total))
            self.mode = "play"
            self.show_feedback("✓", f"Quiz complete: {self.quiz_score}/{total}", SUCCESS)
            self.status.set(f"Quiz complete: {self.quiz_score}/{total}")
            self.update_quiz_counter()
            self.show_quiz_summary()
            self.show_quiz_end_actions(has_misses=bool(self.last_missed_cards))
            self.board.reset()
            self.game = chess.pgn.Game()
            self.current_node = self.game
            self.move_history = []
            self.move_cursor = 0
            self.history_root_fen = chess.Board().fen()
            self.active_line_card = None
            self.editing_card = None
            self.edit_dirty = False
            self.hide_quiz_title_card()
            self.draw_board()
            return

        card = self.quiz_cards[self.quiz_index]
        self.quiz_input_enabled = False
        self.quiz_animation_serial += 1
        animation_serial = self.quiz_animation_serial
        self.orientation_turn = card.get("repertoire_color", chess.Board(card["before_fen"]).turn)
        setup_transition = self.quiz_setup_transition(card)
        self.board = chess.Board(setup_transition[0] if setup_transition else card["before_fen"])
        self.show_quiz_title_card(card)
        study_path = tuple(card["_study_path"]) if "_study_path" in card else self.opening_path(card)
        study_name = " > ".join(study_path)
        self.status.set(
            f"{study_name} — move {card.get('_study_position', 1)}/{card.get('_study_total', 1)}"
        )
        self.show_text(
            "\n".join(
                [
                    "Opening tree drill",
                    "",
                    study_name,
                    "",
                    (
                        f"Tree {card.get('_study_block_index', 1)} of "
                        f"{card.get('_study_block_count', 1)}  •  "
                        f"Move {card.get('_study_position', 1)} of {card.get('_study_total', 1)}"
                    ),
                    "",
                    "Find an accepted repertoire move on the board.",
                ]
            ),
            title="Opening Study",
        )
        self.draw_board()
        if setup_transition:
            _start_fen, setup_move = setup_transition
            self.status.set(f"{study_name} — watch the preceding move")
            self.animate_quiz_setup_move(
                setup_move,
                card["before_fen"],
                animation_serial,
            )
        else:
            self.quiz_input_enabled = True

    def quiz_setup_transition(self, card: dict) -> tuple[str, chess.Move] | None:
        """Return the position and final setup move immediately before a prompt."""
        try:
            game = chess.pgn.read_game(io.StringIO(card.get("pgn", "")))
            if game is None:
                return None
            moves = list(game.mainline_moves())
            # The final PGN move is the trained answer. The move before it is
            # what an online opponent would have just played.
            if len(moves) < 2:
                return None
            board = game.board()
            for move in moves[:-2]:
                if move not in board.legal_moves:
                    return None
                board.push(move)
            setup_move = moves[-2]
            if setup_move not in board.legal_moves:
                return None
            start_fen = board.fen(en_passant="legal")
            board.push(setup_move)
            expected = chess.Board(card["before_fen"])
            if board.board_fen() != expected.board_fen() or board.turn != expected.turn:
                return None
            return start_fen, setup_move
        except (KeyError, ValueError, IndexError):
            return None

    def animate_quiz_setup_move(
        self,
        move: chess.Move,
        destination_fen: str,
        animation_serial: int,
        duration_ms: int = 320,
    ) -> None:
        """Animate the preceding move into the quiz position, then enable input."""
        moving_parts = self.quiz_setup_animation_parts(move)
        if not moving_parts:
            self.board = chess.Board(destination_fen)
            self.quiz_input_enabled = True
            self.draw_board()
            return

        animated_items: list[tuple[int, float, float, float, float]] = []
        for piece, from_square, to_square in moving_parts:
            from_file, from_rank = self.square_to_display(from_square)
            to_file, to_rank = self.square_to_display(to_square)
            start_x = (from_file + 0.5) * SQUARE_SIZE
            start_y = (from_rank + 0.5) * SQUARE_SIZE
            end_x = (to_file + 0.5) * SQUARE_SIZE
            end_y = (to_rank + 0.5) * SQUARE_SIZE
            self.canvas.itemconfigure(f"piece-{from_square}", state="hidden")

            image = self.piece_images.get(piece.symbol())
            if image:
                item = self.canvas.create_image(
                    start_x,
                    start_y,
                    image=image,
                    tags=("quiz-moving-piece",),
                )
            else:
                white_symbol, black_symbol = PIECES[piece.piece_type]
                symbol = white_symbol if piece.color == chess.WHITE else black_symbol
                item = self.canvas.create_text(
                    start_x,
                    start_y,
                    text=symbol,
                    font=("Segoe UI", 36, "bold"),
                    tags=("quiz-moving-piece",),
                )
            self.canvas.tag_raise(item)
            animated_items.append((item, start_x, start_y, end_x, end_y))

        frame_ms = 16
        effective_duration = min(duration_ms, 180) if len(moving_parts) > 1 else duration_ms
        frames = max(1, effective_duration // frame_ms)

        def animate(frame: int) -> None:
            if (
                animation_serial != self.quiz_animation_serial
                or self.mode != "quiz"
                or self.quiz_index >= len(self.quiz_cards)
            ):
                self.canvas.delete("quiz-moving-piece")
                return
            if frame > frames:
                self.board = chess.Board(destination_fen)
                self.canvas.delete("quiz-moving-piece")
                self.quiz_input_enabled = True
                current = self.quiz_cards[self.quiz_index]
                study_path = tuple(current.get("_study_path", self.opening_path(current)))
                self.status.set(
                    f"{' > '.join(study_path)} — your move "
                    f"{current.get('_study_position', 1)}/{current.get('_study_total', 1)}"
                )
                self.draw_board()
                return

            progress = frame / frames
            eased = 1 - ((1 - progress) ** 3)
            for item, start_x, start_y, end_x, end_y in animated_items:
                self.canvas.coords(
                    item,
                    start_x + ((end_x - start_x) * eased),
                    start_y + ((end_y - start_y) * eased),
                )
            self.root.after(frame_ms, lambda: animate(frame + 1))

        animate(0)

    def quiz_setup_animation_parts(
        self,
        move: chess.Move,
    ) -> list[tuple[chess.Piece, chess.Square, chess.Square]]:
        """Return every piece that visibly moves, including the castling rook."""
        piece = self.board.piece_at(move.from_square)
        if piece is None or move not in self.board.legal_moves:
            return []

        parts = [(piece, move.from_square, move.to_square)]
        if not self.board.is_castling(move):
            return parts

        before_rooks = self.board.pieces(chess.ROOK, piece.color)
        after = self.board.copy(stack=False)
        after.push(move)
        after_rooks = after.pieces(chess.ROOK, piece.color)
        rook_from = list(before_rooks - after_rooks)
        rook_to = list(after_rooks - before_rooks)
        if len(rook_from) == 1 and len(rook_to) == 1:
            rook = self.board.piece_at(rook_from[0])
            if rook is not None:
                parts.append((rook, rook_from[0], rook_to[0]))
        return parts

    def handle_quiz_move(self, move: chess.Move) -> None:
        card = self.quiz_cards[self.quiz_index]
        self.quiz_input_enabled = False
        self.selected_square = None
        self.quiz_attempt_counts[self.card_key(card)] = self.quiz_attempt_counts.get(self.card_key(card), 0) + 1

        if move.uci() in card["accepted_uci"]:
            self.quiz_score += 1
            self.add_quiz_result(card, True)
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
        self.add_quiz_result(card, False)
        self.show_feedback("✕", f"Wrong. Correct move: {card['move_san']}", "#dc2626")
        self.status.set(f"Wrong. Correct move: {card['move_san']}")
        self.draw_board()
        self.animate_incorrect_move_square(move.to_square)
        self.root.after(1000, self.advance_quiz)

    def advance_quiz(self) -> None:
        self.clear_feedback()
        self.quiz_input_enabled = False
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

    def add_quiz_result(self, card: dict, correct: bool) -> None:
        self.quiz_results.append({"card": card, "correct": correct})
        self.update_quiz_counter()

    def update_quiz_counter(self) -> None:
        if not self.quiz_cards:
            self.quiz_counter.set("")
            return
        self.quiz_counter.set(f"{len(self.quiz_results)} / {len(self.quiz_cards)}")

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

        self.show_text("\n".join(lines))

    def view_repertoire(self) -> None:
        self.hide_quiz_title_card()
        if self.mode in {"view", "edit"}:
            self.mode = "play"
            self.active_line_card = None
            self.editing_card = None
            self.edit_dirty = False
            self.draw_board()
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
            ttk.Label(
                list_frame,
                text=f"{representative['repertoire_name']} ({len(repertoire_cards)})",
                style="Title.TLabel",
            ).pack(
                anchor="w", pady=(8 if index > 1 else 0, 10)
            )
            for repertoire_color in (chess.WHITE, chess.BLACK):
                side_cards = [
                    card for card in repertoire_cards if card["repertoire_color"] == repertoire_color
                ]
                if not side_cards:
                    continue
                side = "White" if repertoire_color else "Black"
                ttk.Label(
                    list_frame,
                    text=f"{side} repertoire ({len(side_cards)})",
                    style="TLabel",
                    font=("Segoe UI", 11, "bold"),
                ).pack(anchor="w", pady=(6, 6))
                for opening, opening_cards in self.classification_groups(
                    side_cards, "opening"
                ).items():
                    index = self.render_opening_section(list_frame, opening, opening_cards, index)
                    opening_count += 1

        self.restore_repertoire_scroll_position()
        self.status.set(f"Viewing {len(cards)} moves in {opening_count} opening(s)")

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
        side_key = "White" if cards[0]["repertoire_color"] else "Black"
        state_key = (cards[0]["repertoire_id"], side_key, opening)
        label = self.hierarchy_label(opening, cards)
        header.configure(
            text=f"+  {label}",
            command=lambda: self.toggle_opening_section(
                header,
                content,
                label,
                state_key,
            ),
        )
        header.pack(fill="x")

        index = start_index
        for variation, variation_cards in self.classification_groups(cards, "variation").items():
            index = self.render_variation_section(
                content,
                variation,
                variation_cards,
                index,
            )
        self.restore_repertoire_section(header, content, label, state_key)
        return index

    def render_variation_section(
        self,
        parent: ttk.Frame,
        variation: str,
        cards: list[dict[str, str]],
        start_index: int,
    ) -> int:
        section = ttk.Frame(parent, style="Panel.TFrame")
        section.pack(fill="x", pady=(0, 6))

        content = ttk.Frame(section, style="Panel.TFrame", padding=(12, 7, 0, 0))
        header = ttk.Button(section, style="Accordion.TButton")
        classification = self.classify_opening(cards[0])
        state_key = (
            cards[0]["repertoire_id"],
            "White" if cards[0]["repertoire_color"] else "Black",
            classification["opening"],
            variation,
        )
        label = self.hierarchy_label(variation, cards)
        header.configure(
            text=f"+  {label}",
            command=lambda: self.toggle_opening_section(
                header,
                content,
                label,
                state_key,
            ),
        )
        header.pack(fill="x")

        subvariation_groups = self.classification_groups(cards, "subvariation")
        has_named_subvariations = any(name != "Main line" for name in subvariation_groups)
        index = start_index
        if has_named_subvariations:
            for subvariation, subvariation_cards in subvariation_groups.items():
                index = self.render_subvariation_section(
                    content,
                    subvariation,
                    subvariation_cards,
                    index,
                )
        else:
            for card in cards:
                self.render_repertoire_row(content, index, card)
                index += 1
        self.restore_repertoire_section(header, content, label, state_key)
        return index

    def render_subvariation_section(
        self,
        parent: ttk.Frame,
        subvariation: str,
        cards: list[dict[str, str]],
        start_index: int,
    ) -> int:
        section = ttk.Frame(parent, style="Panel.TFrame")
        section.pack(fill="x", pady=(0, 6))

        content = ttk.Frame(section, style="Panel.TFrame", padding=(12, 7, 0, 0))
        header = ttk.Button(section, style="Accordion.TButton")
        classification = self.classify_opening(cards[0])
        state_key = (
            cards[0]["repertoire_id"],
            "White" if cards[0]["repertoire_color"] else "Black",
            classification["opening"],
            classification["variation"] or "Main line",
            subvariation,
        )
        label = self.hierarchy_label(subvariation, cards)
        header.configure(
            text=f"+  {label}",
            command=lambda: self.toggle_opening_section(
                header,
                content,
                label,
                state_key,
            ),
        )
        header.pack(fill="x")

        index = start_index
        for card in cards:
            self.render_repertoire_row(content, index, card)
            index += 1
        self.restore_repertoire_section(header, content, label, state_key)
        return index

    def toggle_opening_section(
        self,
        header: ttk.Button,
        content: ttk.Frame,
        opening: str,
        state_key: tuple[str, ...] | None = None,
    ) -> None:
        if content.winfo_manager():
            content.pack_forget()
            header.configure(text=f"+  {opening}")
            if state_key is not None:
                self.repertoire_expanded_sections.discard(state_key)
        else:
            content.pack(fill="x")
            header.configure(text=f"-  {opening}")
            if state_key is not None:
                self.repertoire_expanded_sections.add(state_key)

    def restore_repertoire_section(
        self,
        header: ttk.Button,
        content: ttk.Frame,
        label: str,
        state_key: tuple[str, ...],
    ) -> None:
        if state_key in self.repertoire_expanded_sections:
            content.pack(fill="x")
            header.configure(text=f"-  {label}")

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
            row=0, column=1, padx=(0, 6), pady=(0, 3)
        )
        ttk.Button(row, text="Remove", width=7, command=lambda c=card: self.remove_card_answer(c)).grid(
            row=0, column=2, pady=(0, 3)
        )
        ttk.Button(row, text="View", width=8, command=lambda c=card: self.open_repertoire_card(c, "view")).grid(
            row=1, column=1, padx=(0, 6), pady=(3, 0)
        )
        ttk.Button(row, text="Edit", width=7, command=lambda c=card: self.open_repertoire_card(c, "edit")).grid(
            row=1, column=2, pady=(3, 0)
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
                f"ECO: {classification['eco'] or '(none identified)'}",
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

    def open_repertoire_card(self, card: dict, mode: str) -> None:
        answers = card["accepted_moves"]
        if len(answers) == 1:
            selected = dict(card)
            selected.update(answers[0])
            self.load_repertoire_card(selected, mode)
            return

        chooser = tk.Toplevel(self.root)
        chooser.title(f"Choose move to {mode}")
        chooser.configure(bg=PANEL)
        chooser.transient(self.root)
        shell = ttk.Frame(chooser, style="Panel.TFrame", padding=16)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text=f"Choose move to {mode}", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        def choose(answer: dict) -> None:
            selected = dict(card)
            selected.update(answer)
            chooser.destroy()
            self.load_repertoire_card(selected, mode)

        for answer in answers:
            ttk.Button(
                shell,
                text=f"{answer['move_san']} ({answer['move_uci']})",
                command=lambda a=answer: choose(a),
            ).pack(fill="x", pady=3)
        ttk.Button(shell, text="Cancel", command=chooser.destroy).pack(fill="x", pady=(10, 0))
        chooser.grab_set()

    def pgn_move_history(self, pgn: str) -> tuple[str, list[dict[str, str]]]:
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            raise ValueError("The saved PGN line could not be read")
        board = game.board()
        root_fen = board.fen()
        history: list[dict[str, str]] = []
        for move in game.mainline_moves():
            if move not in board.legal_moves:
                raise ValueError(f"Illegal move in saved PGN: {move.uci()}")
            before_fen = board.fen()
            san = board.san(move)
            board.push(move)
            history.append(
                {
                    "before_fen": before_fen,
                    "after_fen": board.fen(),
                    "move_uci": move.uci(),
                    "move_san": san,
                    "pgn": pgn,
                }
            )
        return root_fen, history

    def load_repertoire_card(self, card: dict, mode: str) -> None:
        self.hide_quiz_title_card()
        self.capture_repertoire_scroll_position()
        try:
            root_fen, history = self.pgn_move_history(card["pgn"])
        except (ValueError, IndexError) as exc:
            self.status.set(str(exc))
            return
        if not history:
            self.status.set("The saved line contains no moves to view")
            return

        self.mode = mode
        self.history_root_fen = root_fen
        self.move_history = history
        self.move_cursor = self.repertoire_line_start_cursor(mode, len(history))
        self.manual_orientation = card["repertoire_color"]
        self.active_line_card = card
        self.editing_card = card if mode == "edit" else None
        self.edit_dirty = False
        self.clear_feedback()
        self.clear_quiz_actions()
        self.restore_board_to_cursor()
        action = "Editing" if mode == "edit" else "Viewing"
        self.status.set(f"{action} {card['move_san']} — use ← and → to navigate")

    def repertoire_line_start_cursor(self, mode: str, move_count: int) -> int:
        if mode == "view":
            return move_count
        return max(0, move_count - 1)

    def return_to_repertoire(self) -> None:
        self.mode = "play"
        self.active_line_card = None
        self.editing_card = None
        self.edit_dirty = False
        self.draw_board()
        self.view_repertoire()

    def save_edited_move(self) -> None:
        card = self.editing_card
        if self.mode != "edit" or card is None:
            return
        if not self.edit_dirty:
            self.status.set("Make a change on the board before saving")
            return
        info = self.store.get(card["repertoire_id"])
        if info is None:
            self.status.set("The repertoire file could not be found")
            return
        moves = [
            chess.Move.from_uci(entry["move_uci"])
            for entry in self.move_history[: self.move_cursor]
        ]
        try:
            self.store.replace_answer(
                info,
                card["position_key"],
                card["move_uci"],
                moves,
            )
        except (ValueError, OSError) as exc:
            self.status.set(str(exc))
            return

        saved_move = self.move_history[self.move_cursor - 1]["move_san"]
        self.mode = "play"
        self.active_line_card = None
        self.editing_card = None
        self.edit_dirty = False
        self.draw_board()
        self.view_repertoire()
        self.status.set(f"Saved edited move {saved_move} in {info.name}")

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
        if self.mode != "quiz":
            self.show_live_opening_title_card()
        if self.mode in {"view", "edit"}:
            self.show_repertoire_line_mode()
            return
        self.show_text(self.current_pgn() or "Moves will appear here.", title="Live PGN")

    def show_repertoire_line_mode(self) -> None:
        editing = self.mode == "edit"
        title = "Editing Saved Move" if editing else "Viewing Saved Move"
        self.right_title.configure(text=title)
        self.clear_right_body()

        card = self.active_line_card
        mode_text = "EDITING" if editing else "VIEWING"
        mode_color = "#b45309" if editing else "#1d4ed8"
        tk.Label(
            self.right_body,
            text=mode_text,
            font=("Segoe UI", 13, "bold"),
            bg=PANEL,
            fg=mode_color,
        ).pack(anchor="w", pady=(0, 6))
        if card is not None:
            ttk.Label(
                self.right_body,
                text=f"{card['repertoire_name']} — {card['move_san']}",
                style="TLabel",
            ).pack(anchor="w", pady=(0, 8))

        text_box = tk.Text(
            self.right_body,
            width=42,
            height=22,
            wrap="word",
            bg=PANEL,
            fg=TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            padx=4,
            pady=4,
        )
        text_box.insert("1.0", self.current_pgn() or "Starting position")
        text_box.configure(state="disabled")
        text_box.pack(fill="both", expand=True)

        actions = ttk.Frame(self.right_body, style="Panel.TFrame")
        actions.pack(fill="x", pady=(10, 0))
        if editing:
            ttk.Button(
                actions,
                text="Save changes",
                style="Primary.TButton",
                command=self.save_edited_move,
                state="normal" if self.edit_dirty else "disabled",
            ).pack(fill="x", pady=(0, 6))
            ttk.Button(actions, text="Cancel editing", command=self.return_to_repertoire).pack(fill="x")
        else:
            ttk.Button(actions, text="Back to repertoire", command=self.return_to_repertoire).pack(fill="x")

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
        self.repertoire_scroll_canvas = canvas
        return scroll_frame

    def capture_repertoire_scroll_position(self) -> None:
        canvas = self.repertoire_scroll_canvas
        if canvas is None or not canvas.winfo_exists():
            return
        view = canvas.yview()
        if view:
            self.repertoire_scroll_fraction = view[0]

    def restore_repertoire_scroll_position(self) -> None:
        canvas = self.repertoire_scroll_canvas
        fraction = self.repertoire_scroll_fraction
        if canvas is None:
            return

        def restore() -> None:
            if canvas.winfo_exists():
                canvas.update_idletasks()
                canvas.yview_moveto(fraction)

        self.root.after_idle(restore)

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


def validate_runtime_resources() -> list[str]:
    """Return packaging/runtime validation errors without starting the GUI."""
    required = [
        CHECK_SUCCESS_LOTTIE,
        resource_path("data", "openings", "metadata.json"),
        resource_path("data", "openings", "openings.tsv"),
        resource_path("VERSION"),
    ]
    required.extend(
        ASSET_DIR / f"{color}{piece}.png"
        for color in ("w", "b")
        for piece in ("K", "Q", "R", "B", "N", "P")
    )
    errors = [f"Missing bundled resource: {path}" for path in required if not path.is_file()]
    if not REPERTOIRE_DIR.is_dir():
        errors.append(f"Writable repertoire directory was not created: {REPERTOIRE_DIR}")
    if getattr(sys, "frozen", False):
        try:
            REPERTOIRE_DIR.resolve().relative_to(resource_directory().resolve())
        except ValueError:
            pass
        else:
            errors.append("Writable repertoire directory is inside the bundled resource directory")
    return errors


if __name__ == "__main__":
    if "--packaging-self-test" in sys.argv:
        raise SystemExit(1 if validate_runtime_resources() else 0)
    run_desktop_mvp()

