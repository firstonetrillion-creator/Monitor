<#
.SYNOPSIS
    Rotina operacional de atualização incremental semanal do Cerrado Aberto (Fase 4 / ADR-007).
.DESCRIPTION
    1. Executa a coleta incremental educada do Nexlegis (`>= 3,0s` entre requisições) para o ano ativo.
    2. Persiste o bruto imutável em `data/raw/` (com sanitização LGPD) e atualiza o PostgreSQL 16 de forma idempotente.
    3. Executa verificação de qualidade e testes da API antes de encerrar.
.EXAMPLE
    .\scripts\atualizar-semana.ps1 -MunicipioId inhumas-go -Ano 2026
#>
param(
    [string]$MunicipioId = "inhumas-go",
    [int]$Ano = 2026,
    [double]$CrawlDelay = 3.0,
    [switch]$PularTestes
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $RepoRoot

try {
    Write-Host "[Cerrado Aberto] Iniciando atualização incremental semanal ($MunicipioId / $Ano)..." -ForegroundColor Cyan
    uv run --directory apps/coleta python -m cerrado_aberto_coleta.nexlegis.incremental `
        --municipio-id $MunicipioId `
        --ano $Ano `
        --crawl-delay $CrawlDelay

    if (-not $PularTestes) {
        Write-Host "[Cerrado Aberto] Validando testes automatizados de qualidade e LGPD..." -ForegroundColor Cyan
        uv run --directory apps/coleta pytest -q tests/test_nexlegis_incremental.py
        uv run --directory apps/api ruff check src tests
    }

    Write-Host "[Cerrado Aberto] Atualização semanal concluída com sucesso." -ForegroundColor Green
} finally {
    Pop-Location
}
