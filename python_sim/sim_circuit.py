#!/usr/bin/env python3
"""
    FILE: sim_circuit.py
    DESC: Simulador interativo 2D do circuito do Lab 2 controlado pelo teclado
    AUTHOR: Jose Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
"""

from __future__ import annotations

import bisect
import math
from pathlib import Path
import sys
import time
import tkinter as tk
from typing import List, Sequence, Tuple

# Parametros fisicos e nominais do Laboratorio 2
ROBOT_DIAMETER_M = 0.30
ROBOT_RADIUS_M = 0.15
PHYSICS_DT_SEC = 0.05
PILOT_DT_SEC = 0.03
SIM_HORIZON_SEC = 20.0
SIM_SWITCH_TIME_SEC = 10.0
CONTROL_V_MPS = 1.0
CONTROL_OMEGA_RADPS = 0.2 * math.pi

DEFAULT_LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "simulation_log.txt"
SampleRow = Tuple[float, float, float, float, float, float]


def generate_fallback_trajectory() -> List[SampleRow]:
    """
    Reproduz exatamente a cinemática discreta multi-taxa do Lab 2
    de forma 100% independente do codigo em C.
    Retorna lista de tuplas: (t, v, omega, yf_x, yf_y, yf_theta).
    """
    xc = 0.0
    yc = 0.0
    theta = 0.0

    yf_x = xc + ROBOT_RADIUS_M * math.cos(theta)
    yf_y = yc + ROBOT_RADIUS_M * math.sin(theta)

    rows: List[SampleRow] = []
    next_physics_t = PHYSICS_DT_SEC
    u_v = CONTROL_V_MPS
    u_omega = -CONTROL_OMEGA_RADPS

    max_pilot_steps = 668
    for step in range(max_pilot_steps):
        t_sec = step * PILOT_DT_SEC

        # Avanca os passos de 50 ms que ocorreram ate t_sec
        while next_physics_t <= t_sec + 1e-9:
            xc += math.sin(theta) * u_v * PHYSICS_DT_SEC
            yc += math.cos(theta) * u_v * PHYSICS_DT_SEC
            theta += u_omega * PHYSICS_DT_SEC
            yf_x = xc + ROBOT_RADIUS_M * math.cos(theta)
            yf_y = yc + ROBOT_RADIUS_M * math.sin(theta)
            next_physics_t += PHYSICS_DT_SEC

        if t_sec < SIM_SWITCH_TIME_SEC:
            u_v = CONTROL_V_MPS
            u_omega = -CONTROL_OMEGA_RADPS
        else:
            u_v = CONTROL_V_MPS
            u_omega = +CONTROL_OMEGA_RADPS

        rows.append((t_sec, u_v, u_omega, yf_x, yf_y, theta))

    return rows


def load_or_generate_trajectory(log_path: Path) -> Tuple[List[SampleRow], str]:
    """Carrega a telemetria se existir ou gera internamente de forma autonoma."""
    if log_path.is_file():
        try:
            rows: List[SampleRow] = []
            with log_path.open("r", encoding="utf-8") as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) >= 6:
                        rows.append((
                            float(parts[0]),
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3]),
                            float(parts[4]),
                            float(parts[5]),
                        ))
            if len(rows) > 10:
                return rows, f"Telemetria C ({log_path.name})"
        except Exception:
            pass
    return generate_fallback_trajectory(), "Modelo Cinemático Autônomo (Lab 2)"


def compute_tangent_angles(x: Sequence[float], y: Sequence[float]) -> List[float]:
    """
    Mantido para compatibilidade com helpers e setas de fundo,
    mas a orientacao do robo agora utiliza rigorosamente o angulo theta(t) da cinemática real.
    """
    n = len(x)
    headings = [0.0] * n
    last_angle = math.pi / 2.0

    for i in range(n):
        found = False
        for j in range(i + 1, min(i + 8, n)):
            dx = x[j] - x[i]
            dy = y[j] - y[i]
            if math.hypot(dx, dy) > 1e-5:
                last_angle = math.atan2(dy, dx)
                found = True
                break
        if not found and i > 0:
            for j in range(i - 1, max(-1, i - 8), -1):
                dx = x[i] - x[j]
                dy = y[i] - y[j]
                if math.hypot(dx, dy) > 1e-5:
                    last_angle = math.atan2(dy, dx)
                    break
        headings[i] = last_angle

    return headings


