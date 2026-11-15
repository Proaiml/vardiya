# Vardiya

Batch zamanlayici operasyonlari (Control-M ve benzerleri) icin acik, modelden bagimsiz ajan harness'i
ve ona bagli benchmark. Calisma adi; degisebilir.

Harness'in icinde calisan admin ajaninin adi **Usta**: kriz aninda cagrilan urun admini gibi sorunu
teshis eder, guvenli bicimde duzeltir ve isi yeniden baslatir. "Vardiya" harness'in (yetenekler, kurallar, erisim
katmani), "Usta" onu kullanan ajanin adidir.

Iki is kolu var:

- **Talep karsilama (cekirdek).** Ekiplerden zorunlu sablonla gelen is tanimlama ve degisiklik taleplerini alir,
  denetler, uygular ve denetim kaydiyla kapatir. Uygulanamayan talep gerekcesiyle iade edilir.
- **Ariza mudahalesi.** Hata alan isi teshis eder ve guvenli bicimde toparlar.

Bu surum dikey dilimdir: mimarinin butun katmanlarindan bir kez gecer.
Bagimlilik yok; yalnizca Python 3.10+ standart kutuphanesi.

**Nasil kullanilir:** `docs/05-kullanim-kilavuzu.md`. **Olcum ve sonuclar:** `docs/03-scheduler-admin-bench.md`.
**Is tipleri, dunyadaki benchmarklar, olaydan once tahmin:** `docs/06-is-tipleri-benchmarklar-ve-olay-onceligi.md`.
Durum: isler emulatorde ya da yerel JS7 laboratuvarinda durur; uretim ortami icin hazir bir bagdastirici yok.

## Calistirma

```
python -m unittest discover -s tests        # 86 test
python -m vardiya bench                     # iki is kolu icin senaryo x kol matrisi (betik kollar)
python -m vardiya bench --only talep        # yalnizca talep karsilama
python -m vardiya fuzz -n 3000              # guvenlik hatti: rastgele ajan ve bozuk talep, ham vs harness
python -m vardiya talep t-yeni-001          # tek talep: sablon, sonuc, denetim kaydi
python -m vardiya talep --file ornekler/talep-yeni.txt   # kendi talep dosyaniz (--site ile kendi ortaminiz)
python -m vardiya olay run --split test --model ollama:qwen3:8b   # olay bench'i: kucuk model tek basina ve harness icinde
python -m vardiya ops run --split test --arms skill,ham,harness --model ollama:qwen3:8b   # ops bench: forumlardaki gercek admin sorunlari (docs/07)
python -m vardiya web                       # operasyon konsolu: talepler, olaylar, kok neden: http://127.0.0.1:8765
python -m vardiya run partial-load-001      # tek ariza vakasi, operator raporu
```

## Talep sablonu

Talep `templates/talep-sablonu.txt` dosyasinin doldurulmus halidir; her satir `alan: deger`.
Sablon zorunludur: eksik alan, sablonda olmayan satir ya da iki kez yazilmis alan iade nedenidir.

```
talep_no: CHG-1001
talep_eden: odeme-ekibi
islem: yeni
klasor: ODEME_GUNLUK
is_adi: ODM_LOAD_IADE
tip: komut
host: app01
calistiran: odmusr
komut: /opt/odeme/bin/load_iade.sh
gunler: IS_GUNU
saat: 02:30
bagimlilik: [ODM_WATCH_DOSYA]
bildirim: odeme-nobet@ornek.local
aciklama: Iade dosyasini staging tablosuna yukler
```

Is bolumu: sablonu kod okur, tanimi kod derler, denetimleri kod yapar; dili model okur, kod onun okumasini denetler.

`gunler` alani bir takvim adi degil de serbest bir ifadeyse ("ay kapanisinda, son mesai gununde") uc adim calisir:

1. **Model okur.** Ifadeyi bir kural formuna cevirir (her gun, is gunleri, haftanin su gunleri, ayin son is gunu,
   ayin N. gunu, ya da "bu formlarla ifade edilemez"). Harness ona alan sozlukcesini verir.
2. **Kod eslestirir.** Ortamdaki takvimlerden, o kuralin tarihlerini birebir ureten takvim aranir. Yoksa talep iade edilir.
3. **Kod denetler.** Ifadedeki acik isaretler (gun adi, "haric", "iki haftada bir", ay sozcugu, gun numarasi) modelin
   kuraliyla celisiyorsa okuma veto edilir ve talep iade edilir (`gunler.contradicts`). Veto her zaman guvenlidir.
   Okuma ifadede kendi dayanagini da bulmalidir (`gunler.unsupported`): "ay sonunda" ya da "haftada bir" gibi
   belirsiz bir ifade, yakin gorunen takvime zorlanmaz, talep sahibine sorulur.

