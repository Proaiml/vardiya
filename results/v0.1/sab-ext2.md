# Scheduler Admin Bench sonuclari

Satir sayisi: 616. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 56 | 0% (0-6) | 0% | 100% | 0% | 0% | 0% (0-6) | 0.0 | 0.0 |
| Yazilani aynen uygula | 56 | 29% (18-41) | 40% | 0% | 50% | 21% | 71% (59-82) | 0.0 | 0.0 |
| Hepsini iade et | 56 | 64% (51-76) | 50% | 36% | 0% | 0% | 0% (0-6) | 0.0 | 0.0 |
| Referans cozum | 56 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.0 | 0.0 |
| Harness'in kod payi [lex>rule-gloss-veto] | 56 | 88% (76-94) | 87% | 5% | 7% | 0% | 7% (3-17) | 0.0 | 0.0 |
| Ham model `qwen3:14b` | 56 | 23% (14-36) | 31% | 0% | 57% | 20% | 77% (64-86) | 3.1 | 5.1 |
| Ham model + runbook (plasebo) `qwen3:14b` | 56 | 39% (28-52) | 38% | 18% | 32% | 11% | 43% (31-56) | 4.8 | 7.7 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 56 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.4 | 0.5 |
| Ham model `qwen3:8b` | 56 | 23% (14-36) | 28% | 7% | 59% | 11% | 70% (57-80) | 3.1 | 3.6 |
| Ham model + runbook (plasebo) `qwen3:8b` | 56 | 43% (31-56) | 46% | 9% | 38% | 11% | 48% (36-61) | 6.9 | 7.4 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 56 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.4 | 0.4 |

## Aileye gore dogru orani

| Kol | yeni | degisiklik | takvim | t-takvim | t-dongu | t-mevcut | t-olmayan | t-standart | t-sablon | t-referans | kaldir | t-bagimli | aciklamali | t-celiski |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Yazilani aynen uygula | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 |
| Hepsini iade et | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 0/4 | 4/4 |
| Referans cozum | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Harness'in kod payi [lex>rule-gloss-veto] | 4/4 | 4/4 | 1/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 |
| Ham model `qwen3:14b` | 4/4 | 0/4 | 0/4 | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 |
| Ham model + runbook (plasebo) `qwen3:14b` | 4/4 | 2/4 | 0/4 | 4/4 | 1/4 | 1/4 | 1/4 | 0/4 | 2/4 | 0/4 | 1/4 | 3/4 | 0/4 | 3/4 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:8b` | 4/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 0/4 |
| Ham model + runbook (plasebo) `qwen3:8b` | 4/4 | 1/4 | 3/4 | 0/4 | 1/4 | 0/4 | 4/4 | 0/4 | 2/4 | 0/4 | 0/4 | 4/4 | 3/4 | 2/4 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

## Ayni senaryolarda ham modele karsi (eslestirilmis)

| Kol | Ortak senaryo | Ham yanlis, bu dogru | Ham dogru, bu yanlis | p (dogruluk) | Zarari giderdi | Zarar ekledi | p (zarar) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Ham model + runbook (plasebo) `qwen3:14b` | 56 | 16 | 7 | 0.093 | 22 | 3 | 0.000 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 56 | 43 | 0 | 0.000 | 43 | 0 | 0.000 |
| Ham model + runbook (plasebo) `qwen3:8b` | 56 | 12 | 1 | 0.003 | 13 | 1 | 0.002 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 56 | 43 | 0 | 0.000 | 39 | 0 | 0.000 |

p degerleri uyumsuz ciftler uzerinde iki yonlu kesin McNemar testidir.

Yeniden oynatma: 616/616 iz ayni durum ozetine ulasti.
