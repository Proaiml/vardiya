# Zamanlayıcı Ops Bench: forumlardaki gerçek sorunlardan bir benchmark

Amaç: zamanlayıcı yöneticisinin karşılaştığı gerçek sorunlardan bir benchmark kurmak, harness'lı ajanı bununla
ölçmek ve bulunan her açığı bir skill olarak harness'a eklemek. Ölçü şu: aynı model harness içinde bu sorunları
çözebilmeli; harness olmadan çözemediği yerde farkı harness yaratmalı.

## 1. Hazır benchmark var mı (14 Kasım 2026 araması)

Toplu iş zamanlayıcısına özel bir benchmark yok. Alınacak parçalar:

| Kaynak | Ne | Nasıl alınır |
| --- | --- | --- |
| OpsEval (FSE 2025) | BT operasyonu, 7.184 çoktan seçmeli + 1.736 soru-cevap | Zamanlayıcı ve batch ile ilgili alt küme bilgi bölümüne (lisansı kontrol edilecek) |
| CloudIR-Bench (2026) | Olay raporundan kök neden ve müdahale | Vaka biçimi ve puanlama örnek alınır |
| R2Act (2026) | Geçerli ve geçersiz müdahale planları | Zararlı eylem puanımızın karşılığı; biçim örnek alınır |
| RCAgent (Flink iş hataları) | 161 iş hatası | Aynı kök nedenden en fazla iki vaka kuralı |
| ORCA-bench (2026) | Olaysız kontrol görevleri, uydurma oranı | Olaysız vakalar ve uydurma ayrı puan |
| Kaggle Airflow görevleri | Takılı mı yavaş mı ayrımı, DAG ayrıştırma yükü | Vaka olarak alınır (kaynak gösterilerek) |
| FRESCO (Purdue, Slurm) | 480 bin iş, hata ve kaynak serisi | Olaydan önce uyarı parçası için veri |

## 2. Parçalar

