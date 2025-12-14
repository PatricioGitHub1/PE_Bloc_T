# Manual d'ús — Pipeline d'automatització de benchmarks (BlocT_FuckPE)

Aquest manual proporciona una guia completa per utilitzar el sistema d'automatització de benchmarks amb esquema ABBA per a comparació cross-platform entre Windows i Linux.

---

## Taula de continguts

1. [Prerequisits](#1-prerequisits)
2. [Estructura de carpetes i fitxers](#2-estructura-de-carpetes-i-fitxers)
3. [Configuració dels experiments](#3-configuració-dels-experiments)
4. [Compilació idèntica als dos SO](#4-compilació-idèntica-als-dos-so)
5. [Execució automatitzada](#5-execució-automatitzada)
6. [Fusió de dades i arxiu mestre](#6-fusió-de-dades-i-arxiu-mestre)
7. [Lectura i significat de camps clau](#7-lectura-i-significat-de-camps-clau)
8. [Control de qualitat i criteris d'exclusió](#8-control-de-qualitat-i-criteris-dexclusió)
9. [Afegir nous algorismes](#9-afegir-nous-algorismes)
10. [Recollida de metadades de l'equip](#10-recollida-de-metadades-de-lequip)
11. [Validació ràpida del pipeline](#11-validació-ràpida-del-pipeline)
12. [Resolució d'incidències](#12-resolució-dincidències)
13. [Bones pràctiques d'execució](#13-bones-pràctiques-dexecució)
14. [Exportació a l'informe](#14-exportació-a-linforme)

---

## 1) Prerequisits

### Windows

Per executar el pipeline a Windows necessites:

* **MSYS2/MinGW-w64** o **WSL** amb `g++` i `cmake` instal·lats
* **PowerShell 7+** (recomanat per millor compatibilitat)
* **PATH** del sistema incloent `g++`, `cmake`
* Permís d'execució de scripts PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

**Instal·lació de MSYS2 (recomanat):**
1. Descarrega MSYS2 des de https://www.msys2.org/
2. Instal·la i obre el terminal MSYS2 MinGW 64-bit
3. Actualitza el sistema:
   ```bash
   pacman -Syu
   ```
4. Instal·la les eines necessàries:
   ```bash
   pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake make
   ```
5. Afegeix `C:\msys64\mingw64\bin` al PATH del sistema

### Linux

Per executar el pipeline a Linux necessites:

* **Paquets essencials:** `g++`, `cmake`, `make`, `jq`, `python3`
* **Paquets opcionals:** `i2c-tools` (per info RAM detallada), `cpupower` (per control del governor CPU)
* **PATH** incloent `g++`, `cmake`, `jq`

**Instal·lació (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install build-essential cmake jq python3 linux-tools-common linux-tools-generic
```

**Instal·lació (Fedora/RHEL):**
```bash
sudo dnf install gcc-c++ cmake jq python3 kernel-tools
```

**Instal·lació (Arch Linux):**
```bash
sudo pacman -S gcc cmake jq python
```

### Requisits comuns

* **Un únic repositori** amb l'estructura indicada (clone aquest repositori)
* **Mateixes flags de compilació** i **versió de GCC** als dos SO per garantir comparabilitat
* **Espai en disc:** mínim 500 MB lliures per builds i resultats
* **RAM:** mínim 4 GB (recomanat 8 GB o més per n grans)

---

## 2) Estructura de carpetes i fitxers

El repositori segueix aquesta estructura:

```
BlocT_FuckPE/
├─ algs/                  # Implementacions dels algorismes (.cpp)
│  ├─ qs.cpp             # QuickSort
│  └─ mergesort.cpp      # MergeSort
├─ include/
│  └─ metrics.hpp        # Sistema de captura de mètriques (wall, CPU, RSS)
├─ man/
│  └─ manual.md          # Aquest manual d'ús
├─ build/                # Binaris generats (es crea automàticament)
├─ runs/                 # Sortides CSV/JSON (es crea automàticament)
├─ run_linux.sh          # Script orquestrador per Linux
├─ run_windows.ps1       # Script orquestrador per Windows
├─ config.json           # Configuració dels experiments
├─ CMakeLists.txt        # Configuració de build multiplataforma
├─ README.md             # Documentació bàsica
└─ .gitignore            # Exclou build/ i runs/ del control de versions
```

### Descripció dels components

* **`algs/`**: Conté el codi font dels algorismes a benchmarcar. Cada fitxer és un executable independent.
* **`include/metrics.hpp`**: Header que proporciona les classes `BenchTimer` i `BenchResult` per capturar mètriques de rendiment de forma portable.
* **`config.json`**: Fitxer de configuració JSON que defineix quins algorismes executar, amb quines mides d'input, quantes repeticions i la llavor per generació aleatòria.
* **`run_linux.sh`** i **`run_windows.ps1`**: Scripts d'orquestració que automatitzen la compilació, execució i recollida de dades seguint l'esquema ABBA.
* **`build/`**: Directori generat on CMake col·loca els binaris compilats.
* **`runs/`**: Directori generat on s'emmagatzemen els resultats en format CSV i JSON amb marca temporal.

---

## 3) Configuració dels experiments

### Edició del fitxer config.json

El fitxer `config.json` controla tots els paràmetres dels experiments. Exemple:

```json
{
  "algos": [
    {"name": "qs", "bin": "qs"},
    {"name": "mergesort", "bin": "mergesort"}
  ],
  "ns": [100000, 300000, 1000000, 3000000, 10000000],
  "reps": 20,
  "seed_master": 123456789
}
```

### Paràmetres

* **`algos`**: Array d'objectes que defineixen els algorismes a provar
  * `name`: Etiqueta descriptiva de l'algorisme (apareixerà als resultats)
  * `bin`: Nom del binari executable (sense extensió `.exe`)
  
* **`ns`**: Array de mides d'input (valors de N) a provar. Pots usar notació científica si vols.

* **`reps`**: Número de repeticions per cada parell `(algorisme, n)`. Recomanat: mínim 20 per robustesa estadística.

* **`seed_master`**: Llavor base per generació de seeds. La seed real per cada repetició és `seed_master + índex_repetició`, garantint reproducibilitat.

### Consells de configuració

* **Per proves ràpides:** usa `ns` petits (ex: `[1000, 10000, 100000]`) i `reps` baix (ex: `5`)
* **Per resultats finals:** usa `ns` representatius del problema i `reps >= 20`
* **Per maximitzar reproducibilitat:** mantingues `seed_master` constant entre execucions

---

## 4) Compilació idèntica als dos SO

És crucial que la compilació sigui **idèntica** als dos sistemes operatius per garantir una comparació justa. El projecte usa CMake per gestionar això automàticament.

### Linux

Obre un terminal i executa:

```bash
cd /path/to/BlocT_FuckPE
mkdir -p build && cd build
cmake ..
cmake --build . -j
```

**Verificació:**
```bash
ls -lh qs mergesort
./qs --version 2>&1 || echo "Binari generat correctament"
```

### Windows (MSYS2/MinGW)

Obre PowerShell o MSYS2 terminal i executa:

```powershell
cd C:\path\to\BlocT_FuckPE
mkdir build
cd build
cmake .. -G "MinGW Makefiles"
cmake --build . -j
```

**Verificació:**
```powershell
dir qs.exe, mergesort.exe
.\qs.exe
```

### Windows (WSL)

Si fas servir WSL, segueix les mateixes instruccions que per Linux.

### Flags de compilació

El `CMakeLists.txt` aplica automàticament:
* `-O3`: Optimització màxima
* `-march=native`: Optimitzacions per l'arquitectura actual
* `-DNDEBUG`: Desactiva assertions
* `-std=c++20`: Utilitza C++20

Aquestes flags són consistents entre SO i es registren automàticament als CSV de resultats.

### Verificació de versions

**Important:** Assegura't que uses la mateixa versió major de GCC:

```bash
# Linux
g++ --version

# Windows (MSYS2)
g++ --version
```

Si les versions difereixen significativament (ex: GCC 11 vs GCC 13), considera instal·lar la mateixa versió a ambdós sistemes.

---

## 5) Execució automatitzada

### Linux

Des del directori arrel del projecte:

```bash
cd /path/to/BlocT_FuckPE
chmod +x run_linux.sh
./run_linux.sh
```

**Què fa l'script:**
1. Intenta configurar el governor CPU a `performance` (requereix permisos o sudo)
2. Compila els binaris si no existeixen o si són antics
3. Crea un directori de sortida: `runs/linux_YYYYMMDD_HHMMSS/`
4. Per cada parell `(algorisme, n)`:
   * Executa 1 warm-up (no es registra)
   * Executa `reps` repeticions reals amb esquema ABBA (Linux fa les execucions 1 i 4)
   * Aplica cooldown de 60 segons entre execucions
5. Genera `data_linux.csv` amb tots els resultats

**Sortida esperada:**
```
Configurant governor CPU...
Compilant algorismes...
Iniciant benchmark amb esquema ABBA...
[qs, n=100000, rep=1/20] wall=12.3ms
...
Resultats guardats a: runs/linux_20231109_143022/data_linux.csv
```

### Windows

Des del directori arrel del projecte amb PowerShell:

```powershell
cd C:\path\to\BlocT_FuckPE
.\run_windows.ps1
```

**Què fa l'script:**
1. Prioritza el procés de PowerShell a "High" per reduir interferències
2. Compila els binaris si no existeixen o si són antics
3. Crea un directori de sortida: `runs\windows_YYYYMMDD_HHMMSS\`
4. Per cada parell `(algorisme, n)`:
   * Executa 1 warm-up (no es registra)
   * Executa `reps` repeticions reals amb esquema ABBA (Windows fa les execucions 2 i 3)
   * Aplica cooldown de 60 segons entre execucions
5. Genera `data_windows.csv` amb tots els resultats

**Sortida esperada:**
```
Configurant prioritat de procés...
Compilant algorismes...
Iniciant benchmark amb esquema ABBA...
[qs, n=100000, rep=1/20] wall=11.8ms
...
Resultats guardats a: runs\windows_20231109_143022\data_windows.csv
```

### Esquema ABBA explicat

L'esquema ABBA és una tècnica per reduir el biaix temporal entre dues condicions (en aquest cas, SO):

```
Ordre temporal:  1       2       3       4
Sistema:        Linux  Windows Windows  Linux
Etiqueta:         A       B       B       A
```

**Avantatges:**
* Compensa l'efecte del temps (si el sistema s'escalfa o hi ha deriva)
* Proporciona dues mesures per SO intercalades
* Permet detectar tendències temporals

**Nota:** El cooldown de 60 segons entre execucions ajuda a minimitzar efectes tèrmics.

---

## 6) Fusió de dades i arxiu mestre

Després d'executar els benchmarks als dos sistemes, has de fusionar els CSV en un únic arxiu per anàlisi conjunta.

### Linux

Des del directori arrel:

```bash
cd /path/to/BlocT_FuckPE

# Crea l'arxiu fusionat amb la capçalera del primer CSV
head -n 1 runs/linux_*/data_linux.csv | head -n 1 > runs/all_data.csv

# Afegeix totes les files de dades (sense capçaleres repetides)
tail -q -n +2 runs/linux_*/data_linux.csv >> runs/all_data.csv
tail -q -n +2 runs/windows_*/data_windows.csv >> runs/all_data.csv

echo "Fusió completada: runs/all_data.csv"
wc -l runs/all_data.csv
```

### Windows (PowerShell)

Des del directori arrel:

```powershell
cd C:\path\to\BlocT_FuckPE

$all = "runs\all_data.csv"

# Capçalera del primer arxiu Linux
Get-Content (Get-ChildItem runs\linux_*\data_linux.csv)[0] | Select-Object -First 1 | Set-Content $all

# Totes les dades de Linux (sense capçalera)
Get-ChildItem runs\linux_*\data_linux.csv | ForEach-Object { 
    Get-Content $_ | Select-Object -Skip 1 
} | Add-Content $all

# Totes les dades de Windows (sense capçalera)
Get-ChildItem runs\windows_*\data_windows.csv | ForEach-Object { 
    Get-Content $_ | Select-Object -Skip 1 
} | Add-Content $all

Write-Host "Fusió completada: runs\all_data.csv"
(Get-Content $all).Length
```

### Estructura del CSV fusionat

**Capçalera:**
```csv
pair_id,alg,n,seed,os,run_order,run_id,wall_ms,cpu_user_ms,cpu_sys_ms,cpu_pct_avg,threads,rss_peak_mib,compiler,flags,os_name,kernel,timestamp
```

**Exemple de files:**
```csv
qs_100000,qs,100000,123456789,Linux,1,linux_run001,12.345,11.2,0.8,97.4,8,15.2,g++ 11.4.0,-O3 -march=native,Ubuntu 22.04,5.15.0-58,2023-11-09T14:30:22Z
qs_100000,qs,100000,123456789,Windows,2,win_run001,11.876,10.9,0.7,97.8,8,14.8,g++ 13.1.0,-O3 -march=native,Windows 10,19045,2023-11-09T14:31:22Z
```

---

## 7) Lectura i significat de camps clau

### Identificadors

* **`pair_id`**: Clau d'aparellament en format `{alg}_{n}`. Agrupa totes les execucions del mateix algorisme i mida.
* **`run_id`**: Identificador únic de cada execució individual.
* **`alg`**: Nom de l'algorisme (segons `config.json`).
* **`n`**: Mida de l'input.
* **`seed`**: Llavor usada per aquesta execució.

### Identificadors de sistema

* **`os`**: Sistema operatiu (`Linux` o `Windows`).
* **`run_order`**: Posició dins de l'esquema ABBA (1-4):
  * 1: Linux primera execució (A)
  * 2: Windows primera execució (B)
  * 3: Windows segona execució (B)
  * 4: Linux segona execució (A)

### Mètriques de rendiment

* **`wall_ms`**: Temps real total (wall-clock time) en mil·lisegons. És el temps que percebrà un usuari.

* **`cpu_user_ms`**: Temps de CPU gastat en mode usuari (el teu codi) en mil·lisegons.

* **`cpu_sys_ms`**: Temps de CPU gastat en mode sistema (crides al kernel) en mil·lisegons.

* **`cpu_pct_avg`**: Percentatge mitjà d'ús de CPU = `(user + sys) / wall * 100`
  * Valor proper a 100%: CPU-bound, bon ús de recursos
  * Valor baix (<80%): possibles esperes I/O o contesa de memòria

* **`threads`**: Nombre de threads hardware disponibles al sistema (informació de context).

### Mètriques de memòria

* **`rss_peak_mib`**: Pic de memòria RSS (Resident Set Size) en mebibytes (MiB).
  * RSS inclou tot el codi i dades del procés residents a RAM
  * Útil per detectar algorismes amb alt consum de memòria

### Metadades de compilació

* **`compiler`**: Versió completa del compilador (ex: `g++ (GCC) 11.4.0`).

* **`flags`**: Flags de compilació aplicades (ex: `-O3 -march=native -DNDEBUG`).

### Metadades de sistema

* **`os_name`**: Nom i versió del sistema operatiu.
  * Linux: ex: `Ubuntu 22.04.3 LTS`
  * Windows: ex: `Microsoft Windows 10 Pro`

* **`kernel`**: Versió del kernel (Linux) o build (Windows).
  * Linux: ex: `5.15.0-58-generic`
  * Windows: ex: `10.0.19045`

* **`timestamp`**: Marca temporal ISO-8601 de quan es va fer l'execució (UTC).

---

## 8) Control de qualitat i criteris d'exclusió

Per obtenir resultats fiables i reproducibles, és essencial aplicar control de qualitat rigorós.

### Condicions de l'entorn

**Estat energètic:**
* **Portàtils:** SEMPRE connectats a corrent AC durant els benchmarks
* **Sobretaula:** assegura una alimentació estable

**Modes d'estalvi d'energia:**
* **Linux:** Configura governor CPU a `performance`:
  ```bash
  sudo cpupower frequency-set -g performance
  # Verifica:
  cpupower frequency-info
  ```
* **Windows:** Perfil d'energia en "Alto rendimiento" / "High Performance"
  * Configuració > Sistema > Energía y suspensión > Configuración adicional de energía

**Processos en background:**
* Tanca navegadors, clients de correu, sincronitzadors (Dropbox, OneDrive)
* Desactiva actualitzacions automàtiques
* Desactiva antivirus en temps real (si la política de seguretat ho permet)

### Procediment de warm-up

Abans de cada sèrie de repeticions per un parell `(algorisme, n)`:
* Es realitza **1 execució de warm-up** no registrada
* Objectiu: escalfar la cache CPU, carregar llibreries dinàmiques, estabilitzar el sistema

### Cooldown entre execucions

Entre cada execució registrada:
* **Pausa de 60 segons**
* Objectiu: permetre que la CPU es refredi, evitar throttling tèrmic
* Si veus throttling persistent, incrementa a 90-120 segons

### Detecció d'outliers

**Criteri:** Mediana Absolute Deviation (MAD)

Per cada `pair_id` (agrupació per algorisme i n):
1. Calcula la mediana de `wall_ms`
2. Calcula MAD = mediana(|wall_ms - mediana|)
3. **Exclou** execucions amb |wall_ms - mediana| > 3 × MAD

**Implementació Python:**
```python
import pandas as pd
import numpy as np

df = pd.read_csv('runs/all_data.csv')

outliers = []
for pair in df['pair_id'].unique():
    subset = df[df['pair_id'] == pair]
    median = subset['wall_ms'].median()
    mad = np.median(np.abs(subset['wall_ms'] - median))
    
    # Marca outliers
    mask = np.abs(subset['wall_ms'] - median) > 3 * mad
    outliers_subset = subset[mask]
    
    if len(outliers_subset) > 0:
        print(f"⚠️  Outliers detectats a {pair}:")
        for idx, row in outliers_subset.iterrows():
            print(f"   - run_id={row['run_id']}, wall_ms={row['wall_ms']:.2f}")
        outliers.append(outliers_subset)

# Crea dataset net
if outliers:
    outliers_df = pd.concat(outliers)
    df_clean = df[~df.index.isin(outliers_df.index)]
    df_clean.to_csv('runs/all_data_clean.csv', index=False)
    print(f"\n✓ Dataset net guardat: {len(df_clean)} files (excloent {len(outliers_df)} outliers)")
else:
    print("\n✓ No s'han detectat outliers")
```

### Exclusió per error d'execució

**Criteri:** Codi de sortida ≠ 0

Si un binari retorna error:
* L'execució NO es registra al CSV
* Es mostra un warning a la consola
* Es continua amb la següent execució

**Logs:** Revisa els logs de `run_linux.sh` o `run_windows.ps1` si veus gaps als resultats.

### Política de reexecució

Si s'exclouen outliers:
* **Ideal:** Repeteix EL PARELL COMPLET (totes les execucions d'aquell `pair_id`)
* **Motiu:** Mantenir simetria de l'esquema ABBA
* **Pràctic:** Si només tens 1-2 outliers de 20 reps, pots ometre'ls sense repetir si `reps` és alt (≥20)

---

## 9) Afegir nous algorismes

### Pas 1: Crea el fitxer font

Crea `algs/<nom_algorisme>.cpp`:

```cpp
#include "metrics.hpp"
#include <vector>
#include <algorithm>
#include <random>
#include <iostream>

int main(int argc, char** argv) {
    // Validació d'arguments
    if (argc < 4) {
        std::cerr << "Ús: " << argv[0] << " <alg> <n> <seed>" << std::endl;
        return 2;
    }
    
    std::string alg = argv[1];
    long long n = std::atoll(argv[2]);
    uint64_t seed = std::strtoull(argv[3], nullptr, 10);
    
    // Preparació de dades (FORA del timer)
    std::vector<int> data(n);
    std::mt19937_64 gen(seed);
    std::uniform_int_distribution<int> dist(1, 1000000);
    
    for (long long i = 0; i < n; ++i) {
        data[i] = dist(gen);
    }
    
    // Inicialitza el resultat
    BenchResult R{};
    R.alg = alg;
    R.n = n;
    R.seed = seed;
    R.threads = (int)std::thread::hardware_concurrency();
    
    // Inicia el timer
    BenchTimer T;
    T.start();
    
    // ============================================
    // EL TEU ALGORISME AQUÍ
    // ============================================
    std::sort(data.begin(), data.end());
    // ============================================
    
    // Atura el timer i captura mètriques
    T.stop(R);
    
    // Imprimeix resultats en JSON
    print_json(R);
    
    // Opcional: validació
    bool sorted = std::is_sorted(data.begin(), data.end());
    if (!sorted) {
        std::cerr << "ERROR: Dades no ordenades!" << std::endl;
        return 1;
    }
    
    return 0;
}
```

**Notes:**
* Genera les dades ABANS de `T.start()` per no incloure el setup al benchmark
* Usa la mateixa seed per reproducibilitat
* Valida el resultat DESPRÉS de `T.stop()` per evitar incloure la validació al temps mesurat

### Pas 2: Afegeix al CMakeLists.txt

Edita `CMakeLists.txt` i afegeix:

```cmake
add_executable(nom_algorisme algs/nom_algorisme.cpp)
if (WIN32)
  target_link_libraries(nom_algorisme psapi)
endif()
```

**Exemple complet:**
```cmake
cmake_minimum_required(VERSION 3.20)
project(BlocT_FuckPE CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Flags de compilació
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")

include_directories(include)

# QuickSort
add_executable(qs algs/qs.cpp)
if (WIN32)
  target_link_libraries(qs psapi)
endif()

# MergeSort
add_executable(mergesort algs/mergesort.cpp)
if (WIN32)
  target_link_libraries(mergesort psapi)
endif()

# NOU: El teu algorisme
add_executable(nom_algorisme algs/nom_algorisme.cpp)
if (WIN32)
  target_link_libraries(nom_algorisme psapi)
endif()
```

**Nota sobre `psapi`:** A Windows, és necessari enllaçar amb aquesta llibreria per capturar mètriques de memòria RSS.

### Pas 3: Actualitza config.json

Afegeix l'algorisme a la llista:

```json
{
  "algos": [
    {"name": "qs", "bin": "qs"},
    {"name": "mergesort", "bin": "mergesort"},
    {"name": "nom_algorisme", "bin": "nom_algorisme"}
  ],
  "ns": [100000, 300000, 1000000, 3000000, 10000000],
  "reps": 20,
  "seed_master": 123456789
}
```

**Important:** El camp `bin` ha de coincidir exactament amb el nom de l'executable definit al `CMakeLists.txt`.

### Pas 4: Recompila

```bash
# Linux
cd build
cmake --build . -j

# Windows
cd build
cmake --build . -j
```

### Pas 5: Prova manual

Abans d'executar el pipeline complet, prova el binari manualment:

```bash
# Linux
./build/nom_algorisme test_alg 10000 42

# Windows
.\build\nom_algorisme.exe test_alg 10000 42
```

Hauries de veure una sortida JSON amb les mètriques.

### Pas 6: Executa el pipeline

```bash
# Linux
./run_linux.sh

# Windows
.\run_windows.ps1
```

Els resultats inclouran el nou algorisme.

---

## 10) Recollida de metadades de l'equip

Per documentar correctament els experiments, necessites recollir informació detallada del hardware.

### Windows

#### Sistema Operatiu i Build

Ja es registra automàticament al CSV (`os_name`, `kernel`), però pots obtenir més detalls:

```powershell
# Versió completa
systeminfo | findstr /C:"OS Name" /C:"OS Version" /C:"System Type"

# Build exacte
[System.Environment]::OSVersion
```

#### CPU

```powershell
# Informació bàsica
Get-WmiObject Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed

# Model exacte
wmic cpu get name
```

**Recomanat:** Usa **CPU-Z** (gratuït) per obtenir:
* Model de CPU
* Freqüència base i turbo
* Cache L1/L2/L3
* Arquitectura i procés de fabricació

#### RAM i Configuració

**PowerShell:**
```powershell
# Informació bàsica
Get-WmiObject Win32_PhysicalMemory | Select-Object Capacity, Speed, Manufacturer, PartNumber | Format-Table

# Total RAM
(Get-WmiObject Win32_ComputerSystem).TotalPhysicalMemory / 1GB
```

**CPU-Z (pestanya Memory):**
* Capacitat total
* Tipus (DDR4, DDR5)
* Freqüència efectiva
* Timings (CL-tRCD-tRP-tRAS)
* Nombre de canals (single, dual, quad)
* Configuració dels slots

#### Disc i Sistema de Fitxers

```powershell
# Tipus de disc (SSD/HDD), interfície
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, Size | Format-Table

# Volums i sistema de fitxers
Get-Volume | Select-Object DriveLetter, FileSystem, Size, SizeRemaining | Format-Table

# Espai lliure
Get-PSDrive -PSProvider FileSystem
```

### Linux

#### Sistema Operatiu i Kernel

Ja es registra automàticament, però per més detalls:

```bash
# Distribució
cat /etc/os-release

# Kernel exacte
uname -a

# Versió del kernel amb configuració
cat /proc/version
```

#### CPU

```bash
# Informació detallada
lscpu

# Model exacte
cat /proc/cpuinfo | grep "model name" | head -n 1

# Freqüències actuals
watch -n 1 'cat /proc/cpuinfo | grep MHz'

# Governor actiu
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

#### RAM i Timings

```bash
# Capacitat total i disponible
free -h

# Informació detallada (requereix sudo)
sudo dmidecode --type memory | grep -E "Size:|Type:|Speed:|Manufacturer:"

# Timings SPD (requereix i2c-tools)
sudo modprobe eeprom
sudo decode-dimms
```

**Output esperat de `dmidecode`:**
```
Size: 16384 MB
Type: DDR4
Speed: 3200 MT/s
Manufacturer: Corsair
```

#### Disc, Sistema de Fitxers i Espai

```bash
# Llistat de discos amb model i interfície
lsblk -o NAME,MODEL,TRAN,TYPE,SIZE,FSTYPE

# Tipus de disc (rotacional = HDD, 0 = SSD)
cat /sys/block/sda/queue/rotational

# Muntatges i sistemes de fitxers
df -Th

# Espai lliure detallat
df -h
```

**Per informació SMART (salut del disc):**
```bash
sudo apt install smartmontools
sudo smartctl -a /dev/sda
```

### Taula resum recomanada

Crea un document o secció a l'informe amb aquesta informació:

| Component | Windows | Linux |
|-----------|---------|-------|
| **CPU** | Intel Core i7-11700K @ 3.6 GHz (8C/16T) | (mateix) |
| **RAM** | 32 GB DDR4-3200 (2x16GB, dual channel) CL16-18-18-38 | (mateix) |
| **Disc** | Samsung 980 PRO 1TB (NVMe, PCIe 4.0) | (mateix) |
| **OS** | Windows 10 Pro 22H2 (Build 19045.3693) | Ubuntu 22.04.3 LTS |
| **Kernel** | - | 5.15.0-91-generic |
| **GCC** | 13.1.0 (MSYS2) | 11.4.0 |
| **Filesystem** | NTFS | ext4 |

---

## 11) Validació ràpida del pipeline

Abans d'executar els experiments complets (que poden durar hores), és recomanable fer una validació ràpida.

### Pas 1: Configuració de prova

Crea un `config.json` de test:

```json
{
  "algos": [
    {"name": "qs", "bin": "qs"}
  ],
  "ns": [1000, 10000],
  "reps": 3,
  "seed_master": 123456789
}
```

### Pas 2: Compila amb flags de producció

```bash
# Linux
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j

# Verifica flags
strings qs | grep -i "gcc\|g++"
```

```powershell
# Windows
cd build
cmake .. -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build . -j
```

**Flags esperades:** `-O3 -march=native -DNDEBUG`

### Pas 3: Executa als dos SO

```bash
# Linux
./run_linux.sh
```

```powershell
# Windows
.\run_windows.ps1
```

**Temps estimat:** ~5 minuts per SO (amb cooldown de 60s)

### Pas 4: Verifica els CSV

```bash
# Linux
cat runs/linux_*/data_linux.csv | head -n 10
wc -l runs/linux_*/data_linux.csv

# Compte de files esperat: 1 (capçalera) + 2 algorismes × 2 ns × 3 reps × 2 OS (ABBA) = 13
```

```powershell
# Windows
Get-Content runs\windows_*\data_windows.csv | Select-Object -First 10
(Get-Content runs\windows_*\data_windows.csv).Length
```

### Pas 5: Valida la fusió

```bash
# Fusiona
head -n 1 runs/linux_*/data_linux.csv | head -n 1 > runs/all_data.csv
tail -q -n +2 runs/linux_*/data_linux.csv >> runs/all_data.csv
tail -q -n +2 runs/windows_*/data_windows.csv >> runs/all_data.csv

# Verifica
wc -l runs/all_data.csv
# Esperat: 1 + (1 alg × 2 ns × 3 reps × 2 SO × 2 passades ABBA) = 1 + 24 = 25 files
```

### Pas 6: Comprova camps clau

```python
import pandas as pd

df = pd.read_csv('runs/all_data.csv')

print("=== Resum ===")
print(f"Total files: {len(df)}")
print(f"Algorismes: {df['alg'].unique()}")
print(f"SOs: {df['os'].unique()}")
print(f"Run orders: {sorted(df['run_order'].unique())}")

print("\n=== Compiladors ===")
print(df.groupby('os')['compiler'].first())

print("\n=== Flags ===")
print(df.groupby('os')['flags'].first())

print("\n=== Mètriques (exemple) ===")
print(df[['pair_id', 'os', 'wall_ms', 'cpu_user_ms', 'rss_peak_mib']].head(10))

# Validacions
assert set(df['run_order'].unique()) == {1, 2, 3, 4}, "Esquema ABBA incomplet!"
assert df['wall_ms'].notna().all(), "Hi ha valors buits a wall_ms!"
assert df['rss_peak_mib'].notna().all(), "Hi ha valors buits a rss_peak_mib!"
assert (df.groupby(['pair_id', 'os']).size() >= 3).all(), "Falten repeticions!"

print("\n✓ Validació superada!")
```

**Si tot està correcte:** Modifica `config.json` als valors de producció i executa els experiments finals.

---

## 12) Resolució d'incidències

### Problema: `jq: command not found` (Linux)

**Causa:** El paquet `jq` no està instal·lat.

**Solució:**
```bash
sudo apt install jq          # Ubuntu/Debian
sudo dnf install jq          # Fedora
sudo pacman -S jq            # Arch Linux
```

### Problema: `cpupower` sense permisos (Linux)

**Causa:** Configurar el governor CPU requereix permisos d'administrador.

**Solucions:**

1. **Executar l'script amb sudo** (no recomanat per seguretat):
   ```bash
   sudo ./run_linux.sh
   ```

2. **Configurar sudo sense password per cpupower** (recomanat):
   ```bash
   sudo visudo
   # Afegeix al final:
   yourusername ALL=(ALL) NOPASSWD: /usr/bin/cpupower
   ```

3. **Ignorar** (l'script continua sense governor performance, però amb més variabilitat):
   * L'script mostra un warning però continua
   * Accepta resultats amb més variança

### Problema: `g++` diferent entre SO

**Causa:** Versions diferents de GCC als dos sistemes.

**Solució 1 - Alinear versions:**

* **Linux:** Instal·la la versió específica:
  ```bash
  sudo apt install g++-13
  sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 100
  ```

* **Windows (MSYS2):** Actualitza o downgrada:
  ```bash
  pacman -S mingw-w64-x86_64-gcc
  ```

**Solució 2 - Usar Docker/contenidors:**

Crea un `Dockerfile` amb toolchain fix:
```dockerfile
FROM gcc:13.2
RUN apt-get update && apt-get install -y cmake jq python3
WORKDIR /workspace
```

### Problema: `run_windows.ps1` bloquejat per política d'execució

**Causa:** PowerShell bloqueja scripts no signats.

**Solució:**
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Nota:** No utilitzis `Unrestricted` per seguretat. `RemoteSigned` permet scripts locals.

### Problema: Binaris no trobats

**Causa:** El nom del binari a `config.json` no coincideix amb el del `CMakeLists.txt`.

**Diagnòstic:**
```bash
# Linux
ls -lh build/
cat config.json | jq '.algos'

# Windows
dir build\
Get-Content config.json | ConvertFrom-Json | Select-Object -ExpandProperty algos
```

**Solució:** Assegura't que `config.json` tingui:
```json
{"name": "etiqueta", "bin": "nom_executable_sense_extensio"}
```

I `CMakeLists.txt` tingui:
```cmake
add_executable(nom_executable_sense_extensio algs/fitxer.cpp)
```

### Problema: Outliers freqüents (>10% de les execucions)

**Causes possibles:**
* Processos en background actius
* Throttling tèrmic
* Governor CPU incorrecte
* Sistema no estable

**Solucions:**

1. **Incrementa cooldown:**
   Edita `run_linux.sh` i `run_windows.ps1`:
   ```bash
   COOLDOWN=90  # o 120
   ```

2. **Tanca processos:**
   ```bash
   # Linux: revisa processos CPU-intensive
   top
   htop
   
   # Windows: Task Manager > Detalls > CPU
   ```

3. **Millora refrigeració:**
   * Usa suport refrigerat per portàtils
   * Neteja ventiladors
   * Comprova pasta tèrmica

4. **Comprova temperatura:**
   ```bash
   # Linux
   sensors
   
   # Windows
   # Usa HWMonitor o similar
   ```

5. **Verifica governor:**
   ```bash
   # Linux
   cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   # Tots han de dir "performance"
   ```

### Problema: Temps d'execució massa llarg

**Causa:** Configuració amb massa repeticions o mides d'input grans.

**Solució:**

Estima el temps total:
```
temps_total ≈ (n_algos × n_sizes × n_reps × 2_SO × avg_time_per_run + cooldown) × 2_passades_ABBA
```

Exemple:
* 2 algorismes × 5 mides × 20 reps × 2 SO = 400 execucions
* Si cada execució dura ~10s i cooldown 60s → ~7 hores

**Optimitzacions:**
* Redueix `reps` a 10-15 per proves
* Usa `ns` més petits per validació
* Executa en paral·lel a diferents màquines (NO al mateix temps en dual boot)

---

## 13) Bones pràctiques d'execució

### Configuració de l'entorn

#### Perfil d'energia

* **Linux:**
  ```bash
  sudo cpupower frequency-set -g performance
  sudo cpupower idle-set -D 0  # Desactiva C-states profunds (opcional)
  ```

* **Windows:**
  * Configuració > Sistema > Energía > Perfil "Alto rendimiento"
  * O via PowerShell:
    ```powershell
    powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
    ```

#### Estabilitat tèrmica

* **Portàtils:** Usa sempre suport refrigerat o base elevada
* **Sobretaula:** Assegura bon flux d'aire
* **Monitor temperatura:** No superis 85°C (idealment <75°C)

#### Conectivitat

* **Desconnecta WiFi/Ethernet** durant l'execució (si no fas servir remote desktop)
  ```bash
  # Linux
  sudo systemctl stop NetworkManager
  
  # Windows
  # Desactiva l'adaptador de xarxa temporalment
  ```

* **Desactiva sincronitzadors:** Dropbox, OneDrive, Google Drive, etc.

### Processos en background

#### Linux

Mata processos no essencials:
```bash
# Revisa què consumeix CPU
top
htop

# Atura serveis no crítics
sudo systemctl stop cron
sudo systemctl stop cups
sudo systemctl stop bluetooth

# Restaura després
sudo systemctl start <service>
```

#### Windows

* Tanca **Task Manager > Processos** que consumeixin CPU
* Desactiva **Windows Update** temporalment
* Desactiva **Windows Defender** durant l'execució (si la política ho permet):
  ```powershell
  Set-MpPreference -DisableRealtimeMonitoring $true
  # Recorda activar-lo després!
  Set-MpPreference -DisableRealtimeMonitoring $false
  ```

### Planificació de l'execució

#### Durant el dia

* **NO utilitzar la màquina** durant l'execució
* **NO moure el portàtil** (vibració pot afectar discos HDD)
* **Bloqueig d'entrada:** Considera `xscreensaver -lock` (Linux) o bloquejar Windows

#### Durant la nit

* **Configura inhibidors de suspensió:**
  ```bash
  # Linux
  systemd-inhibit ./run_linux.sh
  
  # Windows
  # Desactiva suspensió temporal a Configuració > Energía
  ```

* **Logs:** Redirigeix la sortida a un fitxer per revisar al matí:
  ```bash
  ./run_linux.sh > benchmark.log 2>&1
  ```

### Verificació post-execució

Després de completar els benchmarks:

1. **Revisa logs** per errors o warnings
2. **Comprova recompte de files** als CSV
3. **Executa script de detecció d'outliers**
4. **Revisa temperatura** màxima assolida (si tens logs tèrmics)
5. **Restaura configuració del sistema:**
   ```bash
   # Linux
   sudo cpupower frequency-set -g powersave
   sudo systemctl start NetworkManager
   
   # Windows
   Set-MpPreference -DisableRealtimeMonitoring $false
   ```

---

## 14) Exportació a l'informe

Quan documentis els resultats en un informe acadèmic o tècnic:

### Secció 1: Metadades de l'experiment

**Inclou:**
* **Data i hora** de les execucions
* **Hardware:** CPU, RAM, disc (veure secció 10)
* **Software:** 
  * Versions de GCC als dos SO
  * Versions dels SO i kernels
  * Flags de compilació exactes
* **Configuració:** Valors de `config.json` (algorismes, ns, reps, seed_master)

**Exemple:**
```
Experiments realitzats el 9 de novembre de 2023 entre les 14:00 i les 22:00 UTC.

Hardware:
- CPU: Intel Core i7-11700K @ 3.6 GHz (8 cores, 16 threads)
- RAM: 32 GB DDR4-3200 (dual channel, CL16-18-18-38)
- Disc: Samsung 980 PRO 1TB NVMe (PCIe 4.0)

Software:
- Linux: Ubuntu 22.04.3 LTS, kernel 5.15.0-91-generic, GCC 11.4.0
- Windows: Windows 10 Pro 22H2 (Build 19045.3693), GCC 13.1.0 (MSYS2)
- Flags de compilació: -O3 -march=native -DNDEBUG

Configuració dels experiments:
- Algorismes: QuickSort, MergeSort
- Mides d'input: 100k, 300k, 1M, 3M, 10M elements
- Repeticions: 20 per cada parell (algorisme, mida)
- Llavor mestra: 123456789
```

### Secció 2: Metodologia

**Descriu:**
* **Esquema ABBA:**
  ```
  Per reduir el biaix temporal, s'ha aplicat l'esquema ABBA:
  - Ordre 1: Linux (A)
  - Ordre 2: Windows (B)
  - Ordre 3: Windows (B)
  - Ordre 4: Linux (A)
  Amb cooldown de 60 segons entre execucions i warm-up previ.
  ```

* **Política d'exclusió d'outliers:**
  ```
  S'han exclòs execucions amb |wall_ms - mediana| > 3 × MAD per cada parell,
  on MAD = mediana(|wall_ms - mediana|). Això representa X% de les execucions.
  ```

* **Condicions de l'entorn:**
  ```
  - Portàtil connectat a AC
  - Governor CPU en mode "performance" (Linux)
  - Processos en background minimitzats
  - Antivirus desactivat durant les proves
  ```

### Secció 3: Estructura de dades

**Mostra la capçalera del CSV:**
```csv
pair_id,alg,n,seed,os,run_order,run_id,wall_ms,cpu_user_ms,cpu_sys_ms,cpu_pct_avg,threads,rss_peak_mib,compiler,flags,os_name,kernel,timestamp
```

**Descripció dels camps:**
* `pair_id`: Clau d'aparellament (algorisme_n)
* `wall_ms`: Temps real en mil·lisegons
* `cpu_user_ms`: Temps CPU en mode usuari
* `cpu_sys_ms`: Temps CPU en mode sistema
* `cpu_pct_avg`: Percentatge mitjà d'ús de CPU
* `rss_peak_mib`: Pic de memòria RSS en MiB
* `run_order`: Posició dins l'esquema ABBA (1-4)
* (Descriu la resta segons secció 7)

### Secció 4: Mostra de dades

**Inclou 3-5 files representatives:**

```csv
pair_id,alg,n,os,run_order,wall_ms,cpu_user_ms,cpu_sys_ms,rss_peak_mib
qs_100000,qs,100000,Linux,1,12.345,11.2,0.8,15.2
qs_100000,qs,100000,Windows,2,11.876,10.9,0.7,14.8
qs_100000,qs,100000,Windows,3,11.902,11.1,0.6,14.9
qs_100000,qs,100000,Linux,4,12.298,11.3,0.7,15.1
```

### Secció 5: Estadístiques descriptives

**Genera taules resum:**

```python
import pandas as pd

df = pd.read_csv('runs/all_data_clean.csv')

summary = df.groupby(['alg', 'n', 'os'])['wall_ms'].agg([
    ('count', 'count'),
    ('mean', 'mean'),
    ('std', 'std'),
    ('median', 'median'),
    ('min', 'min'),
    ('max', 'max')
]).reset_index()

summary.to_csv('summary_stats.csv', index=False)
print(summary.to_markdown(index=False))
```

**Output esperat:**
```
| alg       | n       | os      | count | mean    | std   | median  | min     | max     |
|-----------|---------|---------|-------|---------|-------|---------|---------|---------|
| qs        | 100000  | Linux   | 40    | 12.34   | 0.45  | 12.30   | 11.80   | 13.20   |
| qs        | 100000  | Windows | 40    | 11.89   | 0.38  | 11.87   | 11.20   | 12.60   |
| ...       | ...     | ...     | ...   | ...     | ...   | ...     | ...     | ...     |
```

### Secció 6: Visualitzacions

**Genera gràfics:**

```python
import matplotlib.pyplot as plt
import seaborn as sns

# Box plot per algorisme i SO
plt.figure(figsize=(12, 6))
sns.boxplot(data=df, x='n', y='wall_ms', hue='os')
plt.title('Distribució de temps d\'execució per mida d\'input i SO')
plt.xlabel('Mida d\'input (n)')
plt.ylabel('Temps (ms)')
plt.yscale('log')
plt.legend(title='Sistema Operatiu')
plt.tight_layout()
plt.savefig('boxplot_performance.png', dpi=300)
plt.show()

# Línia de mediana
summary_median = df.groupby(['alg', 'n', 'os'])['wall_ms'].median().reset_index()
plt.figure(figsize=(12, 6))
for os in summary_median['os'].unique():
    subset = summary_median[summary_median['os'] == os]
    plt.plot(subset['n'], subset['wall_ms'], marker='o', label=os)
plt.title('Mediana de temps d\'execució vs mida d\'input')
plt.xlabel('Mida d\'input (n)')
plt.ylabel('Temps (ms)')
plt.xscale('log')
plt.yscale('log')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('median_scaling.png', dpi=300)
plt.show()
```

### Secció 7: Interpretació

**Discuteix:**
* Diferències de rendiment entre SO
* Escalabilitat dels algorismes
* Comportament de memòria (RSS)
* Overhead de sistema (cpu_sys_ms)
* Limitacions i threats to validity

**Exemple:**
```
QuickSort mostra un rendiment 3.6% més ràpid a Windows per n=1M,
possiblement degut a diferències en l'allocador de memòria (tcmalloc vs ptmalloc).
L'escalabilitat és O(n log n) com s'esperava, amb desviació estàndard <5%
després d'exclusió d'outliers.
```

---

## Apèndix: Referència ràpida de comandes

### Compilació

```bash
# Linux
mkdir -p build && cd build && cmake .. && cmake --build . -j

# Windows
mkdir build; cd build; cmake .. -G "MinGW Makefiles"; cmake --build . -j
```

### Execució

```bash
# Linux
./run_linux.sh

# Windows
.\run_windows.ps1
```

### Fusió de resultats

```bash
# Linux
head -n 1 runs/linux_*/data_linux.csv | head -n 1 > runs/all_data.csv
tail -q -n +2 runs/linux_*/data_linux.csv >> runs/all_data.csv
tail -q -n +2 runs/windows_*/data_windows.csv >> runs/all_data.csv

# Windows
$all = "runs\all_data.csv"
Get-Content (Get-ChildItem runs\linux_*\data_linux.csv)[0] | Select -First 1 | Set-Content $all
Get-ChildItem runs\linux_*\data_linux.csv | % { Get-Content $_ | Select -Skip 1 } | Add-Content $all
Get-ChildItem runs\windows_*\data_windows.csv | % { Get-Content $_ | Select -Skip 1 } | Add-Content $all
```

### Detecció d'outliers

```python
import pandas as pd
import numpy as np

df = pd.read_csv('runs/all_data.csv')
for pair in df['pair_id'].unique():
    subset = df[df['pair_id'] == pair]
    median = subset['wall_ms'].median()
    mad = np.median(np.abs(subset['wall_ms'] - median))
    mask = np.abs(subset['wall_ms'] - median) > 3 * mad
    if mask.any():
        print(f"⚠️  {pair}: {mask.sum()} outliers")
```

### Configuració del governor (Linux)

```bash
sudo cpupower frequency-set -g performance
```

### Verificació de binaris

```bash
# Linux
ls -lh build/
./build/qs test 1000 42

# Windows
dir build\
.\build\qs.exe test 1000 42
```

---

## Suport i contribucions

Per reportar problemes o suggerir millores:
* Obre un issue al repositori de GitHub
* Consulta el README.md per informació bàsica
* Revisa aquesta documentació per solucions comunes

---

**Versió del manual:** 1.0  
**Data:** Novembre 2023  
**Autors:** Equip BlocT_FuckPE  
**Llicència:** Segons repositori

---

**Fi del manual. Bon benchmarking! 🚀**
