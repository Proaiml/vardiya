# Zamanlayıcı Admininin İşi: Talep Karşılama Araştırması

13 Kasım 2026

## 1. Çerçeve düzeltmesi

01 numaralı belge ürünü arıza müdahalesi etrafında kurmuştu: iş kırmızıya düşer, ajan teşhis eder, toparlar.
İlhan'ın düzeltmesi: rolün çekirdeği bu değil. Temel adminin günlük işi, ekiplerden gelen **iş tanımlama ve
değişiklik taleplerini almak, uygulamak ve denetim kaydıyla kapatmaktır.** Arıza müdahalesi ikinci sıradadır.

Bu belge o çekirdeği araştırır: talep nasıl gelir, admin neyi denetler, ürünler bu iş için ne sunar, hangi hatalar
tanım aşamasında doğar ve harness küçük bir modeli bu işte nasıl yükseltir.

Kullanıcı yorumları da aynı sırayı veriyor: bir yorumcu işinin büyük kısmının iş oluşturmak ve araca eklemek
olduğunu söylüyor; izleme, uyarıya tepki, agent ve bağlantı profili bakımı ile sürüm yükseltme onu izliyor.

## 2. Talebin yaşam döngüsü

İki bağımsız kaynakta aynı akış var: BMC'nin Workload Change Manager ürünü ve Minnesota Üniversitesi'nin AutoSys
ekibinin yayımladığı iç süreç.

| Adım | Ne olur | Kaynaktaki karşılığı |
| --- | --- | --- |
| 1. Talep gelir | Ekip yeni akış ya da değişiklik ister | WCM'de web kullanıcısı istek açar; UMN'de e-posta bilet üretir, sonraki talepler şablon tabloyla gelir |
| 2. Doğrulama | Alanlar tam mı, standartlara uyuyor mu | WCM'de Site Standards; UMN'de "Validate All": hata gönderimi engeller, uyarı engellemez |
| 3. İnceleme | Admin bakar, düzeltir ya da geri yollar | WCM'de çalışma alanı gönderilince salt okunur olur, admin notla geri döndürebilir |
| 4. Uygulama | Tanım alt ortama girer | WCM'de check-in; UMN'de araç satırları TST ortamına iş tanımı olarak yükler |
| 5. Test | Talep sahibi alt ortamda dener | UMN: TST'de hiç çalışmamış iş için uyarı çıkar |
| 6. Terfi | Tanım üst ortama taşınır, ortama özgü değerler dönüştürülür | Control-M'de promotion rules; UMN'de TST, QAT, PRD zinciri ve her iş için üç sütunlu karşılaştırma |
| 7. Kapanış | Bilet, yapılan değişiklikle birlikte kapatılır | UMN'de bilet numarası değişiklik kaydının zorunlu alanı |

Tasarım için üç ayrıntı önemli:

- **İnceleme bir karşılaştırmadır.** UMN'de gözden geçiren her iş için kaynak değeri, hedefin şimdiki değerini ve
  hedefin taşıma sonrası değerini yan yana görür ve tek tek kabul eder. Kuralla dönüşen alanlar bir renkte, kuralsız
  değişen alanlar başka renkte gösterilir; ikinciler elle doğrulanır.
- **Onay dış sistemde olabilir.** WCM bir değişiklik yönetimi sistemine bağlandığında, o sistemdeki koşul
  sağlanmadan check-in yapılamaz.
- **Terfi değer değiştirir.** UMN'de alt ortamlarda bildirim adresi bilerek ölü bir adrestir, üretime geçerken
  gerçek adrese çevrilir. Ortam adı iş adına, takvim adına, dosya yoluna ve komuta gömülüdür.

## 3. Talep türleri

Kaynaklarda doğrudan görülenler ile genel alan bilgisinden eklediklerim ayrı işaretli.

| Talep | Dayanak |
| --- | --- |
| Yeni iş ya da akış tanımı | Kaynak (WCM, UMN) |
| Mevcut işte değişiklik: zaman, takvim, bağımlılık, komut, host, bildirim | Kaynak (UMN şablonu, WCM) |
| Ortamlar arası terfi | Kaynak (promotion rules, UMN) |
| Önceki sürüme dönme, silinen işi geri getirme | Kaynak (Control-M Changes History) |
| Takvim bakımı: tatil, ay sonu, kural tabanlı takvim | Kaynak (Control-M takvim belgeleri) |
| Bağlantı profili ve agent bakımı | Kaynak (kullanıcı yorumları, BMC rol tanımları) |
| İşi kaldırma ya da devre dışı bırakma | Alan bilgisi |
| Tek seferlik çalıştırma (order, force) | Alan bilgisi; `ctmorder` belgesi dolaylı destekliyor |
| Kullanıcı ve rol yetkisi | Alan bilgisi |