| Parça | Soru | Doğru cevap | Puan |
| --- | --- | --- | --- |
| A. Olay | Hata satırı, iş bağlamı, geçmiş | Kök neden, doğru müdahale | doğru / yarım / yanlış / **zararlı** |
| B. Talep | Tanım talebi (yeni, değişiklik, kaldırma) | Kabul ya da gerekçeli iade | SAB'deki gibi |
| C. Adminlik bilgisi | "Şunu nasıl yaparım" (kim sipariş etti, agent'ı nasıl doğrularım) | Doğru araç ve adımlar | Kontrol listesi; tehlikeli adım ayrı |
| D. Olaysız kontrol | Belirti var ama sorun yok | "Sorun yok", müdahale yok | Uydurma ayrı sayılır |
| E. Olaydan önce | Seriler (süre, disk, sertifika bitişi) | Uyarı ve zamanı | Doğru uyarı, yanlış alarm |

Her vaka birden fazla zamanlayıcının diliyle yazılır: Control-M, AutoSys, Airflow, JS7, Slurm, cron. Aynı arıza sınıfı,
başka ürünün sözcükleriyle.

## 3. Sızıntıyı önlemek (mutabık kalınan kural)

Skill'leri yazarken kullanılan bir forum konusu test setine girmez; girerse harness ezberden kazanır.

- Her konu kimliğinin özetine göre konuların yaklaşık %30'u baştan teste ayrılır. Kural: kimliğin 32 bitlik FNV-1a
  özeti 10'a bölündüğünde kalan 0, 1 ya da 2 ise test. İlk envanterde 2.324 geliştirme, 1.016 test. Skill'ler
  yalnızca geliştirme tarafından yazılır.
- Dürüst sınır: envanter çıkarılırken test tarafındaki bazı başlıklar (yalnızca başlık, içerik değil) skill yazan
  oturumda görüldü. Bu yüzden test vakalarının içeriğini ayrı ajan okur ve yazar.
- Test vakalarını ayrı bir ajan, temiz bağlamla yazar; skill'leri yazan oturum test vakalarını puanlamaya kadar görmez.
- Test vakalarında ürün adları ve ifadeler değiştirilir; bir kısmı başka zamanlayıcıdan gelir.
- Forumun ham metni depoya girmez: vakalar kendi sözcüklerimizle yazılır, kaynak yalnızca bağlantıyla gösterilir.

## 4. Kollar

| Kol | Ne görür |
| --- | --- |
| Ham model | Vakanın metni |
| Model + belgeler | Vakanın metni ve ilgili ürün belgesi parçaları |
| Harness | Vaka, yerel çizge, olay sınıfı skill'leri, kanıt sorguları, politika |

Aynı model üç kolda da koşar; fark harness'ın katkısıdır. Küçük yerel modeller ve büyük modeller ayrı raporlanır.

## 5. Öncelik: önemliden az önemliye

Vakalar forumdaki görüntülenme sayısına göre sıralanır; en çok okunan sorun önce vakaya ve skill'e dönüşür.
Tartışmalarda görüntülenme yok; onlar yanıt sayısı ve tarihle sıralanır.

## 6. İlk envanter (BMC topluluğu, 14 Kasım 2026)

Hız sınırına uyularak (40 saniyede bir sayfa) 34 konu aramasıyla 3.340 tekil kayıt toplandı; 3.108'i Control-M
(1.818 bilgi makalesi, 1.263 tartışma, 27 fikir). Ham kayıtlar yalnızca yerelde.

Kaba bir anahtar kelime eşlemesiyle kayıtların %70'i mevcut 20 sınıftan en az birine düştü; eşleme gürültülü
olduğundan vaka yazarken içerik okunacak. Sınıfların dışında kalan ve çok okunan başlıklar yeni skill adaylarıdır:

| Aday | Örnek başlıklar (görüntülenme) |
| --- | --- |
| Port ve güvenlik duvarı | Hangi portlar açılmalı (33 bin); kalıcı bağlantı (5 bin) |
| Windows'ta çalıştırma | OSCOMPSTAT 129 ve üstü (9,9 bin), CreateProcessAsUser 1314 yetki (4,4 bin), TR5111 fork hatası (4,2 bin), iş Windows'ta kayboluyor (5,2 bin), PowerShell çalıştırma (16 bin) |
| Uzak host, agent'sız | SSS (13,6 bin), "uzak sysout bulunamadı" (2,8 bin) |
| Agent'ı tanıtma yetkisi | "Server is not authorized for this agent" (6,3 bin) |
| Değişkenler | Değişken kullanımı (11,8 bin), tarih biçimleri, global ve pool değişkenleri |
| Yüksek erişilebilirlik | Elle failover, EM HA'nın güvenlik duvarında çalışmaması, geri dönüş |
| Veritabanı bakımı | EM ve Server veritabanı yedeği, PostgreSQL bakımı, arşivleme veritabanı hatası |
| Arayüz ile gerçek farkı | Simge renklerinin anlamı (22 bin), ctmpsm'de görünüp arayüzde görünmeyen işler, "çıktı yok" |
| Araçlar | restore_host_config (13,7 bin), ctmorder ile alt klasör zorlama, force_end_job.pl |

Sınıflar içinde en çok okunanlar: sertifika zinciri hataları (52 bin, 46 bin), agent-sunucu iletişiminin
doğrulanması (53 bin), AJF'de işleri komutla tutma, öldürme ve silme (19 bin), artık çalışmayan ama sarı görünen iş
(12 bin), "Maxwait / Keep Active" (9,6 bin), New Day ya da User Daily'den sonra eksik siparişler (9,6 bin), saat
dilimi dosyalarının güncellenmesi (7,2 bin).

## 7. Sıradaki adımlar

1. Konu kimliklerini geliştirme ve test olarak ayır.
2. Geliştirme tarafında en çok okunan ~150 makaleyi oku (40 saniyede bir sayfa), her birini sınıfa bağla, yeni
   sınıfları skill olarak yaz.
3. Test tarafının vakalarını ayrı bir ajan yazsın; diğer zamanlayıcılardan (Stack Overflow, JS7, Slurm) vaka ekle.
4. Dış kaynaklardan uygun parçaları al (OpsEval alt kümesi, Kaggle Airflow görevleri).
5. Üç kolu koş, sonuçları ve sınırları bu belgeye yaz.

## 8. İlk adımlar (14 Kasım akşamı)

- En çok okunan geliştirme makalelerinden 17'si okundu (40 saniyede bir sayfa). Bunlardan:
  - Üç yeni olay sınıfı: **sinyal** (çıkış kodu 129-255, işi dışarıdan gelen sinyal bitirdi), **os_siniri** (açık
    dosya ve süreç sınırları; Kafka servisi açılmıyor), **port_cakismasi** (aynı makinedeki iki bileşen aynı portu
    istiyor). Sertifika sınıfına iki ayrı durum eklendi: eksik ara sertifika ve modül JRE'sinin güven deposu.
  - Hata imzasına bir kural: 129-255 arası çıkış durumu `<n>` yerine `signal` olarak kalır (Unix'te 128 artı sinyal
    numarası). Windows'ta bu aralıktaki kodlar sinyal değildir; bu sınır biliniyor.
- `bench/ops/dev.jsonl`: ilk 13 geliştirme vakası (olay, bilgi, olaysız). Her vaka kendi sözcüklerimizle yazıldı,
  kaynağa yalnızca bağlantı ve görüntülenme sayısıyla işaret ediyor. Puanlama: `steps` içindeki her grup için
  cevapta en az bir eş anlamlı geçmeli; `harmful` gruplarından biri geçerse vaka zararlı sayılır.

## 9. Test seti ve ilk dürüst ölçüm (14 Kasım akşamı)

- `bench/ops/test.jsonl`: 59 vaka, temiz bağlamlı ayrı bir ajan yazdı. Skill'lere, geliştirme vakalarına ve BMC'ye
  bakmadı; yalnızca Stack Exchange API'sini (Stack Overflow, Server Fault) kullandı. Dağılım: 39 olay, 13 bilgi, 7
  olaysız; Airflow 14, cron 11, Slurm 10, Control-M 7, AutoSys 6, Kubernetes 5, Quartz 3, JCL 2, TWS 1. Sertifika
  sınıfından vaka yok; yaklaşık 10 vaka düşük puanlı (0-2) kabul edilmiş cevaplara dayanıyor.
- Puanlamada olumsuzluk denetimi: "yeniden başlatmayın" ya da "do not restart" zararlı öneri sayılmaz.
- Skill kolu (model yok, skill'lerin kendi metni):

| Bölüm | Vaka | Doğru | Yarım | Yanlış | Zararlı |
| --- | --- | --- | --- | --- | --- |
| Geliştirme (Control-M, BMC) | 25 | 24 | 0 | 1 | 0 |
| Test (çoğu başka zamanlayıcı) | 59 | 0 | 3 | 56 | 0 |

  Geliştirme sonucu bu vakalara göre ayarlandığı için iyimser; ölçü test. Testte harness 59 vakanın 15'inde bir sınıf,
  9'unda doğru sınıfı buldu; Slurm, Kubernetes ve Quartz vakalarında hiçbir şey eşleşmedi. Doğru sınıfta bile
  düzeltme metni Control-M'e özgü olduğu için Airflow ya da cron araçlarını adlandırmıyor.
- Ders: skill'ler zamanlayıcıdan bağımsız sınıflara ve her ürün için ayrı yordamlara genişlemeli. Bunun geliştirme
  malzemesi, test setinde kullanılmamış Stack Overflow soruları ve ürün belgeleri olacak; test vakalarının içeriğine
  bakılmayacak, yalnızca kaynak bağlantıları dışlama listesine alınacak.
- Model kolları (ham ve harness) GPU boşalınca koşulacak.

## 10. Skill'leri zamanlayıcıdan bağımsız yapmak (14 Kasım akşamı)

İlk test ölçümü skill'lerin Control-M'e kapalı olduğunu gösterdi. Test vakalarına bakılmadan, test kaynakları
dışlanmış yaklaşık 450 Stack Overflow ve Server Fault sorusundan (Airflow, cron, Slurm, AutoSys, Kubernetes CronJob,
Quartz) ve BMC'nin en çok okunan 45 geliştirme makalesinden şu değişiklikler yapıldı:

- **Sınıflar ürün dili taşıyor.** Bir sınıf genel düzeltmesinin yanında `fix_airflow`, `fix_cron`, `fix_slurm`,
  `fix_autosys`, `fix_kubernetes`, `fix_quartz`, `fix_controlm` satırları taşıyabiliyor. Harness metinden zamanlayıcıyı
  tanıyor ve modele önce o ürünün satırını veriyor.
- **Yeni sınıflar:** `ortam_farki` (elle çalışıyor, zamanlayıcıdan çalışmıyor: PATH, profil, çalışma dizini, TTY,
  cron'da `%`), `windows_yetki` (CreateProcessAsUser 1314, TR5111, cmd.exe izni), `kaybolan` (Windows'ta iş kayboluyor,
  hata 231, antivirüs). Toplam 27 sınıf.
- **Yordamlar 33'e çıktı:** cron sorun giderme ve kaçırılan işler (anacron), Airflow'da görevi yeniden çalıştırma,
  backfill, görünmeyen DAG, paralellik ve tetikleme kuralları, Slurm düğüm durumu, iş bilgisi ve kesinti, AutoSys
  durum değiştirme ve ardılları buza alarak tek başına deneme, Kubernetes CronJob ayarları, Quartz, Control-M'de EM
  sağlığı, HA elle geçiş, PostgreSQL yedeği, döngüsel işe hata sınırı ve diğerleri.
- **Sınıf eşleştirme:** her yönetici metninde geçen genel sözcükler (`agent`, `ssl`, `password` gibi) tek başına bir
  sınıfı çağırmıyor; 129-255 arası çıkış kodu metinde de `signal` olarak okunuyor.
- **Puanlama:** Türkçe ünsüz yumuşaması (bellek/belleği) ve olumsuzluk ("yeniden başlatmayın") doğru değerlendiriliyor.

| Bölüm | Kol | Vaka | Doğru | Yarım | Yanlış | Zararlı |
| --- | --- | --- | --- | --- | --- | --- |
| Geliştirme | skill | 48 | 47 | 0 | 1 | 0 |
| Test | skill (ilk) | 59 | 0 | 3 | 56 | 0 |
| Test | skill (şimdi) | 59 | 4 | 10 | 44 | 1 |

Skill kolu modeli olmayan bir taban çizgisi: yalnızca skill metninin kendisini puanlıyor. Bir vaka için gereken
2-4 belirleyici adımın hepsini tek bir metnin taşıması zor; asıl ölçü, modelin bu bağlamla ne yaptığı (ham ve
harness kolları).

## 11. Kapsam (14 Kasım gecesi)

| | Sayı |
| --- | --- |
| BMC envanteri (tekil kayıt) | 4.578, bunların 3.993'ü Control-M: 2.269 bilgi makalesi, 1.688 tartışma |
| İçeriği okunan (geliştirme tarafı) | 100 makale ve tartışma, görüntülenmeye göre en çok okunandan başlayarak |
| Olay sınıfı / adminlik yordamı | 27 / 37 |
| Geliştirme vakası | 89 (13'ü başka zamanlayıcılardan) |
| Test vakası | 59 (ayrı ajan, Stack Overflow ve Server Fault) |

Sıradaki: kalan geliştirme makalelerini okumaya devam (yaklaşık 1.470, 40 saniyede bir sayfayla yaklaşık 16 saat);
BMC'nin test tarafından da vaka yazdırmak (ayrı ajan, tarayıcı boşken); GPU boşalınca ham ve harness kollarını koşmak.

## 12. BMC tur 2 ve genel sunucu yetenekleri (15 Kasım)

**BMC tur 2.** En çok okunan geliştirme makalelerinin ilk ~100'ü okundu (sayfa başına 40 sn, iframe ile; panel
gizliyken tarayıcı zamanlayıcıları kısıyor). Çıkanlar kendi sözcüklerimizle 37 geliştirme vakası, ~35 yordam ve 15
sınıfa yeni belirti oldu. Öğrenilen: yönetici sorunu hata metnini kopyalamadan anlatıyor; yalnız hata metnine bağlı
belirti kaçırıyor, anlatım sözcükleriyle tetiklenen yordam gerekiyor. Beceri kolu artık her koşuda güncel becerilerle
yeniden puanlanıyor (önbellek yalnız modelli kollarda).

**Genel yetenekler** (`skills/genel-yetenekler`, 27 yetenek). Ürünün altındaki işletim sistemi katmanı: süreç ve
görev yöneticisi, servisler, disk, bellek ve OOM, ağ ve port, DNS, SSH, WinRM ve PowerShell Remoting, kayıt
defteri, Windows kullanıcı hakları ve olay kimlikleri, dosya izinleri ve ACL, ortam farkı, işletim sistemi
sınırları, sertifika ve Java güven deposu, saat ve saat dilimi, günlükler, kilitler, işletim sisteminin kendi
zamanlayıcıları, sürüm ve yamalar, paylaşımlar, aktarım bütünlüğü, veritabanı istemcisi, yeniden başlatıp doğrulama.
Her biri Unix ve Windows için yalnız okuyan teşhis komutu, düzeltme yolu ve kaçınılacakları taşır; bağlı olduğu olay
sınıfları vardır. Harness bir sınıf eşleşince ona bağlı genel yetenekleri, anlatımda iki tetikleyici geçince de
kendiliğinden eşleşenleri (en çok 3) ajana verir; hostun işletim sistemini metinden çıkarıp yalnız o tarafın
komutlarını gösterir. Erişim katmanına aynı yeteneklerin komutları eklendi (`docs/08`).

**Ablasyon (beceri kolu, model yok).** `skill0` genel yetenekler olmadan, `skill` onlarla:

| Bölüm | skill0 doğru | skill doğru | zararlı |
| --- | --- | --- | --- |
| dev (161) | 159 | 159 | 0 / 0 |
| test (128, bakılmadan) | 9 | 17 | 1 / 1 |

Dürüst not: aynı sayıda **rastgele** seçilmiş genel yetenek de testte 16 doğru veriyor. Yani model olmayan kolda
artış, yetenek metninin getirdiği genel işletim sistemi sözcüklerinden geliyor; doğru yeteneği seçmenin değerini bu
kol ölçemez. Genel yeteneklerin gerçek katkısı model kolunda ölçülür: `harness` (genel yeteneklerle) ile `harness0`
(onlarsız), aynı model.

**Dış modelle ilk test.** GPU beklenmeden, bir ajan modeli dosyadan cevaplayabilsin diye `ops export` ve `ops ingest`
eklendi. Her test vakası yalnız bir kola gider (sınıfa göre sıralanıp dönüşümlü: ham 43, harness0 43, harness 42; üç
grubun beceri-kolu zorluğu eşit: 2, 3, 4 doğru). Ajan önce bütün yardımsız vakaları, sonra harness0'ı, en son
harness'ı cevaplar; böylece yardım metni yardımsız cevaplara sızmaz. Cevaplar harness kolunda aynı guard'dan geçip
puanlanır.

```
python -m vardiya ops export --split test --arms ham,harness0,harness --file <istem.jsonl>
python -m vardiya ops ingest --split test --file <cevaplar.jsonl> --label <ajan adi>
```

**İlk dış model sonucu (15 Kasım, KRON-A1, test bölümü, vaka başına tek kol).**

| Kol | Vaka | Doğru | Yarım | Yanlış | Zararlı | Adım grubu isabeti |
| --- | --- | --- | --- | --- | --- | --- |
| ham | 43 | 28 (%65) | 14 | 1 | 0 | %85 |
| harness0 | 43 | 23 (%53) | 18 | 2 | 0 | %82 |
| harness | 42 | 24 (%57) | 15 | 3 | 0 | %82 |

Okuma: güçlü bir model için harness doğruluğu artırmadı; genel yetenekler harness0'a göre bir vaka fark yaptı
(43 vakalık gruplarda gürültü düzeyi, yaklaşık ±7 puan). Hiçbir kolda zararlı cevap yok. Nedeni ölçüldü: harness
görülmemiş test anlatımlarında olay sınıfını vakaların ~%42'sinde **yanlış** eşliyor (harness0 17/43, harness 19/42)
ve bu bağlamı "Matched failure class" diye kesin bir dille veriyor. Doğru sınıf eşleştiğinde harness kolu 13 vakada 8
doğru, 0 yanlış; yanlış sınıfta 19 vakada 9 doğru, 2 yanlış.

Sonuç ve sıradaki iş: (1) Eşleşmenin güveni ajana söylenmeli: hangi belirtilerin eşleştiği, tek belirtiyle zayıf
eşleşmede "olası sınıf" dili, çok zayıfta hiç sınıf vermemek. (2) Bu değişiklik aynı test üzerinde ayarlanmamalı;
ölçüm için yeni, hiç görülmemiş bir test kümesi gerekir. (3) Harness'in asıl hedefi küçük modeller; aynı üç kol
GPU sırası gelince küçük modelle koşulacak. Güçlü modelde harness'in değeri doğruluktan çok güvenlik ve tutarlılıkta
aranmalı; bunun için zararlı tuzak içeren vakaların payı artırılmalı.
