from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.stats as stats

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / "resultats_tots.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sortides" / "agreement_plots"

plt.rcParams["figure.figsize"] = (6, 4)
plt.rcParams["figure.dpi"] = 150


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera QQ-plots de Dlog i grafics Bland-Altman per comparar Linux i Windows."
    )
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=DEFAULT_INPUT,
        help="CSV amb totes les execucions (Windows + Linux).",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Carpeta on es guardaran els grafics.",
    )
    parser.add_argument(
        "--linux-label",
        default="Linux",
        help="Valor de la columna os que identifica Linux.",
    )
    parser.add_argument(
        "--windows-label",
        default="Windows",
        help="Valor de la columna os que identifica Windows.",
    )
    return parser.parse_args()


def sanitize_for_filename(value: str) -> str:
    return value.replace("/", "_").replace("\\", "_").replace(" ", "_")


def has_columns(df: pd.DataFrame, required: Iterable[str]) -> bool:
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"[error] Falten columnes al CSV: {missing}")
        return False
    return True


def load_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path, skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    # Neteja espais a string/object per evitar mismatches (p. ex. "Linux  " vs "Linux")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
    return df


def maybe_add_abba_leg(df: pd.DataFrame, linux_label: str, windows_label: str) -> pd.DataFrame:
    if "run_order" not in df.columns:
        return df

    df = df.copy()
    df["abba_leg"] = None
    linux_map = {1: "A", 4: "B"}
    windows_map = {2: "A", 3: "B"}

    is_linux = df["os"] == linux_label
    is_windows = df["os"] == windows_label

    df.loc[is_linux, "abba_leg"] = df.loc[is_linux, "run_order"].map(linux_map)
    df.loc[is_windows, "abba_leg"] = df.loc[is_windows, "run_order"].map(windows_map)
    return df


def prepare_paired_df(df: pd.DataFrame, linux_label: str, windows_label: str) -> pd.DataFrame:
    required_cols = ("pair_id", "alg", "n", "seed", "os", "wall_ms")
    if not has_columns(df, required_cols):
        return pd.DataFrame()

    df = maybe_add_abba_leg(df, linux_label, windows_label)

    merge_keys = ["pair_id", "alg", "n", "seed"]
    if "abba_leg" in df.columns:
        merge_keys.append("abba_leg")

    base_cols = [*merge_keys, "wall_ms"]
    lin = df[df["os"] == linux_label][base_cols].rename(columns={"wall_ms": "wall_ms_lin"})
    win = df[df["os"] == windows_label][base_cols].rename(columns={"wall_ms": "wall_ms_win"})

    if "abba_leg" in merge_keys:
        lin = lin.dropna(subset=["abba_leg"])
        win = win.dropna(subset=["abba_leg"])

    merged = lin.merge(win, on=merge_keys, suffixes=("_lin", "_win"))
    if merged.empty:
        print("[warn] No s'ha trobat cap parell Linux/Windows amb els criteris indicats.")
        return merged

    merged["Dlog"] = np.log(merged["wall_ms_lin"]) - np.log(merged["wall_ms_win"])
    return merged


def save_qq_plot(dlog: pd.Series, alg_label: str, output_dir: Path) -> None:
    plt.figure()
    stats.probplot(dlog, dist="norm", plot=plt)
    plt.title(f"QQ-plot Dlog_temps - {alg_label}")
    plt.xlabel("Quantils teorics")
    plt.ylabel("Quantils observats")
    plt.tight_layout()
    path = output_dir / f"qqplot_dlog_{sanitize_for_filename(str(alg_label))}.png"
    plt.savefig(path)
    plt.close()
    print(f"[save] {path}")


def save_bland_altman_plot(x: np.ndarray, y: np.ndarray, alg_label: str, output_dir: Path) -> None:
    mean = np.mean([x, y], axis=0)
    diff = x - y
    md = np.mean(diff)
    sd = np.std(diff)

    plt.figure()
    plt.scatter(mean, diff)
    plt.axhline(md, color="red", linestyle="--", label=f"Mitjana diff = {md:.3f}")
    plt.axhline(md + 1.96 * sd, color="gray", linestyle="--")
    plt.axhline(md - 1.96 * sd, color="gray", linestyle="--")
    plt.title(f"Bland-Altman temps - {alg_label}")
    plt.xlabel("Mitjana temps")
    plt.ylabel("Diferencia temps (Linux - Windows)")
    plt.legend()
    plt.tight_layout()
    path = output_dir / f"bland_altman_{sanitize_for_filename(str(alg_label))}.png"
    plt.savefig(path)
    plt.close()
    print(f"[save] {path}")


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"No s'ha trobat el fitxer d'entrada: {args.input}")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataframe(args.input)
    paired = prepare_paired_df(df, args.linux_label, args.windows_label)
    if paired.empty:
        return

    for alg in paired["alg"].dropna().unique():
        sub = paired[paired["alg"] == alg]
        if sub.empty:
            continue
        save_qq_plot(sub["Dlog"], str(alg), output_dir)
        save_bland_altman_plot(
            sub["wall_ms_lin"].to_numpy(), sub["wall_ms_win"].to_numpy(), str(alg), output_dir
        )


if __name__ == "__main__":
    main()
