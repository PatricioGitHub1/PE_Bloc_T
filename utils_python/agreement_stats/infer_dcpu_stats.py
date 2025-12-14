from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import t

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / "resultats_tots.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sortides" / "dcpu_stats"

plt.rcParams["figure.figsize"] = (6, 4)
plt.rcParams["figure.dpi"] = 150
sns.set_theme(style="whitegrid")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calcula diferencies de %CPU (Linux - Windows) per parelles i n'extreu estadistics."
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
        help="Carpeta on es desaran la taula i el boxplot.",
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
    parser.add_argument(
        "--save-paired",
        action="store_true",
        help="Si s'indica, desa també el detall per parella amb Dcpu.",
    )
    return parser.parse_args()


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
    required_cols = ("pair_id", "alg", "n", "seed", "os", "cpu_pct_avg")
    if not has_columns(df, required_cols):
        return pd.DataFrame()

    df = maybe_add_abba_leg(df, linux_label, windows_label)

    merge_keys = ["pair_id", "alg", "n", "seed"]
    if "abba_leg" in df.columns:
        merge_keys.append("abba_leg")

    base_cols = [*merge_keys, "cpu_pct_avg"]
    lin = df[df["os"] == linux_label][base_cols].rename(columns={"cpu_pct_avg": "cpu_pct_avg_lin"})
    win = df[df["os"] == windows_label][base_cols].rename(columns={"cpu_pct_avg": "cpu_pct_avg_win"})

    if "abba_leg" in merge_keys:
        lin = lin.dropna(subset=["abba_leg"])
        win = win.dropna(subset=["abba_leg"])

    merged = lin.merge(win, on=merge_keys, suffixes=("_lin", "_win"))
    if merged.empty:
        print("[warn] No s'ha trobat cap parell Linux/Windows amb els criteris indicats.")
        return merged

    merged["Dcpu"] = merged["cpu_pct_avg_lin"] - merged["cpu_pct_avg_win"]
    return merged


def compute_ic95(series: pd.Series) -> Tuple[float, float] | None:
    n = len(series)
    if n < 2:
        return None

    mean = float(series.mean())
    sd = float(series.std(ddof=1))
    tcrit = float(t.ppf(0.975, df=n - 1))
    margin = tcrit * sd / np.sqrt(n)
    return mean - margin, mean + margin


def summarize_dcpu(paired: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []

    def add_row(label: str, subset: pd.DataFrame) -> None:
        n = len(subset)
        ci = compute_ic95(subset["Dcpu"])
        ci_low, ci_high = ci if ci else (np.nan, np.nan)
        rows.append(
            {
                "alg": label,
                "n": int(n),
                "mean_dcpu": float(subset["Dcpu"].mean()) if n else np.nan,
                "sd_dcpu": float(subset["Dcpu"].std(ddof=1)) if n > 1 else np.nan,
                "min_dcpu": float(subset["Dcpu"].min()) if n else np.nan,
                "max_dcpu": float(subset["Dcpu"].max()) if n else np.nan,
                "ci95_low": ci_low,
                "ci95_high": ci_high,
            }
        )

    add_row("ALL", paired)
    for alg in paired["alg"].dropna().unique():
        add_row(str(alg).strip(), paired[paired["alg"] == alg])

    return pd.DataFrame(rows)


def save_boxplot(paired: pd.DataFrame, output_dir: Path) -> Path:
    plt.figure()
    sns.boxplot(data=paired, x="alg", y="Dcpu")
    plt.axhline(0, color="red", linestyle="--")
    plt.title("Diferencia de CPU (Linux - Windows)")
    plt.xlabel("Algorisme")
    plt.ylabel("Diferencia %CPU")
    plt.tight_layout()
    path = output_dir / "boxplot_dcpu_per_alg.png"
    plt.savefig(path)
    plt.close()
    print(f"[save] {path}")
    return path


def maybe_save_paired(paired: pd.DataFrame, output_dir: Path, enabled: bool) -> None:
    if not enabled:
        return
    paired_path = output_dir / "dcpu_paired.csv"
    cols = ["pair_id", "alg", "n", "seed"]
    if "abba_leg" in paired.columns:
        cols.append("abba_leg")
    cols += ["cpu_pct_avg_lin", "cpu_pct_avg_win", "Dcpu"]
    paired.to_csv(paired_path, index=False, columns=cols)
    print(f"[save] {paired_path}")


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

    summary = summarize_dcpu(paired)
    summary_csv = output_dir / "dcpu_inference.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"[save] {summary_csv}")

    save_boxplot(paired, output_dir)
    maybe_save_paired(paired, output_dir, args.save_paired)

    for _, row in summary.iterrows():
        if np.isnan(row["ci95_low"]) or np.isnan(row["ci95_high"]):
            continue
        print(f"[ic95] {row['alg']}: ({row['ci95_low']:.3f}, {row['ci95_high']:.3f})")


if __name__ == "__main__":
    main()
