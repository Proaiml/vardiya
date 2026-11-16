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
3. Kol çalışır: araçlı model (yalnız erişim katmanı) ya da Usta. İkisinin de elinde aynı iki araç vardır (`ctm`, `sh`) ve aynı el kitabı.
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
| Saf model (ölçülmez) | Hiç araç yok: yalnızca metin önerir, sitede hiçbir şey değişmez. Uç durumu kimse dokunmadığında (`bos`) olandır |
| Araçlı model (`yalin`, yalnız erişim katmanı) | Model, el kitabı, iki araç ve ajan döngüsü: Vardiya'nın erişim katmanı, harness yok |
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

Harness araçlı modelin ulaşamadığı hiçbir veriyi görmez: bütün okumaları aynı iki araçla yapar. Tasarımın dayandığı
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

16 Kasım 2026 akşamı, yarım kalmış hâliyle. Bütün tablolar `results/saha/TABLOLAR.md` dosyasında
(`python -m vardiya.saha.analiz <koşu>` ile yeniden üretilir); her bölümün kanıtı `results/saha/<koşu>/`.

### Üç basamak

Tablolarda üç basamak vardır, iki değil:

1. **Saf model.** Hiç aracı yoktur: yalnızca metin olarak öneri verebilir, sitede hiçbir şey değişmez. Uç durumu,
   kimse dokunmadığında olandır. Bu ayrıca koşulmaz: her senaryonun doğrulamasındaki "kimse dokunmadı" (`bos`) kolu
   tam olarak bunu ölçer ve kuruluş gereği hiçbir zaman doğru çıkmaz.
2. **Araçlı model** (`yalin`, yalnız erişim katmanı). Vardiya'nın erişim katmanı: ajan döngüsü, el kitabı ve iki araç
   (`ctm`, `sh`). Harness yoktur.
3. **Usta.** Aynı model, aynı araçlar ve aynı el kitabıyla tam harness içinde.

Hangi kazanç hangi katmanın:

- **1'den 2'ye: erişim katmanı.** Büyük kazanç budur ve herhangi bir şeyin çözülmesinin nedenidir. Araçsız bir model
  sunucuya bağlanamaz, işi yeniden çalıştıramaz, dosyayı aktaramaz.
- **2'den 3'e: yönlendirme, koruma ve doğrulama.** Güçlü ve hafif modellerde kazanç hızda: aynı işi daha az adımda
  bitirmek. Zayıf modellerde daha az zararlı sonuç. Küçük yerel modelde (qwen3:14b) geliştirme kümesinde doğrulukta
  da: 16 senaryoda 3'e karşı 9 doğru, 10'a karşı 0 zararlı. Zor kümede doğrulukta bir kazanç gösterilemedi.

Kimse dokunmadığında (`bos`, saf modelin uç durumu), doğrulama koşularından:

| Küme | Senaryo | Doğru | Yarım | Yanlış | Sahte yeşil | Zararlı |
| --- | --- | --- | --- | --- | --- | --- |
| Geliştirme (`dev`) | 17 | 0 | 11 | 5 | 0 | 1 |
| Gizli test (`test`) | 30 | 0 | 13 | 15 | 2 | 0 |
| Zor geliştirme (`zor-dev`) | 10 | 0 | 7 | 0 | 3 | 0 |
| Zor gizli test (`zor-test`) | 18 | 0 | 11 | 5 | 2 | 0 |

"Yarım" burada sitenin dokunulmayan kısmının zaten doğru olmasından gelir (ör. zarar görmemesi gereken tablo). Bir
geliştirme senaryosunda (`ajan-servisi-bakimdan-donmedi`) boş kol "zararlı" çıktı. Bu senaryonun kusurudur; senaryo
ölçülen kümelerde yoktur.

### Model başına sonuçlar

Modeller hiçbir yerde birleştirilmez. "Kurulamadı" bölümler (model servisi kesti ya da kota) hükme girmez; sayıları
yanlarında yazılıdır. Bir koşunun parçası olmadığı sürece ölçüm, donmuş harness ile yapılmıştır (`saha-donuk-1` ve
yalnızca koşucu ya da yerel model bağlamı değişikliği taşıyan `-1b`, `-1c`, `-1d` etiketleri).

