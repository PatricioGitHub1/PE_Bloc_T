from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sortides" / "basic_reports"

# Configuracio basica de grafics
plt.rcParams["figure.figsize"] = (6, 4)
plt.rcParams["figure.dpi"] = 150


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera taules i figures (Temps, CPU, Memoria) a partir d'un CSV de resultats."
    )
    parser.add_argument(
        "--input",
        "-i",
        default="resultats_tots.csv",
        help="CSV amb totes les execucions (Windows + Linux).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=DEFAULT_OUTPUT_DIR,
        type=Path,
        help="Carpeta on es guardaran les taules i figures.",
    )
    parser.add_argument(
        "--skip-per-alg-boxplots",
        action="store_true",
        help="Omet els boxplots per algorisme.",
    )
    parser.add_argument(
        "--xlog",
        action="store_true",
        help="Fa servir escala log a l'eix n del grafic temps vs n.",
    )
    return parser.parse_args()


def sanitize_for_filename(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").replace(" ", "_")


def has_columns(df: pd.DataFrame, required: Iterable[str], label: str) -> bool:
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"[omit] {label}: falten columnes {missing}")
        return False
    return True


def load_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    if {"cpu_user_ms", "cpu_sys_ms"}.issubset(df.columns):
        df["cpu_total_ms"] = df["cpu_user_ms"] + df["cpu_sys_ms"]

    for cat_col in ("os", "alg"):
        if cat_col in df.columns:
            df[cat_col] = df[cat_col].astype("category")

    return df


def generate_time_outputs(df: pd.DataFrame, output_dir: Path, skip_per_alg: bool) -> None:
    if not has_columns(df, ("os", "alg", "wall_ms"), "Taula 1 / Figura 1"):
        return

    time_stats = (
        df.groupby(["os", "alg"])["wall_ms"]
        .agg(["mean", "std", "min", "max", "count"])
        .reset_index()
        .rename(
            columns={
                "mean": "wall_mean_ms",
                "std": "wall_sd_ms",
                "min": "wall_min_ms",
                "max": "wall_max_ms",
                "count": "n_obs",
            }
        )
    )

    time_csv = output_dir / "taula1_temps_per_os_alg.csv"
    time_stats.to_csv(time_csv, index=False)
    print(f"[save] {time_csv}")

    plt.figure()
    df.boxplot(column="wall_ms", by="os")
    plt.xlabel("Sistema operatiu")
    plt.ylabel("Temps d'execucio (ms)")
    plt.title("Temps d'execucio per sistema operatiu (tots els algorismes)")
    plt.suptitle("")
    plt.tight_layout()
    wall_global = output_dir / "figura1_boxplot_wall_global.png"
    plt.savefig(wall_global)
    plt.close()
    print(f"[save] {wall_global}")

    if skip_per_alg:
        return

    for alg in df["alg"].dropna().unique():
        sub = df[df["alg"] == alg]
        if sub.empty:
            continue

        alg_label = sanitize_for_filename(str(alg))
        plt.figure()
        sub.boxplot(column="wall_ms", by="os")
        plt.xlabel("Sistema operatiu")
        plt.ylabel("Temps d'execucio (ms)")
        plt.title(f"Temps d'execucio per sistema operatiu - {alg}")
        plt.suptitle("")
        plt.tight_layout()
        per_alg_path = output_dir / f"boxplot_wall_{alg_label}.png"
        plt.savefig(per_alg_path)
        plt.close()
        print(f"[save] {per_alg_path}")


