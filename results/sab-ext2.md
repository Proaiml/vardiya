# Scheduler Admin Bench sonuclari

Satir sayisi: 960. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 72 | 0% (0-5) | 0% | 100% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Yazilani aynen uygula | 72 | 28% (19-39) | 42% | 0% | 53% | 19% | 72% (61-81) | 0.0 | 0.0 |
| Hepsini iade et | 72 | 67% (55-76) | 50% | 33% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Referans cozum | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Harness'in kod payi [lex>rule-gloss-veto] | 72 | 90% (81-95) | 90% | 4% | 6% | 0% | 6% (2-13) | 0.0 | 0.0 |
| Ham model `gemma4:latest` | 64 | 22% (14-33) | 31% | 0% | 58% | 20% | 78% (67-86) | 3.0 | 3.4 |
| Ham model + runbook (plasebo) `gemma4:latest` | 64 | 72% (60-81) | 63% | 19% | 5% | 5% | 9% (4-19) | 5.5 | 6.5 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.4 | 0.9 |
| Ham model `qwen3:14b` | 64 | 20% (12-32) | 31% | 0% | 59% | 20% | 80% (68-88) | 3.1 | 4.3 |
| Ham model + runbook (plasebo) `qwen3:14b` | 64 | 50% (38-62) | 46% | 14% | 28% | 8% | 36% (25-48) | 5.2 | 7.1 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.4 | 0.8 |
| Ham model `qwen3:8b` | 64 | 20% (12-32) | 27% | 6% | 61% | 12% | 73% (62-83) | 3.1 | 3.6 |
| Ham model + runbook (plasebo) `qwen3:8b` | 64 | 41% (29-53) | 45% | 12% | 38% | 9% | 47% (35-59) | 7.8 | 6.5 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 72 | 100% (95-100) | 100% | 0% | 0% | 0% | 0% (0-5) | 0.4 | 0.5 |

## Aileye gore dogru orani

| Kol | yeni | degisiklik | takvim | t-takvim | t-dongu | t-mevcut | t-olmayan | t-standart | t-sablon | t-referans | kaldir | t-bagimli | aciklamali | t-celiski | t-belirsiz | t-uyumsuz | yeni-tip | t-tip |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Yazilani aynen uygula | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 |
| Hepsini iade et | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 |
| Referans cozum | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Harness'in kod payi [lex>rule-gloss-veto] | 4/4 | 4/4 | 1/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `gemma4:latest` | 4/4 | 0/4 | 0/4 | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 2/4 | 0/4 | 4/4 | 0/4 | 3/4 | 0/4 | 0/4 | 0/4 | - | - |
| Ham model + runbook (plasebo) `gemma4:latest` | 1/4 | 3/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 2/4 | 4/4 | 3/4 | 2/4 | 1/4 | 2/4 | 4/4 | 4/4 | 4/4 | - | - |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:14b` | 4/4 | 0/4 | 0/4 | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 | 0/4 | 0/4 | - | - |
| Ham model + runbook (plasebo) `qwen3:14b` | 4/4 | 1/4 | 1/4 | 2/4 | 1/4 | 3/4 | 4/4 | 0/4 | 2/4 | 0/4 | 1/4 | 3/4 | 0/4 | 4/4 | 4/4 | 2/4 | - | - |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:8b` | 4/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | - | - |
| Ham model + runbook (plasebo) `qwen3:8b` | 4/4 | 0/4 | 4/4 | 1/4 | 1/4 | 1/4 | 4/4 | 0/4 | 2/4 | 0/4 | 0/4 | 4/4 | 3/4 | 1/4 | 0/4 | 1/4 | - | - |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

## Ayni senaryolarda ham modele karsi (eslestirilmis)

| Kol | Ortak senaryo | Ham yanlis, bu dogru | Ham dogru, bu yanlis | p (dogruluk) | Zarari giderdi | Zarar ekledi | p (zarar) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ham model + runbook (plasebo) `gemma4:latest` | 64 | 39 | 7 | 0.000 | 44 | 0 | 0.000 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 64 | 50 | 0 | 0.000 | 50 | 0 | 0.000 |
| Ham model + runbook (plasebo) `qwen3:14b` | 64 | 26 | 7 | 0.001 | 32 | 4 | 0.000 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 64 | 51 | 0 | 0.000 | 51 | 0 | 0.000 |
| Ham model + runbook (plasebo) `qwen3:8b` | 64 | 15 | 2 | 0.002 | 18 | 1 | 0.000 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 64 | 51 | 0 | 0.000 | 47 | 0 | 0.000 |

p degerleri uyumsuz ciftler uzerinde iki yonlu kesin McNemar testidir.

Yeniden oynatma: 960/960 iz ayni durum ozetine ulasti.
