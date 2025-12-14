# run_windows.ps1
$ErrorActionPreference = "Stop"
[System.Threading.Thread]::CurrentThread.CurrentCulture = [System.Globalization.CultureInfo]::InvariantCulture
[System.Threading.Thread]::CurrentThread.CurrentUICulture = [System.Globalization.CultureInfo]::InvariantCulture
$InvariantCulture = [System.Globalization.CultureInfo]::InvariantCulture

$ROOT   = Split-Path -Parent $MyInvocation.MyCommand.Path
$CFG    = Join-Path $ROOT "config.json"
$OUTDIR = Join-Path $ROOT ("runs\windows_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $OUTDIR | Out-Null

# Metadata OS / compiler
$osInfo = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
$OSName = $osInfo.ProductName
$Build  = $osInfo.CurrentBuild
$UBR    = $osInfo.UBR
$OSFull = "$OSName Build $Build.$UBR"
$GccVer = (g++ --version | Select-Object -First 1)

# Parse JSON (PowerShell has native JSON support)
$cfgObj     = Get-Content $CFG | ConvertFrom-Json
$algos      = $cfgObj.algos
$defaultNs  = $cfgObj.ns
$reps       = [int]$cfgObj.reps
$seedBase   = [uint64]$cfgObj.seed_master
$WarmupRuns = 5

$CSV = Join-Path $OUTDIR "data_windows.csv"
"pair_id,alg,n,seed,os,run_order,run_id,wall_ms,cpu_user_ms,cpu_sys_ms,cpu_pct_avg,threads,rss_peak_mib,temp_c,compiler,flags,os_name,kernel,timestamp" | Out-File -Encoding UTF8 $CSV

function Cooldown { Start-Sleep -Seconds 10 }

function Get-CpuTemperature {
  $sources = @(
    @{
      Namespace = "root\wmi"
      Class     = "MSAcpi_ThermalZoneTemperature"
      Extract   = {
        param($items)
        if (-not $items) { return $null }
        $avgKelvin = ($items.CurrentTemperature | Measure-Object -Average).Average
        if ($null -eq $avgKelvin) { return $null }
        return ($avgKelvin - 2732) / 10.0
      }
    },
    @{
      Namespace = "root\wmi"
      Class     = "Lenovo_WMI_ThermalSensor"
      Extract   = {
        param($items)
        if (-not $items) { return $null }
        $avg = ($items.CurrentReading | Measure-Object -Average).Average
        if ($null -eq $avg) { return $null }
        return $avg / 10.0
      }
    }
  )

  foreach ($source in $sources) {
    try {
      $data = Get-CimInstance -Namespace $source.Namespace -ClassName $source.Class -ErrorAction Stop
      $value = & $source.Extract $data
      if ($null -ne $value) {
        return [Math]::Round($value, 2)
      }
    } catch {
      continue
    }
  }
  return "NA"
}

function Format-Decimal {
  param(
    [double]$Value,
    [int]$Digits = 3
  )
  $format = "{0:F$Digits}"
  return [string]::Format($InvariantCulture, $format, $Value)
}

function Escape-Csv {
  param([string]$Value)
  if ($null -eq $Value) { return "" }
  if ($Value -match '[,"]') {
    $escaped = $Value -replace '"','""'
    return '"{0}"' -f $escaped
  }
  return $Value
}

function Run-Once {
  param(
    [string]$Alg,[string]$Bin,[long]$N,[uint64]$Seed,[int]$Order,[string]$RunId
  )
  $exe = Join-Path $ROOT "build\$Bin.exe"
  $ts  = Get-Date -Format "s"

  for ($w = 0; $w -lt $WarmupRuns; $w++) {
    & $exe $Alg $N ($Seed + [uint64]$w) | Out-Null
  }

  # Actual execution
  $pinfo = New-Object System.Diagnostics.ProcessStartInfo
  $pinfo.FileName = $exe
  $pinfo.Arguments = "$Alg $N $Seed"
  $pinfo.RedirectStandardOutput = $true
  $pinfo.UseShellExecute = $false
  $pinfo.CreateNoWindow = $true

  $p = New-Object System.Diagnostics.Process
  $p.StartInfo = $pinfo
  [void]$p.Start()
  try {
    $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::High
  } catch {
    Write-Warning "Could not set process priority to High: $($_.Exception.Message)"
  }
  $out = $p.StandardOutput.ReadToEnd()
  $p.WaitForExit()

  $json = $out | ConvertFrom-Json
  $wall = [double]$json.wall_ms
  $cpuu = [double]$json.cpu_user_ms
  $cpus = [double]$json.cpu_sys_ms
  $rss  = [double]$json.rss_peak_mib
  $thr  = [int]$json.threads
  if ($thr -le 0) { $thr = [Environment]::ProcessorCount }
  $cpuPct = 0.0
  if ($wall -gt 0 -and $thr -gt 0) {
    $cpuPct = [Math]::Round((($cpuu + $cpus) / ($wall * $thr)) * 100, 2)
  }

  $flags = "-O3 -march=native -DNDEBUG"
  $temp = Get-CpuTemperature
  if ($null -eq $temp -or $temp -eq "") { $temp = "NA" }

  $wallStr  = Format-Decimal $wall 3
  $cpuuStr  = Format-Decimal $cpuu 3
  $cpusStr  = Format-Decimal $cpus 3
  $cpuPctStr = Format-Decimal $cpuPct 2
  $rssStr   = Format-Decimal $rss 3
  if ($temp -isnot [string]) {
    $temp = Format-Decimal $temp 2
  }

  $fields = @(
    "{0}_{1}" -f $Alg, $N
    $Alg
    $N
    $Seed
    "Windows"
    $Order
    $RunId
    $wallStr
    $cpuuStr
    $cpusStr
    $cpuPctStr
    $thr
    $rssStr
    $temp
    (Escape-Csv $GccVer)
    (Escape-Csv $flags)
    (Escape-Csv $OSFull)
    "N/A"
    (Escape-Csv $ts)
  )

  Add-Content -Path $CSV -Value ($fields -join ",")
}

$runCounter = 1
foreach ($a in $algos) {
  $alg = $a.name; $bin = $a.bin
  $targets = if ($a.ns) { $a.ns } elseif ($defaultNs) { $defaultNs } else { @() }
  foreach ($n in $targets) {
    for ($r=1; $r -le $reps; $r++) {
      $seed = $seedBase + [uint64]$r
      # Windows ordering within ABBA scheme: 2 and 3
      Run-Once -Alg $alg -Bin $bin -N $n -Seed $seed -Order 2 -RunId $runCounter
      $runCounter++
      Cooldown
      Run-Once -Alg $alg -Bin $bin -N $n -Seed $seed -Order 3 -RunId $runCounter
      $runCounter++
      Cooldown
    }
  }
}

Write-Host "Results at: $CSV"
