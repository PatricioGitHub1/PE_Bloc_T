#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$ROOT/config.json"
OUTDIR="$ROOT/runs/linux_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"

# Metadata OS/compiler
OS_NAME=$(source /etc/os-release; echo "${NAME} ${VERSION}")
KERNEL=$(uname -r)
GCC_VER=$(g++ --version | head -n1 | awk '{print $1" "$3}')

# Optional: set CPU governor to performance (requires permissions)
if command -v cpupower >/dev/null 2>&1; then
  sudo cpupower frequency-set -g performance || true
fi

# Parse JSON with jq (install 'jq')
mapfile -t ALGO_ENTRIES < <(jq -c '.algos[]' "$CFG")
mapfile -t DEFAULT_NS < <(jq -r '.ns[]?' "$CFG")
REPS=$(jq -r '.reps' "$CFG")
SEED_MASTER=$(jq -r '.seed_master' "$CFG")
WARMUP_RUNS=5

CSV="$OUTDIR/data_linux.csv"
echo "pair_id,alg,n,seed,os,run_order,run_id,wall_ms,cpu_user_ms,cpu_sys_ms,cpu_pct_avg,threads,rss_peak_mib,temp_c,compiler,flags,os_name,kernel,timestamp" > "$CSV"

FLAGS="-O3 -march=native -DNDEBUG"

cooldown() { sleep 60; }   # simplified and robust

read_temp() {
  if command -v sensors >/dev/null 2>&1; then
    sensors | awk '/Package id 0:/ {gsub(/[^0-9\.-]/,"",$4); print $4; exit}'
  else
    echo ""
  fi
}

run_once() {
  local alg="$1" bin="$2" n="$3" seed="$4" order="$5" runid="$6"
  local exe="$ROOT/build/$bin"
  local ts
  ts=$(date --iso-8601=seconds)

  for ((w=0; w<WARMUP_RUNS; ++w)); do
    "$exe" "$alg" "$n" $((seed + w)) >/dev/null || true
  done

  local json
  json=$("$exe" "$alg" "$n" "$seed")

  local wall cpuu cpus rss thr
  wall=$(jq -r '.wall_ms' <<<"$json")
  cpuu=$(jq -r '.cpu_user_ms' <<<"$json")
  cpus=$(jq -r '.cpu_sys_ms' <<<"$json")
  rss=$(jq -r '.rss_peak_mib' <<<"$json")
  thr=$(jq -r '.threads' <<<"$json")
  if [[ -z "$thr" || "$thr" -le 0 ]]; then
    thr=$(nproc)
  fi
  cpu_pct=$(python3 - <<PY
import math
w=float("$wall")
t=float("$thr")
cpu=float("$cpuu")+float("$cpus")
print(round((cpu/(w*t))*100, 2) if w>0 and t>0 else 0.0)
PY
)
  temp=$(read_temp)

  echo "${alg}_${n},${alg},${n},${seed},Linux,${order},${runid},${wall},${cpuu},${cpus},${cpu_pct},${thr},${rss},${temp},${GCC_VER},\"${FLAGS}\",\"${OS_NAME}\",${KERNEL},${ts}" >> "$CSV"
}

# Experiment loop
for entry in "${ALGO_ENTRIES[@]}"; do
  alg=$(jq -r '.name' <<<"$entry")
  bin=$(jq -r '.bin' <<<"$entry")
  mapfile -t TARGET_NS < <(jq -r '.ns[]?' <<<"$entry")
  if [[ ${#TARGET_NS[@]} -eq 0 && ${#DEFAULT_NS[@]} -gt 0 ]]; then
    TARGET_NS=("${DEFAULT_NS[@]}")
  fi
  if [[ ${#TARGET_NS[@]} -eq 0 ]]; then
    echo "Warning: no ns configured for $alg, skipping" >&2
    continue
  fi
  for n in "${TARGET_NS[@]}"; do
    for ((r=1; r<=REPS; ++r)); do
      seed=$((SEED_MASTER + r))
      # Linux ordering within ABBA scheme: A=1, B=4 (coordinate with Windows)
      run_once "$alg" "$bin" "$n" "$seed" 1 "L${r}A"
      cooldown
      run_once "$alg" "$bin" "$n" "$seed" 4 "L${r}B"
      cooldown
    done
  done
done

echo "Results at: $CSV"
