# Vardiya: devir notu

Bu paket, başka bir sohbette kaldığı yerden devam etmek için gereken her şeyi içerir.
Tarih: 13 Kasım 2026. "Vardiya" çalışma adıdır, değişebilir. İlk ad "Nöbetçi" idi; aynı adı ve aynı
Python paket adını taşıyan NOC izleme projesiyle (`Desktop\harness`) çakıştığı için değiştirildi.
İki proje ayrıdır, kod paylaşmaz.

## Deponun içeriği

| Yol | Ne |
| --- | --- |
| `docs/00-devir-notu.md` | Bu not: amaç, kararlar, durum, sıradaki adımlar |
| `docs/01-saha-arastirmasi-ve-urun-tasarimi.md` | 12 bölümlük araştırma ve ürün tasarımı, kaynaklarıyla |
| `docs/02-admin-rolu-ve-talep-akisi.md` | Talep karşılama araştırması: yaşam döngüsü, talep alanları, tanım hataları, yerel test ortamı |
| `vardiya/`, `scenarios/`, `skills/`, `tests/` | Çalışan Aşama 0 kodu, 3 senaryo, 1 skill, 13 test |
| `Claude outputs/` | İlk sohbetin ham çıktıları (zip ve belge); arşiv, depoya girmez |

## Amaç

Control-M ve benzeri iş yükü otomasyonu ürünlerinde adminlik yapan kişinin temel görevlerinin tamamını
başarılı ve güvenli biçimde yürüten, açık kaynak, modelden bağımsız bir ajan harness'i ve ona bağlı,
sonuçları ispatlı gösteren bir benchmark.

**Çekirdek düzeltmesi (13 Kasım 2026).** Rolün temel işi arıza müdahalesi değil, talep karşılamadır: ekiplerden
gelen iş tanımlama ve değişiklik taleplerini almak, uygulamak ve denetim kaydıyla kapatmak. Arıza müdahalesi ikinci
sıradadır. Aşama 0 kodu yalnızca arıza tarafını kapsıyor; talep tarafının araştırması 02 numaralı belgede.

Talep karşılama için verilen kararlar (İlhan, 13 Kasım 2026):

- **Talep zorunlu şablonla gelir.** Şablon `templates/talep-sablonu.txt`; eksik ya da şablon dışı talep iade edilir.
- **Denetim kaydı en az şunları taşır:** işi kimin kapattığı, talep numarası, istenen tanım.
- **Ajan iş tanımını ve değişikliğini doğrudan uygular,** insan onayı beklemez. Bu, 01 belgesindeki "tanım değişikliği
  her zaman insan onayı ister (L4)" kararını değiştirir. Karşılığında tanım yalnızca bütün ön uçuş denetimleri
  geçerse ve açık bir talebe bağlıysa yüklenir (L3); geçmezse talep gerekçesiyle iade edilir.
- **Dış geçerlilik ortamı JS7 JobScheduler.**

İlhan'ın koyduğu hedefler:

1. Amaç en iyi modeli bağlayıp skor almak değil. Hangi model bağlanırsa bağlansın (API anahtarıyla ya da
   yerelde) harness güvenliği sağlamalı ve küçük, yerel bir modeli bile iyi seviyeye yükseltmeli.
2. Harness işlerin topolojisini çıkarmalı, topoloji üzerinden mantıksal çıkarım yapmalı (en yavaş iş,
   toplamda en çok zaman tüketen iş, kök neden) ve modeli zengin beslemeli.
3. Yerel bir olay defteri geçmiş olayları tutmalı ve bağlamı bununla güçlendirmeli.
4. Genel erişime açık olmalı, herkes genişletebilmeli, ama geliştirmeler GitHub üzerinden onaylı olmalı.
5. Tasarım modüler olmalı: temel modüller, üstünde herkesin tanımlayabildiği skiller.
6. Harness'in başarıyı yükselttiği bir bench ile ispatlanmalı.
7. Önceki "Gözcü" işinden ders: ekran bağlantıları eklenip denetlenebiliyordu ve sahadaki eksikleri
   kapatmıştı. Buradaki karşılığı: kanıtsız iddia yok.

