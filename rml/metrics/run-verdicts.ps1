# Rigenera .pl, esegue ogni metrica su traccia ok e fail, confronta verdetti.
# Uso: .\run-verdicts.ps1
# traces/: un evento MIDI JSONL per riga; ok=Main soddisfatta, fail=Main violata.
# Monitor RML: exit 0 = conforme, exit 1 = violata.
$ErrorActionPreference = 'Stop'
$metricsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tracesDir = Join-Path $metricsDir 'traces'
$monitorDir = (Resolve-Path (Join-Path $metricsDir '..\monitor')).Path -replace '\\', '/'

$failed = @()
foreach ($rml in Get-ChildItem (Join-Path $metricsDir '*.rml') | Sort-Object Name) {
    $name = $rml.BaseName
    $pl = Join-Path $metricsDir "$name.pl"
    if (-not (Test-Path $pl)) {
        Write-Host "$name`: SKIP (nessun .pl, lancia build-pl.ps1)" -ForegroundColor Yellow
        $failed += $name
        continue
    }
    foreach ($case in @('ok', 'fail')) {
        $trace = Join-Path $tracesDir "$name.$case.jsonl"
        if (-not (Test-Path $trace)) {
            Write-Host "$name/$case`: SKIP (manca $trace)" -ForegroundColor Yellow
            $failed += "$name/$case"
            continue
        }
        # Ordine obbligato: spec, trace, poi flag — prima fallisce load_spec.
        $out = & swipl -O -p monitor="$monitorDir" "$monitorDir/monitor.pl" -- $pl $trace --silent 2>&1
        $code = $LASTEXITCODE
        $expect = if ($case -eq 'ok') { 0 } else { 1 }
        if ($code -eq $expect) {
            Write-Host ("{0,-20} {1,-4} OK  exit={2}" -f $name, $case, $code)
        }
        else {
            Write-Host ("{0,-20} {1,-4} FAIL atteso exit={2} ottenuto {3} :: {4}" -f $name, $case, $expect, $code, ($out | Select-Object -Last 1)) -ForegroundColor Red
            $failed += "$name/$case"
        }
    }
}

if ($failed.Count -gt 0) {
    Write-Host "`nverdetti inattesi: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "`ntutti i verdetti sono quelli attesi" -ForegroundColor Green
