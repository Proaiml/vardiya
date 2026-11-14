# Kullanım kılavuzu

Sürüm 0.2, 13 Kasım 2026

## 1. Bu ne, ne değil

Vardiya, bir zamanlayıcı admininin temel işini yapan bir ajan harness'idir: ekiplerden gelen iş tanımlama, değişiklik
ve kaldırma taleplerini alır, denetler, uygular ve denetim kaydıyla kapatır; uygulanmaması gereken talebi gerekçesiyle
iade eder. Arkasına ücretsiz ya da ücretli herhangi bir dil modeli bağlanabilir.

İş bölümü: şablonu kod okur, tanımı kod derler, denetimleri kod yapar. Model yalnızca dil işini yapar (serbest yazılmış
günleri ve açıklamayı okur) ve kod onun okumasını denetler. Model zamanlayıcıya hiç dokunmaz.

Bugünkü durum, açıkça:

- İşler **emülatörde** ya da yerel **JS7 laboratuvarında** durur. Control-M bağdaştırıcısı yok; üretim ortamına
  bağlanacak hazır bir yol yok.
- Ölçümler sentetik senaryolarla yapıldı (`docs/03-scheduler-admin-bench.md`). Gerçek kullanıcı talepleriyle ölçüm yok.
- Arıza müdahalesi kolu yalnızca üç senaryoluk bir gösterimdir.

Yani bu sürüm denemek, ölçmek ve üzerine geliştirmek içindir; üretimde iş tanımı yükletmek için değil.

## 2. Kurulum

Python 3.10 ya da üstü yeterli; bağımlılık yok.

```
git clone <depo adresi>
cd schedularharness
python -m unittest discover -s tests
```

Testler geçiyorsa kurulum tamamdır. İsteğe bağlı: `pip install -e .` sonrasında `python -m vardiya` yerine `vardiya`
yazılabilir.

## 3. Beş dakikada

```
python -m vardiya talep t-yeni-001                      # hazır bir talep: şablon, sonuç, denetim kaydı
python -m vardiya talep --file ornekler/talep-yeni.txt  # dosyadan talep: günler serbest yazılmış
python -m vardiya talep --file ornekler/talep-uyumsuz.txt   # iade edilen bir talep ve gerekçesi
python -m vardiya bench --only talep                    # dokuz sabit senaryo, betik kollar
python -m vardiya fuzz -n 3000                          # güvenlik hattı
```

### Önyüz

```
python -m vardiya web                                   # http://127.0.0.1:8765
python -m vardiya web --model ollama:qwen3:8b --site benim-ortamim.json --licence 2
```

Tarayıcıda açılan sayfanın beş sekmesi var:

| Sekme | Ne gösterir |
| --- | --- |
| Talep | Şablon düzenleyici, örnek talepler, sonuç kartı: kapandı / iade / öneri, iade gerekçesi, günlerin hangi takvime kim tarafından çevrildiği, uygulanan tanım ya da değişikliğin önce ve sonrası, sonraki çalışma günleri, denetim kaydı, ajanın adımları ve eylem izi |
| Ortam | İşlerin bağımlılık çizgesi (değişen işler vurgulu), iş tablosu, takvimler ve sonraki günleri, hostlar, klasörler, standartlar, tatiller |
| Geçmiş | Bu oturumda işlenen bütün talepler; "Ortamı başa döndür" |
| Denetim defteri | Özet zincirli kayıtlar ve zincirin bütünlük denetimi |
| Bench | `results/` altındaki sonuç dosyalarından kol ve aile bazında doğru ve zararlı oranları |

Sayfa tek bir bellek içi ortamla çalışır: uygulanan her talep, sonraki talebin gördüğü işleri değiştirir. Sunucu
kapanınca ortam başa döner. Talep, komut satırındakiyle aynı masadan geçer; önyüzün masayı atlayan bir yolu yok.
Sunucu yalnızca 127.0.0.1'i dinler ve girişi yoktur; ağa açmayın. `--model` verilirse her talep o modeli çağırabilir
(yerel modelde GPU kullanır).

