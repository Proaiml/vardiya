# Scheduler Admin Bench sonuclari

Satir sayisi: 354. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 59 | 98% (91-100) | 98% | 0% | 2% | 0% | 2% (0-9) | 1.0 | 2.6 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-desc1] | 59 | 90% (80-95) | 90% | 2% | 8% | 0% | 8% (4-18) | 1.0 | 1.1 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-ilk] | 59 | 97% (88-99) | 97% | 0% | 3% | 0% | 3% (1-12) | 1.0 | 1.9 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 59 | 97% (88-99) | 97% | 0% | 3% | 0% | 3% (1-12) | 1.1 | 1.2 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-desc1] | 59 | 71% (59-81) | 71% | 0% | 29% | 0% | 29% (19-41) | 1.0 | 0.8 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-ilk] | 59 | 92% (82-96) | 91% | 3% | 5% | 0% | 5% (2-14) | 1.0 | 1.2 |

## Aileye gore dogru orani

| Kol | aciklamali | t-celiski |
| --- | --- | --- |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 30/30 | 28/29 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-desc1] | 29/30 | 24/29 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-ilk] | 30/30 | 27/29 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 30/30 | 27/29 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-desc1] | 30/30 | 12/29 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-ilk] | 28/30 | 26/29 |

Yeniden oynatma: 354/354 iz ayni durum ozetine ulasti.
