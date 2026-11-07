#!/usr/bin/env python3
"""
    FILE: plot_results.py
    DESC: Pos-processamento, calculo de jitter e geracao de graficos da simulacao
    AUTHOR: Jose Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
    NOTE: Feito com Auxilio do google antigravity com modelos gemini flash
"""

import argparse
from pathlib import Path
import sys

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as err:
    print("\n[ERRO DE DEPENDÊNCIA] Não foi possível importar os pacotes necessários para gerar os gráficos.", file=sys.stderr)
    print(f"Detalhe: {err}\n", file=sys.stderr)
    print("Para instalar as dependências necessárias no Python, execute:", file=sys.stderr)
    print("  pip install numpy matplotlib", file=sys.stderr)
    print("Ou no Linux (Debian/Ubuntu/Mint):", file=sys.stderr)
    print("  sudo apt install python3-numpy python3-matplotlib", file=sys.stderr)
    print("Ou no Fedora/RHEL:", file=sys.stderr)
    print("  sudo dnf install python3-numpy python3-matplotlib\n", file=sys.stderr)
    sys.exit(1)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "data" / "simulation_log.txt"
OUTPUT_DIR = PROJECT_ROOT / "data"


def load_telemetry(log_path: Path) -> np.ndarray:
    """Loads and validates the tab-separated telemetry log file."""
    if not log_path.is_file():
        raise FileNotFoundError(
            f"Telemetry log file not found: {log_path}. "
            "Run './build/robot_sim' first."
        )

    data = np.loadtxt(log_path, delimiter="\t", comments="#")
    if data.ndim != 2 or data.shape[1] < 6:
        raise ValueError(
            f"Unexpected data shape {data.shape} in {log_path}; "
            "expected at least 6 columns (t, v, omega, yf_x, yf_y, yf_theta)."
        )
    return data


def _format_tag(scenario_label: str) -> str:
    return f" [{scenario_label}]" if scenario_label else ""


