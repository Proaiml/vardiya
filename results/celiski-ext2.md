# Scheduler Admin Bench sonuclari

Satir sayisi: 90. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 30 | 100% (89-100) | 100% | 0% | 0% | 0% | 0% (0-11) | 1.1 | 1.8 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 30 | 100% (89-100) | 100% | 0% | 0% | 0% | 0% (0-11) | 1.0 | 1.8 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 30 | 100% (89-100) | 100% | 0% | 0% | 0% | 0% (0-11) | 1.1 | 1.3 |

## Aileye gore dogru orani

| Kol | aciklamali | t-celiski |
| --- | --- | --- |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 14/14 | 16/16 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 14/14 | 16/16 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 14/14 | 16/16 |

Yeniden oynatma: 90/90 iz ayni durum ozetine ulasti.
