from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd
from scipy import stats

DEFAULT_INPUT = Path(__file__).resolve().parents[2] / "resultats_tots.csv"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "sortides" / "agreement_stats"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estima mitjana/log-ratio i IC95% de Dlog (log(Linux)-log(Windows)) i fa test t."
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
        help="Carpeta on es desa el CSV d'inferencia.",
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


def sanitize_for_string(value: str) -> str:
    return value.replace("\n", " ").strip()


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


def compute_dlog_stats(dlog: np.ndarray) -> dict | None:
    n = len(dlog)
    if n < 2:
        print(f"[omit] Només {n} observacio(ns); es necessita n>=2 per IC i test t.")
        return None

    mu_hat = float(np.mean(dlog))
    sd = float(np.std(dlog, ddof=1))
    t_crit = float(stats.t.ppf(0.975, df=n - 1))
    se = sd / np.sqrt(n)
    ci_low = mu_hat - t_crit * se
    ci_high = mu_hat + t_crit * se
    t_stat, p_value = stats.ttest_1samp(dlog, 0.0)

    ratio = np.exp(mu_hat)
    ratio_ci_low = np.exp(ci_low)
    ratio_ci_high = np.exp(ci_high)

    return {
        "n": int(n),
        "mean_dlog": mu_hat,
        "sd_dlog": sd,
        "ci95_low": ci_low,
        "ci95_high": ci_high,
        "t_stat": float(t_stat),
        "p_value": float(p_value),
        "ratio": float(ratio),
        "ratio_ci_low": float(ratio_ci_low),
        "ratio_ci_high": float(ratio_ci_high),
    }


def build_results(paired: pd.DataFrame) -> pd.DataFrame:
    rows: List[dict] = []

    # Global
    global_stats = compute_dlog_stats(paired["Dlog"].to_numpy())
    if global_stats:
        rows.append({"alg": "ALL", **global_stats})

    # Per algorisme
    for alg in paired["alg"].dropna().unique():
        sub = paired[paired["alg"] == alg]
        stats_dict = compute_dlog_stats(sub["Dlog"].to_numpy())
        if stats_dict:
            rows.append({"alg": sanitize_for_string(str(alg)), **stats_dict})

    return pd.DataFrame(rows)


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

    results_df = build_results(paired)
    if results_df.empty:
        print("[warn] No s'ha pogut calcular cap estadistic (potser n<2).")
        return

    out_csv = output_dir / "dlog_inference.csv"
    results_df.to_csv(out_csv, index=False)
    print(f"[save] {out_csv}")


if __name__ == "__main__":
    main()
