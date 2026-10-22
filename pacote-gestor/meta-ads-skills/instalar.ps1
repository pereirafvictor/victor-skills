# Instala as skills de Meta Ads no Claude Code (Windows).
# Uso: clique com o botao direito > "Executar com o PowerShell"
#      ou: powershell -ExecutionPolicy Bypass -File instalar.ps1

$ErrorActionPreference = "Stop"
$origem = Join-Path $PSScriptRoot "skills"
$destino = Join-Path $HOME ".claude\skills"
$config = Join-Path $HOME ".meta-ads"

Write-Host "`n== Skills Meta Ads ==`n"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "X Python nao encontrado. Instale em https://www.python.org/downloads/ (marque 'Add to PATH') e rode de novo."
    exit 1
}

New-Item -ItemType Directory -Force $destino | Out-Null
foreach ($skill in Get-ChildItem $origem -Directory) {
    $alvo = Join-Path $destino $skill.Name
    if (Test-Path $alvo) { Remove-Item -Recurse -Force $alvo }
    Copy-Item -Recurse $skill.FullName $alvo
    Write-Host "OK skill $($skill.Name)"
}

python -m pip install --quiet -r (Join-Path $PSScriptRoot "requirements.txt")
Write-Host "OK dependencias Python"

New-Item -ItemType Directory -Force $config | Out-Null
$envFile = Join-Path $config ".env"
if (-not (Test-Path $envFile)) {
    "META_ACCESS_TOKEN=" | Out-File -Encoding utf8 $envFile
    Write-Host "OK criado $envFile (cole seu token nele)"
} else {
    Write-Host "OK $envFile ja existe (mantido)"
}

Write-Host "`nPronto! Abra o Claude Code e diga: configura meu meta ads`n"