def plot_trajectory_2d(
    t: np.ndarray,
    yf_x: np.ndarray,
    yf_y: np.ndarray,
    out_path: Path,
    scenario_label: str = "",
) -> None:
    """Plots the 2D plane trajectory (yf_x vs yf_y) of the robot front point."""
    fig, ax = plt.subplots(figsize=(8.5, 7.2), dpi=150)

    mask_phase1 = t < 10.0
    mask_phase2 = t >= 10.0

    ax.plot(
        yf_x[mask_phase1],
        yf_y[mask_phase1],
        color="#1f77b4",
        linewidth=2.2,
        marker=".",
        markersize=3.5,
        label=r"$0 \leq t < 10\,$s ($v=1\,$m/s, $\omega = -0.2\pi\,$rad/s)",
    )
    ax.plot(
        yf_x[mask_phase2],
        yf_y[mask_phase2],
        color="#ff7f0e",
        linewidth=2.2,
        marker=".",
        markersize=3.5,
        label=r"$10 \leq t \leq 20\,$s ($v=1\,$m/s, $\omega = +0.2\pi\,$rad/s)",
    )

    ax.scatter(
        yf_x[0],
        yf_y[0],
        color="#2ca02c",
        s=90,
        zorder=5,
        label=f"Início/Transição/Fim ({yf_x[0]:.2f}, {yf_y[0]:.2f}) m",
    )

    tag = _format_tag(scenario_label)
    ax.set_title(
        f"Trajetória no Plano XY da Frente do Robô $y_f(t)$ ($t \\in [0, 20]\\,$s){tag}",
        fontsize=11.5,
        fontweight="bold",
    )
    ax.set_xlabel("Posição $y_{f,x}$ [m]", fontsize=11)
    ax.set_ylabel("Posição $y_{f,y}$ [m]", fontsize=11)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(loc="best", fontsize=9.5)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_states_and_inputs(
    t: np.ndarray,
    v: np.ndarray,
    omega: np.ndarray,
    yf_x: np.ndarray,
    yf_y: np.ndarray,
    yf_theta: np.ndarray,
    out_path: Path,
    scenario_label: str = "",
) -> None:
    """Plots sampled output y(t) and control input u(t) over t in [0, 20] s."""
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), dpi=150, sharex=True)
    tag = _format_tag(scenario_label)

    # Subplot 1: Sampled positions yf_x(t) and yf_y(t)
    axes[0].step(
        t,
        yf_x,
        where="post",
        color="#1f77b4",
        linewidth=1.8,
        label="$y_{f,x}(t)$ amostrado (30 ms) [m]",
    )
    axes[0].step(
        t,
        yf_y,
        where="post",
        color="#d62728",
        linewidth=1.8,
        label="$y_{f,y}(t)$ amostrado (30 ms) [m]",
    )
    axes[0].axvline(10.0, color="gray", linestyle=":", alpha=0.8)
    axes[0].set_ylabel("Posição [m]", fontsize=10)
    axes[0].set_title(
        f"Item 5 do Roteiro: Saída $y(t)$ Amostrada para $t \\in [0, 20]\\,$s{tag}",
        fontsize=12,
        fontweight="bold",
    )
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(loc="upper right", fontsize=9.5)

    # Subplot 2: Sampled orientation theta(t)
    axes[1].step(
        t,
        yf_theta,
        where="post",
        color="#2ca02c",
        linewidth=1.8,
        label=r"Orientação $\theta(t)$ amostrada (30 ms) [rad]",
    )
    axes[1].axvline(10.0, color="gray", linestyle=":", alpha=0.8)
    axes[1].set_ylabel(r"$\theta(t)$ [rad]", fontsize=10)
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend(loc="upper right", fontsize=9.5)

    # Subplot 3: Control inputs v(t) and omega(t)
    axes[2].step(
        t,
        v,
        where="post",
        color="#9467bd",
        linewidth=1.8,
        label="Velocidade Linear $v(t)$ [m/s]",
    )
    axes[2].step(
        t,
        omega,
        where="post",
        color="#ff7f0e",
        linewidth=1.8,
        label=r"Velocidade Angular $\omega(t)$ [rad/s]",
    )
    axes[2].axvline(10.0, color="gray", linestyle=":", alpha=0.8)
    axes[2].set_xlabel("Tempo $t$ [s]", fontsize=11)
    axes[2].set_ylabel("Entrada $u(t)$", fontsize=10)
    axes[2].grid(True, linestyle="--", alpha=0.6)
    axes[2].legend(loc="lower right", fontsize=9.5)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_combined_dashboard(
    t: np.ndarray,
    v: np.ndarray,
    omega: np.ndarray,
    yf_x: np.ndarray,
    yf_y: np.ndarray,
    yf_theta: np.ndarray,
    out_path: Path,
    scenario_label: str = "",
) -> None:
    """Generates a comprehensive 2x2 validation figure."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 9), dpi=150)
    tag = _format_tag(scenario_label)

    # Top-left: Sampled y_x(t) and y_y(t) vs time t
    ax_pos = axes[0, 0]
    ax_pos.step(
        t, yf_x, where="post", label="$y_{f,x}(t)$ [m]", color="#1f77b4", linewidth=1.7
    )
    ax_pos.step(
        t, yf_y, where="post", label="$y_{f,y}(t)$ [m]", color="#d62728", linewidth=1.7
    )
    ax_pos.axvline(10.0, color="gray", linestyle=":", alpha=0.8)
    ax_pos.set_title("Saída Amostrada $y_{f,x}(t)$ e $y_{f,y}(t)$ vs Tempo $t$")
    ax_pos.set_xlabel("Tempo $t$ [s]")
    ax_pos.set_ylabel("Posição [m]")
    ax_pos.grid(True, linestyle="--", alpha=0.6)
    ax_pos.legend(loc="best", fontsize=8.5)

    # Top-right: 2D Trajectory (y_x vs y_y)
    ax_traj = axes[0, 1]
    mask1 = t < 10.0
    mask2 = t >= 10.0
    ax_traj.plot(
        yf_x[mask1],
        yf_y[mask1],
        color="#1f77b4",
        linewidth=2.0,
        label=r"$0 \leq t < 10\,$s ($\omega = -0.2\pi$)",
    )
    ax_traj.plot(
        yf_x[mask2],
        yf_y[mask2],
        color="#ff7f0e",
        linewidth=2.0,
        label=r"$10 \leq t \leq 20\,$s ($\omega = +0.2\pi$)",
    )
    ax_traj.scatter(
        yf_x[0], yf_y[0], color="green", s=60, zorder=5, label="Início/Fim (0.15, 0)"
    )
    ax_traj.set_title("Trajetória Planar ($y_{f,x} \\times y_{f,y}$)")
    ax_traj.set_xlabel("$y_{f,x}$ [m]")
    ax_traj.set_ylabel("$y_{f,y}$ [m]")
    ax_traj.set_aspect("equal", adjustable="box")
    ax_traj.grid(True, linestyle="--", alpha=0.6)
    ax_traj.legend(loc="best", fontsize=8.5)

    # Bottom-left: Sampled Orientation theta(t) vs time t
    ax_theta = axes[1, 0]
    ax_theta.step(
        t,
        yf_theta,
        where="post",
        color="#2ca02c",
        linewidth=1.7,
        label=r"$\theta(t)$ [rad]",
    )
    ax_theta.axvline(10.0, color="gray", linestyle=":", alpha=0.8)
    ax_theta.set_title(r"Orientação Amostrada $\theta(t)$ vs Tempo $t$")
    ax_theta.set_xlabel("Tempo $t$ [s]")
    ax_theta.set_ylabel(r"Ângulo $\theta$ [rad]")
    ax_theta.grid(True, linestyle="--", alpha=0.6)
    ax_theta.legend(loc="best", fontsize=8.5)

    # Bottom-right: Control inputs u(t)
    ax_ctrl = axes[1, 1]
    ax_ctrl.step(
        t, v, where="post", color="#9467bd", linewidth=1.7, label="$v(t)$ [m/s]"
    )
    ax_ctrl.step(
        t,
        omega,
        where="post",
        color="#ff7f0e",
        linewidth=1.7,
        label=r"$\omega(t)$ [rad/s]",
    )
    ax_ctrl.axvline(10.0, color="gray", linestyle=":", alpha=0.8)
    ax_ctrl.set_title("Entrada de Controle $u(t) = [v(t), \\omega(t)]^T$")
    ax_ctrl.set_xlabel("Tempo $t$ [s]")
    ax_ctrl.set_ylabel("Amplitude")
    ax_ctrl.grid(True, linestyle="--", alpha=0.6)
    ax_ctrl.legend(loc="best", fontsize=8.5)

    fig.suptitle(
        f"Laboratório 2 (FTL066) — Simulação de Robô Móvel com Múltiplas Threads{tag}",
        fontsize=13.5,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_figures_for_log(
    log_path: Path,
    output_dir: Path,
    suffix: str = "",
    scenario_label: str = "",
    verbose: bool = True,
) -> list[Path]:
    """Generates trajectory_2d, states_and_inputs, and simulation_results for a given log."""
    output_dir.mkdir(parents=True, exist_ok=True)
    data = load_telemetry(log_path)

    t = data[:, 0]
    v = data[:, 1]
    omega = data[:, 2]
    yf_x = data[:, 3]
    yf_y = data[:, 4]
    yf_theta = data[:, 5]

    periods_ms = np.diff(t) * 1000.0
    jitters_ms = periods_ms - 30.0

    traj_path = output_dir / f"trajectory_2d{suffix}.png"
    states_path = output_dir / f"states_and_inputs{suffix}.png"
    dashboard_path = output_dir / f"simulation_results{suffix}.png"

    plot_trajectory_2d(t, yf_x, yf_y, traj_path, scenario_label=scenario_label)
    plot_states_and_inputs(
        t, v, omega, yf_x, yf_y, yf_theta, states_path, scenario_label=scenario_label
    )
    plot_combined_dashboard(
        t, v, omega, yf_x, yf_y, yf_theta, dashboard_path, scenario_label=scenario_label
    )

    if verbose:
        header_tag = f" ({scenario_label})" if scenario_label else ""
        print(f"=== Validação Pós-Processamento (Lab 2){header_tag} ===")
        print(f"Arquivo de log lido     : {log_path}")
        print(f"Total de amostras lidas : {len(t)}")
        print(f"Horizonte de tempo      : [{t[0]:.6f} s, {t[-1]:.6f} s]")
        print(
            f"Postura inicial y_f(0)  : "
            f"x={yf_x[0]:.4f} m, y={yf_y[0]:.4f} m, theta={yf_theta[0]:.4f} rad"
        )
        print(
            f"Postura final y_f(20)   : "
            f"x={yf_x[-1]:.4f} m, y={yf_y[-1]:.4f} m, theta={yf_theta[-1]:.4f} rad"
        )
        print(
            f"Período T(k) Thread 1   : "
            f"média={np.mean(periods_ms):.4f} ms, "
            f"var={np.var(periods_ms, ddof=1):.6f} ms^2, "
            f"std={np.std(periods_ms, ddof=1):.4f} ms, "
            f"min={np.min(periods_ms):.4f} ms, "
            f"max={np.max(periods_ms):.4f} ms"
        )
        print(
            f"Jitter J(k) Thread 1    : "
            f"média={np.mean(jitters_ms):+.4f} ms, "
            f"var={np.var(jitters_ms, ddof=1):.6f} ms^2, "
            f"std={np.std(jitters_ms, ddof=1):.4f} ms, "
            f"min={np.min(jitters_ms):+.4f} ms, "
            f"max={np.max(jitters_ms):+.4f} ms"
        )
        print("\nGráficos salvos em:")
        print(f"  - {states_path}")
        print(f"  - {traj_path}")
        print(f"  - {dashboard_path}")

    return [states_path, traj_path, dashboard_path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera os gráficos de trajetória e estados a partir de um log de telemetria."
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=LOG_FILE,
        help="Caminho do arquivo de telemetria (padrão: data/simulation_log.txt).",
    )
    parser.add_argument(
        "--suffix",
        type=str,
        default="",
        help="Sufixo opcional para os arquivos PNG (ex.: _idle ou _stress).",
    )
    parser.add_argument(
        "--label",
        type=str,
        default="",
        help="Rótulo opcional exibido no título dos gráficos (ex.: 'Sem Carga').",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point for telemetry validation and figure generation."""
    args = parse_args()
    generate_figures_for_log(
        log_path=args.log,
        output_dir=OUTPUT_DIR,
        suffix=args.suffix,
        scenario_label=args.label,
        verbose=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