def plot_time_vs_n(df: pd.DataFrame, output_dir: Path, log_scale: bool) -> None:
    if not has_columns(df, ("os", "alg", "n", "wall_ms"), "Figura 6"):
        return

    mean_time_n = df.groupby(["os", "alg", "n"])["wall_ms"].mean().reset_index()
    mean_csv = output_dir / "temps_mig_per_os_alg_n.csv"
    mean_time_n.to_csv(mean_csv, index=False)
    print(f"[save] {mean_csv}")

    plt.figure()
    for os_name, sub in mean_time_n.groupby("os"):
        plt.plot(sub["n"], sub["wall_ms"], marker="o", linestyle="-", label=os_name)

    plt.xlabel("Mida de l'input (n)")
    plt.ylabel("Temps mitja d'execucio (ms)")
    plt.title("Temps mitja vs mida de l'input per sistema operatiu")
    plt.legend(title="Sistema operatiu")
    if log_scale:
        plt.xscale("log")
    plt.tight_layout()
    fig_path = output_dir / "figura6_temps_vs_n_per_os.png"
    plt.savefig(fig_path)
    plt.close()
    print(f"[save] {fig_path}")


def generate_cpu_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    if "cpu_total_ms" not in df.columns and {"cpu_user_ms", "cpu_sys_ms"}.issubset(df.columns):
        df["cpu_total_ms"] = df["cpu_user_ms"] + df["cpu_sys_ms"]

    if not has_columns(df, ("os", "alg", "cpu_total_ms", "cpu_pct_avg"), "Taula 2 / Figura 7"):
        return

    cpu_stats = (
        df.groupby(["os", "alg"])
        .agg(
            cpu_total_mean_ms=("cpu_total_ms", "mean"),
            cpu_total_sd_ms=("cpu_total_ms", "std"),
            cpu_pct_mean=("cpu_pct_avg", "mean"),
            cpu_pct_sd=("cpu_pct_avg", "std"),
        )
        .reset_index()
    )

    cpu_csv = output_dir / "taula2_cpu_per_os_alg.csv"
    cpu_stats.to_csv(cpu_csv, index=False)
    print(f"[save] {cpu_csv}")

    plt.figure()
    df.boxplot(column="cpu_pct_avg", by="os")
    plt.xlabel("Sistema operatiu")
    plt.ylabel("% CPU (sobre tots els fils)")
    plt.title("Percentatge de CPU per sistema operatiu (tots els algorismes)")
    plt.suptitle("")
    plt.tight_layout()
    cpu_fig = output_dir / "figura7_boxplot_cpu_pct_global.png"
    plt.savefig(cpu_fig)
    plt.close()
    print(f"[save] {cpu_fig}")


def generate_mem_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    if not has_columns(df, ("os", "alg", "rss_peak_mib"), "Taula 3 / Figura 8"):
        return

    mem_stats = (
        df.groupby(["os", "alg"])
        .agg(
            rss_mean_mib=("rss_peak_mib", "mean"),
            rss_sd_mib=("rss_peak_mib", "std"),
            rss_min_mib=("rss_peak_mib", "min"),
            rss_max_mib=("rss_peak_mib", "max"),
        )
        .reset_index()
    )

    mem_csv = output_dir / "taula3_mem_per_os_alg.csv"
    mem_stats.to_csv(mem_csv, index=False)
    print(f"[save] {mem_csv}")

    plt.figure()
    df.boxplot(column="rss_peak_mib", by="os")
    plt.xlabel("Sistema operatiu")
    plt.ylabel("Pic de memoria RSS (MiB)")
    plt.title("Pic de memoria per sistema operatiu (tots els algorismes)")
    plt.suptitle("")
    plt.tight_layout()
    mem_fig = output_dir / "figura8_boxplot_rss_global.png"
    plt.savefig(mem_fig)
    plt.close()
    print(f"[save] {mem_fig}")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = Path(args.input)
    if not csv_path.exists():
        raise FileNotFoundError(f"No s'ha trobat el fitxer d'entrada: {csv_path}")

    df = load_dataframe(csv_path)
    if df.empty:
        print("[warn] El DataFrame es buit, no hi ha res a processar.")
        return

    generate_time_outputs(df, output_dir, args.skip_per_alg_boxplots)
    plot_time_vs_n(df, output_dir, args.xlog)
    generate_cpu_outputs(df, output_dir)
    generate_mem_outputs(df, output_dir)


if __name__ == "__main__":
    main()