## 4. Bir talepte bulunması gerekenler

UMN şablonu, gerçek bir kurumun istediği alanları gösteriyor. Her satır bir iştir.

| Bölüm | Alanlar |
| --- | --- |
| Kimlik | İş adı, iş tipi, grup ve uygulama, bağlı olduğu kutu (klasör) |
| Başlama | Başlama koşulları (bağımlılıklar) |
| Zaman | Gün ya da takvim, başlama saati ya da saat başına dakikalar |
| Çalışma yeri | Makine |
| Tipe özgü | Komut ve çıktı dosyaları; izlenecek dosya ve tetik tipi; HTTP alanları; uygulama işleri için süreç adı ve çalıştırma kimliği |
| Hata davranışı | Hata olursa kutuyu sonlandır |
| Bildirim | Bildirim açık mı, adres, mesaj |

Kurallar da şablonla gelir: iş tipine göre hangi alanın doldurulacağı renkle belirtilir, parola tabloya yazılmaz ve
ayrıca iletilir. Control-M tarafında aynı liste; uygulama ve alt uygulama, çalıştıran kullanıcı, kaynak havuzu,
öncelik, en çok bekleme günü, yeniden deneme sayısı, değişkenler ve iş belgesiyle genişler (bu genişleme alan
bilgisidir, şablondan değil).

## 5. Ürünler bu iş için ne sunuyor

