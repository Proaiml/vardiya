# Serbest yazilmis gun ifadelerinde harness stratejilerini karsilastirir.
#   powershell -File scripts\strategy_sweep.ps1 -Model ollama:qwen3:8b -Split dev
# Yalnizca modele ihtiyac duyan iki aile kosulur; sonuc results\strategy-<split>.jsonl dosyasina eklenir.
param(
    [string]$Model = "ollama:qwen3:8b",
    [string]$Split = "dev",
    [int]$PerFamily = 30,
    [int]$Seed = 2,
    [string[]]$Variants = @("single", "agree2", "vote3", "rule", "rule-gloss", "rulecheck", "rulecheck-gloss"),
    [int]$Budget = 500,
    [switch]$Think
)
$Variants = @($Variants | ForEach-Object { $_ -split "," } | Where-Object { $_ })  # -File ile gelen "a,b,c" tek dizgedir
$out = "results\strategy-$Split.jsonl"
$start = Get-Date
foreach ($v in $Variants) {
    $left = $Budget - [int]((Get-Date) - $start).TotalSeconds
    if ($left -lt 20) { "butce doldu, kalan strateji: $v ve sonrasi"; exit 3 }
    $extra = @(); if ($Think) { $extra = @("--think") }
    python -m vardiya sab run --families takvim,t-takvim --per-family $PerFamily --seed $Seed --split $Split `
        --model $Model --arms harness_llm --variant $v --out $out --budget $left @extra | Select-Object -Last 1
}
exit 0
