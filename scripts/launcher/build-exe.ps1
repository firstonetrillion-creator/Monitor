$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$source = Join-Path $PSScriptRoot "CerradoAbertoLauncher.cs"
$output = Join-Path $repoRoot "CerradoAberto.exe"
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"

if (-not (Test-Path $csc)) {
    throw "Compilador C# do .NET Framework nao encontrado em $csc"
}

& $csc /nologo /optimize+ /target:exe /out:$output $source
if ($LASTEXITCODE -ne 0) {
    throw "Falha ao compilar $output"
}

Write-Host "Gerado com sucesso: $output"