`talep` çıktısı nasıl okunur:

| Satır | Anlamı |
| --- | --- |
| `Sonuc: closed` | Tanım yüklendi, geri okundu ve talep denetim kaydıyla kapandı |
| `Sonuc: returned` | Hiçbir şey değişmedi; `Gerekce` satırları talep sahibine ne düzeltmesi gerektiğini söyler |
| `Sonuc: proposed` | Ajanın yetkisi yüklemeye yetmedi; tanım öneri olarak kaldı |
| `Gunler ifadesi` | Serbest yazılmış günlerin hangi takvime, kim tarafından (kod ya da model) çevrildiği |
| `Sonraki calismalar` | Yüklenen işin ilk çalışma günleri; yanlış takvim seçildiyse burada görünür |

## 4. Kendi talebinizi denemek

1. `templates/talep-sablonu.txt` dosyasını kopyalayıp doldurun. Her satır `alan: deger`; `#` ile başlayan satır yorumdur.
2. Çalıştırın:

```
python -m vardiya talep --file benim-talebim.txt
python -m vardiya talep --file benim-talebim.txt --model ollama:qwen3:8b
python -m vardiya talep --file benim-talebim.txt --site benim-ortamim.json
```

Üç işlem türü vardır:

| `islem` | Yazılacak alanlar | Ne olur |
| --- | --- | --- |
| `yeni` | Bütün alanlar (bağımlılık yoksa `[]`) | İş tanımlanır |
| `degisiklik` | `klasor`, `is_adi` ve yalnızca değişecek alanlar | Yalnızca yazılan alanlar değişir |
| `kaldir` | Yalnızca `klasor` ve `is_adi` | İş kaldırılır; başka iş ona bağımlıysa iade edilir |