| Yetenek | Control-M | AutoSys |
| --- | --- | --- |
| Talep arayüzü | Workload Change Manager: istek, not, geri döndürme, check-in | Site araçları (UMN'de ACCE ve şablon tablo) |
| Standart denetimi | Site Standards: klasöre atanır, kural ihlali uyarı ya da hata olur | Job Validation Exit (JVE): her değişiklikte, hangi arayüzden gelirse gelsin çalışır |
| Kod olarak tanım | Automation API: `build` doğrular, `deploy` önce build eder, deploy descriptor ortama göre dönüştürür | JIL: `insert_job`, `update_job`; web servisi aynı JIL'i kabul eder |
| Terfi | Promotion rules, `emwacli` | Site araçları |
| Sürüm geçmişi | Her oluşturma ve değişiklikte yeni sürüm; karşılaştır, geri yükle, silineni geri getir | Belgede bulunamadı |
| Denetim | Audit ve annotation: denetlenen her eylem için gerekçe sorulabilir | Belgede bulunamadı |
| Değişiklik yönetimi bağlantısı | WCM ile değişiklik yönetimi sistemi; koşul sağlanmazsa check-in olmaz | ServiceNow entegrasyonu anılıyor |

Broadcom'un JVE yazısındaki denetim örnekleri, bir adminin elle baktığı şeylerin iyi bir listesi:

- Ad standardı.
- Azami değerler, örneğin yeniden deneme sayısı.
- Desteklenmeyen özniteliklerin atılması.
- Değerin kurum biçimine çevrilmesi, örneğin sahip alanı. Burada değişiklik reddedilmez, düzeltilir ve kullanıcıya bildirilir.
- Asgari çalışma aralığı.
- Hem hata alarmı hem yeniden deneme açık olan iş.
- Zamanlanmamış işin kendine bağımlı olması.

Aynı yazı standardın neden araçta olması gerektiğini de söylüyor: kılavuzlar yazılır ama okunmaz, uyumsuzluk üst
ortama terfide ortaya çıkar ve değişiklik geri döner. Komut satırını saran betikler de yetmez, çünkü web arayüzü ve
REST üzerinden gelen değişiklik onları atlar.

## 6. Tanım aşamasında doğan hatalar

Her satır bir bench senaryo ailesi ve harness için deterministik bir denetimdir.

| Hata | Kaynak | Harness'in denetimi |
| --- | --- | --- |
| Değişiklik bugünkü çalışmayı etkilemez: plana alınmış iş eski tanımla çalışır | HCL ve Hitachi belgeleri açıkça söylüyor; Control-M'de `ctmorder` belgesi dolaylı | Değişikliğin hangi çalışmadan itibaren geçerli olacağını hesapla ve rapora yaz |
| Güncelleme yerine ekleme: iş zaten var | Broadcom bilgi bankası | Var olan tanımı ara, ekle ya da güncelle kararını kod versin |
| İçe aktarma yanlış işin üzerine yazar | `defjob` belgesi | Hedef kimliği önce çöz, fark çıkar |
| Takvim yanlış güne denk gelir: tatil kaydırma, "her ikinci cumartesi" | BMC takvim belgesi, Broadcom bilgi bankası | Takvimi ileri sar, önümüzdeki çalışma günlerini listele |
| Mantıksal gün ile New Day saati arasında kalan iş yanlış tarihe düşer | BMC belgesi | Başlama saatini New Day saatine göre denetle |
| Sabit saatle bağımlılık taklidi: üst iş uzarsa alt iş eksik veriyle çalışır | JAMS, Fortra | Saatli işin öncülünün süre dağılımına bak, bağımlılık öner |
| Hata aşağı akışa yayılmaz, bağımlı iş bozuk veriyle çalışır | JAMS | Bağımlılık ve hata davranışını birlikte denetle |
| Kutu "çalışıyor" durumunda takılır, ertesi günü engeller | UMN | Hata davranışı alanını zorunlu kıl |
| Ortam adı iş adında, yolda ya da takvimde yanlış kalır | UMN doğrulama kuralları | Terfi dönüşümünden sonra kalıntı ara |
| Test bildirimi üretime taşınır | UMN | Bildirim adresini ortama göre denetle |
| Ad ve değer standartları ihlali | Site Standards, JVE | Kural kümesi |
| Yalnızca arayüzden düzenleme: geçmiş yok, geri dönüş zor | JAMS | Her değişiklik önce ve sonra hâliyle kaydedilir |

Döngüsel bağımlılık, olmayan host ya da çalıştıran kullanıcı, tanımsız kaynak havuzu ve silinen işe bağımlı kalan
işler listede yok, çünkü taradığım kaynaklarda geçmediler. Alan bilgisi olarak eklenmeleri gerekir; sahadaki
sıklıklarını İlhan'ın deneyimi belirlemeli.

## 7. Harness'in modele vereceği bağlam

İlke aynı: hesaplanabilen şey modele hesaplatılmaz. Talep karşılamada modele giden paket şunlardan oluşur.

| Bağlam | Nasıl hesaplanır | Modele giden |
| --- | --- | --- |
| Benzer işler | Aynı klasörde ad, tip ve host benzerliği | "Bu klasördeki 12 yükleme işi şu kalıbı kullanıyor" |
| Klasörün kuralları | Standart kümesi ve mevcut tanımlardan çıkarılan fiilî kalıp | "Ad şu biçimde, sahip şu, bildirim şu adrese" |
| Etki alanı | Bağımlılık çizgesinde kapanış | "Bu işin saatini değiştirmek 9 işi ve 1 kritik servisi etkiler" |
| Çalışma günleri | Takvimin ileri sarılması | "Önümüzdeki 30 günde şu 21 günde çalışır; 29 Ekim tatil, bir sonraki iş gününe kayar" |
| Süre ve pay | Geçmiş çalışmaların medyanı ve yüzde 90'lık dilimi | "Öncül genelde 02:40'ta biter, en geç 03:25; 03:00 başlangıcı riskli" |
| Pencere yükü | İstenen saatte host ve kaynak havuzu doluluğu | "02:00 ile 03:00 arası bu host'ta 14 iş, havuz dolu" |
| İşin geçmişi | Olay defteri: hata oranı, hata imzaları, önceki değişiklikler | "Bu iş son 90 günde 4 kez hata aldı, üçü dosya gecikmesi" |
| Klasörün yavaşları | Süre sıralaması, kritik yol payı | "Klasörün en uzun zinciri şu, payı 20 dakika" |
| Emsal talepler | Defterde benzer talep ve nasıl kapatıldığı | "Benzer talep üç kez geldi, üçünde de şu alan düzeltildi" |

Kullanılacak yöntemler: döngü tespiti, takvim benzetimi, kritik yol ve pay, kaynak dengeleme ile boş pencere
arama (istenen saat doluysa en yakın uygun pencereyi öner), süre dağılımı ve yapısal tanım farkı.

## 8. Küçük modeli yükselten mekanizma

Talep karşılama, arıza teşhisinden daha elverişli bir iştir, çünkü çıktının doğruluğu büyük ölçüde kodla
denetlenebilir. Önerdiğim iş bölümü:

1. **Model tanım yazmaz, form doldurur.** Model talep metninden tipli bir talep kaydı çıkarır: iş adı, tip, host,
   zaman, bağımlılıklar. JSON ya da JIL'i derleyici üretir. Küçük modelin sözdizimi hatası yapacağı yer kalmaz.
2. **Eksik alan soruya dönüşür.** Zorunlu alan boşsa model uydurmaz; harness talep sahibine sorulacak soruyu üretir.
3. **Seçenekler sayılıdır.** Host, takvim, kaynak havuzu ve klasör, var olanların listesinden seçilir.
4. **Doğrulama döngüsü.** Derlenen tanım standart kümesinden ve denetimlerden geçer; hata modele kısa ve yapılandırılmış
   olarak döner, model yalnızca o alanı düzeltir.
5. **Emsal kalıp.** Aynı klasördeki benzer iş taslak olarak verilir; model sıfırdan değil, farkı yazar.
6. **Uygulama modelin değil.** Tanım politika çekirdeğinden geçer, önce ve sonra hâli kaydedilir, denetim kaydı
   kendiliğinden oluşur.

Sınırı açık yazmak gerekir: "kötü model, iyi model kadar başarılı olur" bir hedeftir, garanti değil. Bu yapı,
farkı talebi anlama adımına sıkıştırır. Talep açık ve alanları belliyse fark kapanmaya yakın olur; talep muğlaksa
iyi model daha iyi soru sorar. Bunu ölçecek olan bench'tir.

## 9. Bench'e etkisi

Yeni çekirdek senaryo ailesi: talep metni ve başlangıç ortamı verilir, beklenen sonuç bir tanım durumudur.

| Hüküm | Talep karşılamada anlamı |
| --- | --- |
| Doğru | Tanım beklenenle eşdeğer, standartlar tamam, çalışma günleri doğru, başka işe dokunulmamış, denetim kaydı eksiksiz |
| Sahte yeşil | Tanım yüklendi ve geçerli, ama yanlış: yanlış günde çalışacak, bağımlılık eksik, bildirim yanlış adrese |
| Güvenli başarısızlık | Tamamlayamadı ama dokunmadı: soru sordu ya da insana devretti |
| Yıkıcı | Başka işi bozdu, yanlış işin üzerine yazdı, döngü yarattı |

Ters tuzaklar burada da gerekir: doğru hamlenin talebi reddetmek ya da soru sormak olduğu vakalar (muğlak talep,
standarda aykırı istek, döngü yaratan bağımlılık) ve doğru hamlenin hiç soru sormadan uygulamak olduğu vakalar.
Her şeyi soran harness ikincide, hiç sormayan birincide ceza alır.

Aşama 0'daki üç arıza senaryosu duruyor; talep ailesi onların yanına gelir, yerine değil.

## 10. Yerel test ortamı

| Ürün | Durum | Talep karşılama için uygunluk |
| --- | --- | --- |
| JS7 JobScheduler | Açık kaynak; `sosberlin/js7` imajları Docker Hub'da, güncel etiket 2.8.2 | Envanter ve dağıtım REST üzerinden; Control-M kavramlarına en yakın aday. Eşleme henüz elle doğrulanmadı |
| Control-M Workbench | Ücretsiz, ama güncel imaj BMC'nin indirme portalından hesap ve belirteçle çekiliyor | Gerçek Control-M tanım biçimi ve `build`, `deploy`. Kalıcı değil: tanımlar konteyner yeniden başlayınca gider. 8 GB bellek ister |
| Rundeck | Açık kaynak | Tanımlar YAML; takvim ve koşul semantiği zayıf |
| Kestra | Açık kaynak | Tanımlar YAML ve sürümlü; sipariş tarihi ve koşul yerleşik değil |

Öneri değişmedi: çekirdek deterministik emülatör, dış geçerlilik için JS7. BMC hesabı varsa Workbench ikinci dış
ortam olarak çok değerlidir, çünkü ürettiğimiz tanımı gerçek Control-M'in doğrulayıcısından geçirir.

Makinenin durumu (13 Kasım 2026): Docker 29.1.3 ve WSL Ubuntu kurulu, 30 GB bellek var, Java yok. Ollama kurulu ama
sunucusu çalışmıyordu. Kurulu modeller bir merdiven kurmaya yetiyor: `qwen3:8b`, `qwen3:14b`, `qwen3:30b` ve
`gemma4:31b`; ayrıca `qwen3.5` ve `ornith` aileleri var.

## 11. Doğrulanamayanlar

- BMC'nin belge sitesi sayfa çekmeyi reddetti. Control-M bilgileri arama özetlerine ve aynı yardımı barındıran
  kurum sitelerine dayanıyor; sayfaların tam metnini okuyamadım.
- BMC topluluk forumu girişe kapalı. Reddit'te admin gününü anlatan bir başlık bulamadım; günlük iş sıralaması
  kullanıcı yorum sitelerinden geliyor.
- Annotation'ın zorunlu yapılıp yapılamadığı ve denetim raporunun tam alanları resmî belgeden doğrulanmadı.
- Control-M iş parametrelerinin tam listesi ve Bölüm 6'nın son paragrafındaki hatalar alan bilgisidir.
- JS7'nin güncel sürümü ve Workbench'in erişim koşulları hızlı değişir; kurmadan önce yeniden bakılmalı.

## 12. Kaynaklar

- [BMC: Workload Change Manager](https://documents.bmc.com/supportu/9.0.20/help/Main_help/en-US/34138.htm)
- [BMC: Request Workspace lifecycle](https://documents.bmc.com/supportu/9.0.19/help/Main_help/en-US/34195.htm)
- [BMC: WCM ve değişiklik yönetimi sistemi](https://documents.bmc.com/supportu/9.0.22/en-US/Documentation/WCM_Integration_with_Change_Managment_System.htm)
- [BMC: Site Standards](https://controlm.uconn.edu/help/CTMHelp/en-US/Documentation/Site_Standard_Management.htm)
- [BMC: Promotion rules](https://documents.bmc.com/supportu/ctrlm9/help/Main_help/en-US/Tools_PromotionRules.htm)
- [BMC: Automation API Build Service](https://documents.bmc.com/supportu/API/9.0.22/9.0.22.000/en-US/Documentation/API_Services_BuildService.htm)
- [BMC: Automation API Deploy Service](https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_DeployService.htm)
- [BMC: Deploy Descriptor](https://documents.bmc.com/supportu/API/Helix/en-US/Documentation/API_DeployDescriptor.htm)
- [BMC: Changes History](https://controlm.wisconsin.gov/help/CTMHelp/en-US/Documentation/Changes_History.htm)
- [BMC: Audit and Annotation parameters](https://documents.bmc.com/supportu/9.0.20/help/Main_help/en-US/CCMOptionsAuditAndAnnotationUC.htm)
- [BMC: ctmorder](https://controlm.uconn.edu/help/CTMHelp/en-US/Documentation/Utilities/ctmorder.htm)
- [BMC: defjob](https://documents.bmc.com/supportu/9.0.22/en-US/Documentation/Utilities/defjob.htm)
- [BMC: Calendars](https://controlm.uconn.edu/help/CTMHelp/en-US/Documentation/Calendars.htm)
- [Control-M Workbench deposu](https://github.com/controlm/workbench)
- [Minnesota Üniversitesi: AutoSys hizmeti](https://docs.jst.oit.umn.edu/Autosys)
- [Minnesota Üniversitesi: şablon tablo yönergesi](https://docs.jst.oit.umn.edu/Autosys/autojil-instructions)
- [Minnesota Üniversitesi: değişiklik talebi süreci](https://docs.jst.oit.umn.edu/ACCE/10_change_request)
- [Broadcom: AutoSys'te site standartlarını zorlamak](https://academy.broadcom.com/blog/automation/autosys/best-practices-for-enforcing-site-standards-with-autosys)
- [Broadcom: grup içindeki iş tanımlarını güncelleme](https://knowledge.broadcom.com/external/article/279314/how-can-we-update-autosys-jobs-defintion.html)
- [Broadcom: tatilde çalışan iş](https://knowledge.broadcom.com/external/article/200131/simulating-a-rule-job-executes-on-holida.html)
- [HCL: plandaki işin tanımını değiştirmek](https://help.hcl-software.com/workloadautomation/v1024/common/src_gi/eqqg1editjdef.html)
- [JAMS: toplu iş bağımlılığı uygulamaları](https://www.jamsscheduler.com/blog/batch-job-dependency-best-practices/)
- [Fortra: otomatik iş zamanlama üzerine](https://power.fortra.com/blog/dozen-things-you-should-know-about-automated-job-scheduling)
- [PeerSpot: Control-M kullanım amaçları](https://www.peerspot.com/questions/what-is-your-primary-use-case-for-control-m)
- [JS7 Docker imajları](https://hub.docker.com/r/sosberlin/js7)
