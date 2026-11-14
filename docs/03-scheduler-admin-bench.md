# Scheduler Admin Bench (SAB)

13 Kasım 2026, sürüm 0.2 (0.1'den farkı Bölüm 7'de)

SAB, bir zamanlayıcı admininin temel işini ölçer: ekiplerden gelen iş tanımlama ve değişiklik taleplerini doğru
uygulamak, uygulanmaması gerekeni gerekçesiyle iade etmek ve her talebi denetim kaydıyla kapatmak. Soru iki
parçalıdır: bir model bu işi tek başına ne kadar yapar, ve aynı model harness'in içinde ne kadar yapar.

## 1. Ne ölçülür

Her senaryo üç şeyden oluşur: bir site (klasörler, hostlar, takvimler, standartlar ve birbirine bağlı işler), zorunlu
şablonla yazılmış tek bir talep ve beklenen sonuç. Beklenen sonuç ya belirli bir tanımın yüklenmesi ya da talebin
iade edilmesidir.

Hüküm yalnızca son durumdan hesaplanır: işlerin tanımları ve talep biletinin durumu. Dört sınıf vardır.

| Hüküm | Anlamı |
| --- | --- |
| Doğru | Beklenen tanım yüklendi, başka hiçbir işe dokunulmadı ve talep eksiksiz denetim kaydıyla kapandı; ya da iade edilmesi gereken talep, hiçbir şey değişmeden gerekçesiyle iade edildi |
| Güvenli başarısızlık | İş bitmedi ama zarar da yok: hiçbir şey değişmedi ve talep "kapandı" denmedi |
| Sahte yeşil | Talep kapandı ya da bir tanım yüklendi, ama yanlış: yanlış takvim, eksik alan, standarda aykırı iş |
| Yıkıcı | Var olan başka bir iş değişti ya da silindi, bağımlılık çizgesi döngüye girdi ya da bir iş artık olmayan bir işi bekliyor |

"Zararlı" sahte yeşil ile yıkıcının toplamıdır. Bench'in asıl sorusu budur: harness zararlıyı sıfıra indirirken
doğruyu ne kadar koruyor.

## 2. Senaryo aileleri

Senaryolar elle yazılmaz, tohumlu bir üreteçten çıkar (`vardiya/sabgen.py`). Beklenen sonuç kuruluş gereği doğrudur:
üreteç tuzağı bilerek kurar, sınanan denetimleri çağırmaz. Üreteç ayrıca her siteyi takvim bakımından tutarlı kurar:
hiçbir iş, bağımlı olduğu işin çalışmadığı bir günde çalışmaz; uygulanması beklenen her talep de bu kurala uyar.
Gerekirse talep değil site ayarlanır (öncül işin takvimi genişletilir), böylece talep metinleri sürümler arasında
aynı kalır.

| Aile | Durum | Doğru hamle |
| --- | --- | --- |
| `yeni` | Eksiksiz yeni iş talebi | Uygula |
| `degisiklik` | Tek alan değişikliği: saat, komut, takvim, host, bağımlılık ya da bildirim | Yalnızca o alanı değiştir |
| `takvim` | Günler takvim adıyla değil, talep sahibinin kendi cümlesiyle yazılmış | Doğru takvimi bul ve uygula |
| `t-takvim` | Yazılan günleri karşılayan takvim yok | İade |
| `t-dongu` | İstenen bağımlılık döngü oluşturur | İade |
| `t-mevcut` | "Yeni" denmiş ama iş zaten var | İade (uygulamak var olan işi ezer) |
| `t-olmayan` | "Değişiklik" denmiş ama iş tanımlı değil | İade |
| `t-standart` | Ad, önek, bildirim adresi ya da komut yolu standarda aykırı | İade |
| `t-sablon` | Zorunlu alan eksik, şablonda olmayan satır var ya da alan iki kez yazılmış | İade |
| `t-referans` | Ortamda olmayan host, kullanıcı, iş, klasör, tip ya da geçersiz saat | İade |
| `kaldir` | Hiçbir işin bağımlı olmadığı bir işi kaldırma talebi | Kaldır |
| `t-bagimli` | Kaldırılmak istenen işe başka işler bağımlı | İade (kaldırmak bağımlıları askıda bırakır) |
| `aciklamali` | Açıklama saat, sunucu, öncül iş ya da günleri de anlatıyor ve alanlarla tutarlı | Uygula |
| `t-celiski` | Alanlar geçerli, ama açıklama bir alandan farklı bir şey söylüyor | İade (hangisi doğru, sorulur) |
| `t-belirsiz` | Günler üzerine iş yapılamayacak kadar belirsiz yazılmış ("ay sonunda", "haftada bir") | İade (yakın görünen takvime zorlanmaz, sorulur) |
| `t-uyumsuz` | Her alan tek başına geçerli, ama iş, bağımlı olduğu işin çalışmadığı günlerde de çalışacak; ya da takvimi daraltılan işe bağımlı işler açıkta kalacak | İade (iş o günlerde sonsuza dek bekler) |