`gunler` alanına takvim adı yazılabilir (`IS_GUNU`) ya da günler kendi cümlenizle anlatılabilir ("her ayın son iş
günü"). Kalıp ifadeleri kod okur; gerisi için bir model bağlı olmalıdır. Model bağlı değilken okunamayan ifade iade
edilir, tahmin edilmez.

Harness'in iade ettiği durumlar: şablona uymayan talep; var olan işe "yeni", olmayan işe "değişiklik"; ortamda
olmayan host, kullanıcı, klasör, iş ya da takvim; döngü kuran bağımlılık; kurum standardına aykırı ad, komut yolu ya
da bildirim adresi; karşılayan takvimi olmayan ya da belirsiz yazılmış günler ("ay sonunda", "haftada bir");
açıklamanın alanlardan farklı bir şey söylemesi; işin, bağımlı olduğu işin çalışmadığı günlerde de çalışacak olması.

## 5. Model bağlamak

| Yol | Örnek | Not |
| --- | --- | --- |
| Yerel, Ollama | `--model ollama:qwen3:8b` | `python -m vardiya models` kurulu modelleri listeler |
| OpenAI uyumlu herhangi bir uç nokta | `--model x:model-adi --base-url http://host:port/v1` | Anahtar `VARDIYA_API_KEY` ortam değişkeninden okunur |
| Antigravity komut satırı aracı | `--model agy:gemini-4-hydrogen-xhigh` | `agy` kurulu olmalı; kimlikler `agy models` |

Ortam değişkenleri: `VARDIYA_BASE_URL`, `VARDIYA_API_KEY`, `VARDIYA_THINK=1` (akıl yürüten yerel modellerde gizli
düşünmeyi açar; çağrı başına onlarca saniye sürer, varsayılan kapalı), `VARDIYA_NUM_CTX` (Ollama bağlam boyu,
varsayılan 16384).

Hangi model: ölçülen üç yerel model de (`qwen3:8b`, `qwen3:14b`, `gemma4`) harness içinde bench'in ana tablosunda aynı
sonucu verdi. Fark serbest yazılmış günlerde çıkıyor: 8 milyar parametreli model 30 ifadenin 27'sini, diğer ikisi
29'unu doğru takvime çevirdi. Dizüstü ekran kartında talep başına bir saniye civarı sürüyor. Barındırılan
sağlayıcılar (OpenAI, Anthropic, Gemini uç noktaları) denenmedi.

Anahtarları dosyaya yazmayın; ortam değişkeni kullanın. Talep şablonuna parola ve gizli bilgi yazılmaz: talep metni
olduğu gibi denetim kaydına ve, model bağlıysa, modele gider.

## 6. Kendi ortamınızı tanımlamak

Ortam tek bir JSON dosyasıdır; örnek `scenarios/talep/_ortam.json`. `--site` ile verilir.

```
{
 "today": "2026-11-13",
 "env": {
  "hosts":     {"app01": {"users": ["batchusr"], "desc": "uygulama sunucusu"}},
  "calendars": {"IS_GUNU": {"rule": {"type": "workdays"}, "desc": "pazartesiden cumaya, resmi tatiller haric"}},
  "folders":   {"RAPOR": {"prefix": "RPR_"}},
  "standards": {"name_regex": "[A-Z][A-Z0-9_]{3,29}", "notify_suffix": "@ornek.local"},
  "holidays":  ["2026-12-31", "2027-01-01"]
 },
 "jobs": [
  {"name": "RPR_GUNLUK_OZET", "folder": "RAPOR", "type": "komut", "host": "app01", "run_as": "batchusr",
   "command": "/opt/rapor/bin/ozet.sh", "calendar": "IS_GUNU", "time": "05:00", "deps": [],
   "notify": "rapor-nobet@ornek.local", "description": "Gunluk ozet raporu"}
 ]
}
```

Takvim kuralı biçimleri:

| Kural | Anlamı |
| --- | --- |
| `{"type": "daily"}` | Her gün, tatiller dahil |
| `{"type": "workdays"}` | Pazartesiden cumaya, resmi tatiller hariç |
| `{"type": "weekly", "days": [0, 5]}` | Haftanın belirli günleri (0 pazartesi, 6 pazar) |
| `{"type": "month_end_workday"}` | Her ayın son iş günü |
| `{"type": "month_day", "day": 15, "shift": "next"}` | Ayın belirli günü; iş günü değilse `next` sonraki, `prev` önceki iş gününe kayar, `none` kaymaz |

İş tipleri: `komut` ve `dosya_izleme`.

## 7. Kurum kuralı eklemek (skill)

Kurum standartları kod değil veridir: `skills/talep-standartlari/SKILL.md`. Yeni bir kural için `skills/` altında
yeni bir klasör açıp kendi `SKILL.md` dosyanızı yazın:

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

Kullanılabilen olgular ve işleçler aynı dosyada listelidir. Bir skill yalnızca iade gerekçesi ekleyebilir; çekirdek
denetimlerinin reddettiğini kabul ettiremez, kod çalıştıramaz. Listede olmayan bir olguya başvuran skill yüklenmez.

## 8. Ölçmek: Scheduler Admin Bench

```
python -m vardiya sab list --per-family 2 --seed 1                      # senaryoları gör
python -m vardiya sab run  --per-family 4 --seed 1 --split ext2 --out results/benim.jsonl
python -m vardiya sab run  --per-family 4 --seed 1 --split ext2 --out results/benim.jsonl --model ollama:qwen3:8b
python -m vardiya sab report --out results/benim.jsonl --md results/benim.md
```

- İlk `run` betik kolları koşar (model gerekmez). `--model` ile üç model kolu eklenir: ham model, ham model ve
  runbook, harness ve model. Yalnızca birini koşmak için `--arms harness_llm`.
- Koşu kaldığı yerden devam eder; `--budget 600` ile süre sınırı konur.
- `--split`: gün ifadelerinin kimin yazdığı küme. Kendi modelinizi karşılaştırırken `ext2` kullanın.
- Rapordaki dört hüküm: doğru, güvenli başarısızlık (iş bitmedi ama zarar yok), sahte yeşil (yanlış iş yüklendi ya
  da talep yanlış kapandı), yıkıcı. Bakılacak iki sayı: **doğru** ve **zararlı** (sahte yeşil ile yıkıcının toplamı).

Sonuç nasıl okunmalı: harness'in işi zararlıyı sıfıra indirirken doğruyu korumaktır. "Hepsini iade et" kolu da sıfır
zararlıdır ama dengeli doğruda %50 alır; yalnızca zararlıya bakmak yanıltır. Yayımlanmış sayılar ve sınırları için
`docs/03-scheduler-admin-bench.md`.

## 9. JS7 laboratuvarı

Aynı fiiller gerçek bir zamanlayıcıda da çalışır. Kurulum ve bilinen tuzaklar `lab/js7/README.md` dosyasında.

```
docker compose -f lab/js7/docker-compose.yml up -d
python lab/js7/setup.py
python -m vardiya.js7bench --per-family 1 --seed 1
```

Laboratuvar yalnızca 127.0.0.1'e bağlanır ve JS7'nin belgelenmiş varsayılan yönetici hesabını kullanır; ağa açmadan
önce hesabı değiştirin. `JS7_URL`, `JS7_ACCOUNT` ve `JS7_PASSWORD` ortam değişkenleri `lab/js7/lab.json` dosyasını ezer.

## 10. Nasıl kullanılmalı

- **Talepler şablonla gelsin.** Harness'in güvenilirliği buradan başlıyor: şablon dışı metni kod okumaz, iade eder.
- **Önce öneri modunda çalıştırın.** `Desk(..., licence=2)` ile ajan tanımı derler ve denetler ama yüklemez
  (`Sonuc: proposed`). Bir süre önerileri admin onaylasın; iade gerekçelerinin ve seçilen takvimlerin doğru olduğunu
  görünce yetkiyi açın.
- **İadeleri okuyun.** Her iade bir gerekçe taşır. Haksız iade (geçerli talebin iadesi) bir kayıptır ama zarar
  değildir; hangi denetimin ya da okumanın sebep olduğu denetim kaydındaki notlarda yazar.
- **"Sonraki çalışmalar" satırına bakın.** Modelin günleri yanlış okuduğu ve kodun yakalayamadığı tek durum burada
  görünür: iş beklenen günlerde değil başka günlerde çalışacaktır.
- **Kurum standardını skill'e yazın, koda değil.** Böylece kural değişince kod değişmez ve kural herkese açık kalır.
- **Yeni bir modeli bağlamadan önce ölçün.** Bölüm 8'deki üç komut on dakika sürer.
- **Güçlü bir modeli harness'siz de koşturun ve "yanlış" bitirdiği talepleri okuyun.** Bench 0.2'deki en önemli
  düzeltme böyle bulundu: model haklıydı, bench yanılıyordu (`docs/03-scheduler-admin-bench.md`, Bölüm 7).

## 11. Nasıl kullanılmamalı

- Üretim zamanlayıcısına doğrudan bağlayıp onaysız iş yüklemek için: bağdaştırıcı yalnızca emülatör ve JS7
  laboratuvarı için var, ve ölçümler sentetik.
- Bench sayılarını sahadaki başarı oranı diye sunmak için: örneklem küçük, senaryoları üreteç, bağımsız ifadeleri de
  modeller yazdı.
- Model bağlamadan dil gerektiren talepler için: serbest yazılmış günlerin çoğu ve açıklama çelişkileri modelin işi.

## 12. Sorun giderme

| Belirti | Sebep ve çözüm |
| --- | --- |
| Model çağrısı onlarca saniye sürüyor | Düşünme açık kalmış; `VARDIYA_THINK` tanımlı olmasın |
| `gunler alani bir takvime cevrilemedi` | Model bağlı değil, ya da okuma ifadeyle çelişti; takvim adını yazın |
| Ollama cevap vermiyor | `ollama serve` çalışıyor mu, model adı `python -m vardiya models` çıktısındaki gibi mi |
| JS7'de dağıtım takıldı | `lab/js7/README.md`: geçersiz taslak dağıtım kuyruğunu durdurur; `docker compose ... restart joc` |
| Windows'ta Türkçe karakterler bozuk görünüyor | Konsol kod sayfası; dosyalar UTF-8'dir, `chcp 65001` deneyin |
