# Scheduler Admin Bench sonuclari

Satir sayisi: 420. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `qwen3:8b` [agree2] | 60 | 55% (42-67) | 55% | 45% | 0% | 0% | 0% (0-6) | 1.8 | 3.1 |
| Harness + model `qwen3:8b` [rule] | 60 | 68% (56-79) | 68% | 17% | 15% | 0% | 15% (8-26) | 1.0 | 1.0 |
| Harness + model `qwen3:8b` [rule-gloss] | 60 | 65% (52-76) | 65% | 5% | 30% | 0% | 30% (20-43) | 1.0 | 1.1 |
| Harness + model `qwen3:8b` [rulecheck] | 60 | 55% (42-67) | 55% | 43% | 2% | 0% | 2% (0-9) | 1.4 | 2.0 |
| Harness + model `qwen3:8b` [rulecheck-gloss] | 60 | 53% (41-65) | 53% | 43% | 3% | 0% | 3% (1-11) | 1.6 | 2.3 |
| Harness + model `qwen3:8b` [single] | 60 | 47% (35-59) | 47% | 3% | 50% | 0% | 50% (38-62) | 1.0 | 1.4 |
| Harness + model `qwen3:8b` [vote3] | 60 | 62% (49-73) | 62% | 30% | 8% | 0% | 8% (4-18) | 2.8 | 4.5 |

## Aileye gore dogru orani

| Kol | takvim | t-takvim |
| --- | --- | --- |
| Harness + model `qwen3:8b` [agree2] | 3/30 | 30/30 |
| Harness + model `qwen3:8b` [rule] | 15/30 | 26/30 |
| Harness + model `qwen3:8b` [rule-gloss] | 20/30 | 19/30 |
| Harness + model `qwen3:8b` [rulecheck] | 3/30 | 30/30 |
| Harness + model `qwen3:8b` [rulecheck-gloss] | 4/30 | 28/30 |
| Harness + model `qwen3:8b` [single] | 18/30 | 10/30 |
| Harness + model `qwen3:8b` [vote3] | 11/30 | 26/30 |

Yeniden oynatma: 420/420 iz ayni durum ozetine ulasti.
