# Scheduler Admin Bench sonuclari

Satir sayisi: 360. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 60 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 1.0 | 1.9 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-desc1] | 60 | 82% (70-89) | 82% | 0% | 18% | 0% | 18% (11-30) | 1.0 | 1.0 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-evethayir] | 60 | 90% (80-95) | 90% | 0% | 10% | 0% | 10% (5-20) | 1.1 | 1.5 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 60 | 95% (86-98) | 95% | 5% | 0% | 0% | 0% (0-6) | 1.0 | 1.1 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-desc1] | 60 | 77% (65-86) | 77% | 0% | 23% | 0% | 23% (14-35) | 1.0 | 0.8 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-evethayir] | 60 | 80% (68-88) | 80% | 0% | 20% | 0% | 20% (12-32) | 1.2 | 1.0 |

## Aileye gore dogru orani

| Kol | aciklamali | t-celiski |
| --- | --- | --- |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 30/30 | 30/30 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-desc1] | 30/30 | 19/30 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-evethayir] | 30/30 | 24/30 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 27/30 | 30/30 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-desc1] | 30/30 | 16/30 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-evethayir] | 30/30 | 18/30 |

Yeniden oynatma: 360/360 iz ayni durum ozetine ulasti.
