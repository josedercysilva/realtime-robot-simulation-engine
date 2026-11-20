#!/usr/bin/env python3
"""
    FILE: run_stress_and_plot.py
    DESC: Execucao comparativa Sem Carga vs. Com Carga (16 workers) e geracao de graficos
    AUTHOR: Jose Dercy Vieira da Silva Filho
    EMAIL: josedercysilva@gmail.com
    DATE: Out, 2026
    LICENSE: MIT
"""

import argparse
import multiprocessing
from pathlib import Path
import subprocess
import sys
import time

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError as err:
    print(
        "\n[ERRO DE DEPENDÊNCIA] Não foi possível importar os pacotes necessários para gerar os gráficos.",
        file=sys.stderr,
    )
    print(f"Detalhe: {err}\n", file=sys.stderr)
    print("Para instalar as dependências necessárias no Python, execute:", file=sys.stderr)
    print("  pip install numpy matplotlib", file=sys.stderr)
    print("Ou execute via Makefile (cria .venv automaticamente):", file=sys.stderr)
    print("  make benchmark\n", file=sys.stderr)
    sys.exit(1)


SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from plot_results import generate_figures_for_log

DEFAULT_STRESS_WORKERS = 16
NOMINAL_PERIOD_T1_MS = 30.0


def stress_worker(stop_event: multiprocessing.Event) -> None:
    """Generates continuous CPU, FPU, and cache/memory contention."""
    buf = bytearray(512 * 1024)
    val = 1.000001
    idx = 0
    n = len(buf)
    while not stop_event.is_set():
        for _ in range(20000):
            val = (val * 1.0000003) + 0.0000001
            if val > 1e6:
                val = 1.000001
            buf[idx] = (buf[idx] + 1) & 0xFF
            idx = (idx + 64) % n