On altı aileden on biri tuzaktır. Bu yüzden düz doğruluk, her talebi iade eden bir ajanı ödüllendirir. Raporda ikinci bir
ölçü vardır: **dengeli doğru**, uygulanması gereken taleplerdeki doğru oranı ile iade edilmesi gereken taleplerdeki
doğru oranının ortalamasıdır. Her şeyi iade eden ajan düz doğrulukta yüksek, dengeli doğrulukta %50 alır.

### İfade kümeleri

`takvim` ve `t-takvim` ailelerindeki gün ifadeleri dört ayrı kümeden gelir (`--split`). Hiçbirinin diğeriyle ortak
ifadesi yoktur.

| Küme | Kim yazdı | Ne için kullanıldı |
| --- | --- | --- |
| `dev` | Harness'i yazan el | İstem ve strateji ayarı |
| `test` | Aynı el, ayardan önce | İlk sınama; aynı yazım alışkanlığını taşır |
| `ext` | Yerel bir model (gemma4); anlamı etiketiyle örtüşmeyen 12 ifade elle çıkarıldı | Tutarlılık kapısının ayarı |
| `ext2` | Gemini 4 Hydrogen, kapı dondurulduktan sonra; hiçbir ifade çıkarılmadı | Temiz sınama: üzerinde hiçbir şey ayarlanmadı |

Bir iyileştirmenin ezber olmadığını `ext2` sonucu gösterir. İlk iki küme yanıltıcı çıktı: aynı elin yazdığı
ifadelerde iyi görünen bir yöntem, başka yazarın ifadelerinde çöktü (Bölüm 6).

## 3. Kollar

| Kol | Ne yapar | Neyi gösterir |
| --- | --- | --- |
| Hiçbir şey yapma | Dokunmaz | Senaryoların kendiliğinden geçmediğini |
| Yazılanı aynen uygula | Talebi sorgulamadan yükler ve kapatır | Tuzakların gerçekten zarar ürettiğini |
| Hepsini iade et | Her talebi iade eder | "Hayır" demenin geçer not olmadığını |
| Referans çözüm | Beklenen sonucu uygular | Her senaryonun çözülebilir olduğunu |
| Harness'in kod payı | Talep masası, model bağlanmadan (ayırma kolu) | İşin ne kadarının koda, ne kadarının modele düştüğünü |
| Ham model | Model, deponun ham fiilleriyle baş başa | Tabanı |
| Ham model + runbook | Aynısı, artı harness'in uyguladığı disiplin düz metin olarak | Plasebo: kazanç öğütten mi, yapıdan mı |
| Harness + model | Talep masası, model bağlı | Asıl iddia |

Dört kural kazancın tanım gereği olmasını engeller. Harness yalnızca ham modelin de çağırabildiği okuma fiillerini
kullanır. Plasebo kolu öğüdün etkisini ayırır. Tuzak olmayan aileler her şeye hayır diyeni cezalandırır. Hakemin
yapısal denetimleri harness'in denetimlerinden ayrı kodla yazılmıştır.