Kalip halinde yazilmis ifadeleri kod kendisi okur (`gunler.parse`); baska yazarlarin ifadelerinde bu bes ifadeden
biridir, gerisini model okur.

Olcum (Scheduler Admin Bench 0.2, baska bir yazarin ifadeleri, 90 talep, uc yerel model): harness icinde dogru
takvim 30 ifadenin 27 ile 29'unda bulundu; karsilayan takvimi olmayan 30 ve belirsiz yazilmis 30 ifadenin hepsi iade
edildi; 270 talepte 1 yanlis takvim. Ayni ifadelerde model tek basina (bench 0.1) %76 ile %81 dogru, %16 ile %20
yanlis takvimdi. Ayrinti: `docs/03-scheduler-admin-bench.md`.

Kapatilan her talebe denetim kaydi yazilir: kapatan, talep numarasi, istenen tanim, uygulanan tanim,
onceki tanim, uyarilar ve sonraki calisma gunleri.

Yerel modelle (Ollama calisiyor olmali):

```
python -m vardiya models                                  # kurulu Ollama modelleri
python -m vardiya bench --model ollama:qwen3:8b           # raw_llm ve harness_llm kollari eklenir
python -m vardiya talep t-takvim-005 --model ollama:qwen3:8b
```

Antigravity komut satiri araci (`agy`) kuruluysa, API anahtari olmayan modeller de baglanir:
`--model agy:gemini-4-hydrogen-xhigh` (kimlikler: `agy models`). Model bos bir klasorde calistirilir ve
yalnizca metin cevabi alinir.

Baska bir uc nokta: `--model herhangi:model-adi --base-url http://host:port/v1`, anahtar icin
`VARDIYA_API_KEY`. OpenAI uyumlu sohbet arayuzu konusan her sunucu baglanir.
Yalnizca Ollama yolu hedeflendi; barindirilan saglayicilar henuz denenmedi.

## Katmanlar

| Dosya | Modul | Isi |
| --- | --- | --- |
| `emulator.py` | Emulator | Deterministik zamanlayici: event, host, kaynak, hold, rerun, set to ok |
| `adapter.py` | Bagdastirici | Harness ile zamanlayici arasindaki tek kapi; eylem izi tutar |
| `world.py` | Dunya modeli | Topoloji, etki alani, kritik yol, ilk ariza yalitimi, sysout farki, imza |
| `policy.py` | Politika cekirdegi | Yetki seviyeleri, on ucus denetimleri, onay, dongu korumasi |
| `ledger.py` | Olay defteri | Yerel, yalnizca eklemeli, ozet zincirli vaka kaydi; emsal arama |
| `skills.py` | Skill katmani | Deklaratif runbook yukleyici, guvenli kosul degerlendirici |
| `gateway.py` | Model gecidi | OpenAI uyumlu uc nokta; sema onarimi; kisitli secim |
| `harness.py` | Olay dongusu | Gozle, hatirla, teshis et, oner, denetle, uygula, dogrula, kaydet |
| `bench.py` | Bench | Kollar, hukum siniflari, yeniden oynatma, guvenlik fuzz'i |
| `repo.py` | Tanim deposu | Is tanimlari, takvimler, hostlar, talep bileti; takvim ileri sarma |
| `intake.py` | Talep girisi | Zorunlu sablonun kati ayristiricisi |
| `checks.py` | On ucus denetimleri | Standart, referans, dongu, mevcut is, saat ve bagimlilik denetimleri; isin takvimi, bagimli oldugu islerin takvimine sigmali; is tipine gore alanlar, baglanti profili, talebe yazilmis parola |
| `desk.py` | Talep masasi | Sablon, derleme, denetim, yukleme, geri okuma, denetim kaydi |
| `bench_req.py` | Talep bench'i | Kollar, hukum, bozuk talep fuzz'i; hakem denetimleri `checks.py`'den bagimsiz |
| `gunler.py` | Gun ifadesi sozlugu | Kalip halindeki Turkce gun ifadelerini kodla takvim kuralina cevirir; gerisi modele kalir |
| `sabgen.py`, `sab.py` | Scheduler Admin Bench | Tohumlu senaryo ureteci; kosucu, kayitli sonuclar, rapor |
| `web.py`, `static/index.html` | Onyuz | Operasyon konsolu: genel bakis, olaylar ve kok neden, erken uyari, talep masasi, ortam, denetim defteri, bench |
| `saglik.py` | Tanim sagligi | Ortamdaki her isi yeni talep gibi denetler: takvim uyumsuzlugu, sure sinirsiz dosya izleme, tanimdaki parola, ayni komut |
| `olaybench.py` | Olay bench'i | Ayni olaylarda kod, ham model ve harness + model; adlari ve hata yazimlari degistirilmis test bolumu |
| `graph.py`, `gecmis.py`, `cozumle.py` | Yerel hata cizgesi | Isler, calismalar, hata imzalari, degisiklikler ve olaylar SQLite'ta; kod kanit toplar ve kok neden adaylarini siralar, model yalnizca adaylar arasindan secer; erken uyarilar |
| `js7.py`, `js7repo.py`, `js7bench.py` | JS7 bagdastiricisi | Ayni fiiller gercek zamanlayici uzerinde; dis gecerlilik kosusu |

