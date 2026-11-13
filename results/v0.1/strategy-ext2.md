# Scheduler Admin Bench sonuclari

Satir sayisi: 842. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Harness'in kod payi [lex>agree2] | 80 | 61% (50-71) | 61% | 39% | 0% | 0% | 0% (0-5) | 0.0 | 0.0 |
| Harness + model `gemini-4-hydrogen-xhigh` [rule-gloss] | 7 | 100% (65-100) | 100% | 0% | 0% | 0% | 0% (0-35) | 2.0 | 18.4 |
| Harness + model `gemini-4-hydrogen-xhigh` [rule-gloss-veto] | 16 | 100% (81-100) | 100% | 0% | 0% | 0% | 0% (0-19) | 1.0 | 27.3 |
| Harness + model `qwen3:14b` [agree2] | 80 | 62% (52-72) | 62% | 35% | 2% | 0% | 2% (1-9) | 1.8 | 3.1 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 19 | 74% (51-88) | 74% | 26% | 0% | 0% | 0% (0-17) | 1.8 | 10.6 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-celiskisiz] | 80 | 95% (88-98) | 95% | 5% | 0% | 0% | 0% (0-5) | 0.8 | 0.4 |
| Harness + model `qwen3:14b` [rule-gloss] | 80 | 81% (71-88) | 81% | 2% | 16% | 0% | 16% (10-26) | 1.0 | 1.4 |
| Harness + model `qwen3:14b` [rule-gloss-veto-celiskisiz] | 80 | 95% (88-98) | 95% | 5% | 0% | 0% | 0% (0-5) | 1.0 | 0.6 |
| Harness + model `qwen3:8b` [agree2] | 80 | 49% (38-60) | 49% | 48% | 4% | 0% | 4% (1-10) | 1.8 | 2.0 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 80 | 89% (80-94) | 89% | 10% | 1% | 0% | 1% (0-7) | 1.2 | 1.6 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-celiskisiz] | 80 | 92% (85-97) | 92% | 6% | 1% | 0% | 1% (0-7) | 0.8 | 0.5 |
| Harness + model `qwen3:8b` [rule-gloss] | 80 | 76% (66-84) | 76% | 4% | 20% | 0% | 20% (13-30) | 1.0 | 0.6 |
| Harness + model `qwen3:8b` [rule-gloss-veto-celiskisiz] | 80 | 91% (83-96) | 91% | 8% | 1% | 0% | 1% (0-7) | 1.0 | 0.5 |

## Aileye gore dogru orani

| Kol | takvim | t-takvim |
| --- | --- | --- |
| Harness'in kod payi [lex>agree2] | 9/40 | 40/40 |
| Harness + model `gemini-4-hydrogen-xhigh` [rule-gloss] | 7/7 | - |
| Harness + model `gemini-4-hydrogen-xhigh` [rule-gloss-veto] | 8/8 | 8/8 |
| Harness + model `qwen3:14b` [agree2] | 12/40 | 38/40 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 14/19 | - |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto-celiskisiz] | 36/40 | 40/40 |
| Harness + model `qwen3:14b` [rule-gloss] | 38/40 | 27/40 |
| Harness + model `qwen3:14b` [rule-gloss-veto-celiskisiz] | 36/40 | 40/40 |
| Harness + model `qwen3:8b` [agree2] | 2/40 | 37/40 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 31/40 | 40/40 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto-celiskisiz] | 34/40 | 40/40 |
| Harness + model `qwen3:8b` [rule-gloss] | 34/40 | 27/40 |
| Harness + model `qwen3:8b` [rule-gloss-veto-celiskisiz] | 33/40 | 40/40 |

Yeniden oynatma: 842/842 iz ayni durum ozetine ulasti.
