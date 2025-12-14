# Utils Python

Carpeta autonoma per generar informes a partir d'un CSV amb totes les execucions (Windows + Linux). No toca cap arxiu existent del projecte.

## Dependencies
- Python 3.9+ i pip
- `pip install -r utils_python/requirements.txt` (recomanat dins d'un entorn virtual)

## Estructura d'eines
- `basic_reports/`: taules 1-3 i Figures 1, 6, 7 i 8 (temps, CPU, memoria). Desa a `utils_python/sortides/basic_reports`.
- `agreement_plots/`: QQ-plot de `Dlog` i Bland-Altman per comparar Linux vs Windows. Desa a `utils_python/sortides/agreement_plots`.
- `agreement_stats/`: diferencies parellades de %CPU (Linux - Windows). Desa a `utils_python/sortides/dcpu_stats`.
- `rss_stats/`: estadistics RSS (Taula 6) i boxplots (Figures 10 i 11). Desa a `utils_python/sortides/rss_stats`.
- Les sortides dins `utils_python/sortides/` estan separades per carpeta segons l'eina.

## Com executar (pas a pas)
1. (Opcional) Crear entorn virtual a l'arrel:
```
python -m venv .venv
```
   - Activar a Windows: `.venv\\Scripts\\activate`
   - Activar a Linux/macOS: `source .venv/bin/activate`
2. Installa dependencies:
```
pip install -r utils_python/requirements.txt
```
3. Tens a ma el CSV complet (p. ex. `resultats_tots.csv`). Si nomes tens un CSV parcial (p. ex. `runs/windows_*/data_windows.csv`), el pots passar directament a `--input`.
4. Executa l'eina que necessites (pots canviar `--output-dir` si vols un altre desti):

### Resums basics (taules i boxplots)
```
python utils_python/basic_reports/run_analysis.py --input resultats_tots.csv --output-dir utils_python/sortides/basic_reports
```
- `--skip-per-alg-boxplots` per ometre els boxplots per algorisme.
- `--xlog` per fer servir escala log a l'eix n del grafic temps vs n.

### QQ-plot + Bland-Altman (Linux vs Windows)
```
python utils_python/agreement_plots/generate_agreement_plots.py --input resultats_tots.csv --output-dir utils_python/sortides/agreement_plots
```
- `--linux-label` i `--windows-label` si al CSV els valors de `os` son diferents de `Linux` / `Windows`.
- Si el CSV te `run_order` (esquema ABBA), l'eina alinea les execucions amb `abba_leg` (Linux: 1/4, Windows: 2/3) per evitar merges many-to-many.
- Si no hi ha `run_order`, necessita parelles per `pair_id`, `alg`, `n`, `seed` amb una fila per Linux i una per Windows; si no hi son, l'eina avisa.
- Genera per a cada algorisme: `qqplot_dlog_<alg>.png` i `bland_altman_<alg>.png`.

### Inferencia de Dlog (IC95%, test t, ratio)
```
python utils_python/agreement_plots/infer_dlog_stats.py --input resultats_tots.csv --output-dir utils_python/sortides/agreement_stats
```
- `--linux-label` i `--windows-label` per ajustar valors de `os` si cal.
- Si el CSV te `run_order` (esquema ABBA), l'eina alinea les execucions amb `abba_leg` (Linux: 1/4, Windows: 2/3) per evitar merges many-to-many.
- Si no hi ha `run_order`, necessita parelles per `pair_id`, `alg`, `n`, `seed` amb una fila per Linux i una per Windows; si no hi son, l'eina avisa.
- Desa `dlog_inference.csv` amb files per algorisme i un agregat `ALL`.

### Diferencies parellades de %CPU (Linux vs Windows)
```
python utils_python/agreement_stats/infer_dcpu_stats.py --input resultats_tots.csv --output-dir utils_python/sortides/dcpu_stats
```
- `--linux-label` i `--windows-label` per ajustar valors de `os` si cal.
- Si el CSV te `run_order` (esquema ABBA), l'eina alinea les execucions amb `abba_leg` (Linux: 1/4, Windows: 2/3) per evitar merges many-to-many.
- Si no hi ha `run_order`, necessita parelles per `pair_id`, `alg`, `n`, `seed` amb una fila per Linux i una per Windows; si no hi son, l'eina avisa.
- Calcula `Dcpu = cpu_pct_avg_lin - cpu_pct_avg_win` i desa `dcpu_inference.csv` (mitjana, sd, min, max, IC95% per `alg` i `ALL`), el boxplot `boxplot_dcpu_per_alg.png` i, si s'activa `--save-paired`, també `dcpu_paired.csv`.

### RSS (Taula 6 + Figures 10-11)
```
python utils_python/rss_stats/infer_drss_stats.py --input resultats_tots.csv --output-dir utils_python/sortides/rss_stats
```
- Desa `taula6_rss_per_os_alg.csv` (mean/std/min/max de `rss_peak_mib` per `os` i `alg`).
- Desa `figura10_boxplot_rss_per_os.png` (distribucio RSS per OS).
- Calcula `Drss = rss_peak_mib_lin - rss_peak_mib_win` per parelles i desa `drss_stats.csv` i `figura11_boxplot_drss_per_alg.png` (boxplot de diferencies per algorisme).
- Si s'activa `--save-paired`, també desa `drss_paired.csv`.

Interpretacio rapida dels grafics:
- QQ-plot: punts alineats amb la diagonal -> normalitat acceptable. Forma en S o punts lluny de la linia -> normalitat feble.
- Bland-Altman: linia central sota 0 -> Linux es mes rapid. Amplada dels limits +-1.96*sigma dona l'estabilitat de diferencies. Comprova si el nuvol depen de la magnitud del temps.

5. Revisa la carpeta de sortida indicada a `--output-dir` per veure taules i figures (per defecte, cada eina crea la seva carpeta dins `utils_python/sortides`, separades per eina).

## Fitxers generats
- Resums basics (per defecte a `utils_python/sortides/basic_reports`): `taula1_temps_per_os_alg.csv`, `taula2_cpu_per_os_alg.csv`, `taula3_mem_per_os_alg.csv`, `figura1_boxplot_wall_global.png`, `boxplot_wall_<alg>.png`, `figura6_temps_vs_n_per_os.png`, `figura7_boxplot_cpu_pct_global.png`, `figura8_boxplot_rss_global.png`, `temps_mig_per_os_alg_n.csv`.
- QQ/Bland-Altman (per defecte a `utils_python/sortides/agreement_plots`): `qqplot_dlog_<alg>.png`, `bland_altman_<alg>.png`.
- Inferencia Dlog (per defecte a `utils_python/sortides/agreement_stats`): `dlog_inference.csv` amb n, mitjana, IC95%, t, p-value, ratio i IC95% de ratio per algorisme i agregat `ALL`.
- Diferencies parellades de %CPU (per defecte a `utils_python/sortides/dcpu_stats`): `dcpu_inference.csv` amb n, mitjana, sd, min, max i IC95% per algorisme i `ALL`, `boxplot_dcpu_per_alg.png` i, si es demana, `dcpu_paired.csv`.
- RSS (per defecte a `utils_python/sortides/rss_stats`): `taula6_rss_per_os_alg.csv`, `figura10_boxplot_rss_per_os.png`, `drss_stats.csv`, `figura11_boxplot_drss_per_alg.png` i, si es demana, `drss_paired.csv`.

## Columnes esperades
- Temps basic: `os`, `alg`, `wall_ms`, `n` (+ `cpu_user_ms`, `cpu_sys_ms`, `cpu_pct_avg`, `rss_peak_mib` per les taules 2 i 3).
- QQ/Bland-Altman: `pair_id`, `alg`, `n`, `seed`, `os`, `wall_ms` (s'uneixen parelles Linux/Windows per aquestes claus).
- Inferencia Dlog / diferencies %CPU: `pair_id`, `alg`, `n`, `seed`, `os`, `wall_ms` (per Dlog) i `cpu_pct_avg` (per Dcpu). S'uneixen parelles Linux/Windows per aquestes claus.
- Si el CSV inclou `run_order` (ABBA), les eines de comparacio Linux/Windows afegeixen `abba_leg` (Linux: 1/4, Windows: 2/3) i fan el merge amb aquesta clau extra.
Les capsaleres es netegen amb `strip()`, aixi que funcionen els CSV de `runs/*/data_*.csv`.