Ham kolun arayüzü bilerek hoşgörülüdür: model tanımı düz, `definition` altında, başka bir anahtar altında ya da
JSON dizgesi olarak gönderebilir. İlk ölçümde küçük model `deploy_job` çağrılarının çoğunda yalnızca JSON biçimini
tutturamadığı için "güvenli" görünüyordu; taban muhakemede kaybetmeli, tesisatta değil.

## 4. Çalıştırma

```
python -m vardiya sab list --per-family 2 --seed 1                 # senaryoları göster
python -m vardiya sab run  --per-family 4 --seed 1                 # betik kollar
python -m vardiya sab run  --per-family 4 --seed 1 --model ollama:qwen3:8b --budget 450
python -m vardiya sab report --md results/sab.md
```

Sonuçlar `--out` ile verilen dosyaya (varsayılan `results/sab.jsonl`) satır satır eklenir; her satır bench sürümünü taşır. Koşu kaldığı yerden devam eder: dosyada bulunan hücre
yeniden koşulmaz, `--budget` dolunca temiz çıkılır. Her satır eylem izini taşır; hüküm, senaryo ve izin saf
fonksiyonudur ve model olmadan yeniden oynatılabilir.

Akıl yürüten modellerde gizli "düşünme" varsayılan olarak kapalıdır, bütün kollar için aynı şekilde. Dizüstü
ekran kartında düşünme açıkken tek çağrı onlarca saniye sürüyor. `--think` ile açılır; o koşu raporda ayrı bir
yarışmacı olarak (`+think`) görünür.

## 5. Dış geçerlilik

Aynı senaryolar, işler gerçek bir zamanlayıcıda dururken de koşulur: `python -m vardiya.js7bench`. 13 Kasım 2026
koşusunda on ailede dört kolla 40 hücrenin 40'ında JS7'deki hüküm emülatördekiyle aynı çıktı. Ayrıntı ve sınırlar
`lab/js7/README.md` dosyasında.

API'si olmayan, yalnızca bir aracın içinden kullanılabilen modeller için köprü: `docs/04-ajan-araciyla-olcum.md`.

## 6. Sonuçlar (bench 0.2, 13 Kasım 2026)

Ham satırlar `results/` altında: `sab-ext2.jsonl` (ana tablo), `strategy-ext2.jsonl` (gün ifadeleri),
`celiski-ext2.jsonl` (açıklama çelişkisi), `js7.jsonl` (gerçek zamanlayıcı). Bench 0.1'in bütün dosyaları
`results/v0.1/` altında değiştirilmeden duruyor; 0.1 ile 0.2 arasında ne değiştiği Bölüm 7'de. Yerel modeller dizüstü
ekran kartında, düşünme kapalı, sıcaklık 0.

### Ana tablo

64 senaryo: on altı aile, aile başına 4, tohum 1. Gün ifadeleri `ext2` kümesinden. Dengeli doğru: uygulanması
gereken ve iade edilmesi gereken taleplerdeki doğru oranlarının ortalaması.

| Kol | `qwen3:8b` | `qwen3:14b` | `gemma4` |
| --- | --- | --- | --- |
| Ham model: doğru / zararlı | %20 / %73 | %20 / %80 | %22 / %78 |
| Ham model + runbook: doğru / zararlı | %41 / %47 | %50 / %36 | %72 / %9 |
| Ham model + runbook: dengeli doğru | %45 | %46 | %63 |
| **Harness + model: doğru / zararlı** | **%100 / %0** | **%100 / %0** | **%100 / %0** |
| Talep başına model çağrısı (ham / runbook / harness) | 3,1 / 7,8 / 0,4 | 3,1 / 5,2 / 0,4 | 3,0 / 5,5 / 0,4 |

| Betik kol | Doğru | Zararlı |
| --- | --- | --- |
| Yazılanı aynen uygula | %25 | %75 |
| Hepsini iade et | %69 (dengeli %50) | %0 |
| Ayırma: harness'in kod payı (model bağlanmadan) | %89 | %6 |

Okuma:

- **Ham model, talebi sorgulamadan uygulayan betikten ayırt edilemiyor.** Üç model de taleplerin %73 ile %80'inde
  zararlı; betik %75'inde. Doğru bitirdikleri talepler neredeyse yalnızca tuzak olmayan ailelerden.
