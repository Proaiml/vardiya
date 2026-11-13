# Scheduler Admin Bench sonuclari

Satir sayisi: 671. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 48 | 0% (0-7) | 0% | 100% | 0% | 0% | 0% (0-7) | 0.0 | 0.0 |
| Yazilani aynen uygula | 48 | 25% (15-39) | 38% | 0% | 50% | 25% | 75% (61-85) | 0.0 | 0.0 |
| Hepsini iade et | 48 | 67% (53-78) | 50% | 33% | 0% | 0% | 0% (0-7) | 0.0 | 0.0 |
| Referans cozum | 48 | 100% (93-100) | 100% | 0% | 0% | 0% | 0% (0-7) | 0.0 | 0.0 |
| Harness'in kod payi [agree2] | 40 | 90% (77-96) | 83% | 10% | 0% | 0% | 0% (0-9) | 0.0 | 0.0 |
| Harness'in kod payi [lex>agree2] | 48 | 100% (93-100) | 100% | 0% | 0% | 0% | 0% (0-7) | 0.0 | 0.0 |
| Ham model `gemini-4-hydrogen-xhigh` | 11 | 100% (74-100) | 100% | 0% | 0% | 0% | 0% (0-26) | 6.4 | 170.5 |
| Harness + model `gemini-4-hydrogen-xhigh` [lex>agree2] | 12 | 100% (76-100) | 100% | 0% | 0% | 0% | 0% (0-24) | 0.0 | 0.0 |
| Ham model `qwen3:14b` | 48 | 19% (10-32) | 27% | 0% | 58% | 23% | 81% (68-90) | 3.1 | 4.8 |
| Ham model + runbook (plasebo) `qwen3:14b` | 48 | 44% (31-58) | 42% | 21% | 25% | 10% | 35% (23-50) | 4.6 | 6.9 |
| Harness + model `qwen3:14b` [agree2] | 40 | 90% (77-96) | 83% | 10% | 0% | 0% | 0% (0-9) | 0.4 | 1.0 |
| Harness + model `qwen3:14b` [lex>agree2] | 48 | 100% (93-100) | 100% | 0% | 0% | 0% | 0% (0-7) | 0.1 | 0.1 |
| Ham model `qwen3:8b` | 48 | 19% (10-32) | 22% | 8% | 60% | 12% | 73% (59-83) | 3.1 | 4.8 |
| Ham model + runbook (plasebo) `qwen3:8b` | 48 | 42% (29-56) | 44% | 19% | 25% | 15% | 40% (27-54) | 7.4 | 9.2 |
| Harness + model `qwen3:8b` [agree2] | 40 | 90% (77-96) | 83% | 10% | 0% | 0% | 0% (0-9) | 0.3 | 0.4 |
| Harness + model `qwen3:8b` [lex>agree2] | 48 | 100% (93-100) | 100% | 0% | 0% | 0% | 0% (0-7) | 0.1 | 0.3 |

## Aileye gore dogru orani

| Kol | yeni | degisiklik | takvim | t-takvim | t-dongu | t-mevcut | t-olmayan | t-standart | t-sablon | t-referans | kaldir | t-bagimli |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Yazilani aynen uygula | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 |
| Hepsini iade et | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 |
| Referans cozum | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Harness'in kod payi [agree2] | 4/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | - | - |
| Harness'in kod payi [lex>agree2] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `gemini-4-hydrogen-xhigh` | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | - | 1/1 |
| Harness + model `gemini-4-hydrogen-xhigh` [lex>agree2] | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| Ham model `qwen3:14b` | 4/4 | 0/4 | 0/4 | 0/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 |
| Ham model + runbook (plasebo) `qwen3:14b` | 4/4 | 1/4 | 0/4 | 4/4 | 1/4 | 3/4 | 2/4 | 0/4 | 2/4 | 0/4 | 1/4 | 3/4 |
| Harness + model `qwen3:14b` [agree2] | 4/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | - | - |
| Harness + model `qwen3:14b` [lex>agree2] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:8b` | 4/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 |
| Ham model + runbook (plasebo) `qwen3:8b` | 4/4 | 0/4 | 4/4 | 1/4 | 1/4 | 0/4 | 4/4 | 0/4 | 2/4 | 0/4 | 0/4 | 4/4 |
| Harness + model `qwen3:8b` [agree2] | 4/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | - | - |
| Harness + model `qwen3:8b` [lex>agree2] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

## Ayni senaryolarda ham modele karsi (eslestirilmis)

| Kol | Ortak senaryo | Ham yanlis, bu dogru | Ham dogru, bu yanlis | p (dogruluk) | Zarari giderdi | Zarar ekledi | p (zarar) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `gemini-4-hydrogen-xhigh` [lex>agree2] | 11 | 0 | 0 | 1.000 | 0 | 0 | 1.000 |
| Ham model + runbook (plasebo) `qwen3:14b` | 48 | 15 | 3 | 0.008 | 22 | 0 | 0.000 |
| Harness + model `qwen3:14b` [agree2] | 40 | 31 | 0 | 0.000 | 35 | 0 | 0.000 |
| Harness + model `qwen3:14b` [lex>agree2] | 48 | 39 | 0 | 0.000 | 39 | 0 | 0.000 |
| Ham model + runbook (plasebo) `qwen3:8b` | 48 | 12 | 1 | 0.003 | 16 | 0 | 0.000 |
| Harness + model `qwen3:8b` [agree2] | 40 | 31 | 0 | 0.000 | 35 | 0 | 0.000 |
| Harness + model `qwen3:8b` [lex>agree2] | 48 | 39 | 0 | 0.000 | 35 | 0 | 0.000 |

p degerleri uyumsuz ciftler uzerinde iki yonlu kesin McNemar testidir.

Yeniden oynatma: 671/671 iz ayni durum ozetine ulasti.