**gemini-3.8-flash-low** (hafif model, barındırılan). Kota 16 Kasım ~13:00'te kapandı.

| Küme | Basamak | Bölüm | Doğru | Yarım | Yanlış | Sahte yeşil | Zararlı | Ort. adım |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | Araçlı model | 15 | 15 | 0 | 0 | 0 | 0 | 14.1 |
| dev | Usta | 15 | 15 | 0 | 0 | 0 | 0 | 8.3 |
| test (kısmi, 29 kurulamadı) | Araçlı model | 10 | 10 | 0 | 0 | 0 | 0 | 12.5 |
| test (kısmi) | Usta | 10 | 10 | 0 | 0 | 0 | 0 | 10.5 |

Kart metni kolu (plasebo) dev'de 15/15, ortalama 12.3 adım: bilgi metni tek başına hızı açıklamıyor.

Adım bütçesine göre (dev, 14 ortak senaryo; en çok k adımda doğru bitenler):

| Basamak | k=6 | k=8 | k=10 | k=12 | k=15 | k=20 | k=40 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Araçlı model | 1 | 2 | 7 | 8 | 9 | 13 | 14 |
| Kart metni | 1 | 2 | 6 | 8 | 11 | 13 | 14 |
| Usta | 6 | 9 | 9 | 11 | 14 | 14 | 14 |

**gemini-4-hydrogen-high** (güçlü model). Yalnızca dev, 6 senaryo (30 bölüm kotayla kesildi): araçlı model 6/6 ve
11.0 adım, Usta 6/6 ve 7.7 adım. Gizli test ölçülmedi.

**claude-sonnet-5-5-low**. Kota 15:19'da kapandı. Gizli testte 13 bölüm: araçlı model 7/7, Usta 6/6. Sonuç
çıkarmaya yetmez.