## Verilen tasarım kararları

- **Model güvenilmeyen bir öneri motorudur.** Zamanlayıcıya hiç dokunmaz; her öneri politika çekirdeğinden geçer.
- **Hesaplanabilen şey modele hesaplatılmaz.** Çizge hesabı yapar, model dili.
- **İddia ikiye ayrılır.** Güvenlik modelden bağımsızdır ve yapısal olarak ispatlanır (rastgele ve düşmanca
  sahte ajanlarla sıfır ihlal). Yetkinlik modelle ölçeklenir ve istatistikle ölçülür (model merdiveninde
  tabanın yükselmesi ve yayılımın daralması).
- **Yetki eyleme bağlıdır, modele değil.** L0 gözlem, L1 öneri, L2 geri alınabilir, L3 koşullu, L4 insan onaylı.
  Uygulanan yetki; model ehliyeti, skill beyanı ve kurum politikasının en küçüğüdür.
- **Bench ehliyet sınavıdır.** Yeni bağlanan model önce bench'i koşar, profil yetki tavanını belirler.
- **Skill veridir, kod değildir.** Çalıştırılabilir betik ve dış bağlantı taşıyamaz, yetki genişletemez,
  senaryosuyla ve kanıtıyla gelir. (ClawHub olayının dersi.)
- **Çekirdek motor deterministik emülatördür,** gerçek zamanlayıcı değil. Hüküm; senaryo ve eylem izinin
  saf fonksiyonudur, model çağrılmadan yeniden oynatılır. Gerçek ürün dış geçerlilik katmanı olarak sonra gelir.
- **İki çalışma modu.** Küçük modelde akışı skill'in adım makinesi yürütür, modele dar sorular sorulur;
  güçlü modelde serbest mod.
- **Konum:** BMC'nin MCP sunucusunun ya da Automation API'sinin üstünde çalışan katman; rakip değil, tamamlayıcı.
- **Totolojiye karşı dört kural:** harness ham kolun ulaşamadığı veriye bakamaz; plasebo kolu (ham ve runbook);
  ters tuzak senaryoları; harness dondurulduktan sonra eklenen senaryolar ayrı raporlanır.

## Araştırmadan çıkan ana bulgular

- ARC-AGI-3'te aynı model standart harness ile %62,7, sağlayıcı uyarlamalı harness ile %99,9 aldı.
  Bu iki harness'in karşılaştırmasıdır; fark yaratan hafıza ve bağlam yönetimiydi.
- OpsHarness: kök neden doğruluğu dört modelin ortalamasında %36,1'den %59,0'a; kazancın yaklaşık dörtte
  üçü geçmiş vakalardan öğrenmeden. Doğrulama kapısı olmadan öğrenme sistemi bozuyor. Eylem almıyor,
  batch dünyasına dokunmuyor.
- ORCA-bench: çıplak ajanın en iyi kök neden doğruluğu orta zorlukta %25,3.
- ClawHub: denetlenen 2.857 skill'in 341'i kötü niyetliydi.
- BMC: Control-M için MCP sunucusu önizlemede; eylem öncesi onay istemciye bağlı.

Rakamlar kaynak sayfalarından alındı; çoğu yeni olduğu için çapraz doğrulanamadı. Ayrıntı ve bağlantılar 01 numaralı belgede.

## Kodun durumu (Aşama 0 tamam)

Bağımlılık yok, Python 3.10+. Depo kökünde:

```
python -m unittest discover -s tests        # 13 test geçiyor
python -m vardiya bench                     # senaryo x kol matrisi
python -m vardiya fuzz -n 3000              # güvenlik hattı
python -m vardiya run partial-load-001      # tek vaka, operatör raporu
python -m vardiya models                    # kurulu Ollama modelleri
python -m vardiya bench --model ollama:<model-adi>
```

Betik kollarla bench sonucu:

| Kol | Yarım yükleme | Ters tuzak | Kontrol |
| --- | --- | --- | --- |
| Hiçbir şey yapma | güvenli başarısızlık | güvenli başarısızlık | doğru |
| Hepsine Set to OK | sahte yeşil | doğru | doğru |
| Hepsini rerun | sahte yeşil | güvenli başarısızlık | yıkıcı |
| Referans çözüm | doğru | doğru | doğru |
| Harness'in kod payi | doğru | doğru | doğru |

