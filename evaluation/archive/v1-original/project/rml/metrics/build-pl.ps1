# Compila ogni metrica .rml nel modulo Prolog .pl corrispondente.
# Compilatore vendorizzato in vendor/rml-compiler/.
$ErrorActionPreference = 'Stop'
$metricsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $metricsDir '..\..')).Path
$compiler = Join-Path $repoRoot 'vendor\rml-compiler\bin\rml-compiler'

if (-not (Test-Path $compiler)) { throw "compilatore RML non trovato: $compiler" }

Get-ChildItem (Join-Path $metricsDir '*.rml') | ForEach-Object {
    $pl = Join-Path $metricsDir ($_.BaseName + '.pl')
    # Non usare `> $pl`: PS 5.1 scrive UTF-16LE e SWI-Prolog non legge.
    # Si cattura l'output e si scrive UTF-8 senza BOM.
    $out = & java -cp (Join-Path $repoRoot 'vendor\rml-compiler\lib\*') compiler.MainKt --input $_.FullName 2>&1
    if ($LASTEXITCODE -ne 0) { throw "compilazione fallita: $($_.Name)`n$out" }
    [System.IO.File]::WriteAllText($pl, ($out -join "`n") + "`n", (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "compilato $($_.Name) -> $([System.IO.Path]::GetFileName($pl))"
}
