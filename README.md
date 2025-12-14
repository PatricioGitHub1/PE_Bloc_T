# BlocT PE
- `temp_c`: Temperatura instantània reportada pel sensor (Windows WMI / `sensors` a Linux)

Sistema d'automatitzacio per benchmark d'algorismes amb esquema ABBA, cross-platform (Linux i Windows).

## Estructura del projecte

```
project/
├─ algs/                  # Implementacions C++ (linear_scan.cpp, mergesort.cpp, log_halving.cpp, quadratic_bench.cpp, ...)
├─ include/metrics.hpp    # Wrapper mètriques (cross-platform)
├─ build/                 # Binaris per OS (generat)
├─ runs/                  # Sortides (JSON + CSV, generat)
├─ run_linux.sh           # Orquestrador Linux
├─ run_windows.ps1        # Orquestrador Windows
├─ config.json            # Definició d'algorismes, ns i repeticions
└─ CMakeLists.txt         # Build config
```

## Requisits

### Linux
- GCC/G++ amb suport C++20
- CMake >= 3.20
- jq (parser JSON)
- Python 3
- Opcional: cpupower per governador CPU

```bash
sudo apt install build-essential cmake jq python3
```

### Windows
- MinGW/MSYS2 o WSL amb GCC
- CMake >= 3.20
- PowerShell

## Compilacio

### Linux
```bash
mkdir -p build && cd build
cmake ..
cmake --build . -j
```

### Windows (PowerShell, MinGW)
```powershell
mkdir build; cd build
cmake .. -G "MinGW Makefiles"
cmake --build . -j
```

## Configuracio

Edita `config.json` per definir els experiments:

```json
{
  "algos": [
    {"name": "linear_scan", "bin": "linear_scan", "complexity": "O(n)", "ns": [2000000]},
    {"name": "mergesort", "bin": "mergesort", "complexity": "O(n log n)", "ns": [100000, 300000, 1000000]},
    {"name": "quadratic_bench", "bin": "quadratic_bench", "complexity": "O(n^2)", "ns": [2000, 4000]},
    {"name": "log_halving", "bin": "log_halving", "complexity": "O(log n)", "ns": [1000000000]}
  ],
  "reps": 10,
  "seed_master": 123456789
}
```

- **algos**: defineix la parella `name/bin` i permet indicar `ns` específiques (si no n'hi ha, s'aplica la llista global).
- **reps**: nombre de repeticions per parell (per defecte 10 per arribar a 40 execucions per OS amb 4 algorismes).
- **seed_master**: llavor base per generar els seeds aparellats entre plataformes.


## Execucio

### Linux
```bash
./run_linux.sh
```

Resultats a: `runs/linux_YYYYMMDD_HHMMSS/data_linux.csv`

### Windows
```powershell
.\run_windows.ps1
```

Resultats a: `runs\windows_YYYYMMDD_HHMMSS\data_windows.csv`

## Esquema ABBA

El sistema implementa esquema ABBA per reduir bias entre OS:

- Linux: ordre 1 (A) i 4 (B)
- Windows: ordre 2 (A) i 3 (B)

Cada experiment inclou:
- **Warm-up**: 5 execucions prèvies consecutives amb el mateix input per estabilitzar temperatura/caches
- **Cooldown**: 60 segons entre execucions

## Metriques recollides

Cada execucio registra:


- `wall_ms`: Temps real (wall-clock)
- `cpu_user_ms`: Temps CPU en mode usuari
- `cpu_sys_ms`: Temps CPU en mode sistema
- `cpu_pct_avg`: Percentatge mitjà de CPU utilitzat (normalitzat per `threads`)
- `rss_peak_mib`: Memòria RSS màxima (MiB)
- `threads`: Nombre de threads hardware disponibles
- `temp_c`: Temperatura instantània reportada pel sensor (Windows WMI / `sensors` a Linux)

Metadades:
- `compiler`: Versio del compilador
- `flags`: Flags de compilacio
- `os_name`: Nom i versio del SO
- `kernel`: Versio del kernel (Linux) o build (Windows)
- `timestamp`: Marca temporal ISO-8601

## Afegir nous algorismes

1. Crea el fitxer C++ a `algs/`:

```cpp
#include "metrics.hpp"
#include <vector>
// ... els teus includes

int main(int argc, char** argv) {
  if (argc < 4) return 2;
  std::string alg = argv[1];
  long long n     = std::atoll(argv[2]);
  uint64_t seed   = std::strtoull(argv[3], nullptr, 10);

  // Prepara les dades
  // ...

  BenchResult R{};
  R.alg = alg; R.n = n; R.seed = seed;
  R.threads = (int)std::thread::hardware_concurrency();

  BenchTimer T; T.start();
  
  // EL TEU ALGORISME AQUi
  
  T.stop(R);
  print_json(R);
  return 0;
}
```

2. Afegeix a `CMakeLists.txt`:

```cmake
add_executable(nom_alg algs/nom_alg.cpp)
if (WIN32)
  target_link_libraries(nom_alg psapi)
endif()
```

3. Actualitza `config.json`:

```json
{
  "algos": [
    {"name": "linear_scan", "bin": "linear_scan", "ns": [2000000]},
    {"name": "nom_alg", "bin": "nom_alg", "ns": [12345]}
  ],
  ...
}
```

4. Recompila i executa

## Fusio de resultats

Per combinar resultats de Linux i Windows:

```bash
# Linux
cat runs/linux_*/data_linux.csv runs/windows_*/data_windows.csv > runs/all_data.csv
# Elimina duplicats de capcalera si cal
```

## Notes importants

- Executa amb la maquina connectada a AC power
- Minimitza processos en background
- Linux: considera usar `cpupower frequency-set -g performance`
- Les flags de compilacio han de ser identiques als dos OS
- Usa el mateix GCC major version si es possible

## Deteccio d'outliers

Per detectar i filtrar outliers (sugerencia):

```python
import pandas as pd
import numpy as np

df = pd.read_csv('runs/all_data.csv')
for pair in df['pair_id'].unique():
    subset = df[df['pair_id'] == pair]
    median = subset['wall_ms'].median()
    mad = np.median(np.abs(subset['wall_ms'] - median))
    # Descarta si |wall - median| > 3*MAD
    outliers = subset[np.abs(subset['wall_ms'] - median) > 3*mad]
    if len(outliers) > 0:
        print(f"Outliers detectats a {pair}: {outliers['run_id'].tolist()}")
```