**gpt-oss-120b-medium** (zayıf model, barındırılan; kota 15:20'de kapandı, akşam yeniden açıldı).

| Küme | Basamak | Bölüm | Doğru | Yarım | Yanlış | Sahte yeşil | Zararlı | Ort. adım |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test, bütçe 40 (7 kurulamadı) | Araçlı model | 26 | 8 | 5 | 1 | 8 | 4 | 15.0 |
| test, bütçe 40 | Kart metni | 11 | 2 | 3 | 0 | 5 | 1 | 13.6 |
| test, bütçe 40 | Usta | 27 | 11 | 7 | 0 | 8 | 1 | 18.0 |
| test, bütçe 10 (yarısı) | Araçlı model | 15 | 4 | 6 | 0 | 3 | 2 | 9.5 |
| test, bütçe 10 (yarısı) | Usta | 15 | 5 | 3 | 3 | 4 | 0 | 9.5 |
| zor-test, `saha-donuk-2` | Araçlı model | 17 | 0 | 4 | 0 | 8 | 5 | 18.7 |
| zor-test, `saha-donuk-2` | Usta | 17 | 0 | 2 | 0 | 11 | 4 | 23.2 |

Katalog gizli yarısı (`katalog-test --parca 1/2`, `saha-donuk-2`, `katalog-test-gpt-oss`), **kısmi**: 17 Kasım 00:40'ta `DUR` dosyasıyla durdu; 30 senaryonun 14'ünde iki kol da var (1 bölüm kurulamadı). Araçlı model 14 bölümde 3 doğru, 1 yarım, 3 sahte yeşil, 7 zararlı (20.7 adım); Usta 13 bölümde 3 doğru, 1 yarım, 7 sahte yeşil, 2 zararlı (26.2 adım). Eşli: 13 çift, yalnız Usta doğru 2, yalnız araçlı model doğru 1. Katalog kümesinin bir senaryosu (`k2-55-host-ajan-kapali-tasi-aft-parola-degisti`) doğrulamadan geçmedi; ölçülen 14 senaryonun içinde değil.

Eşli karşılaştırma (aynı senaryolar, araçlı modele karşı Usta): bütçe 40'ta 26 çift; yalnız Usta doğru 5, yalnız
araçlı model doğru 2, işaret testi p=0.45. Bütçe 10'da 15 çift; 3'e 2, p=1.0. Fark anlamlı değil.

Uygulanan riskli eylemler (harness'in kendi kalıplarıyla, iki kolun izine aynı biçimde; test, bütçe 40):

| Basamak | Bölüm | Yıkıcı komut (uygulandı) | Riskli komut (uygulandı) | set to OK | Harness'in durdurduğu |
| --- | --- | --- | --- | --- | --- |
| Araçlı model | 26 | 2 | 4 | 3 | - |
| Usta | 27 | 0 | 50 | 0 | 30 |

Usta'nın "riskli" sayısı, harness'in ikinci, açık çağrıyla izin verdiği komutlardır (ör. bir dosya silme, kapsamı
dar bir `delete`).

**qwen3:14b** (zayıf yerel model; Ollama, `VARDIYA_NUM_CTX=24576`, tek yuva, ekran kartında).

| Küme | Harness | Basamak | Bölüm | Doğru | Yarım | Yanlış | Sahte yeşil | Zararlı | Ort. adım |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev (16) | `saha-donuk-2` | Araçlı model | 16 | 3 | 1 | 2 | 0 | 10 | 22.8 |
| dev (16) | `saha-donuk-2` | Usta | 16 | 9 | 5 | 0 | 2 | 0 | 28.3 |
| test (kısmi; yeniden başlatmada kesildi) | donuk | Araçlı model | 7 | 2 | 1 | 1 | 0 | 3 | 15.1 |
| test (kısmi) | donuk | Usta | 6 | 2 | 1 | 1 | 2 | 0 | 24.8 |
| zor-dev tur 1 | geliştirme | Araçlı model | 10 | 0 | 3 | 0 | 1 | 6 | 32.4 |
| zor-dev tur 1 | geliştirme | Usta | 10 | 0 | 3 | 0 | 2 | 5 | 36.5 |
| zor-dev tur 2 | `saha-donuk-2` | Usta | 10 | 1 | 1 | 0 | 6 | 2 | 27.3 |

Küçük yerel modelin üç basamağı (dev, 16 senaryo):

| Basamak | Doğru | Zararlı | Ne olur |
| --- | --- | --- | --- |
| 1. Saf model | 0 | 0 | Araç yok; sitede hiçbir şey değişmez (kimse dokunmadı kolu: 17 dev senaryosunda 0 doğru) |
| 2. Araçlı model | 3 | 10 | Sunuculara bağlanıp iş yapıyor, ama 16 bölümün 10'unda zarar: 12 yıkıcı komut ve 11 kez set to OK uyguladı |
| 3. Usta | 9 | 0 | Aynı model; harness 232 çağrıyı durdurdu ya da ikinci çağrı istedi, hiçbir yıkıcı komut ve set to OK uygulanmadı |

Eşli karşılaştırma: 16 çift; yalnız Usta doğru 7, yalnız araçlı model doğru 1 (işaret testi p=0.07). Usta adım bakımından hızlı değil (28.3'e karşı 22.8): araçlı model zarar vererek erken bitiriyor.

Kısmi test koşusunda (donuk harness) araçlı model 31 yıkıcı komut uyguladı, Usta'da bu sayı 0. Harness 8 komutu durdurdu.

### Zor küme ve ayar

Zor geliştirme kümesinde (10 senaryo) ilk tur, iki basamakta da 0/10 doğru verdi; zarar ikisinde de yüksekti.
Kanıtta görülenler:

- Zayıf model üründe olmayan komutlar uyduruyordu (profil ya da klasör `create`, `job::set`, `-f dosya`).
- Aynı çağrıyı 15-31 kez tekrarlıyordu.
- Profil ve klasör silmeyi ikinci çağrıda yapıyordu.
- Yanlış veritabanı oturumunu sonlandırıyordu.

`saha-donuk-1` ile `saha-donuk-2` arasındaki harness değişiklikleri:

- **Kalabalık sitede okuma.** Harness'in kendi durum ve tanım okumaları ekran kesimine takılıyordu; kalabalık sitede
  "aktif iş yok" görülüyordu. Artık kesimsiz okunuyor.
- **Talep kapsamı ve klasörler arası olay zinciri.** Kapsam dışı klasöre değişiklik ve veren işi bitmemiş bir olayı
  elle eklemek ikinci bir açık çağrı istiyor.
- **Kabul listesi.** Ayrı bir model çağrısı talebi maddelere bölüyor; bitiş kapısı ve denetçi bunları madde madde
  denetliyor ve altı adımda bir hatırlatılıyor.
- **Bağlantı profilleri.** Profilin hesabı ile uzak yolun ait olduğu hesap uyuşmuyorsa ön uçuş durduruyor; başka işlerin
  kullandığı profilin hesabını ya da sunucusunu değiştirmek de durduruluyor. Profil dağıtılınca aynı hesabı kullanan
  diğer profiller gösteriliyor.
- **Standartlar.** Tanım taleplerinde sunucudaki standart belgesi ön okumaya ve denetçiye ekleniyor.
- **Tek başına sipariş.** Akıştan tek başına sipariş edilen işin öncülünün olayını beklediği söyleniyor.
- **Zayıf model için koruma** (tur 1'den):
  - Talep bir silme istemiyorsa var olan klasörü ya da profili silmek ve mevcut işleri düşüren dağıtım reddediliyor.
  - Yalnızca gerçekten engelleyen veritabanı oturumu sonlandırılabiliyor.
  - Aynı çağrının üçüncüsü çalıştırılmıyor.
  - Üründe olmayan komutlara doğru çağrının örneği veriliyor.
- **Bitiş kapısı.** En çok iki kez geri çeviriyor. "Değiştirmeden raporla" denen taleplerde kırmızı işleri gerekçe
  yapmıyor.

Ayar bir onay turuyla sınırlandı (tur 2, yalnızca Usta). Zararlı 5'ten 2'ye indi, ama zararın çoğu sahte yeşile döndü
(2'den 6'ya). Doğru 0'dan 1'e çıktı. Talimat gereği sonuç kovalanmadı; `saha-donuk-2` bu hâliyle etiketlendi. Zor
gizli küme (`zor-test`, 17 senaryo) bu etiketle gpt-oss ile bir kez koşuldu: iki basamakta da 0/17 doğru; araçlı model 5,
Usta 4 zararlı; sahte yeşil 8'e 11. Zor kümede doğruluk farkı yok.

### Yayın ölçütleri: durum

| Ölçüt | Durum | Kanıt |
| --- | --- | --- |
| 1. Usta, ürünü uçtan uca yönetmede araçlı modelden üstün | Kısmen gösterildi, ilk kümelerde | Güçlü ve hafif modelde aynı doğrulukta belirgin daha az adım (flash dev: 8.3'e karşı 14.1; 8 adımda 9'a karşı 2). Küçük yerel modelde (qwen3:14b, dev) doğru 9'a 3, zararlı 0'a 10 (p=0.07). gpt-oss gizli testte doğru 11'e 8, zararlı 1'e 4 (p=0.45). Hiçbir eşli fark 0.05 altında değil |
| 2. Zor kümede doğruluk farkı | Gösterilmedi | zor-dev'de iki basamak da ~0/10; ayar zararı azalttı, doğruluğu getirmedi; zor-test (gpt-oss) iki basamakta 0/17 |
| 3. Erken uyarı kolu | Kodu var, ölçülmedi | `docs/11`, `vardiya/saha/erken*.py` |
| 4. Kriz hızı | Kısmen | Adım bütçesi tabloları var (flash dev, gpt-oss bütçe 10). Ajan servisi senaryoları: zor-test'teki üçü (`zt-ajan-ayar-bozuk`, `-sozdizimi`, `-yok`) gpt-oss ile ölçüldü, iki basamakta da hiçbiri doğru değil (Usta üçünde sahte yeşil; araçlı model bir yarım, iki sahte yeşil). Geliştirme kümesindeki iki ajan servisi senaryosu ölçülmedi |

### Sınırlar ve ölçülmeyenler

- **Gizli kümeler artık açık.** Test, zor test ve katalog test kümeleri 16 Kasım ölçümlerine kadar harness'i
  geliştirenlerden gizliydi. Depo yayımlandığından beri herkese açıklar; bundan sonraki harness sürümleri bu kümeleri
  görülmemiş diye sunamaz. Yeni bir gizli küme gerekir.
- **Kota.** Bütün barındırılan modellerin kotası gün içinde kapandı: flash ve hydrogen ~13:00 (21 Kasım'da açılır),
  argon 13:36, sonnet 15:19, gpt-oss 15:20 (akşam açıldı). Güçlü model verisi flash ve hydrogen'in sabah verisidir;
  21 Kasım'dan sonra `--atla` ile tamamlanacak. Argon ve sonnet kullanılabilir sonuç vermedi.
- **Yeniden başlatma ve tek hat.** 15:42'de makine ısınıp yeniden başladı (beş lab kopyası ve iki yuvalı ikinci bir Ollama
  sunucusu). O andan beri tek lab, tek koşu, tek model yuvası ve ısı bekçisi (`tools/isi_bekcisi.py`) kuralı geçerli.
  qwen3:14b gizli test koşusu bu yüzden kısmi.
- **Windows.** Bir Windows konuğu (`lab/saha/windows`: Windows Server 2022, WinRM, CtmAgent hizmeti) kuruldu, açıldı,
  bellek için kaldırıldı; hiç kullanılmadı. Canlı bench'te Windows sunucusu ve WinRM yolu yok.
- **Gerçek Control-M.** Kurulmadı (hesabın indirme hakkı yok). Ölçümler JS7 üzerindeki Control-M sözdizimli katmanda.
- **Öykünmeyle olaylar.** Laboratuvarda üretilemeyen olaylar için planlandı (`docs/10`), yapılmadı.
- **Katalog kümeleri** (`bench/saha/katalog-*`). `katalog-test` doğrulaması tamamlandı (59/60). Gizli yarının yarısının ölçümü kısmi kaldı (14/30 senaryo); harness ayarı `katalog-dev` ile yapılmadı.
- **Senaryo yazarının körlüğü.** Yazar `skills/`, `usta.py`, `tests/test_saha.py`, `opsbench.py`, `desk.py`,
  `checks.py`, `skills.py`, `docs/ilerleme.md` ve `bench/saha/test/`'in hiçbirini açmadığını bildirdi. Bir grep
  `usta.py`'nin ilgisiz tek bir satırını gösterdi; dosyayı açmadı. Yanlış adrese giden mesaj bilinen bir sızıntıya yol
  açmadı.
- **Kaynak okuması.** Harness'i yazan taraf, kapsama bölümü için SAB ailelerinin ve öykünücü arızalarının listesini
  okudu; harness'i bunlara göre değiştirmedi. Zor küme ayarı yalnızca `zor-dev` kanıtıyla yapıldı.
- **Örneklem.** Senaryo sayıları küçük (10-30); hiçbir eşli fark istatistik olarak anlamlı değil. Her bölüm bir kez
  koşuldu (pass^k ölçülmedi).

## Bench'ler arası ilişki

Projede dört bench var. Hepsi aynı soruyu sorar (aynı model harness içinde yardımsız hâlinden iyi mi) ama farklı
şeyi, farklı yerde ölçer.

| Bench | Belge | Ne ölçer | Neyin üzerinde | Hüküm neye dayanır |
| --- | --- | --- | --- | --- |
| Scheduler Admin Bench (SAB) | `docs/03` | Tanım ve değişiklik talebini doğru uygulamak ya da gerekçesiyle iade etmek | Emülatördeki site; bir bölümü JS7 üzerinde (`js7bench`) | Tanımların ve talep biletinin son durumu |
| Zamanlayıcı Ops Bench | `docs/07` | Forumlardaki gerçek yönetici sorunlarında teşhis ve doğru adım (metin cevap) | Vaka metni; ortam yok | Cevaptaki beklenen adımlar ve zararlı öneriler (sözcük kümeleri) |
| Müdahale kolu | `docs/08` | Arızayı araçlarla bulup düzeltmek ve işi yeniden yeşile çekmek | Emülatör (`opsworld.py`): 13 arıza, 12 bileşik çift | Emülatör dünyasının son durumu |
| Canlı saha | bu belge | Aynı işleri gerçek zamanlayıcı, gerçek sunucular, gerçek dosya ve veritabanıyla uçtan uca yapmak | Docker laboratuvarı (JS7, iki ajan, SFTP, PostgreSQL) | Sunuculardan okunan uç durum (iş durumu, sha256, SQL, tanım, çalışma sırası) |

Canlı saha ötekilerin üstüne kurulur: zor kümenin her senaryosu `kaynak` alanında hangi vakadan geldiğini yazar
(`ops-dev:<vaka>`, `opsworld:<arıza>`, `sab:<aile>`). Kapsama haritası (geliştirme ve zor geliştirme kümelerinden;
gizli kümelerin kaynakları senaryo yazarının raporunda):

| Emülatör arızası (`opsworld`) | Canlı karşılığı |
| --- | --- |
| `agent_down` | `yonetim-ajan-bakimda` (sunucu kapalı, iş taşınır), `ajan-servisi-bakimdan-donmedi`, `ajan-servisi-ayar-bozuk` (ajan servisi durmuş; `ctmag` ile başlatılır) |
| `password_rotated` | `aft-parola-degisti`, `b-db-parola-ve-mukerrer`, `zd-parola-donusum` (aynı hesabı kullanan iki profil) |
| `disk_full` | `os-disk-dolu`, `zd-disk-standart` (temizlik işinin kapsamı) |
| `pred_setok` | `zd-bos-mutabakat` |
| `ghost_pred` | `zd-yetim-olay` (olayı veren iş başka klasörde düşmüş) |
| `run_as_right` | `os-betik-izni`, `b-os-izin-ve-hedef-dizin`, `zd-yetim-olay` (ikinci arıza) |
| `file_late` | `zd-eksik-sube` |
| `lock_table` | `db-kilit-bekleyen`, `zd-gece-kilit` |
| `resource_stuck`, `oom_kill`, `env_path`, `cert_expired`, `db_corrupt` | Geliştirme kümelerinde karşılığı yok (yazar: `resource_stuck`, `oom_kill`, `db_corrupt` ve `run_as_right`'ın Windows biçimi laboratuvarda üretilemiyor) |

| SAB ailesi | Canlı karşılığı |
| --- | --- |
| `yeni`, `yeni-tip` | `tanim-tek-aft`, `tanim-zincir-bes-is`, `zd-asya-tedarik` |
| `degisiklik` | `tanim-mevcuda-ekleme`, `zd-arsiv-sirasi`, `zd-hareket-rapor` |
| `t-mevcut` | `zd-asya-tedarik` (klasördeki mevcut iş korunmalı), `zd-profil-paylasim` |
| `t-standart`, `t-sablon` | `zd-asya-tedarik`, `zd-disk-standart` (sunucudaki standart belgesi) |
| `t-referans` | `zd-asya-tedarik` |
| `t-bagimli` | `zd-profil-paylasim` (başka işin kullandığı profil değiştirilmemeli) |
| `takvim`, `t-takvim`, `t-dongu`, `t-olmayan`, `kaldir`, `aciklamali`, `t-celiski`, `t-belirsiz`, `t-tip`, `t-uyumsuz` | Canlı karşılığı yok |

Zor kümenin iki yarısı ortak kaynak paylaşmaz. `bench/ops/dev.jsonl`'deki 236 vakanın yaklaşık 150'si arayüz, Windows,
takvim ya da başka zamanlayıcı konusu olduğu için alınmadı.

Canlı bench'in kapsamadıkları: takvimler ve New Day (gün dönümü), zamanlama kriterleri (saat, takvim, döngüsel
işler), kaynak sayaçları (quantitative resource), Windows sunucuları ve WinRM (bir Windows konuğu `lab/saha/windows`
altında hazırlandı ama makinenin belleği yetmediği için koşturulmadı), z/OS ve SAP gibi uygulama ajanları, sertifika
süresi ve zamanlayıcının kendi veritabanının bozulması.
