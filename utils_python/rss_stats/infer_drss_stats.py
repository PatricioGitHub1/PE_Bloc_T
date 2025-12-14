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
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sortides" / "rss_stats"

plt.rcParams["figure.figsize"] = (6, 4)
plt.rcParams["figure.dpi"] = 150
sns.set_theme(style="whitegrid")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Genera estadistics i boxplots de RSS (MiB) per OS, i diferencies aparellades "
            "Drss = rss_peak_mib_lin - rss_peak_mib_win per algorisme."
        )
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
        help="Carpeta on es desaran les taules i els boxplots.",
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
        help="Si s'indica, desa també el detall per parella amb Drss.",
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


def compute_ic95(series: pd.Series) -> Tuple[float, float] | None:
    n = len(series)
    if n < 2:
        return None

    mean = float(series.mean())
    sd = float(series.std(ddof=1))
    tcrit = float(t.ppf(0.975, df=n - 1))
    margin = tcrit * sd / np.sqrt(n)
    return mean - margin, mean + margin


def build_table6_rss(df: pd.DataFrame) -> pd.DataFrame:
    required = ("os", "alg", "rss_peak_mib")
    if not has_columns(df, required):
        return pd.DataFrame()

    return (
        df.groupby(["os", "alg"])["rss_peak_mib"]
        .agg(["mean", "std", "min", "max"])
        .reset_index()
        .rename(
            columns={
                "mean": "mean_rss_mib",
                "std": "sd_rss_mib",
                "min": "min_rss_mib",
                "max": "max_rss_mib",
            }
        )
    )


def save_figura10_boxplot_rss_per_os(df: pd.DataFrame, output_dir: Path) -> Path | None:
    required = ("os", "rss_peak_mib")
    if not has_columns(df, required):
        return None

    plt.figure()
    sns.boxplot(data=df, x="os", y="rss_peak_mib")
    plt.ylabel("Pic de memòria RSS (MiB)")
    plt.xlabel("Sistema operatiu")
    plt.title("Distribució del pic de memòria per sistema operatiu")
    plt.tight_layout()
    path = output_dir / "figura10_boxplot_rss_per_os.png"
    plt.savefig(path)
    plt.close()
    print(f"[save] {path}")
    return path


def prepare_paired_df(df: pd.DataFrame, linux_label: str, windows_label: str) -> pd.DataFrame:
    required_cols = ("pair_id", "alg", "n", "seed", "os", "rss_peak_mib")
    if not has_columns(df, required_cols):
        return pd.DataFrame()

    df = maybe_add_abba_leg(df, linux_label, windows_label)

    merge_keys = ["pair_id", "alg", "n", "seed"]
    if "abba_leg" in df.columns:
        merge_keys.append("abba_leg")

    base_cols = [*merge_keys, "rss_peak_mib"]
    lin = df[df["os"] == linux_label][base_cols].rename(columns={"rss_peak_mib": "rss_peak_mib_lin"})
    win = df[df["os"] == windows_label][base_cols].rename(columns={"rss_peak_mib": "rss_peak_mib_win"})

    if "abba_leg" in merge_keys:
        lin = lin.dropna(subset=["abba_leg"])
        win = win.dropna(subset=["abba_leg"])

    merged = lin.merge(win, on=merge_keys, suffixes=("_lin", "_win"))
    if merged.empty:
        print("[warn] No s'ha trobat cap parell Linux/Windows amb els criteris indicats.")
        return merged

    merged["Drss"] = merged["rss_peak_mib_lin"] - merged["rss_peak_mib_win"]
    return merged


def summarize_drss(paired: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []

    def add_row(label: str, subset: pd.DataFrame) -> None:
        n = len(subset)
        ci = compute_ic95(subset["Drss"]) if n else None
        ci_low, ci_high = ci if ci else (np.nan, np.nan)
        rows.append(
            {
                "alg": label,
                "n": int(n),
                "mean_drss_mib": float(subset["Drss"].mean()) if n else np.nan,
                "sd_drss_mib": float(subset["Drss"].std(ddof=1)) if n > 1 else np.nan,
                "min_drss_mib": float(subset["Drss"].min()) if n else np.nan,
                "max_drss_mib": float(subset["Drss"].max()) if n else np.nan,
                "ci95_low_mib": ci_low,
                "ci95_high_mib": ci_high,
            }
        )

    add_row("ALL", paired)
    for alg in paired["alg"].dropna().unique():
        add_row(str(alg).strip(), paired[paired["alg"] == alg])

    return pd.DataFrame(rows)


def save_figura11_boxplot_drss_per_alg(paired: pd.DataFrame, output_dir: Path) -> Path:
    plt.figure()
    sns.boxplot(data=paired, x="alg", y="Drss")
    plt.axhline(0, color="red", linestyle="--")
    plt.ylabel("Diferència RSS (Linux - Windows) [MiB]")
    plt.xlabel("Algorisme")
    plt.title("Diferències aparellades de memòria per algorisme")
    plt.tight_layout()
    path = output_dir / "figura11_boxplot_drss_per_alg.png"
    plt.savefig(path)
    plt.close()
    print(f"[save] {path}")
    return path


def maybe_save_paired(paired: pd.DataFrame, output_dir: Path, enabled: bool) -> None:
    if not enabled:
        return
    paired_path = output_dir / "drss_paired.csv"
    cols = ["pair_id", "alg", "n", "seed"]
    if "abba_leg" in paired.columns:
        cols.append("abba_leg")
    cols += ["rss_peak_mib_lin", "rss_peak_mib_win", "Drss"]
    paired.to_csv(paired_path, index=False, columns=cols)
    print(f"[save] {paired_path}")


def main() -> None:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"No s'ha trobat el fitxer d'entrada: {args.input}")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_dataframe(args.input)

    table6 = build_table6_rss(df)
    if not table6.empty:
        out_table6 = output_dir / "taula6_rss_per_os_alg.csv"
        table6.to_csv(out_table6, index=False)
        print(f"[save] {out_table6}")

    save_figura10_boxplot_rss_per_os(df, output_dir)

    paired = prepare_paired_df(df, args.linux_label, args.windows_label)
    if paired.empty:
        return

    drss_stats = summarize_drss(paired)
    out_drss = output_dir / "drss_stats.csv"
    drss_stats.to_csv(out_drss, index=False)
    print(f"[save] {out_drss}")

    save_figura11_boxplot_drss_per_alg(paired, output_dir)
    maybe_save_paired(paired, output_dir, args.save_paired)


if __name__ == "__main__":
    main()
