# Scheduler Admin Bench sonuclari

Satir sayisi: 120. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 30 | 97% (83-99) | 97% | 3% | 0% | 0% | 0% (0-11) | 1.0 | 2.1 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-desc1] | 30 | 73% (56-86) | 73% | 0% | 27% | 0% | 27% (14-44) | 1.0 | 1.0 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 30 | 97% (83-99) | 97% | 3% | 0% | 0% | 0% (0-11) | 1.1 | 2.9 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-desc1] | 30 | 70% (52-83) | 70% | 0% | 30% | 0% | 30% (17-48) | 1.0 | 0.7 |

## Aileye gore dogru orani

| Kol | aciklamali | t-celiski |
| --- | --- | --- |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 14/15 | 15/15 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-desc1] | 15/15 | 7/15 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 14/15 | 15/15 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-desc1] | 15/15 | 6/15 |

Yeniden oynatma: 120/120 iz ayni durum ozetine ulasti.
