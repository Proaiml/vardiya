# Scheduler Admin Bench sonuclari

Satir sayisi: 880. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness'in kod payi [lex>agree2] | 80 | 60% (49-70) | 60% | 40% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Harness + model `qwen3:8b` [agree2] | 80 | 56% (45-67) | 56% | 44% | 0% | 0% | 0% (0-5) | 1.9 | 2.3 |
| Harness + model `qwen3:8b` [any2-gloss-veto] | 80 | 88% (78-93) | 88% | 9% | 4% | 0% | 4% (1-10) | 2.1 | 1.5 |
| Harness + model `qwen3:8b` [lex>agree2] | 80 | 62% (52-72) | 62% | 36% | 1% | 0% | 1% (0-7) | 1.7 | 1.9 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 80 | 92% (85-97) | 92% | 8% | 0% | 0% | 0% (0-5) | 0.9 | 0.4 |
| Harness + model `qwen3:8b` [rule] | 80 | 70% (59-79) | 70% | 8% | 22% | 0% | 22% (15-33) | 1.0 | 0.5 |
| Harness + model `qwen3:8b` [rule-gloss] | 80 | 74% (63-82) | 74% | 5% | 21% | 0% | 21% (14-31) | 1.0 | 0.5 |
| Harness + model `qwen3:8b` [rule-gloss-veto] | 80 | 91% (83-96) | 91% | 9% | 0% | 0% | 0% (0-5) | 1.0 | 0.5 |
| Harness + model `qwen3:8b` [tree] | 80 | 65% (54-75) | 65% | 12% | 22% | 0% | 22% (15-33) | 1.4 | 1.2 |
| Harness + model `qwen3:8b` [tree2] | 80 | 69% (58-78) | 69% | 22% | 9% | 0% | 9% (4-17) | 1.9 | 1.4 |
| Harness + model `qwen3:8b` [tree2-gloss-veto] | 80 | 75% (65-83) | 75% | 25% | 0% | 0% | 0% (0-5) | 1.7 | 1.3 |

## Aileye gore dogru orani

| Kol | takvim | t-takvim |
| --- | --- | --- |
| Harness'in kod payi [lex>agree2] | 8/40 | 40/40 |
| Harness + model `qwen3:8b` [agree2] | 5/40 | 40/40 |
| Harness + model `qwen3:8b` [any2-gloss-veto] | 30/40 | 40/40 |
| Harness + model `qwen3:8b` [lex>agree2] | 11/40 | 39/40 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 34/40 | 40/40 |
| Harness + model `qwen3:8b` [rule] | 29/40 | 27/40 |
| Harness + model `qwen3:8b` [rule-gloss] | 33/40 | 26/40 |
| Harness + model `qwen3:8b` [rule-gloss-veto] | 33/40 | 40/40 |
| Harness + model `qwen3:8b` [tree] | 20/40 | 32/40 |
| Harness + model `qwen3:8b` [tree2] | 20/40 | 35/40 |
| Harness + model `qwen3:8b` [tree2-gloss-veto] | 20/40 | 40/40 |

Yeniden oynatma: 880/880 iz ayni durum ozetine ulasti.