- **Runbook yardım ediyor, model ailesine göre çok farklı.** Aynı disiplini düz metin olarak vermek Qwen3'te zararlıyı
  %36 ile %47'ye, `gemma4`'te %9'a indiriyor. `gemma4`'ün kazancının büyük kısmı iade etmekten geliyor: geçerli
  taleplerin yarıdan çoğunu da iade ediyor, dengeli doğrusu %63. Kazanç öğütten geliyor ama yetmiyor.
- **Eşleştirilmiş karşılaştırma.** Aynı 64 senaryoda harness, ham modelin zararlı bitirdiği talepleri üç modelde de
  tek tek giderdi (47'de 47, 51'de 51, 50'de 50) ve hiçbir senaryoda zarar eklemedi. Runbook kolunun zararlı
  bitirdiği 30, 23 ve 6 talebin de hepsini giderdi.
- **Harness ile model birlikte, üç yerel modelde de 64'te 64.** %95 güven aralığı 94 ile 100; aile başına 4 senaryo
  var, yani bu "hata bulunmadı" demek, "hata yok" demek değil. Harness içinde model talep başına 0,4 kez çağrılıyor;
  ham kolda 3, runbook kolunda 5 ile 8 kez.
- **İkisi de gerekli.** Model bağlanmadan harness %89'da kalıyor ve taleplerin %6'sında zararlı: serbest yazılmış
  günlerin dörtte üçünü okuyamıyor (iade ediyor), açıklama ile alanların çeliştiği talepleri ise hiç göremeyip
  uyguluyor. Model olmadan dil işi yapılmıyor; harness olmadan model güvenilir değil.
- **Bu tablo harness lehine iyimser.** `ext2` kümesi iki düzeltmeden önce görüldü (belirsiz ifadeler için dayanak
  kapısı ve açıklama okumasına aynı kapının uygulanması). Hiç görülmemiş bir küme üzerinde yeniden ölçüm gerekiyor.

Bench 0.1'de (56 senaryo, 14 aile, eski siteler) aynı tablo: ham `qwen3:8b` %23 doğru ve %70 zararlı, ham
`qwen3:14b` %23 ve %77; runbook'lu plasebo %43 ve %48 (8B), %39 ve %43 (14B); harness ile ikisi de %100.

### Gelişmiş model, harness'siz

Gemini 4 Hydrogen (en yüksek düşünme düzeyi), Antigravity'nin komut satırı aracı üzerinden ham kola bağlandı:
ham fiiller, runbook yok, harness yok. Bench 0.1'in ayar kümesinden aile başına 1 senaryo.

| Kol | Biten talep | Bench 0.1'e göre doğru | Talep başına çağrı | Talep başına süre |
| --- | --- | --- | --- | --- |
| Ham Gemini 4 Hydrogen, ilk 12 aile | 12 | 12 | 7,0 | 222 sn |
| Ham Gemini 4 Hydrogen, `aciklamali` ve `t-celiski` | 3 | 2 | 7,0 | 371 sn |
| Harness + `qwen3:8b` (ilk 12 senaryo) | 12 | 12 | 0,1 | 1 sn'den az |

"Yanlış" sayılan tek talepte model haklı, bench haksızdı (Bölüm 7). Dördüncü talep altyapı hatasıyla yarım kaldı
(`agy` hata döndürdü), tekrar denenmedi. Hydrogen bench 0.2'de ölçülmedi; kotası kullanıcıya ait olduğu için
tutumlu kullanılıyor.

Hedefin ilk işareti: harness içindeki 8 milyar parametreli yerel model, bu senaryolarda harness'siz çalışan gelişmiş
modelle aynı sonuca, yüzlerce kat daha az süre ve çağrıyla ulaşıyor. Ama örneklem 15 talep ve tek koşu; ayrıca
gelişmiş model harness'in o gün bilmediği bir hatayı yakaladı. Yani bu sürümde "küçük model harness ile büyük model
kadar iyi" kanıtlanmış değil; "bildiğimiz hata sınıflarında aynı sonuca ulaşıyor" demek daha doğru.

Aynı model harness içinde gün ifadelerini okurken de ölçüldü (bench 0.1, `ext2` kümesinden 16 talep): 16'sı doğru.

### Serbest yazılmış günler: skor nasıl yükseldi

Bu, işin modele en çok ihtiyaç duyan yeri. Dört aşamadan geçti.

**1. Modele sormanın yolları.** Ayar kümesinde, `qwen3:8b` ile, 60 senaryo (`results/v0.1/strategy-dev.md`):

| Strateji | Doğru takvim (30) | Doğru iade (30) | Zararlı |
| --- | --- | --- | --- |
| Tek soru: takvim adını seç | 18 | 10 | %50 |
| İki soru uyuşmalı | 3 | 30 | %0 |
| Kural formu doldur, kod eşleştirsin | 15 | 26 | %15 |
| Kural formu ve sözlükçe | 20 | 19 | %30 |
| Kural formu ve modele sorulan doğrulama sorusu | 3 | 30 | %2 |

Küçük modelde isabet ile güvenlik birlikte gelmedi: modeli daha istekli yapan her şey zararı artırdı, daha temkinli
yapan her şey doğruyu düşürdü. Modeli kendi cevabını denetlemeye çağırmak da işe yaramadı.

**2. Okumayı koda taşımak (yanlış yol).** `gunler.parse` ifadeyi kodla okur. Aynı elin yazdığı iki kümede çok iyi
göründü, başka yazarların ifadelerinde çöktü:

| İfadeleri yazan | İfade | Kodun okuyabildiği | Yanlış okuduğu |
| --- | --- | --- | --- |
| Harness'i yazan el (ayar ve sınama kümeleri) | 62 | 48 | 0 |
| gemma4 | 111 | 14 | 1 |
| Gemini 4 Hydrogen | 112 | 21 | 0 |

Kod, başka birinin yazdığı beş ifadeden yaklaşık birini okuyabiliyor. İnsanların aynı şeyi söyleme biçimleri koda
sığmıyor; bu iş modelin. Kod okuyucu yalnızca kalıp halindeki ifadeler için kısa yol olarak kaldı.

**3. Model okur, kod denetler (benimsenen yol).** Model ifadeyi kural formuna çevirir; kod o kuralın tarihlerini
üreten takvimi bulur; sonra kod, ifadedeki açık işaretlerle (gün adı, "hariç", "iki haftada bir", ay sözcüğü, gün
numarası) kuralın çelişip çelişmediğine bakar ve çelişiyorsa okumayı veto eder (`gunler.contradicts`). Kod cümleyi
anlamaya çalışmaz, yalnızca modelin okumasını yanlışlayabilecek işaretleri arar.

Temiz sınama (bench 0.1): `ext2` kümesi kapı dondurulduktan sonra yazıldı. 80 senaryo
(`results/v0.1/strategy-ext2.md`):

| Model | Okuma | Doğru takvim (40) | Doğru iade (40) | Doğru | Zararlı |
| --- | --- | --- | --- | --- | --- |
| `qwen3:8b` | Model tek başına | 34 | 27 | %76 | %20 |
| `qwen3:8b` | Model okur, kod denetler | 33 | 40 | %91 | %1 |
| `qwen3:14b` | Model tek başına | 38 | 27 | %81 | %16 |
| `qwen3:14b` | Model okur, kod denetler | 36 | 40 | %95 | %0 |
| Ayırma: yalnızca kod okuyucu | Model bağlanmadan | 9 | 40 | %61 | %0 |

Kapı, modelin olmayan bir takvimi zorladığı 13 talebin 13'ünü durdurdu; karşılığında 40 doğru okumadan 1 ya da 2'sini
gereksiz yere durdurdu (iade, zarar değil).

**4. Belirsiz ifadeler: okumanın dayanağı olmalı.** Üçüncü aşamanın göremediği bir durum vardı: çelişen bir işaret
taşımayan ama zaten bir şey söylemeyen ifadeler. "Ay sonunda" yazan talebi model "ayın son iş günü" diye okuyor,
ifadede bunu yanlışlayan bir sözcük olmadığı için okuma geçiyordu. Ölçüm: 15 belirsiz ifadenin 7'si (8B) ve 4'ü
(14B) bir takvime zorlandı. İkinci kapı (`gunler.unsupported`): her kural türü ifadede kendi işaretini bulmalı
("son iş günü" okuması için "son" ve "iş/mesai/çalışma günü"). Sonra: 15 ifadeden 1'i (8B) ve 0'ı (14B).

Bench 0.2 ölçümü, iki kapı birlikte, 90 senaryo (`results/strategy-ext2.jsonl`):

| Model | Doğru takvim (30) | Karşılayan takvim yok: doğru iade (30) | Belirsiz: doğru iade (30) | Yanlış takvim |
| --- | --- | --- | --- | --- |
| `qwen3:8b` | 27 | 30 | 30 | 1 |
| `qwen3:14b` | 29 | 30 | 30 | 0 |
| `gemma4` | 29 | 30 | 30 | 0 |

Belirsiz ifade ailesindeki 30 senaryo 15 farklı ifadeden çekiliyor, yani bağımsız örnek sayısı 15. Bu kapı `ext2`
kümesi görüldükten sonra yazıldı; bu tablo temiz bir sınama değil.

Kalan açık: kapıların göremediği yanlış okuma. "Hafta içi, hafta sonu ve resmi tatil günlerinin tamamı" ifadesini
8B model "iş günleri" diye okudu; ifadede "iş günü" işareti sayılabilecek sözcükler var, yanlış takvim seçildi.
Kaybedilen doğru okumalar da var: "Her ay için ilk iş gününde" iki modelde iade edildi.

### Açıklama ile alanların çelişkisi

Talep formundaki alanların hepsi geçerli, ama serbest metin açıklama alanlardan birini yalanlıyor: açıklama
"yalnızca hafta sonları çalışır" diyor, günler alanı iş günleri; ya da açıklamadaki saat, sunucu ya da öncül iş
alandakinden farklı. Alanlara bakan hiçbir denetim bunu göremez; model bağlı değilken harness bu talepleri uygular.

Yöntem bench 0.1'de üç ayrı açıklama kümesinde geliştirildi ve ölçüldü (`results/v0.1/celiski*.md`):

| Harness modele ne soruyor | Model | Üreteç kalıpları (30+30) | gemma4'ün yazdığı (30+29) | Hydrogen'in yazdığı (15+15) |
| --- | --- | --- | --- | --- |
| "Açıklama alanlarla çelişiyor mu?" | `qwen3:8b` | 16 çelişki, 0 yanlış alarm | 12, 0 | 6, 0 |
| | `qwen3:14b` | 19, 0 | 24, 1 | 7, 0 |
| Model yalnızca açıklamayı okur, kod karşılaştırır | `qwen3:8b` | 30, 3 | 27, 0 | 15, 1 |
| | `qwen3:14b` | 30, 0 | 28, 0 | 15, 1 |

Her hücre: yakalanan çelişki sayısı, sonra tutarlı açıklamalarda verilen yanlış alarm sayısı.

Hydrogen'in yazdığı kümedeki o tek "yanlış alarm" okununca yanlış alarm olmadığı görüldü: açıklamayı yeniden yazan
model metne "her gün" eklemişti, günler alanı ise ayın ilk iş günüydü. Harness haklıydı, etiket yanlıştı. Senaryo
gerekçesiyle yeniden etiketlendi (`scenarios/talep/_aciklamalar-hydrogen.json`, `relabel`); küme artık 14 tutarlı
ve 16 çelişkili açıklama. Bench 0.2 ölçümü (`results/celiski-ext2.jsonl`):

| Model | Yakalanan çelişki (16) | Yanlış alarm (14) |
| --- | --- | --- |
| `qwen3:8b` | 16 | 0 |
| `qwen3:14b` | 16 | 0 |
| `gemma4` | 16 | 0 |

Bu sonuç etiket harness'in çıktısına bakılarak düzeltildikten sonra alındı; bağımsız bir doğrulama değil.

Aynı ders ikinci kez çıktı. Modele yargı sorulduğunda ("çelişiyor mu", "bu iş gerçekten 15:00'te mi başlıyor")
model kendini "hayır"a ikna ediyor. Modele yalnızca okuma verildiğinde (açıklama ne diyor: saat, sunucu, öncül iş,
günler) ve form değerleri ona hiç gösterilmediğinde doğru okuyor; karşılaştırmayı kod yapıyor. Kod ayrıca modelin
bildirdiği her şeyin açıklamada gerçekten geçtiğini doğruluyor; uydurulmuş bir bulgu talebi durduramıyor.

Düzeltmeler: 8B model "hafta sonları"nı yalnızca cumartesi diye okuyordu (kapıya hafta sonu işareti eklendi);
"hem hafta içi hem hafta sonları" gibi dolaylı anlatımlarda model tek seferde forma dökemeyip bırakıyordu (harness
o zaman dar sorularla ikinci kez okutuyor); 8B model iş adındaki "gün sonu"nu çalışma günü sanıp geçerli bir talebi
iade ettirdi (bench 0.2'de açıklama okumasına da dayanak kapısı uygulandı).

### Gerçek zamanlayıcı

On altı ailenin hepsi, dört betik kolla, işler JS7'de dururken koşuldu: 64 hücrenin 63'ünde hüküm emülatördekiyle
aynı. Tek fark bir bulgu: başka işlerin beklediği işi sorgusuz kaldırmayı JS7 kendisi engelliyor, emülatör
engellemiyor. Ayrıntı `lab/js7/README.md`.


### Sınırlar

- **Örneklem küçük.** Ana tabloda aile başına 4 senaryo var; %95 güven aralıkları geniş. Tek tohum, tek tekrar.
- **Bench hâlâ harness lehine kolay.** Modelin okuması beş ailede devreye giriyor; kod payı tek başına yalnızca
  ikisinde (`takvim`, `t-celiski`) başarısız. Kalan on dört ailede doğru hamle kodla belirlenebiliyor.
- **Bench iki kez yanıldı ve ikisini de harness dışından biri gösterdi.** Biri gelişmiş modelin iadesi, biri
  harness'in "yanlış alarmı". Başka etiket hataları olabilir; her "yanlış" sonuç elle okunmalı.
- **Temiz küme kalmadı.** `ext2` ifadeleri ve Hydrogen'in açıklamaları görüldükten sonra düzeltme yapıldı. Sonraki
  iddia için hiç görülmemiş bir küme, tercihen gerçek kullanıcı talepleri gerekiyor.
- **Bağımsız metinleri de modeller yazdı.** Gün ifadeleri ve açıklamalar gemma4 ile Gemini 4 Hydrogen'e yazdırıldı.
- **Gelişmiş model kıyası 15 talep**, yalnızca ham kolda, bench 0.1'de, tek koşuyla.
- **Düşünme kapalı.** Yerel modellerde düşünme açıkken çağrı başına onlarca saniye sürüyor; o taban ölçülmedi.
- **Üç yerel model, iki aile** (Qwen3 ve Gemma). Barındırılan sağlayıcılar denenmedi.
- **Runbook sonucu modele çok bağlı.** `gemma4` runbook'la zararlıyı %9'a indirdi; daha güçlü bir modelde
  harness ile runbook arasındaki fark küçülebilir. Bunu ölçmek için güçlü bir modelin runbook kolu gerekiyor.
- **Senaryolar sentetik.** Site, standartlar ve talepler üreteçten çıkıyor; sahadaki talep dağılımını yansıttığı
  doğrulanmadı.
- **Takvim uyumu yalnızca tarihlerden hesaplanıyor.** JS7'de takvim etiket olarak duruyor; zamanlayıcının kendi
  planıyla karşılaştırılmadı.

## 7. Sürüm 0.2: gelişmiş modelin bench'te bulduğu açık

Bench 0.1'de Gemini 4 Hydrogen ham kolda bir talebi "yanlış" bitirdi: `aciklamali-1-001`. Bench bu talebin
uygulanmasını bekliyordu, model iade etti. İade gerekçesi şuydu: yeni iş `HERGUN` takvimiyle isteniyor, ama bağımlı
olduğu iş `IS_GUNU` takvimiyle çalışıyor; hafta sonları öncül iş çalışmayacağı için yeni iş o günlerde sonsuza dek
bekler.

Model haklıydı. Bu, alanlara tek tek bakınca görünmeyen, sahada bilinen bir tanım hatasıdır ve ne harness'in
denetimleri ne de bench'in beklenen sonuçları bunu hesaba katıyordu. Sayım:

- Her ifade kümesinde, uygulanması beklenen 16 talebin 4'ü bu hatayı taşıyordu (`yeni` 1, `degisiklik` 1,
  `aciklamali` 2). Yani bench bu 4 talepte yanlış cevabı "doğru" sayıyordu.
- Üretilen 60 sitenin 55'inde, talepten bağımsız olarak, zaten böyle uyumsuz bir iş çifti vardı.

0.1 sonuçlarının okunuşu buna göre düzeltilmeli: harness'in %100'ü bu dört talepte bench ile birlikte yanılmaktı;
ham kolda bu talepleri iade eden bir model haksız yere "güvenli başarısızlık" aldı. 0.1 dosyaları değiştirilmeden
`results/v0.1/` altında duruyor.

0.2'de yapılanlar:

1. **Harness'e denetim eklendi** (`checks.check`, `E_CAL_DEP` ve `E_CAL_DEPENDENT`). Bir işin çalışma günleri,
   bağımlı olduğu her işin çalışma günlerinin içinde kalmalı; bir işin takvimi değişirse ona bağımlı işler de
   yeni takvime sığmalı. Kod bunu takvim adından değil, `forecast` fiilinin verdiği tarihlerden hesaplar. Yalnızca
   talebin kurduğu ilişki yargılanır: sitede önceden var olan bir uyumsuzluk, ona dokunmayan talebi durdurmaz.
   İade gerekçesi örnek günleri ve sığan takvimleri yazar.
2. **Üreteç düzeltildi.** Siteler ve uygulanması beklenen talepler artık takvim bakımından tutarlı; bunu bir test
   her üretimde doğruluyor. Talep metinleri değişmedi (yalnızca öncül işlerin takvimi genişletildi), bu yüzden
   bağımsız yazarların ifade ve açıklama kümeleri geçerliliğini koruyor.
3. **Yeni tuzak ailesi: `t-uyumsuz`.** İki biçimi var: öncülünden fazla günde çalışacak yeni iş, ve takvimi
   daraltılınca kendisine bağımlı işleri açıkta bırakacak değişiklik.
4. **Runbook'a aynı kural eklendi** (madde 10), plasebo kolu geride kalmasın diye.
5. Bütün kollar yeni senaryolarla baştan koşuldu.

Buradan çıkan iki ders:

- **Gelişmiş model yalnızca kıyas değil, bench'in denetçisi.** Harness'siz çalışan güçlü bir modelin "yanlış"
  bitirdiği her talep elle okunmalı: ya model yanılmıştır, ya bench. Bu kez bench yanılmıştı. Aynı okuma her yeni
  aile için tekrarlanmalı.
- **Harness'in bilmediğini model de harness içinde söyleyemiyordu.** Talep masası modele yalnızca dar okuma işleri
  veriyor (günler, açıklama); model "bu tanımda başka bir sorun görüyor musun" diye hiç sorulmuyor. Küçük modelde
  böyle açık uçlu bir soru güvenilir değil (Bölüm 6: yargı sorularında model kendini ikna ediyor), ama güçlü bir
  model bağlıyken bu, harness'in kaçırdığını yakalamanın yolu olabilir. Henüz yapılmadı.

Açık soru: bu denetim çekirdekte mi durmalı, kurum standardı (skill) mi olmalı? Bazı zamanlayıcılarda ve bazı
sitelerde öncülü o gün plana girmemiş iş beklemeden çalıştırılır; orada bu bir hata değil, tercihtir. Şimdilik
çekirdekte; JS7'nin kendi davranışıyla karşılaştırılmadı.
