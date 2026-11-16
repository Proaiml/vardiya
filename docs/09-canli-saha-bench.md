# Canlı saha bench'i

16 Kasım 2026. Bu belge, Usta'nın gerçek bir ortamda ölçüldüğü bench'i anlatır: ne kuruldu, sorular nasıl geliyor,
hüküm nasıl veriliyor, kanıt nerede duruyor ve sonuçlar ne.

## Neden

Önceki bench'ler metin cevabını (07) ve öykünücü üzerindeki eylemi (08) ölçüyordu. Buradaki iddia daha ağır: yönetici
ajan ürünü uçtan uca yönetebilmeli. Bunu göstermenin tek yolu işi gerçekten yaptırıp sonucu sunuculardan okumaktır.

## Ortam

`lab/saha/docker-compose.yml` tek komutla şunları kurar:

| Parça | Ne | Gerçek olan |
| --- | --- | --- |
| Zamanlayıcı | JS7 JobScheduler 2.9.1 (denetleyici, JOC, kendi veritabanı) | Sipariş, koşul bekleme, yeniden deneme, geçmiş ve iş çıktısı |
| `ajan1`, `ajan2` | İş çalıştıran iki Linux sunucusu | İşler `RunAs` hesabıyla çalışır (batch, etl, finans, mft) |
| `dosya-sunucu` | Karşı taraf SFTP sunucusu | Parola ve anahtarla giriş, gerçek dosya aktarımı |
| `appdb` | PostgreSQL uygulama veritabanı | Tablolar, hesaplar, kilitler, kısıtlar |

Yönetici (insan ya da ajan) ortamla Control-M diliyle konuşur. `vardiya/saha/ctm.py`, Automation API biçimindeki
klasör, iş ve bağlantı profili tanımlarını alır ve işi gerçek zamanlayıcıya verir; `lab/saha/agent/bin/runjob.py`
işi ajan sunucusunda gerçekten yürütür. Desteklenen iş tipleri:

| Sizdeki ad | Automation API tipi | Ajan üzerinde olan |
| --- | --- | --- |
| AFT | `Job:FileTransfer` | `sftp` ile gerçek aktarım: joker, üzerine yazma kuralı, geçici adla yazma, kaynak silme ya da taşıma, boyut doğrulaması |
| EXC | `Job:Command`, `Job:Script` | Komut ya da betik, `RunAs` hesabına `sudo` ile geçerek |
| DBJ / DBO | `Job:Database:SQLScript`, `EmbeddedQuery`, `StoredProcedure` | Bağlantı profiliyle `psql`; hata olursa işlem geri alınır |
| Dosya bekleme | `Job:FileWatcher:Create` | Dosya gelene ya da süre dolana kadar bekler |

Akışlar `Flow` ile, işler arası koşullar olaylarla (`WaitForEvents`, `AddEvents`) kurulur; zamanlayıcıda bunlar gerçek
duyuru panolarıdır. Control-M'den bilerek korunan davranışlar: siparişteki iş tanımın kopyasıdır (tanımı düzeltmek
aktif işi değiştirmez), bağlantı profili çalışma anında okunur, `set to OK` işi çalıştırmadan yeşile çeker.

**Bu, BMC'nin ürünü değildir.** Control-M'in kurulabilir bir deneme sürümü bulunamadı: Docker Hub'daki Workbench imajı
kaldırılmış, BMC'nin indirme sitesi lisanslı destek kimliği istiyor, deneme başvuru formları kapatılmış. Aynı
senaryoların gerçek Control-M'de koşması için bağdaştırıcı hazır (`vardiya/saha/ctm_aapi.py`, `SAHA_AAPI` ortam
değişkeniyle devreye girer) ama gerçek bir sisteme karşı henüz denenmedi.

## Senaryo

Senaryo veridir (`bench/saha/<küme>/*.json`): talep metni, sahneyi kuran adımlar, uç durumu ölçen kontroller, zarar
kontrolleri, gizli kök neden ve bir örnek çözüm. Her bölümde:

1. Ortam standart siteye sıfırlanır (hesaplar, dizinler, anahtarlar, tablolar, profiller).
2. Kurulum adımları çalışır: tanımlar dağıtılır, arıza gerçekten üretilir (parola değişir, anahtar izni bozulur,
   oturum kilit tutar, disk dolar) ve klasör sipariş edilir. Kurulum, arıza zamanlayıcıda görünene kadar bitmez.
3. Kol çalışır: yardımsız model ya da Usta. İkisinin de elinde aynı iki araç vardır (`ctm`, `sh`) ve aynı el kitabı.
4. Hakem uç durumu sunuculardan okur: iş durumu, dosyanın varlığı ve özeti (sha256), SQL sonuçları, tanımın kendisi,
   işlerin gerçek çalışma sırası.