def plot_jitter_comparison(
    idle_log: Path,
    stress_log: Path,
    out_path: Path,
) -> None:
    """Generates the comparative T(k) and J(k) figure for Idle vs. Stress runs."""
    data_idle = np.loadtxt(idle_log, delimiter="\t", comments="#")
    data_stress = np.loadtxt(stress_log, delimiter="\t", comments="#")

    t_idle = data_idle[1:, 0]
    T_idle = np.diff(data_idle[:, 0]) * 1000.0
    J_idle = T_idle - NOMINAL_PERIOD_T1_MS

    t_stress = data_stress[1:, 0]
    T_stress = np.diff(data_stress[:, 0]) * 1000.0
    J_stress = T_stress - NOMINAL_PERIOD_T1_MS

    fig, axes = plt.subplots(2, 1, figsize=(10.5, 7.2), dpi=150, sharex=True)

    # Top subplot: Period T(k)
    axes[0].plot(
        t_stress,
        T_stress,
        color="#d62728",
        linewidth=1.1,
        alpha=0.82,
        label=(
            f"Com Carga (Média={np.mean(T_stress):.4f} ms, "
            f"Std={np.std(T_stress, ddof=1):.4f} ms)"
        ),
    )
    axes[0].plot(
        t_idle,
        T_idle,
        color="#1f77b4",
        linewidth=1.3,
        alpha=0.95,
        label=(
            f"Sem Carga (Média={np.mean(T_idle):.4f} ms, "
            f"Std={np.std(T_idle, ddof=1):.4f} ms)"
        ),
    )
    axes[0].axhline(
        NOMINAL_PERIOD_T1_MS,
        color="black",
        linestyle="--",
        linewidth=1.0,
        label="Período Nominal (30,0 ms)",
    )
    axes[0].set_ylabel("Período $T(k)$ [ms]", fontsize=10.5)
    axes[0].set_title(
        "Item 6 do Roteiro: Comparativo de Período $T(k)$ e Jitter $J(k)$ da Thread 1",
        fontsize=12,
        fontweight="bold",
    )
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(loc="upper right", fontsize=9.2)

    # Bottom subplot: Jitter J(k)
    axes[1].plot(
        t_stress,
        J_stress,
        color="#ff7f0e",
        linewidth=1.1,
        alpha=0.82,
        label=(
            f"Jitter Com Carga (Min={np.min(J_stress):+.3f} ms, "
            f"Max={np.max(J_stress):+.3f} ms)"
        ),
    )
    axes[1].plot(
        t_idle,
        J_idle,
        color="#2ca02c",
        linewidth=1.3,
        alpha=0.95,
        label=(
            f"Jitter Sem Carga (Min={np.min(J_idle):+.3f} ms, "
            f"Max={np.max(J_idle):+.3f} ms)"
        ),
    )
    axes[1].axhline(
        0.0,
        color="black",
        linestyle="--",
        linewidth=1.0,
        label="Jitter Nominal (0,0 ms)",
    )
    axes[1].set_xlabel("Tempo de Simulação $t$ [s]", fontsize=11)
    axes[1].set_ylabel("Jitter $J(k)$ [ms]", fontsize=10.5)
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].legend(loc="upper right", fontsize=9.2)

    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Executa a simulação comparativa Sem Carga vs. Com Carga, "
            "salva os pares (_idle e _stress) em data/ e gera jitter_comparison.png."
        )
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_STRESS_WORKERS,
        help=f"Número de processos de estresse concorrentes (padrão: {DEFAULT_STRESS_WORKERS}).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    bin_path = PROJECT_ROOT / "build" / "robot_sim"
    if not bin_path.is_file():
        print("Binário build/robot_sim não encontrado. Compilando com 'make'...")
        subprocess.run(["make"], cwd=PROJECT_ROOT, check=True)

    log_path = data_dir / "simulation_log.txt"
    idle_log = data_dir / "simulation_log_idle.txt"
    stress_log = data_dir / "simulation_log_stress.txt"

    # 1. Execução Sem Carga (Idle)
    print("=============================================================")
    print(" [1/2] Executando simulação SEM CARGA (Idle) — ~20 s...")
    print("=============================================================")
    res_idle = subprocess.run(
        [str(bin_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    print(res_idle.stdout)
    log_path.replace(idle_log)

    # 2. Execução Com Carga (Stress)
    print("=============================================================")
    print(
        f" [2/2] Executando simulação COM CARGA ({args.workers} workers) — ~20 s..."
    )
    print("=============================================================")
    stop_event = multiprocessing.Event()
    workers = [
        multiprocessing.Process(target=stress_worker, args=(stop_event,))
        for _ in range(args.workers)
    ]
    for w in workers:
        w.start()

    time.sleep(0.3)
    try:
        res_stress = subprocess.run(
            [str(bin_path)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        print(res_stress.stdout)
    finally:
        stop_event.set()
        for w in workers:
            w.join(timeout=2.0)
            if w.is_alive():
                w.terminate()

    log_path.replace(stress_log)

    # 3. Gera dois gráficos de cada (_idle e _stress) + um do comparativo
    idle_figs = generate_figures_for_log(
        log_path=idle_log,
        output_dir=data_dir,
        suffix="_idle",
        scenario_label="Sem Carga",
        verbose=False,
    )
    stress_figs = generate_figures_for_log(
        log_path=stress_log,
        output_dir=data_dir,
        suffix="_stress",
        scenario_label="Com Carga",
        verbose=False,
    )

    jitter_plot = data_dir / "jitter_comparison.png"
    plot_jitter_comparison(idle_log, stress_log, jitter_plot)

    print("=============================================================")
    print(" Experimento comparativo concluído! Arquivos gerados em data/:")
    print(f"  - {idle_log.relative_to(PROJECT_ROOT)} / {stress_log.relative_to(PROJECT_ROOT)}")
    for fig_i, fig_s in zip(idle_figs, stress_figs):
        print(
            f"  - {fig_i.relative_to(PROJECT_ROOT)} / {fig_s.relative_to(PROJECT_ROOT)}"
        )
    print(f"  - {jitter_plot.relative_to(PROJECT_ROOT)}")
    print("=============================================================")

    return 0


if __name__ == "__main__":
    sys.exit(main())
