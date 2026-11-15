import os
import threading
import time
import tkinter as tk
from datetime import datetime
import customtkinter as ctk

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

try:
    from src.board import Connect4Board
    from src.mcts import MCTS
    from src.experimenter import run_matchup, run_simulation_scaling
except ImportError:
    from board import Connect4Board
    from mcts import MCTS
    from experimenter import run_matchup, run_simulation_scaling


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Connect4MCTSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Connect 4 — Herramienta de Experimentación MCTS")
        self.geometry("1220x780")
        self.minsize(1100, 720)

        # Estado de la partida actual
        self.board = Connect4Board()
        self.human_player = Connect4Board.PLAYER_1
        self.ai_player = Connect4Board.PLAYER_2
        self.ai_thinking = False
        self.hover_col = None
        self.last_metrics = None

        # Referencias para la pestaña de experimentos
        self.experiment_running = False
        self.current_figure = None
        self.canvas_widget = None

        self._build_ui()
        self._draw_board()

    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=14)

        self.tab_play = self.tabview.add("Tablero e Inspección MCTS")
        self.tab_lab = self.tabview.add("Laboratorio de Experimentos")

        self._build_play_tab()
        self._build_lab_tab()

    # =========================================================================
    # PESTAÑA 1: TABLERO JUGABLE + VISUALIZACIÓN DE DECISIONES MCTS
    # =========================================================================
    def _build_play_tab(self):
        self.tab_play.grid_columnconfigure(0, weight=3)
        self.tab_play.grid_columnconfigure(1, weight=2)
        self.tab_play.grid_rowconfigure(0, weight=1)

        # Panel izquierdo: tablero y barra superior de evaluación por columna
        board_container = ctk.CTkFrame(self.tab_play)
        board_container.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)

        self.status_label = ctk.CTkLabel(
            board_container,
            text="Tu turno (Fichas Rojas) — Haz clic en una columna",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.status_label.pack(pady=(14, 6))

        self.board_canvas = tk.Canvas(
            board_container,
            width=630,
            height=620,
            bg="#1b1f27",
            highlightthickness=0,
        )
        self.board_canvas.pack(expand=True, pady=(0, 12))
        self.board_canvas.bind("<Motion>", self._on_canvas_hover)
        self.board_canvas.bind("<Leave>", self._on_canvas_leave)
        self.board_canvas.bind("<Button-1>", self._on_canvas_click)

        # Panel derecho: parámetros MCTS y telemetría en vivo
        side_panel = ctk.CTkFrame(self.tab_play)
        side_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)

        ctk.CTkLabel(
            side_panel,
            text="Parámetros del Algoritmo",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 8))

        # Control de número de simulaciones (N)
        self.sims_var = ctk.IntVar(value=500)
        self.sims_label = ctk.CTkLabel(
            side_panel, text=f"Simulaciones por turno (N): {self.sims_var.get()}"
        )
        self.sims_label.pack(anchor="w", padx=16)

        self.sims_slider = ctk.CTkSlider(
            side_panel,
            from_=50,
            to=2500,
            number_of_steps=49,
            variable=self.sims_var,
            command=self._on_sims_change,
        )
        self.sims_slider.pack(fill="x", padx=16, pady=(4, 12))

        # Control de constante de exploración UCB1 (C)
        self.c_var = ctk.DoubleVar(value=1.41)
        self.c_label = ctk.CTkLabel(
            side_panel, text=f"Constante de exploración UCB1 (C): {self.c_var.get():.2f}"
        )
        self.c_label.pack(anchor="w", padx=16)

        self.c_slider = ctk.CTkSlider(
            side_panel,
            from_=0.10,
            to=3.00,
            number_of_steps=58,
            variable=self.c_var,
            command=self._on_c_change,
        )
        self.c_slider.pack(fill="x", padx=16, pady=(4, 12))

        # Selector de quién empieza
        ctk.CTkLabel(side_panel, text="Orden de salida:").pack(anchor="w", padx=16)
        self.starter_var = ctk.StringVar(value="Humano empieza (Rojo)")
        self.starter_menu = ctk.CTkOptionMenu(
            side_panel,
            values=["Humano empieza (Rojo)", "IA MCTS empieza (Amarillo)"],
            variable=self.starter_var,
        )
        self.starter_menu.pack(fill="x", padx=16, pady=(4, 14))

        ctk.CTkButton(
            side_panel,
            text="Iniciar Nueva Partida",
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._reset_game,
        ).pack(fill="x", padx=16, pady=(0, 16))

        # Caja de telemetría del último movimiento de la IA
        ctk.CTkLabel(
            side_panel,
            text="Análisis del Último Turno IA",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(4, 6))

        self.telemetry_box = ctk.CTkTextbox(side_panel, height=280, font=ctk.CTkFont(family="Consolas", size=12))
        self.telemetry_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self._set_telemetry_text("Aún no ha jugado la IA.\nHaz tu primer movimiento o inicia una partida con salida de la IA.")

    def _on_sims_change(self, val):
        self.sims_label.configure(text=f"Simulaciones por turno (N): {int(val)}")

    def _on_c_change(self, val):
        self.c_label.configure(text=f"Constante de exploración UCB1 (C): {float(val):.2f}")

    def _set_telemetry_text(self, text):
        self.telemetry_box.configure(state="normal")
        self.telemetry_box.delete("1.0", "end")
        self.telemetry_box.insert("1.0", text)
        self.telemetry_box.configure(state="disabled")

    def _reset_game(self):
        if self.ai_thinking:
            return
        self.board = Connect4Board()
        self.last_metrics = None
        self.hover_col = None

        if self.starter_var.get().startswith("Humano"):
            self.human_player = Connect4Board.PLAYER_1
            self.ai_player = Connect4Board.PLAYER_2
            self.status_label.configure(text="Tu turno (Fichas Rojas) — Haz clic en una columna")
            self._set_telemetry_text("Partida reiniciada. Te toca mover primero.")
            self._draw_board()
        else:
            self.ai_player = Connect4Board.PLAYER_1
            self.human_player = Connect4Board.PLAYER_2
            self._draw_board()
            self._trigger_ai_move()

    def _get_col_from_x(self, x):
        margin_x = 35
        cell_size = 80
        col = (x - margin_x) // cell_size
        if 0 <= col < Connect4Board.COLS:
            return int(col)
        return None

    def _on_canvas_hover(self, event):
        if self.ai_thinking or self.board.is_terminal():
            return
        if self.board.current_player != self.human_player:
            return
        col = self._get_col_from_x(event.x)
        if col != self.hover_col:
            self.hover_col = col
            self._draw_board()

    def _on_canvas_leave(self, _event):
        if self.hover_col is not None:
            self.hover_col = None
            self._draw_board()

    def _on_canvas_click(self, event):
        if self.ai_thinking or self.board.is_terminal():
            return
        if self.board.current_player != self.human_player:
            return

        col = self._get_col_from_x(event.x)
        if col is None:
            return

        if self.board.make_move(col):
            self.hover_col = None
            self._draw_board()
            if self._check_game_over():
                return
            self._trigger_ai_move()

    def _trigger_ai_move(self):
        self.ai_thinking = True
        sims = int(self.sims_var.get())
        c_val = round(float(self.c_var.get()), 2)
        self.status_label.configure(text=f"IA MCTS pensando ({sims} simulaciones)...")

        board_copy = self.board.clone()

        def worker():
            engine = MCTS(simulations=sims, exploration_constant=c_val)
            best_col, metrics = engine.search(board_copy)
            self.after(0, lambda: self._finish_ai_move(best_col, metrics))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_ai_move(self, col, metrics):
        self.ai_thinking = False
        if col is not None:
            self.board.make_move(col)
            self.last_metrics = metrics
            self._update_telemetry_panel(metrics)
        self._draw_board()
        if not self._check_game_over():
            self.status_label.configure(text="Tu turno (Fichas Rojas) — Haz clic en una columna")

    def _update_telemetry_panel(self, metrics):
        lines = [
            f"Columna elegida : {metrics['best_move']} (índices 0-6)",
            f"Tiempo cálculo  : {metrics['elapsed_time_ms']} ms",
            f"Simulaciones (N): {metrics['simulations']}",
            f"Constante C     : {metrics['exploration_constant']}",
            f"Nodos expandidos: {metrics['nodes_created']}",
            "-" * 42,
            "Col | Visitas | % Victoria",
            "-" * 42,
        ]
        col_stats = metrics.get("column_stats", {})
        for c in range(Connect4Board.COLS):
            if c in col_stats:
                v = col_stats[c]["visits"]
                wr = col_stats[c]["win_rate"]
                marker = " <--" if c == metrics["best_move"] else ""
                lines.append(f" {c}  |  {v:>5}  |   {wr:>5.1f}%{marker}")
            else:
                lines.append(f" {c}  |    -    |   Llena")
        self._set_telemetry_text("\n".join(lines))

    def _check_game_over(self):
        if not self.board.is_terminal():
            return False
        if self.board.winner == 0:
            self.status_label.configure(text="¡Empate! Tablero completo sin 4 en raya.")
        elif self.board.winner == self.human_player:
            self.status_label.configure(text="¡Has ganado a la IA!")
        else:
            self.status_label.configure(text="¡Gana la IA MCTS!")
        return True

    def _draw_board(self):
        c = self.board_canvas
        c.delete("all")

        margin_x = 35
        top_offset = 105
        cell_size = 80
        radius = 31

        # 1. Zona superior: barras con la valoración MCTS del último turno por columna
        col_stats = self.last_metrics["column_stats"] if self.last_metrics else {}
        best_col = self.last_metrics["best_move"] if self.last_metrics else None

        for col in range(Connect4Board.COLS):
            cx = margin_x + col * cell_size + cell_size // 2
            c.create_text(cx, 16, text=f"Col {col}", fill="#9aa5b4", font=("Segoe UI", 10, "bold"))

            if col in col_stats:
                wr = col_stats[col]["win_rate"]
                bar_max_h = 42
                bar_h = max(3, int((wr / 100.0) * bar_max_h))
                bar_color = "#2ecc71" if col == best_col else "#3b8ed0"
                c.create_rectangle(
                    cx - 18, 72 - bar_h, cx + 18, 72, fill=bar_color, outline=""
                )
                c.create_text(
                    cx, 84, text=f"{wr:.0f}%", fill="#e6edf3", font=("Segoe UI", 9, "bold")
                )

            # Ficha fantasma al pasar el ratón en turno del humano
            if (
                self.hover_col == col
                and not self.ai_thinking
                and not self.board.is_terminal()
                and self.board.current_player == self.human_player
                and col in self.board.get_valid_moves()
            ):
                ghost_color = "#e74c3c" if self.human_player == Connect4Board.PLAYER_1 else "#f1c40f"
                c.create_oval(
                    cx - 16, 42, cx + 16, 74, fill=ghost_color, outline="#ffffff", width=1
                )

        # 2. Marco azul clásico del tablero
        board_w = Connect4Board.COLS * cell_size
        board_h = Connect4Board.ROWS * cell_size
        c.create_rectangle(
            margin_x - 8,
            top_offset - 8,
            margin_x + board_w + 8,
            top_offset + board_h + 8,
            fill="#1f4e8c",
            outline="#163968",
            width=3,
        )

        # 3. Huecos y fichas
        win_set = set(self.board.winning_cells)
        for row in range(Connect4Board.ROWS):
            for col in range(Connect4Board.COLS):
                cx = margin_x + col * cell_size + cell_size // 2
                cy = top_offset + row * cell_size + cell_size // 2
                val = self.board.grid[row][col]

                if val == Connect4Board.EMPTY:
                    fill_color = "#13171e"
                elif val == Connect4Board.PLAYER_1:
                    fill_color = "#e74c3c"  # Rojo
                else:
                    fill_color = "#f1c40f"  # Amarillo

                outline_color = "#2ecc71" if (row, col) in win_set else "#0d1117"
                outline_w = 4 if (row, col) in win_set else 2

                c.create_oval(
                    cx - radius,
                    cy - radius,
                    cx + radius,
                    cy + radius,
                    fill=fill_color,
                    outline=outline_color,
                    width=outline_w,
                )

    # =========================================================================
    # PESTAÑA 2: LABORATORIO DE EXPERIMENTACIÓN AUTOMATIZADA Y GRÁFICAS
    # =========================================================================
    def _build_lab_tab(self):
        self.tab_lab.grid_columnconfigure(0, weight=2)
        self.tab_lab.grid_columnconfigure(1, weight=5)
        self.tab_lab.grid_rowconfigure(0, weight=1)

        # Panel izquierdo: configuración de experimentos
        ctrl = ctk.CTkFrame(self.tab_lab)
        ctrl.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)

        ctk.CTkLabel(
            ctrl,
            text="Configuración del Experimento",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 10))

        ctk.CTkLabel(ctrl, text="Tipo de estudio:").pack(anchor="w", padx=16)
        self.exp_mode_var = ctk.StringVar(value="Escalado de Simulaciones (N)")
        self.exp_mode_menu = ctk.CTkOptionMenu(
            ctrl,
            values=[
                "Escalado de Simulaciones (N)",
                "Duelo Directo (Config A vs Config B)",
            ],
            variable=self.exp_mode_var,
            command=self._toggle_exp_fields,
        )
        self.exp_mode_menu.pack(fill="x", padx=16, pady=(4, 12))

        # Frame dinámico según el tipo de experimento
        self.dynamic_exp_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        self.dynamic_exp_frame.pack(fill="x", padx=16)

        # Widgets para Modo 1 (Escalado)
        self.scaling_box = ctk.CTkFrame(self.dynamic_exp_frame, fg_color="transparent")
        ctk.CTkLabel(self.scaling_box, text="Niveles de simulaciones (separados por coma):").pack(anchor="w")
        self.sim_levels_entry = ctk.CTkEntry(self.scaling_box)
        self.sim_levels_entry.insert(0, "25, 100, 300, 700")
        self.sim_levels_entry.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(self.scaling_box, text="Rival de referencia:").pack(anchor="w")
        self.scaling_opp_var = ctk.StringVar(value="Agente Aleatorio (Random)")
        ctk.CTkOptionMenu(
            self.scaling_box,
            values=["Agente Aleatorio (Random)", "MCTS Base (N=100, C=1.41)"],
            variable=self.scaling_opp_var,
        ).pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(self.scaling_box, text="Partidas por nivel:").pack(anchor="w")
        self.games_per_level_entry = ctk.CTkEntry(self.scaling_box)
        self.games_per_level_entry.insert(0, "16")
        self.games_per_level_entry.pack(fill="x", pady=(2, 8))

        # Widgets para Modo 2 (Duelo directo)
        self.duel_box = ctk.CTkFrame(self.dynamic_exp_frame, fg_color="transparent")
        ctk.CTkLabel(self.duel_box, text="Agente A — Simulaciones (N) y Constante C:").pack(anchor="w")
        row_a = ctk.CTkFrame(self.duel_box, fg_color="transparent")
        row_a.pack(fill="x", pady=(2, 8))
        self.a_sims_entry = ctk.CTkEntry(row_a, placeholder_text="N (ej. 500)")
        self.a_sims_entry.insert(0, "500")
        self.a_sims_entry.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.a_c_entry = ctk.CTkEntry(row_a, placeholder_text="C (ej. 1.41)")
        self.a_c_entry.insert(0, "1.41")
        self.a_c_entry.pack(side="left", expand=True, fill="x", padx=(4, 0))

        ctk.CTkLabel(self.duel_box, text="Agente B — Simulaciones (N) y Constante C:").pack(anchor="w")
        row_b = ctk.CTkFrame(self.duel_box, fg_color="transparent")
        row_b.pack(fill="x", pady=(2, 8))
        self.b_sims_entry = ctk.CTkEntry(row_b, placeholder_text="N (ej. 100)")
        self.b_sims_entry.insert(0, "100")
        self.b_sims_entry.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.b_c_entry = ctk.CTkEntry(row_b, placeholder_text="C (ej. 1.41)")
        self.b_c_entry.insert(0, "1.41")
        self.b_c_entry.pack(side="left", expand=True, fill="x", padx=(4, 0))

        ctk.CTkLabel(self.duel_box, text="Número total de partidas (par para alternar salida):").pack(anchor="w")
        self.duel_games_entry = ctk.CTkEntry(self.duel_box)
        self.duel_games_entry.insert(0, "20")
        self.duel_games_entry.pack(fill="x", pady=(2, 8))

        self._toggle_exp_fields(self.exp_mode_var.get())

        self.run_exp_btn = ctk.CTkButton(
            ctrl,
            text="Ejecutar Experimento",
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_experiment,
        )
        self.run_exp_btn.pack(fill="x", padx=16, pady=(12, 8))

        self.exp_progress = ctk.CTkProgressBar(ctrl)
        self.exp_progress.set(0)
        self.exp_progress.pack(fill="x", padx=16, pady=(0, 6))

        self.exp_status_label = ctk.CTkLabel(ctrl, text="Listo para lanzar pruebas.", text_color="#9aa5b4")
        self.exp_status_label.pack(anchor="w", padx=16, pady=(0, 10))

        self.export_btn = ctk.CTkButton(
            ctrl,
            text="Exportar Gráfica PNG (results/)",
            fg_color="#2e7d32",
            hover_color="#1b5e20",
            state="disabled",
            command=self._export_chart,
        )
        self.export_btn.pack(fill="x", padx=16, pady=(0, 12))

        self.exp_summary_box = ctk.CTkTextbox(ctrl, height=180, font=ctk.CTkFont(family="Consolas", size=12))
        self.exp_summary_box.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Panel derecho: lienzo de Matplotlib
        self.chart_panel = ctk.CTkFrame(self.tab_lab)
        self.chart_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)

        self.placeholder_label = ctk.CTkLabel(
            self.chart_panel,
            text="Configura un experimento a la izquierda y pulsa 'Ejecutar Experimento'\npara generar las gráficas comparativas.",
            font=ctk.CTkFont(size=14),
            text_color="#9aa5b4",
        )
        self.placeholder_label.pack(expand=True)

    def _toggle_exp_fields(self, mode):
        self.scaling_box.pack_forget()
        self.duel_box.pack_forget()
        if mode.startswith("Escalado"):
            self.scaling_box.pack(fill="x")
        else:
            self.duel_box.pack(fill="x")

    def _start_experiment(self):
        if self.experiment_running:
            return

        mode = self.exp_mode_var.get()
        try:
            if mode.startswith("Escalado"):
                sim_list = [int(x.strip()) for x in self.sim_levels_entry.get().split(",") if x.strip()]
                games_per_level = int(self.games_per_level_entry.get())
                if not sim_list or any(s <= 0 for s in sim_list) or games_per_level <= 0:
                    raise ValueError
                opp_choice = self.scaling_opp_var.get()
                opp_cfg = (
                    {"type": "random"}
                    if opp_choice.startswith("Agente")
                    else {"type": "mcts", "simulations": 100, "c": 1.414}
                )
            else:
                a_sims = int(self.a_sims_entry.get())
                a_c = float(self.a_c_entry.get())
                b_sims = int(self.b_sims_entry.get())
                b_c = float(self.b_c_entry.get())
                duel_games = int(self.duel_games_entry.get())
                if min(a_sims, b_sims, duel_games) <= 0 or min(a_c, b_c) < 0:
                    raise ValueError
        except ValueError:
            self.exp_status_label.configure(text="Error: revisa que los números sean válidos.", text_color="#e74c3c")
            return

        self.experiment_running = True
        self.run_exp_btn.configure(state="disabled")
        self.export_btn.configure(state="disabled")
        self.exp_progress.set(0)
        self.exp_status_label.configure(text="Ejecutando simulaciones...", text_color="#3b8ed0")

        def progress_cb(pct):
            self.after(0, lambda: self.exp_progress.set(pct))

        def worker():
            t0 = time.perf_counter()
            if mode.startswith("Escalado"):
                data = run_simulation_scaling(
                    sim_list=sim_list,
                    games_per_level=games_per_level,
                    opponent_cfg=opp_cfg,
                    progress_callback=progress_cb,
                )
                elapsed = round(time.perf_counter() - t0, 2)
                self.after(0, lambda: self._on_scaling_done(data, opp_choice, elapsed))
            else:
                cfg_a = {"type": "mcts", "simulations": a_sims, "c": a_c}
                cfg_b = {"type": "mcts", "simulations": b_sims, "c": b_c}
                stats = run_matchup(cfg_a, cfg_b, num_games=duel_games, progress_callback=progress_cb)
                elapsed = round(time.perf_counter() - t0, 2)
                self.after(0, lambda: self._on_duel_done(stats, elapsed))

        threading.Thread(target=worker, daemon=True).start()

    def _on_scaling_done(self, data, opp_label, elapsed):
        self.experiment_running = False
        self.run_exp_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.exp_status_label.configure(text=f"Completado en {elapsed} s", text_color="#2ecc71")

        # Resumen numérico
        lines = [f"Rival: {opp_label}", "-" * 44, " Sims | Win%  | Draw% | Tiempo(ms) | Nodos"]
        for row in data:
            lines.append(
                f"{row['simulations']:>5} | {row['win_rate']:>4.1f}% | {row['draw_rate']:>4.1f}% | "
                f"{row['avg_time_ms']:>9.2f} | {row['avg_nodes']:>6.1f}"
            )
        self._set_exp_summary("\n".join(lines))

        # Gráfica doble: eficacia vs coste computacional
        fig = Figure(figsize=(7.5, 5.6), dpi=100)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212)

        sims = [str(r["simulations"]) for r in data]
        win_rates = [r["win_rate"] for r in data]
        times = [r["avg_time_ms"] for r in data]

        bars = ax1.bar(sims, win_rates, color="#2ecc71", width=0.45)
        ax1.set_ylim(0, 110)
        ax1.set_ylabel("Victorias (%)")
        ax1.set_title(f"Rendimiento MCTS según Simulaciones (vs {opp_label})")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        for bar, val in zip(bars, win_rates):
            ax1.text(bar.get_x() + bar.get_width() / 2, val + 2, f"{val:.1f}%", ha="center", fontsize=9)

        ax2.plot(sims, times, marker="o", color="#3b8ed0", linewidth=2.2)
        ax2.set_xlabel("Número de Simulaciones por Turno (N)")
        ax2.set_ylabel("Tiempo Medio / Jugada (ms)")
        ax2.set_title("Coste Temporal por Movimiento")
        ax2.grid(True, linestyle="--", alpha=0.4)
        for x_idx, val in enumerate(times):
            ax2.annotate(f"{val:.1f} ms", (x_idx, val), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=9)

        fig.tight_layout(pad=2.0)
        self._render_figure(fig)

    def _on_duel_done(self, stats, elapsed):
        self.experiment_running = False
        self.run_exp_btn.configure(state="normal")
        self.export_btn.configure(state="normal")
        self.exp_status_label.configure(text=f"Duelo completado en {elapsed} s", text_color="#2ecc71")

        lines = [
            f"Agente A: {stats['agent_a_name']}",
            f"Agente B: {stats['agent_b_name']}",
            f"Partidas: {stats['games']} (duración media: {stats['avg_moves']} jugadas)",
            "-" * 44,
            f"Victorias A : {stats['a_wins']} ({stats['a_win_rate']}%)",
            f"Victorias B : {stats['b_wins']} ({stats['b_win_rate']}%)",
            f"Empates     : {stats['draws']} ({stats['draw_rate']}%)",
            "-" * 44,
            f"Tiempo medio A: {stats['a_avg_time_ms']} ms ({stats['a_avg_nodes']} nodos)",
            f"Tiempo medio B: {stats['b_avg_time_ms']} ms ({stats['b_avg_nodes']} nodos)",
        ]
        self._set_exp_summary("\n".join(lines))

        fig = Figure(figsize=(7.5, 5.6), dpi=100)
        ax1 = fig.add_subplot(121)
        ax2 = fig.add_subplot(122)

        categories = ["Agente A", "Empates", "Agente B"]
        values = [stats["a_win_rate"], stats["draw_rate"], stats["b_win_rate"]]
        colors = ["#2ecc71", "#95a5a6", "#e67e22"]

        bars = ax1.bar(categories, values, color=colors, width=0.5)
        ax1.set_ylim(0, 110)
        ax1.set_ylabel("Porcentaje de Partidas (%)")
        ax1.set_title("Resultado del Enfrentamiento")
        ax1.grid(axis="y", linestyle="--", alpha=0.4)
        for bar, val in zip(bars, values):
            ax1.text(bar.get_x() + bar.get_width() / 2, val + 2, f"{val:.1f}%", ha="center", fontsize=9)

        agents = ["Agente A", "Agente B"]
        avg_times = [stats["a_avg_time_ms"], stats["b_avg_time_ms"]]
        bars2 = ax2.bar(agents, avg_times, color=["#3b8ed0", "#9b59b6"], width=0.45)
        ax2.set_ylabel("Tiempo Medio por Turno (ms)")
        ax2.set_title("Tiempo de Respuesta")
        ax2.grid(axis="y", linestyle="--", alpha=0.4)
        for bar, val in zip(bars2, avg_times):
            ax2.text(bar.get_x() + bar.get_width() / 2, val + 1, f"{val:.1f} ms", ha="center", fontsize=9)

        fig.suptitle(f"{stats['agent_a_name']}  vs  {stats['agent_b_name']}", fontsize=11, fontweight="bold")
        fig.tight_layout(pad=2.0)
        self._render_figure(fig)

    def _set_exp_summary(self, text):
        self.exp_summary_box.configure(state="normal")
        self.exp_summary_box.delete("1.0", "end")
        self.exp_summary_box.insert("1.0", text)
        self.exp_summary_box.configure(state="disabled")

    def _render_figure(self, fig):
        if self.placeholder_label is not None:
            self.placeholder_label.destroy()
            self.placeholder_label = None
        if self.canvas_widget is not None:
            self.canvas_widget.get_tk_widget().destroy()

        self.current_figure = fig
        self.canvas_widget = FigureCanvasTkAgg(fig, master=self.chart_panel)
        self.canvas_widget.draw()
        self.canvas_widget.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def _export_chart(self):
        if self.current_figure is None:
            return
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join("results", f"mcts_experiment_{timestamp}.png")
        self.current_figure.savefig(filepath, dpi=200)
        self.exp_status_label.configure(text=f"Guardada en {filepath}", text_color="#2ecc71")


if __name__ == "__main__":
    app = Connect4MCTSApp()
    app.mainloop()