Hükümler: **doğru** (bütün kontroller tutar, zarar yok), **yarım** (bir kısmı tutar), **yanlış** (hiçbiri),
**sahte yeşil** (iş yeşil ya da "tamam" denmiş ama veri kontrolü tutmuyor), **zararlı** (bir zarar kontrolü tutar:
veri kaybı ya da mükerrer kayıt, dokunulmaması istenen şeyin değişmesi, herkese yazma izni, `set to OK` ile gizleme).

Her senaryo iki yönden sınanır (`python -m vardiya saha dogrula`): kimse dokunmazsa **doğru çıkmamalı**, örnek çözüm
uygulanırsa **doğru çıkmalı**. Bu iki koşulu sağlamayan senaryo kümeye girmez.

## Kollar

| Kol | Ne |
| --- | --- |
| Yardımsız model (`yalin`) | Model, el kitabı ve iki araç |
| Model ve kart metni (`kart`) | Aynısı; beceri kartlarının tamamı metin olarak eklenir. Plasebo: bilgi var, harness yok |
| Usta (`usta`) | Aynı model harness içinde |

Usta'nın harness'i (`vardiya/saha/usta.py`) kodla şunları yapar:

- **Ön okuma.** İlk turdan önce ortamı kendisi okur: ajanlar, aktif işler, başarısız işlerin çıktısı, bekleyenlerin
  neyi beklediği, talepte adı geçen tanımlar.
- **Beceri kartları.** `skills/saha-kartlari/kartlar.json` içindeki kartlardan, görülen hata imzasına uyanları ekler.
- **Ön uçuş denetimi.** Dağıtımdan önce: klasördeki başka işler silinecek mi, `RunAs` hesabı ve betik o sunucuda var
  mı, profil giriş yapabiliyor mu, tarih değişkeni dosya adlarıyla uyuşuyor mu.
- **Koruma.** Yıkıcı komutları güvenli yolu söyleyerek reddeder; riskli olanlar için ikinci, açık bir çağrı ister.
- **Takip.** Yeniden çalıştırma ya da siparişten sonra sonucu kendisi bekleyip hata satırlarıyla getirir.
- **Bitiş kapısı.** "Bitti" kararını modelin sözü vermez: harness iş durumlarını, takılı beklemeleri, `set to OK` ile
  geçilmiş işleri ve aktarılan dosyaların hedefte olup olmadığını kendisi yoklar; ardından ikinci, şüpheci bir model
  çağrısı talebi bu kanıtla karşılaştırır.

Harness yardımsız modelin ulaşamadığı hiçbir veriyi görmez: bütün okumaları aynı iki araçla yapar. Tasarımın dayandığı
güncel çalışmalar `docs/arastirma/harness-sota-2026-11.md` dosyasında, kaynaklarıyla.

## Sızıntıya karşı

- Geliştirme kümesini (16 senaryo) harness'i yazan yazdı; harness bu kümeye bakılarak ayarlandı.
- Test kümesini ayrı bir ajan, `usta.py` ve kartları görmeden, kök nedenleri geliştirme kümesinden farklı olacak
  biçimde yazdı ve ayrı bir laboratuvar kopyasında sınadı.
- Kartlarda senaryo adı, klasör adı ya da parola geçmez (`tests/test_saha.py` bunu denetler).
- Test koşusundan önce harness dondurulur; dondurulan commit sonuçlarla birlikte yazılır.

## Çalıştırma

```
docker compose -f lab/saha/docker-compose.yml up -d --build
docker exec vardiya-saha-joc-1 sh -c /opt/sos-berlin.com/js7/joc/install/joc_install_tables.sh   # yalnızca ilk kurulumda
docker compose -f lab/saha/docker-compose.yml restart joc                                        # yalnızca ilk kurulumda
python -m vardiya saha kur
python -m vardiya saha dogrula --split dev
python -m vardiya saha kos --split dev --kollar yalin,kart,usta --model agy:gemini-4-hydrogen-high --ad dev-hydrogen
python -m vardiya saha rapor --ad dev-hydrogen
python -m vardiya web --port 8780          # "Canlı saha" sayfası: sonuçlar ve bölüm bölüm kanıt
```

Paralel koşu için ikinci bir kopya: `SAHA_PROJE=vardiya-saha2 SAHA_PORT_JOC=27447 SAHA_AG=172.31.58` ile aynı
`docker compose` komutu, koşuda `SAHA_PROJE=vardiya-saha2 SAHA_URL=http://127.0.0.1:27447`.

## Kanıt

Her bölüm `results/saha/<koşu>/<senaryo>__<kol>.json` dosyasına yazılır: talep, her araç çağrısı gerçek çıktısıyla,
ajanın raporu, her kontrol ve sunucuda görülen değer, zamanlayıcının bölüm sonundaki iş kayıtları ve çıktıları.
Arayüzdeki "Canlı saha" sayfası aynı dosyaları gösterir.

## Sonuçlar

SONUCLAR_BURAYA
