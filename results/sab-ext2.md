# Scheduler Admin Bench sonuclari

Satir sayisi: 576. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.
Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.

## Genel

| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 64 | 0% (0-6) | 0% | 100% | 0% | 0% | 0% (0-6) | 0.0 | 0.0 |
| Yazilani aynen uygula | 64 | 25% (16-37) | 40% | 0% | 53% | 22% | 75% (63-84) | 0.0 | 0.0 |
| Hepsini iade et | 64 | 69% (57-79) | 50% | 31% | 0% | 0% | 0% (0-6) | 0.0 | 0.0 |
| Referans cozum | 64 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.0 | 0.0 |
| Harness'in kod payi [lex>rule-gloss-veto] | 64 | 89% (79-95) | 88% | 5% | 6% | 0% | 6% (2-15) | 0.0 | 0.0 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 64 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.4 | 0.8 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 64 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.4 | 0.6 |
| Ham model `qwen3:8b` | 64 | 20% (12-32) | 27% | 6% | 61% | 12% | 73% (62-83) | 3.1 | 3.5 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 64 | 100% (94-100) | 100% | 0% | 0% | 0% | 0% (0-6) | 0.4 | 0.4 |

## Aileye gore dogru orani

| Kol | yeni | degisiklik | takvim | t-takvim | t-dongu | t-mevcut | t-olmayan | t-standart | t-sablon | t-referans | kaldir | t-bagimli | aciklamali | t-celiski | t-belirsiz | t-uyumsuz |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Hicbir sey yapma | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 |
| Yazilani aynen uygula | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 0/4 | 4/4 | 0/4 | 0/4 | 0/4 |
| Hepsini iade et | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 0/4 | 4/4 | 4/4 | 4/4 |
| Referans cozum | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Harness'in kod payi [lex>rule-gloss-veto] | 4/4 | 4/4 | 1/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 0/4 | 4/4 | 4/4 |
| Harness + model `gemma4:latest` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Harness + model `qwen3:14b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |
| Ham model `qwen3:8b` | 4/4 | 1/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 0/4 | 4/4 | 4/4 | 0/4 | 0/4 | 0/4 |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 | 4/4 |

## Ayni senaryolarda ham modele karsi (eslestirilmis)

| Kol | Ortak senaryo | Ham yanlis, bu dogru | Ham dogru, bu yanlis | p (dogruluk) | Zarari giderdi | Zarar ekledi | p (zarar) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Harness + model `qwen3:8b` [lex>rule-gloss-veto] | 64 | 51 | 0 | 0.000 | 47 | 0 | 0.000 |

p degerleri uyumsuz ciftler uzerinde iki yonlu kesin McNemar testidir.

Yeniden oynatma: 576/576 iz ayni durum ozetine ulasti.