## Iki degismez kural

1. Model zamanlayiciya dokunmaz; yalnizca oneri uretir.
2. Her oneri, kimden gelirse gelsin, politika cekirdeginden gecer.

## Hukum siniflari

`correct`, `false_green` (zincir yesil, veri bozuk), `safe_fail` (cozemedi ama zarar vermedi),
`destructive`. Hukum yalnizca dunya durumundan hesaplanir ve her iz model cagrilmadan yeniden oynatilabilir.

## Senaryolar

| Kimlik | Ne sinar |
| --- | --- |
| `partial-load-001` | Yarim yukleme: temizliksiz rerun mukerrer, Set to OK eksik veri uretir |
| `expected-nodata-002` | Ters tuzak: dogru hamle gerekceli Set to OK |
| `no-incident-003` | Kontrol: ariza yok, dogru hamle hicbir sey yapmamak |

Talep senaryolari `scenarios/talep/` altinda; ortak ortam `_ortam.json` dosyasinda.

| Kimlik | Ne sinar |
| --- | --- |
| `t-yeni-001`, `t-degis-002` | Eksiksiz talep: dogru hamle uygulamak; degisiklikte yalnizca istenen alan degisir |
| `t-dongu-003` | Tuzak: istenen bagimlilik dongu olusturur |
| `t-mevcut-004` | Tuzak: "yeni" denmis ama is zaten var; uygulamak mevcut isi ezer |
| `t-standart-006`, `t-eksik-007` | Tuzak: standart ihlali, eksik sablon |
| `t-takvim-005`, `t-takvim-008` | Gunler serbest yazilmis; dogru takvimi model bulmali |
| `t-takvim-009` | Tuzak: istenen gunleri karsilayan takvim yok; dogru hamle iade |

Hicbir kestirme hepsini gecemez: her seyi uygulayan tuzaklarda, her seyi iade eden gecerli taleplerde kalir.
Bu dokuz senaryo mimarinin calistigini gosterir; olcum icin uretilmis senaryolar ve bagimsiz yazarli ifade
kumeleri kullanilir (asagida, Scheduler Admin Bench).

## Skill yazmak

Skill, `skills/<ad>/SKILL.md` dosyasidir: ustte on bilgi blogu, altinda duz yazi aciklama. Skill veri olarak
yuklenir; kod calistiramaz, dis baglanti tasiyamaz, cekirdekte olmayan fiil ya da olgu kullanamaz. Iki tur var.

**Talep kurali skill'i** (`kind: request_rules`): kurumun is tanimi standartlari. Her kural bir kosul ve kosul
saglanmadiginda talep sahibine donecek gerekcedir. Ornek: `skills/talep-standartlari/SKILL.md`.

```
---
name: gece-penceresi
description: Komut isleri gece penceresinde baslar.
kind: request_rules
rules:
  gece_penceresi:
    when: type == komut
    require: hour < 6
    message: komut isleri 00:00 ile 06:00 arasinda baslamali
---
```

Bu dosyayi `skills/gece-penceresi/SKILL.md` olarak kaydetmek yeterlidir; kod degismez. Kural yalnizca iade
gerekcesi ekleyebilir: cekirdek denetimlerinin (var olan is, olmayan host, dongu, eksik alan, acik talebe bagli
olmayan tanim) reddettigini hicbir skill kabul ettiremez. Standart skill'i hic yuklenmese bile bu denetimler calisir.

**Ariza skill'i**: tetik, yetki, izinli eylemler, teshis kosullari, planlar ve dogrulama kosullari.
Ornek: `skills/failed-load-triage/SKILL.md`.

## Scheduler Admin Bench

Uretilen talep senaryolariyla kollari karsilastiran bench. Tasarim, kollar ve sonuclar:
`docs/03-scheduler-admin-bench.md`.

```
python -m vardiya sab run --per-family 4 --seed 1                              # betik kollar
python -m vardiya sab run --per-family 4 --seed 1 --model ollama:qwen3:8b      # ham, plasebo ve harness kollari
python -m vardiya sab report
python -m vardiya.js7bench --per-family 1 --seed 1                             # ayni senaryolar gercek JS7 uzerinde
```