class CircuitSimulatorApp:
    """Interface grafica interativa (Tkinter Canvas) para o circuito do Lab 2."""

    def __init__(self, root: tk.Tk, data: Sequence[SampleRow], source_label: str) -> None:
        self.root = root
        self.root.title("Lab 2 (FTL066) — Simulador Interativo do Robô Diferencial")
        self.root.geometry("1040x720")
        self.root.minsize(860, 620)
        self.root.configure(bg="#0f172a")

        self.source_label = source_label
        self.t = [row[0] for row in data]
        self.v = [row[1] for row in data]
        self.omega = [row[2] for row in data]
        self.yf_x = [row[3] for row in data]
        self.yf_y = [row[4] for row in data]
        self.yf_theta = [row[5] for row in data]
        self.headings = compute_tangent_angles(self.yf_x, self.yf_y)
        self.num_samples = len(self.t)

        # Centro de massa real deduzido exatamente da equacao da frente:
        # yf_x = xc + 0.15*cos(theta) => xc = yf_x - 0.15*cos(theta)
        # yf_y = yc + 0.15*sin(theta) => yc = yf_y - 0.15*sin(theta)
        self.xc = [
            self.yf_x[i] - ROBOT_RADIUS_M * math.cos(self.yf_theta[i])
            for i in range(self.num_samples)
        ]
        self.yc = [
            self.yf_y[i] - ROBOT_RADIUS_M * math.sin(self.yf_theta[i])
            for i in range(self.num_samples)
        ]

        # Estado de reproducao:
        # direction: 0 = parado, +1 = avancando (Seta Direita), -1 = voltando (Seta Esquerda)
        self.direction: int = 0
        self.current_time: float = 0.0
        self.max_time: float = float(self.t[-1])
        self.speed_multiplier: float = 1.0
        self.visual_scale: float = 1.0  # 1.0 = Escala 100% fisica real e geometricamente exata
        self.last_tick: float = time.perf_counter()

        # Limites do mundo em metros (com margem)
        self.world_xmin = -3.65
        self.world_xmax = +3.45
        self.world_ymin = -2.05
        self.world_ymax = +2.15

        self._build_ui()
        self._bind_keys()
        self._schedule_loop()

    def _build_ui(self) -> None:
        """Constroi o cabecalho, o canvas 2D e a barra de controles."""
        header = tk.Frame(self.root, bg="#1e293b", padx=16, pady=10)
        header.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="Simulação Interativa — Robô Móvel Diferencial (Circuito Lab 2)",
            fg="#f8fafc",
            bg="#1e293b",
            font=("DejaVu Sans", 13, "bold"),
        )
        title_lbl.pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            header,
            text="⏸ PAUSADO (Pressione → para iniciar)",
            fg="#fbbf24",
            bg="#0f172a",
            font=("DejaVu Sans Mono", 10, "bold"),
            padx=12,
            pady=4,
        )
        self.status_badge.pack(side=tk.RIGHT)

        # Canvas principal
        self.canvas = tk.Canvas(
            self.root,
            bg="#0b1120",
            highlightthickness=0,
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Painel inferior com botoes e instrucoes
        footer = tk.Frame(self.root, bg="#1e293b", padx=14, pady=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X)

        btn_style = {
            "font": ("DejaVu Sans", 10, "bold"),
            "bd": 0,
            "padx": 14,
            "pady": 6,
            "cursor": "hand2",
        }

        btn_back = tk.Button(
            footer,
            text="◀ Voltar (Seta Esquerda)",
            bg="#ea580c",
            fg="#ffffff",
            activebackground="#c2410c",
            activeforeground="#ffffff",
            command=self.start_backward,
            **btn_style,
        )
        btn_back.pack(side=tk.LEFT, padx=(0, 8))

        btn_pause = tk.Button(
            footer,
            text="⏯ Pausar (Espaço)",
            bg="#475569",
            fg="#ffffff",
            activebackground="#334155",
            activeforeground="#ffffff",
            command=self.toggle_pause,
            **btn_style,
        )
        btn_pause.pack(side=tk.LEFT, padx=8)

        btn_forward = tk.Button(
            footer,
            text="▶ Iniciar / Seguir Lab 2 (Seta Direita)",
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            command=self.start_forward,
            **btn_style,
        )
        btn_forward.pack(side=tk.LEFT, padx=8)

        btn_reset = tk.Button(
            footer,
            text="↺ Início (R)",
            bg="#334155",
            fg="#e2e8f0",
            activebackground="#1e293b",
            activeforeground="#ffffff",
            command=self.reset_sim,
            **btn_style,
        )
        btn_reset.pack(side=tk.LEFT, padx=8)

        help_lbl = tk.Label(
            footer,
            text="Atalhos: [→] Segue Lab 2 (Anti-horário → Horário)   [←] Volta   [Espaço] Pausa   [↑/↓] Velocidade   [R] Reset",
            fg="#94a3b8",
            bg="#1e293b",
            font=("DejaVu Sans", 9),
        )
        help_lbl.pack(side=tk.RIGHT)

    def _bind_keys(self) -> None:
        """Associa as teclas de controle."""
        self.root.bind("<Right>", lambda _e: self.start_forward())
        self.root.bind("<Left>", lambda _e: self.start_backward())
        self.root.bind("<space>", lambda _e: self.toggle_pause())
        self.root.bind("<Up>", lambda _e: self.change_speed(1.5))
        self.root.bind("<Down>", lambda _e: self.change_speed(1.0 / 1.5))
        self.root.bind("r", lambda _e: self.reset_sim())
        self.root.bind("R", lambda _e: self.reset_sim())
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.root.bind("q", lambda _e: self.root.destroy())

    def start_forward(self) -> None:
        """Inicia ou retoma a trajetoria no sentido normal do Lab 2 (iniciando anti-horario)."""
        if self.current_time >= self.max_time - 1e-4:
            self.current_time = 0.0
        self.direction = +1

    def start_backward(self) -> None:
        """Reverte o movimento fazendo o robo voltar pelo circuito ate t = 0."""
        if self.current_time <= 1e-4:
            self.current_time = self.max_time
        self.direction = -1

    def toggle_pause(self) -> None:
        """Pausa ou retoma o movimento."""
        if self.direction != 0:
            self.direction = 0
        else:
            self.direction = +1

    def reset_sim(self) -> None:
        """Posiciona o robo de volta no inicio (t = 0 s) e pausa."""
        self.current_time = 0.0
        self.direction = 0

    def change_speed(self, factor: float) -> None:
        """Ajusta o multiplicador de velocidade da simulacao."""
        new_speed = self.speed_multiplier * factor
        self.speed_multiplier = max(0.25, min(8.0, round(new_speed * 4.0) / 4.0))

    def _world_to_screen(
        self,
        wx: float,
        wy: float,
        canvas_w: int,
        canvas_h: int,
    ) -> Tuple[float, float, float]:
        """Converte coordenadas (x, y) em metros para pixels mantendo proporcao 1:1."""
        pad_left = 65.0
        pad_right = 270.0  # Espaco reservado para o painel de telemetria lateral
        pad_top = 45.0
        pad_bottom = 55.0

        avail_w = max(200.0, canvas_w - pad_left - pad_right)
        avail_h = max(200.0, canvas_h - pad_top - pad_bottom)

        span_x = self.world_xmax - self.world_xmin
        span_y = self.world_ymax - self.world_ymin

        scale = min(avail_w / span_x, avail_h / span_y)

        cx_world = 0.5 * (self.world_xmin + self.world_xmax)
        cy_world = 0.5 * (self.world_ymin + self.world_ymax)

        cx_screen = pad_left + 0.5 * avail_w
        cy_screen = pad_top + 0.5 * avail_h

        sx = cx_screen + (wx - cx_world) * scale
        sy = cy_screen - (wy - cy_world) * scale
        return sx, sy, scale

    def _get_current_index(self) -> int:
        """Retorna o indice da amostra mais proxima de current_time."""
        idx = bisect.bisect_right(self.t, self.current_time) - 1
        return max(0, min(self.num_samples - 1, idx))

    def _draw_direction_arrow(
        self,
        idx: int,
        color: str,
        cw: int,
        ch: int,
    ) -> None:
        """Desenha uma pequena seta indicando o sentido nominal do circuito."""
        if idx < 0 or idx >= self.num_samples:
            return
        sx, sy, _ = self._world_to_screen(self.yf_x[idx], self.yf_y[idx], cw, ch)
        ang = self.headings[idx]
        size = 9.0
        tip_x = sx + size * math.cos(ang)
        tip_y = sy - size * math.sin(ang)
        left_x = sx + size * 0.75 * math.cos(ang + 2.5)
        left_y = sy - size * 0.75 * math.sin(ang + 2.5)
        right_x = sx + size * 0.75 * math.cos(ang - 2.5)
        right_y = sy - size * 0.75 * math.sin(ang - 2.5)
        self.canvas.create_polygon(
            tip_x, tip_y, left_x, left_y, right_x, right_y,
            fill=color,
            outline="",
        )

    def _render(self) -> None:
        """Renderiza o grid, o circuito completo, o robo com bolinha frontal e o HUD."""
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return

        # 1. Grid cartesiano em metros
        for gx in range(-3, 4):
            x0, y0, _ = self._world_to_screen(float(gx), self.world_ymin, cw, ch)
            x1, y1, _ = self._world_to_screen(float(gx), self.world_ymax, cw, ch)
            line_color = "#334155" if gx == 0 else "#1e293b"
            self.canvas.create_line(x0, y0, x1, y1, fill=line_color, dash=(3, 3) if gx != 0 else None)
            self.canvas.create_text(
                x0, y0 + 16,
                text=f"{gx} m",
                fill="#64748b",
                font=("DejaVu Sans Mono", 9),
            )

        for gy_half in range(-3, 4):
            gy = gy_half * 0.5
            x0, y0, _ = self._world_to_screen(self.world_xmin, gy, cw, ch)
            x1, y1, _ = self._world_to_screen(self.world_xmax, gy, cw, ch)
            line_color = "#334155" if abs(gy) < 1e-6 else "#1e293b"
            self.canvas.create_line(x0, y0, x1, y1, fill=line_color, dash=(3, 3) if abs(gy) > 1e-6 else None)
            self.canvas.create_text(
                x0 - 28, y0,
                text=f"{gy:+.1f} m" if abs(gy) > 1e-6 else "0.0 m",
                fill="#64748b",
                font=("DejaVu Sans Mono", 9),
            )

        # 2. Circuito fixo de fundo (Fase 1 Azul: Anti-horario | Fase 2 Laranja: Horario)
        pts_phase1: List[float] = []
        pts_phase2: List[float] = []

        for i in range(self.num_samples):
            sx, sy, _ = self._world_to_screen(self.yf_x[i], self.yf_y[i], cw, ch)
            if self.t[i] < SIM_SWITCH_TIME_SEC:
                pts_phase1.extend([sx, sy])
            else:
                pts_phase2.extend([sx, sy])

        if len(pts_phase1) >= 4:
            self.canvas.create_line(
                *pts_phase1,
                fill="#1e40af",
                width=3,
                dash=(6, 4),
                smooth=True,
            )
        if len(pts_phase2) >= 4:
            self.canvas.create_line(
                *pts_phase2,
                fill="#9a3412",
                width=3,
                dash=(6, 4),
                smooth=True,
            )

        # Setas indicadoras do sentido no circuito de fundo
        for frac in (0.12, 0.37, 0.62, 0.87):
            idx1 = int(frac * (self.num_samples // 2))
            idx2 = (self.num_samples // 2) + int(frac * (self.num_samples // 2))
            self._draw_direction_arrow(idx1, "#3b82f6", cw, ch)
            self._draw_direction_arrow(min(self.num_samples - 1, idx2), "#f97316", cw, ch)

        # 3. Rastro ja percorrido ate o tempo atual t
        curr_idx = self._get_current_index()
        if curr_idx >= 1:
            active_phase1: List[float] = []
            active_phase2: List[float] = []
            for i in range(curr_idx + 1):
                sx, sy, _ = self._world_to_screen(self.yf_x[i], self.yf_y[i], cw, ch)
                if self.t[i] < SIM_SWITCH_TIME_SEC:
                    active_phase1.extend([sx, sy])
                else:
                    if not active_phase2 and active_phase1:
                        active_phase2.extend(active_phase1[-2:])
                    active_phase2.extend([sx, sy])

            if len(active_phase1) >= 4:
                self.canvas.create_line(*active_phase1, fill="#38bdf8", width=4, smooth=True)
            if len(active_phase2) >= 4:
                self.canvas.create_line(*active_phase2, fill="#fb923c", width=4, smooth=True)

        # 4. Ponto de Inicio / Transicao / Fim (0.15, 0.00) m
        start_sx, start_sy, scale = self._world_to_screen(self.yf_x[0], self.yf_y[0], cw, ch)
        self.canvas.create_oval(
            start_sx - 6, start_sy - 6, start_sx + 6, start_sy + 6,
            fill="#22c55e",
            outline="#dcfce7",
            width=2,
        )
        self.canvas.create_text(
            start_sx + 58, start_sy + 18,
            text="Início (0.15, 0.00)",
            fill="#4ade80",
            font=("DejaVu Sans", 9, "bold"),
        )

        # 5. Desenho Fisico 100% Realista do Robo:
        # - Centro geometrico do chassi: (xc, yc)
        # - Orientacao fisica real: theta(t)
        # - Frente do robo (nariz): exatamente yf_x = xc + 0.15*cos(theta), yf_y = yc + 0.15*sin(theta)
        xc_world = self.xc[curr_idx]
        yc_world = self.yc[curr_idx]
        yf_x_world = self.yf_x[curr_idx]
        yf_y_world = self.yf_y[curr_idx]
        theta_val = self.yf_theta[curr_idx]

        # Coordenadas na tela
        csx, csy, _ = self._world_to_screen(xc_world, yc_world, cw, ch)
        fsx, fsy, _ = self._world_to_screen(yf_x_world, yf_y_world, cw, ch)
        robot_px_radius = ROBOT_RADIUS_M * scale * self.visual_scale

        # Corpo circular do robo (centralizado no centro de massa xc, yc)
        body_fill = "#0369a1" if self.t[curr_idx] < SIM_SWITCH_TIME_SEC else "#c2410c"
        self.canvas.create_oval(
            csx - robot_px_radius,
            csy - robot_px_radius,
            csx + robot_px_radius,
            csy + robot_px_radius,
            fill=body_fill,
            outline="#f8fafc",
            width=2.5,
        )

        # Rodas tracionadas laterais (perpendiculares ao eixo do nariz: theta +- pi/2)
        wheel_w = max(4.0, robot_px_radius * 0.35)
        wheel_len = max(8.0, robot_px_radius * 0.70)
        for side in (+1, -1):
            wheel_ang = theta_val + side * (math.pi / 2.0)
            wx = csx + (robot_px_radius * 0.88) * math.cos(wheel_ang)
            wy = csy - (robot_px_radius * 0.88) * math.sin(wheel_ang)
            # orienta a roda na direcao de rolamento (perpendicular ao raio)
            dx_w = (wheel_len * 0.5) * math.sin(wheel_ang)
            dy_w = (wheel_len * 0.5) * math.cos(wheel_ang)
            self.canvas.create_line(
                wx - dx_w, wy - dy_w, wx + dx_w, wy + dy_w,
                fill="#0f172a",
                width=wheel_w,
            )

        # Centro de massa (ponto central)
        cm_r = max(2.5, robot_px_radius * 0.15)
        self.canvas.create_oval(
            csx - cm_r, csy - cm_r, csx + cm_r, csy + cm_r,
            fill="#ffffff",
            outline="#0f172a",
            width=1,
        )

        # Eixo interno ligando o centro de massa ate o ponto frontal
        self.canvas.create_line(
            csx, csy, fsx, fsy,
            fill="#facc15",
            width=2.5,
        )

        # Bolinha identificadora da FRENTE do robô (ponto amostrado yf_x, yf_y)
        ball_r = max(4.5, robot_px_radius * 0.28)
        self.canvas.create_oval(
            fsx - ball_r,
            fsy - ball_r,
            fsx + ball_r,
            fsy + ball_r,
            fill="#facc15",
            outline="#0f172a",
            width=1.8,
        )

        # 6. Painel lateral de Telemetria (HUD)
        self._draw_hud(curr_idx, cw, ch)

    def _draw_hud(self, idx: int, cw: int, ch: int) -> None:
        """Desenha o painel lateral com dados de tempo real e legenda."""
        panel_x0 = cw - 245
        panel_y0 = 20
        panel_x1 = cw - 14
        panel_y1 = ch - 20

        self.canvas.create_rectangle(
            panel_x0, panel_y0, panel_x1, panel_y1,
            fill="#1e293b",
            outline="#334155",
            width=1.5,
        )

        t_val = self.t[idx]
        v_val = self.v[idx]
        w_val = self.omega[idx]
        x_val = self.yf_x[idx]
        y_val = self.yf_y[idx]
        th_val = self.yf_theta[idx]
        phase_str = "Fase 1: Anti-horário (0–10s)" if t_val < SIM_SWITCH_TIME_SEC else "Fase 2: Horário (10–20s)"
        phase_color = "#38bdf8" if t_val < SIM_SWITCH_TIME_SEC else "#fb923c"

        tx = panel_x0 + 14
        ty = panel_y0 + 20

        self.canvas.create_text(
            tx, ty, anchor="nw",
            text="TELEMETRIA LAB 2",
            fill="#f8fafc",
            font=("DejaVu Sans", 10, "bold"),
        )
        ty += 24
        self.canvas.create_text(
            tx, ty, anchor="nw",
            text=phase_str,
            fill=phase_color,
            font=("DejaVu Sans", 9, "bold"),
        )

        ty += 28
        metrics = [
            ("Tempo t", f"{t_val:6.2f} / {self.max_time:.1f} s"),
            ("Amostra k", f"{idx:4d} / {self.num_samples - 1}"),
            ("Vel. Linear v", f"{v_val:+6.2f} m/s"),
            ("Vel. Angular ω", f"{w_val:+6.3f} rad/s"),
            ("Frente yf_x", f"{x_val:+6.3f} m"),
            ("Frente yf_y", f"{y_val:+6.3f} m"),
            ("Ângulo θ(t)", f"{th_val:+6.3f} rad"),
            ("Velocidade Sim", f"{self.speed_multiplier:.2f}x"),
        ]

        for label, val in metrics:
            self.canvas.create_text(
                tx, ty, anchor="nw",
                text=f"{label}:",
                fill="#94a3b8",
                font=("DejaVu Sans", 9),
            )
            self.canvas.create_text(
                panel_x1 - 14, ty, anchor="ne",
                text=val,
                fill="#f1f5f9",
                font=("DejaVu Sans Mono", 9, "bold"),
            )
            ty += 22

        # Barra de progresso temporal
        ty += 10
        bar_w = (panel_x1 - panel_x0) - 28
        progress = max(0.0, min(1.0, self.current_time / self.max_time))
        self.canvas.create_rectangle(
            tx, ty, tx + bar_w, ty + 12,
            fill="#0f172a",
            outline="#475569",
        )
        if progress > 0:
            self.canvas.create_rectangle(
                tx, ty, tx + bar_w * progress, ty + 12,
                fill=phase_color,
                outline="",
            )

        # Legenda do Circuito e do Robo
        ty += 32
        self.canvas.create_text(
            tx, ty, anchor="nw",
            text="LEGENDA",
            fill="#f8fafc",
            font=("DejaVu Sans", 10, "bold"),
        )
        ty += 22
        legend_items = [
            ("#38bdf8", "0 ≤ t < 10s (ω = -0.2π rad/s)"),
            ("#fb923c", "10 ≤ t ≤ 20s (ω = +0.2π rad/s)"),
            ("#22c55e", "Origem yf(0) = (0.15, 0.00) m"),
            ("#ffffff", "Ponto Branco = Centro de Massa (xc, yc)"),
            ("#facc15", "Bolinha Amarela = Frente yf(t) (Nariz)"),
            ("#0f172a", "Barras Pretas = Rodas Tracionadas"),
        ]
        for color, desc in legend_items:
            self.canvas.create_oval(tx, ty + 3, tx + 10, ty + 13, fill=color, outline="")
            self.canvas.create_text(
                tx + 18, ty, anchor="nw",
                text=desc,
                fill="#cbd5e1",
                font=("DejaVu Sans", 8),
            )
            ty += 20

        ty += 12
        self.canvas.create_text(
            tx, ty, anchor="nw",
            text=f"Fonte: {self.source_label}",
            fill="#64748b",
            font=("DejaVu Sans", 8),
        )

    def _update_status_badge(self) -> None:
        """Atualiza o indicador visual de estado no topo."""
        if self.direction > 0:
            self.status_badge.configure(
                text=f"▶ SEGUINDO LAB 2 ({self.speed_multiplier:.2f}x) — Seta Esquerda volta",
                fg="#38bdf8",
            )
        elif self.direction < 0:
            self.status_badge.configure(
                text=f"◀ VOLTANDO ({self.speed_multiplier:.2f}x) — Seta Direita avança",
                fg="#fb923c",
            )
        else:
            self.status_badge.configure(
                text="⏸ PAUSADO — [→] Seguir Lab 2  |  [←] Voltar",
                fg="#fbbf24",
            )

    def _schedule_loop(self) -> None:
        """Loop de atualizacao a ~60 FPS."""
        now = time.perf_counter()
        dt = min(0.1, now - self.last_tick)
        self.last_tick = now

        if self.direction != 0:
            self.current_time += self.direction * dt * self.speed_multiplier
            if self.current_time >= self.max_time:
                self.current_time = self.max_time
                self.direction = 0
            elif self.current_time <= 0.0:
                self.current_time = 0.0
                self.direction = 0

        self._update_status_badge()
        self._render()
        self.root.after(16, self._schedule_loop)


def main() -> int:
    """Ponto de entrada do simulador interativo."""
    data, source_label = load_or_generate_trajectory(DEFAULT_LOG_PATH)

    if "--check" in sys.argv:
        xs = [row[3] for row in data]
        ys = [row[4] for row in data]
        headings = compute_tangent_angles(xs, ys)
        print(f"[OK] Fonte carregada: {source_label}")
        print(f"[OK] Amostras: {len(data)} | Horizonte: [{data[0][0]:.2f}s, {data[-1][0]:.2f}s]")
        print(f"[OK] Pose inicial: ({data[0][3]:.3f}, {data[0][4]:.3f}) m | Heading inicial: {math.degrees(headings[0]):.1f} deg")
        return 0

    root = tk.Tk()
    _app = CircuitSimulatorApp(root, data, source_label)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

