# Scheduler Admin Bench sonuclari

Satir sayisi: 270. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 90 | 99% (94-100) | 98% | 1% | 0% | 0% | 0% (0-4) | 1.2 | 1.4 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 90 | 99% (94-100) | 98% | 1% | 0% | 0% | 0% (0-4) | 1.2 | 1.1 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 90 | 97% (91-99) | 95% | 2% | 1% | 0% | 1% (0-6) | 1.2 | 0.8 |

## Aileye gore dogru orani

| Kol | takvim | t-takvim | t-belirsiz |
| --- | --- | --- | --- |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 29/30 | 30/30 | 30/30 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 29/30 | 30/30 | 30/30 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 27/30 | 30/30 | 30/30 |

Yeniden oynatma: 270/270 iz ayni durum ozetine ulasti.
