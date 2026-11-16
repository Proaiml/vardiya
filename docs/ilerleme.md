# İlerleme (baş işçi)

Son güncelleme: 16 Kasım 2026, 13:20

## ENGEL: Gemini kotası doldu

Antigravity, `gemini-3.8-flash-*` ve `gemini-4-hydrogen-*` için "Individual quota reached ... Resets in 125h39m"
döndürüyor (yaklaşık 21 Kasım 18:50'ye kadar). Yaklaşık 13:00'ten beri `test-flash-low` (lab 2) ve
`dev-hydrogen-high` (lab 3) koşularındaki her bölüm `kurulamadi` olarak yazılıyor; bunlar hüküm değil, kota açılınca
`--atla` ile doldurulacak.

Kotası açık olanlar (16 Kasım 13:15 yoklaması): `gpt-oss-120b-medium`, `gemini-4-argon-low`, `claude-sonnet-5-5-low`.

Karar gereken: hafif model ve hydrogen ölçümleri (Aşama 1'in iki modeli, Aşama 2'nin tamamı) ya kotanın açılmasını
bekler ya da başka bir modelle yapılır (örneğin `gemini-4-argon-low` güçlü model yerine). Karar gelene kadar
gpt-oss ile ilerliyorum; Aşama 3'teki harness ayarını da gpt-oss ile yapacağım.

## Not: yanlış adrese gelmiş olabilecek mesaj

13:25 civarı bana "senaryo kaynağını değiştir, `kaynak` alanı ekle; `usta.py`, `skills/`, `tests/test_saha.py`
okuma" diye bir mesaj geldi. Bu, senaryo yazarına yönelik görünüyor (ben harness'i yazan tarafım ve senaryo
yazmıyorum). Ben senaryo yazmadım ve yazmayacağım; mesajın senaryo yazarına iletildiğinden emin olun. Sızıntıya
karşı: zor kümenin kaynakları (`bench/ops/dev.jsonl`, opsworld, sabgen, forum taslakları) gizli yarıyı da
besleyeceği için harness'i bu kaynaklara bakarak değil, yalnızca `zor-dev` senaryolarındaki bulgularla ayarlıyorum.

## Laboratuvarlar

| Lab | Şimdi | Sırada (kuyruk betiği) |
| --- | --- | --- |
| 1 | `dev-gpt-oss` (orkestratörün koşusu) | aynı koşunun boşluk doldurma geçişleri |
| 2 | `test-flash-low` kota hatalarıyla bitiyor | `test-gpt-oss --parca 1/2` |
| 3 | `dev-hydrogen-high` kota hatalarıyla bitiyor | `test-gpt-oss --parca 2/2` |
| 4 | ayrılmış (senaryo yazarı) | - |

Kuyruk günlüğü: `results/saha/durum/kuyruk.log`. Dondurulmuş harness ile yapılan koşular ayrı bir çalışma kopyasından
(`C:\D\projelerardiya-donuk1`, commit e632004: `saha-donuk-1` + bütçe değişiklikleri + yalnızca koşucu/analiz) koşuyor,
`SAHA_SONUC` ile ana kanıt dizinine yazıyor; ana depodaki `usta.py` geliştirmesi onları etkilemiyor.

## Yapılanlar

- Durum okundu; kota sorunu bulundu.
- `analiz.py`: bütçe tablosu (`--butce`) ve uygulanan riskli eylem tablosu.
- Usta geliştirmesi başladı (commit d85bc4a, henüz etiketlenmedi): kalabalık sitede kesilen durum/tanım okuması düzeltildi,
  talep kapsamı ve olay zinciri, kapsam dışı ve elle olay koruması, kabul listesi.

## Sırada

- Aşama 1: `test-gpt-oss` (90 bölüm), `dev-gpt-oss` tamamlanır.
- Aşama 2: kriz bütçesi; kota kararına göre.
- Aşama 3: `bench/saha/zor-dev/` henüz yok.