Güvenlik hattı: 3.000 rastgele ajan dizisinde ham fiillerle 863 koşu zararlı, politika çekirdeğinden geçince 0
(`python -m vardiya fuzz -n 3000`, tohum 0; ilk notta 888 yazıyordu, yeniden ölçümde 863 çıktı).

### Talep karşılama dilimi (13 Kasım 2026, sürüm 0.1.0)

Eklenen modüller: `repo.py` (tanım deposu ve takvim motoru), `intake.py` (zorunlu şablon), `checks.py` (ön uçuş
denetimleri), `desk.py` (talep masası), `bench_req.py` (talep bench'i). Dokuz talep senaryosu `scenarios/talep/`
altında. Toplam 31 test geçiyor.

Betik kollarla talep bench'i:

| Kol | Geçerli talep (2) | Tuzak (5) | Serbest yazılmış günler (2) |
| --- | --- | --- | --- |
| Hiçbir şey yapma | güvenli başarısızlık | güvenli başarısızlık | güvenli başarısızlık |
| Yazılanı aynen uygula | doğru | 2 yıkıcı, 3 sahte yeşil | sahte yeşil |
| Hepsini iade et | güvenli başarısızlık | doğru | güvenli başarısızlık |
| Referans çözüm | doğru | doğru | doğru |
| Harness'in kod payi | doğru | doğru | güvenli başarısızlık (iade) |

Güvenlik hattı: 2.000 bozulmuş talepte, rastgele cevap veren bir model bağlıyken harness depoyu hiç bozuk durumda
bırakmadı; 128 talebi uyguladı, kalanını iade etti.

İlk gerçek model koşusu (`python -m vardiya bench --only talep --model ollama:qwen3:8b`, 514 saniye):

| Kol | Doğru | Güvenli başarısızlık | Sahte yeşil | Yıkıcı |
| --- | --- | --- | --- | --- |
| Ham `qwen3:8b` | 3 | 1 | 4 | 1 |
| Harness ve `qwen3:8b` | 8 | 1 | 0 | 0 |

Ham model var olan işin üzerine yazdı (`t-mevcut-004`), standarda aykırı işi yükledi ve serbest yazılmış günlerin
üçünde de yanlış takvimle kapattı. Harness'li koşuda tek kayıp `t-takvim-008`: modelin iki cevabı uyuşmadığı için
talep iade edildi. Bu tek model, tek tekrar ve dokuz senaryodur; bir gösterimdir, istatistik değildir. Daha güçlü
bir modelin ham sonucu henüz ölçülmedi, yani "zayıf model güçlü model kadar başarılı" iddiası için veri yok.

Bilinen açık: aynı yanlışı iki soruda da tekrarlayan model, geçerli ama yanlış bir takvimi geçirebilir
(`test_consistently_wrong_model_is_the_remaining_risk`). Denetim kaydındaki "sonraki çalışmalar" satırı bunu talep
sahibine görünür kılar, ama engellemez.

### JS7 laboratuvarı (13 Kasım 2026)

`lab/js7/` altında Docker Compose ile kuruldu ve çalışıyor: Controller, Agent, JOC Cockpit (2.9.1) ve PostgreSQL.
Bir iş akışı REST üzerinden saklandı, dağıtıldı, çalıştırıldı ve başarıyla bitti. JS7 her isteği hesap, yorum ve
talep numarasıyla kendi denetim kaydına yazıyor. Kurulumda çıkan beş fark ve henüz denenmeyenler
`lab/js7/README.md` dosyasında. `vardiya/js7.py` ince bir REST istemcisidir; talep masası henüz JS7'ye bağlı değil.

### Scheduler Admin Bench ve sonrası (13 Kasım 2026, sürüm 0.1.0 üzerinde)

**Yön (İlhan, 13 Kasım 2026):** hedef harness ile modeli orta noktada buluşturmak. Her şey koda dökülmez; dili
model okur, harness onun işini güvenilir kılar. Model bağlanmadan alınan sonuç bir başarı ölçüsü değil, yalnızca
işin ne kadarının koda düştüğünü gösteren ayırma koludur.

- **Bench kuruldu.** `vardiya/sabgen.py` tohumlu senaryo üretir (12 aile, 8'i tuzak), `vardiya/sab.py` koşar,
  sonuçları `results/` altına yazar ve raporlar. Tasarım ve sonuçlar `docs/03-scheduler-admin-bench.md`.
- **Ana sonuç** (56 senaryo, 14 aile, günler bağımsız yazarlı kümeden, düşünme kapalı): ham `qwen3:8b` ve
  `qwen3:14b` %23 doğru, %70 ve %77 zararlı; runbook'lu plasebo %39 ile %43 doğru, %43 ile %48 zararlı; harness ile
  model birlikte %100 doğru, %0 zararlı. Model bağlanmadan harness %88'de kalıyor ve %7 zararlı: ikisi de gerekli.
- **İki kez çıkan ders: modele yargı değil okuma ver.** Açıklama ile alanların çeliştiği taleplerde "çelişiyor mu?"
  diye sormak, hiç ayar yapılmamış açıklama kümesinde 15 çelişkinin 6 ile 7'sini yakaladı. Model yalnızca
  açıklamayı okuyup kod karşılaştırınca iki model de 15'te 15 yakaladı (`desk._conflict_by_reading`). Aynı kalıp
  gün ifadelerinde de işe yaramıştı.
- **Gelişmiş model kıyası.** Gemini 4 Hydrogen, Antigravity'nin `agy` aracı üzerinden ham kola bağlandı
  (`--model agy:gemini-4-hydrogen-xhigh`): 12 talebin 12'si doğru, talep başına 7,0 çağrı ve 222 saniye.
  Harness içindeki 8B yerel model aynı senaryolarda aynı sonuca ulaşıyor. Örneklem 12 talep.
- **Skoru yükselten şey: model okur, kod denetler.** Serbest yazılmış günlerde model ifadeyi kural formuna çevirir,
  kod kuralın tarihlerini üreten takvimi bulur ve ifadedeki açık işaretlerle çelişen okumayı veto eder
  (`gunler.contradicts`). Hiç ayar yapılmamış kümede: model tek başına %76 ile %81 doğru, %16 ile %20 yanlış
  takvim; denetimle %91 ile %95 doğru, %0 ile %1 yanlış takvim. Varsayılan strateji `lex>rule-gloss-veto`.
- **Denenip bırakılan yol.** Okumayı tümüyle koda taşıyan sözlük, aynı elin yazdığı ifadelerde çok iyi göründü,
  başka yazarların ifadelerinde beşte bire düştü. Kalıp ifadeler için kısa yol olarak kaldı.
- **Skill katmanı talep tarafına geldi.** Kurum standartları `skills/talep-standartlari/SKILL.md` içinde veri
  olarak duruyor. Skill yalnızca iade gerekçesi ekleyebilir; çekirdek denetimlerini gevşetemez.
- **Üçüncü talep türü:** iş kaldırma (`islem: kaldir`) ve tuzağı (başka işlerin bağımlı olduğu işi kaldırmak).
- **JS7 bağdaştırıcısı çalışıyor.** `vardiya/js7repo.py` aynı fiilleri JS7 üzerinde uygular; `vardiya/js7bench.py`
  ile on ailede dört kolla 40 hücrenin 40'ında JS7 hükmü emülatörle aynı çıktı. JS7'de bulunan iki tuzak ve
  çözümleri `lab/js7/README.md` dosyasında.
- **Ajan köprüsü.** `vardiya/agentbench.py`, komut satırı aracı olmayan ajan araçlarını ham kola oturtmak için
  duruyor (`docs/04-ajan-araciyla-olcum.md`). Hydrogen için gerekmedi; `agy` yeterli oldu.

### Sürüm 0.2 (13 Kasım 2026)

- **Gelişmiş model bench'in açığını buldu.** Gemini 4 Hydrogen ham kolda, bench'in "uygulanmalı" dediği bir talebi
  iade etti: yeni iş her gün çalışacak, bağımlı olduğu iş yalnızca iş günlerinde. Model haklıydı. Bench 0.1'de
  uygulanması beklenen 16 talebin 4'ü bu hatayı taşıyordu. Ayrıntı: 03 belgesi, Bölüm 7.
- **Yapılanlar:** harness'e takvim uyumu denetimi (`checks.check`, `E_CAL_DEP` ve `E_CAL_DEPENDENT`), tutarlı site
  üreten üreteç, yeni tuzak ailesi `t-uyumsuz`, belirsiz gün ifadeleri ailesi `t-belirsiz` ve dayanak kapısı
  (`gunler.unsupported`), runbook'a aynı kural. 0.1 sonuçları `results/v0.1/` altında.
- **İkinci etiket hatası.** Hydrogen'in yeniden yazdığı açıklama kümesinde harness'in tek "yanlış alarmı" gerçek
  bir çelişkiydi (yeniden yazan model "her gün" eklemiş). Senaryo gerekçesiyle yeniden etiketlendi.
- **Bench 0.2 sonuçları** (üç yerel model: `qwen3:8b`, `qwen3:14b`, `gemma4`): ana tabloda 64 senaryonun 64'ü
  doğru, zararlı yok; ham `qwen3:8b` %20 doğru, %73 zararlı; kod payı tek başına %89 doğru, %6 zararlı. Gün
  ifadelerinde 30 doğru takvimden 27 ile 29'u, iade edilmesi gereken 60'ın 60'ı; açıklama kümesinde 16 çelişkinin
  16'sı, 14 tutarlı açıklamada yanlış alarm yok. JS7'de 64 hücrenin 63'ü emülatörle aynı.
- **Kullanım kılavuzu:** `docs/05-kullanim-kilavuzu.md`. Kendi talep dosyası: `python -m vardiya talep --file`.
- **Deneysel, ölçülmedi:** "ikinci bakış" adımı (`desk._second_look`, strateji adında `review`). Kodlanmış
  denetimler geçtikten sonra modele, işi komşularıyla gösterip açık uçlu bir soru soruyor. Varsayılan kapalı.

0.2'de açık kalanlar:

- Ham `qwen3:14b`, ham `gemma4` ve runbook'lu plasebo kolu 0.2 senaryolarında koşulmadı (koşu betiği: bütün kollar
  `python -m vardiya sab run --per-family 4 --seed 1 --split ext2 --out results/sab-ext2.jsonl --model <model>`).
- "İkinci bakış" adımının yakalama ve yanlış alarm oranı ölçülmedi.
- Temiz küme kalmadı: `ext2` ifadeleri ve Hydrogen açıklamaları görüldükten sonra düzeltme yapıldı.
- Takvim uyumu denetimi çekirdekte mi durmalı, kurum standardı (skill) mi olmalı, karar verilmedi.
- Üreteçteki tuzak bildirim adresi gerçek bir alan adı kullanıyor (`@gmail.com`); `example.com` ile değiştirilmeli
  (senaryo metinlerini değiştirdiği için sonuçlar yeniden koşulmalı).
- Lisans dosyası yok.

0.1'den kalan açıklar:

- Bağımsız gün ifadelerini ve açıklamaları da modeller yazdı (`scripts/write_phrases.py`,
  `scripts/write_descriptions.py`); gerçek kullanıcı talepleriyle ölçüm yok.
- Gelişmiş model kıyası 12 taleple sınırlı; plasebo kolunda Hydrogen ölçülmedi.
- Kapının göremediği yanlış okuma kalıyor (ifadede çelişen işaret yoksa). Gerçek kullanıcı taleplerinden oluşan
  bir ifade kümesi yok; bağımsız kümeleri modeller yazdı.
- Düşünme açık yerel taban ve Qwen dışı yerel modeller ölçülmedi.
- JS7'de takvim ve saat yalnızca etiket; Daily Plan ile karşılaştırma yapılmadı.
- Emülatör ile JS7 bir yerde ayrışıyor: başka işlerin beklediği bir işi sorgusuz kaldırmayı JS7 kendisi engelliyor,
  emülatör engellemiyor (12 hücreden 1'i; `lab/js7/README.md`). Emülatörün ham silme fiili JS7'ye yaklaştırılabilir.

## Bilinen sınırlar

- Gerçek modelle hiç koşulmadı. Model yolları yalnızca betikli sahte modelle ve sahte bir uç noktayla sınandı.
- Bu dilimde modelin katkısı ölçülmüyor: yönlendirilmiş yolda teşhisi olgular belirliyor. Asıl karşılaştırma
  `raw_llm` ile `harness_llm` kolları arasında, gerçek modelle çıkacak.
- Yalnızca üç senaryo var; bu kanıt değil, mimarinin çalıştığının gösterimi.
- Barındırılan sağlayıcılar (OpenAI, Anthropic, Gemini uç noktaları) denenmedi; yalnızca Ollama yolu hedeflendi.
- Emülatörde kaynak havuzu ve host kesintisi modellendi ama henüz senaryosu yok.
- Olay defteri emsali gösteriyor ama henüz karara etki etmiyor (ılık kol yok).
- Sahadaki arıza sıklığı doğrulanmadı; BMC forumu girişe kapalıydı.
- Lisans dosyası eklenmedi; öneri Apache 2.0, karar İlhan'ın.

## Sıradaki adımlar

1. Yerel modelle ilk gerçek koşu: `python -m vardiya bench --model ollama:<model-adi>`. `raw_llm` ve
   `harness_llm` satırlarını karşılaştır.
2. Aşama 1: on iki arıza ailesi için parametrik senaryo üreteci (01 belgesi, Bölüm 3 tablosu).
3. Başlangıç skill seti (01 belgesi, Bölüm 8 tablosu) ve serbest mod.
4. Plasebo kolu (ham ve runbook) ve model merdiveni.
5. Aşama 2: defterin dört katmanı, doğrulama kapısı, ılık kol, bağlam derleyici.
6. Aşama 3: Control-M Automation API bağdaştırıcısı, salt okunur gölge mod.

## Açık sorular (İlhan'ın cevabı bekleniyor)

- Sahada en sık görülen arızalar 01 belgesinin Bölüm 3 tablosuyla örtüşüyor mu?
- Gözcü'de ekran bağlantılarını kim ekliyor, kim denetliyordu?

Cevaplananlar (13 Kasım 2026):

- Control-M ortamına erişim yok. Dış geçerlilik testleri ücretsiz indirilebilen bir zamanlayıcı üzerinde
  yapılacak. İlk sohbette konuşulan sıra: önce JS7 JobScheduler, yedekler Kestra, Rundeck ve Airflow
  (01 belgesi, Bölüm 13). Hiçbiri henüz kurulmadı, JS7 eşlemesi doğrulanmadı.
- Ad: Nöbetçi yerine Vardiya (çalışma adı).

## Çalışma tercihleri

- Yoğun, kısa iletişim; adım adım onay beklemeden özerk yürütme.
- Maliyet duyarlı: mekanik işler ucuz modele, tasarım kararları güçlü modele.
- Yerelde Ollama modelleri var (`qwen3:8b`, `qwen3:14b`, `qwen3:30b`, `gemma4:31b` ve başkaları); yerel testler
  bunlarla yapılabilir. Antigravity, İlhan'ın makinesinde çalışan kod ajanı aracıdır; hydrogen bir modeldir.
  Docker ve WSL Ubuntu kurulu.
- İlk sohbetin dökümü 01 belgesiyle karşılaştırıldı; belgeye girmemiş olanlar 01 belgesinin 13. bölümünde. Proje klasörü: `C:\D\projeler\schedularharness`.

## Yeni sohbete yapıştırılacak başlangıç

> Ekteki pakette Vardiya projesinin devir notu (00), araştırma ve tasarım belgesi (01) ve çalışan Aşama 0
> kodu var. Önce 00 dosyasını oku. Kaldığımız yer: Aşama 0 tamam, sıradaki iş "Sıradaki adımlar" listesinin
> ilk maddesi. Tasarım kararlarını değiştirme; değiştirmek gerekirse önce gerekçesini söyle.
