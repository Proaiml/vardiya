# Scheduler Admin Bench sonuclari

Satir sayisi: 1008. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 72 | 0% (0-5) | 0% | 100% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Yazilani aynen uygula | 72 | 28% (19-39) | 42% | 0% | 53% | 19% | 72% (61-81) | 0.0 | 0.0 |
| Hepsini iade et | 72 | 67% (55-76) | 50% | 33% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Referans cozum | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Harness'in kod payi [lex>rule-gloss-veto] | 72 | 90% (81-95) | 90% | 4% | 6% | 0% | 6% (2-13) | 0.0 | 0.0 |
| Ham model `gemma4:latest` | 72 | 24% (15-35) | 32% | 0% | 58% | 18% | 76% (65-85) | 3.0 | 3.7 |
| Ham model + runbook (plasebo) `gemma4:latest` | 72 | 69% (58-79) | 60% | 22% | 4% | 4% | 8% (4-17) | 5.3 | 6.3 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.4 | 0.9 |
| Ham model `qwen3:14b` | 72 | 24% (15-35) | 34% | 0% | 58% | 18% | 76% (65-85) | 3.1 | 4.5 |
| Ham model + runbook (plasebo) `qwen3:14b` | 72 | 49% (37-60) | 47% | 14% | 31% | 7% | 38% (27-49) | 5.4 | 7.6 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.4 | 0.8 |
| Ham model `qwen3:8b` | 72 | 21% (13-32) | 27% | 6% | 62% | 11% | 74% (62-82) | 3.1 | 3.7 |
| Ham model + runbook (plasebo) `qwen3:8b` | 72 | 39% (28-50) | 43% | 11% | 42% | 8% | 50% (39-61) | 7.7 | 6.8 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.4 | 0.5 |

## Aileye gore dogru orani

| Kol | yeni | degisiklik | takvim | t-takvim | t-dongu | t-mevcut | t-olmayan | t-standart | t-sablon | t-referans | kaldir | t-bagimli | aciklamali | t-celiski | t-belirsiz | t-uyumsuz | yeni-tip | t-tip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Yazilani aynen uygula | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 |
| Hepsini iade et | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 |
| Referans cozum | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Harness'in kod payi [lex>rule-gloss-veto] | 4/4 | 4/4 | 1/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `gemma4:latest` | 4/4 | 0/4 | 0/4 | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 2/4 | 0/4 | 4/4 | 0/4 | 3/4 | 0/4 | 0/4 | 0/4 | 3/4 | 0/4 |
| Ham model + runbook (plasebo) `gemma4:latest` | 1/4 | 3/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 2/4 | 4/4 | 3/4 | 2/4 | 1/4 | 2/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:14b` | 4/4 | 0/4 | 0/4 | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 |
| Ham model + runbook (plasebo) `qwen3:14b` | 4/4 | 1/4 | 1/4 | 2/4 | 1/4 | 3/4 | 4/4 | 0/4 | 2/4 | 0/4 | 1/4 | 3/4 | 0/4 | 4/4 | 4/4 | 2/4 | 3/4 | 0/4 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:8b` | 4/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | 2/4 | 0/4 |
| Ham model + runbook (plasebo) `qwen3:8b` | 4/4 | 0/4 | 4/4 | 1/4 | 1/4 | 1/4 | 4/4 | 0/4 | 2/4 | 0/4 | 0/4 | 4/4 | 3/4 | 1/4 | 0/4 | 1/4 | 2/4 | 0/4 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

## Ayni senaryolarda ham modele karsi (eslestirilmis)

| Kol | Ortak senaryo | Ham yanlis, bu dogru | Ham dogru, bu yanlis | p (dogruluk) | Zarari giderdi | Zarar ekledi | p (zarar) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ham model + runbook (plasebo) `gemma4:latest` | 72 | 43 | 10 | 0.000 | 49 | 0 | 0.000 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 72 | 55 | 0 | 0.000 | 55 | 0 | 0.000 |
| Ham model + runbook (plasebo) `qwen3:14b` | 72 | 26 | 8 | 0.003 | 32 | 4 | 0.000 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 72 | 55 | 0 | 0.000 | 55 | 0 | 0.000 |
| Ham model + runbook (plasebo) `qwen3:8b` | 72 | 16 | 3 | 0.004 | 19 | 2 | 0.000 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 72 | 57 | 0 | 0.000 | 53 | 0 | 0.000 |

p degerleri uyumsuz ciftler uzerinde iki yonlu kesin McNemar testidir.

Yeniden oynatma: 1008/1008 iz ayni durum ozetine ulasti.
