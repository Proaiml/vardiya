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
| `resource_stuck`, `oom_kill`, `env_path`, `cert_expired`, `db_corrupt` | Geliştirme kümelerinde karşılığı yok |

| SAB ailesi | Canlı karşılığı |
| --- | --- |
| `yeni`, `yeni-tip` | `tanim-tek-aft`, `tanim-zincir-bes-is`, `zd-asya-tedarik` |
| `degisiklik` | `tanim-mevcuda-ekleme`, `zd-arsiv-sirasi`, `zd-hareket-rapor` |
| `t-mevcut` | `zd-asya-tedarik` (klasördeki mevcut iş korunmalı), `zd-profil-paylasim` |
| `t-standart`, `t-sablon` | `zd-asya-tedarik`, `zd-disk-standart` (sunucudaki standart belgesi) |
| `t-referans` | `zd-asya-tedarik` |
| `t-bagimli` | `zd-profil-paylasim` (başka işin kullandığı profil değiştirilmemeli) |
| `takvim`, `t-takvim`, `t-dongu`, `t-olmayan`, `kaldir`, `aciklamali`, `t-celiski`, `t-belirsiz`, `t-tip`, `t-uyumsuz` | Canlı karşılığı yok |

Canlı bench'in kapsamadıkları: takvimler ve New Day (gün dönümü), zamanlama kriterleri (saat, takvim, döngüsel
işler), kaynak sayaçları (quantitative resource), Windows sunucuları ve WinRM (bir Windows konuğu `lab/saha/windows`
altında hazırlandı ama makinenin belleği yetmediği için koşturulmadı), z/OS ve SAP gibi uygulama ajanları, sertifika
süresi ve zamanlayıcının kendi veritabanının bozulması.
