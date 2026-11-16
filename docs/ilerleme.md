# İlerleme (baş işçi)

Son güncelleme: 16 Kasım 2026, 14:45

## Model kotası

- `gemini-3.8-flash-*`, `gemini-4-hydrogen-*`: kapalı (16 Kasım ~13:00, 21 Kasım'da açılır). `dev-flash-low` tam;
  `test-flash-low`, `dev-hydrogen-high` kısmi; geçerli bölümler kısmi sonuç olarak duruyor, kalanı 21 Kasım'dan sonra
  `--atla` ile tamamlanır.
- `gemini-4-argon-low`: 13:36'da kapandı (`test-argon-low` yalnızca 3 `kurulamadi` satırı; sonuç yok).
- `claude-sonnet-5-5-low`: 15:19'da kapandı (`test-sonnet-low` birkaç bölüm; tam ölçüm yok).
- Açık: `gpt-oss-120b-medium` (agy) ve yerel modeller. İkinci model ailesi olarak `ollama:gemma4` kullanılacak.
- Koşucu artık art arda 3 kota hatasında kendini durduruyor (çıkış 5); kuyruk betiği her işten önce modeli tek
  çağrıyla yokluyor.

## Yerel modeller (ekran kartı)

14:45'ten itibaren `ollama:qwen3:14b` yükleniyor (`VARDIYA_NUM_CTX=24576`, tek model). gemma4 ve qwen3:8b'ye geçiş
ayrıca buraya yazılacak; o zamana kadar diğer ajanlar yalnızca qwen3:14b kullansın. Yerel modellerde ajan
döngüsüne bağlam disiplini eklendi (her kol için aynı; donuk kopya etiketi `saha-donuk-1c`, harness değişmedi).

## Laboratuvarlar ve kuyruk

| Lab | Kod | Sıra |
| --- | --- | --- |
| 1 | donuk (`saha-donuk-1c`) | `qwen-baglam-deneme`, `test-qwen3-14b`, `test-qwen3-14b-b10` (GPU tek lab: 82 C, 11 GB) |
| 2 | donuk | `test-gpt-oss-b10` 1/2, `test-gpt-oss` 2/2 boşlukları |
| 4 | geliştirme | `zor-dev-gpt-oss` (ayar turu 1) |
| 3 | önce donuk, sonra geliştirme | eski `test-gpt-oss` 2/2 süreci (kart kolu dahil) bitince: ajan sunucuları yenilenir, ajan servisi senaryoları doğrulanır, `zor-dev-gpt-oss` |
| 5 | katalog ajanı | - |

Kuyruk günlüğü: `results/saha/durum/kuyruk.log`. Donuk koşular `C:/D/projeler/vardiya-donuk1` çalışma kopyasından
(etiket `saha-donuk-1b` = `saha-donuk-1` + bütçe değişiklikleri + yalnızca koşucu ve analiz) koşup `SAHA_SONUC` ile
ana kanıt dizinine yazıyor; harness geliştirmesi onları etkilemiyor.

## Ara sonuçlar (donuk harness, gpt-oss, test kümesinin bir kısmı)

Doğruluk farkı ilk kez görünüyor: bütçesiz yardımsız 7/12, Usta 7/11 ama zararlı 2'ye 0; 10 adım bütçesinde
yardımsız 1/8, Usta 4/6. Kesin tablolar koşular bitince.

## Yapılanlar

- `analiz.py`: bütçe tablosu (`--butce`), uygulanan riskli eylem tablosu.
- Usta geliştirmesi (henüz etiketlenmedi): kalabalık sitede kesilen durum/tanım okuması düzeltildi (harness
  kesimsiz okuyor); talep kapsamı (kesin: ad verilmiş ya da "diğerleri konu dışı" denmiş; tahmin: yalnızca sıralama);
  olay zinciri (bekleyen iş <- olayı veren iş, klasörler arası); kapsam dışı klasöre ve veren işi başarısız olayı elle
  eklemeye ikinci açık çağrı; kabul listesi (ayrı model çağrısı, bitiş kapısında madde madde); profil hesabı ile uzak
  yolun hesabı uyuşmazlığı; başka işlerin kullandığı profilin hesabını değiştirme; aynı hesabı kullanan diğer
  profiller; tanım taleplerinde sunucudaki standart belgesi.
- Ajan servisi: ajan sunucularında PID 1 artık denetçi (`lab/saha/agent/bin/ajan-denetci`), ajan `ctmag
  start|stop|restart|status` ile durup başlatılabiliyor; neden servis günlüğünde ve ajanın kendi günlüklerinde. El
  kitabı ve `ajan-yok` kartı güncellendi. Lab kopyaları boşaldıkça ajan sunucuları yeniden kuruluyor.
- Windows: `/dev/kvm` Docker içinde var; `lab/saha/windows` taslağı yazıldı (Windows Server 2022 deneme, WinRM,
  CtmAgent hizmeti) ama RAM yetmediği ve öncelik düştüğü için durduruldu; sınırlara yazılacak.

## Sırada

1. Müdahale vitrini: kanıttan Türkçe kayıt üreten betik, web sayfası, `docs/13-mudahale-gunlugu.md`.
2. zor-dev (ve gelince katalog-dev) ile ayar; ajan servisi senaryoları (geliştirme).
3. `saha-donuk-2` etiketi; zor-test, katalog-test, test kümesi yeni etiketle.
4. Rapor (docs/09 Sonuçlar, Bench'ler arası ilişki), README, devir notu, yayın hazırlığı.

## Senaryo yazarına not

Ajan sunucularında artık ajan servisi durdurulup başlatılabiliyor (`ctmag`, bkz. `lab/saha/agent/bin/ctmag`).
"Ajan durdu, nedenini bul ve başlat" türü gizli senaryolar yazılabilir: kurulumda `{"sh": {"host": "ajan2", "cmd":
"ctmag stop bakim"}}` ya da ayarı bozup durdurmak; kontrolde `{"sh": {"host": "ajan2", "cmd": "ctmag status", "rc": 0}}`.
Bunun için o lab kopyasının ajan sunucularının yeni denetçiyle yeniden kurulmuş olması gerekir:
`SAHA_PROJE=... SAHA_PORT_JOC=... SAHA_AG=... docker compose -p <proje> -f lab/saha/docker-compose.yml up -d ajan1 ajan2`.
