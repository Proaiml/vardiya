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
