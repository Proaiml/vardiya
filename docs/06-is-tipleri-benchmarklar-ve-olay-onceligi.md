# İş Tipleri, Benchmarklar ve Olaydan Önce Davranmak

14 Kasım 2026. Üç soruya cevap: (1) Control-M'de hangi iş tipleri var, JS7'de kaçı tanımlanabiliyor, Vardiya'da
kaçı var; (2) dünyada iş tanımı, değişikliği, silinmesi ve kaydı için ya da adminlik olayları için bir benchmark
var mı; (3) geçmişi bir çizgeye yazıp modele bağlam olarak vermek ve olaydan önce tahmin yapmak için ne biliniyor,
Vardiya'ya nasıl girer.

Kaynaklar sonda. Ürün belgeleri resmî sayfalardan okundu; makale ve satıcı rakamları kaynağın kendi iddiasıdır,
bağımsız doğrulanmadı. Forum taraması iki kaynaktan: Stack Overflow'un açık arşivi ve BMC topluluğu (giriş yapılarak) (Bölüm 7).

## 1. Control-M iş tipleri

BMC'nin Automation API kod başvurusu (SaaS sürümü) iş tiplerini 25 kategoride listeliyor. Bir admin için önemli
olan ayrım şu: çekirdekte bir avuç genel iş tipi var, gerisi belirli bir ürüne bağlanan eklentiler.

**Çekirdek iş tipleri** (her kurulumda, eklentisiz):

| Kategori | API adı | Ne yapar |
| --- | --- | --- |
| İşletim sistemi | `Job:Command` | Tek bir işletim sistemi komutu (exe, betik çağrısı) |
| | `Job:Script` | Agent makinesindeki bir betik dosyası |
| | `Job:EmbeddedScript`, `Job:DetachedEmbeddedScript` | Betik metni tanımın içinde |
| Dosya izleme | `Job:FileWatcher:Create`, `Job:FileWatcher:Delete` | Dosyanın oluşmasını ya da silinmesini bekler; yol, tarama aralığı, süre sınırı |
| Veritabanı | `Job:Database:SQLScript` | SQL betiği çalıştırır |
| | `Job:Database:StoredProcedure` | Saklı yordam çağırır (şema, ad, parametreler) |
| | `Job:Database:EmbeddedQuery` | Sorgu tanımın içinde |
| | `Job:Database:MSSQL:AgentJob`, `Job:Database:MSSQL:SSIS` | SQL Server Agent işi ve SSIS paketi |
| Dosya aktarımı | `Job:FileTransfer` | FTP, SFTP, yerel arasında aktarım (MFT) |
| Web servisleri | `Job:WebServices`, REST, SOAP | HTTP çağrısı |
| Boş | `Job:Dummy` | Hiçbir şey çalıştırmaz; akışı birleştirmek ve koşul üretmek için |
| Ana bilgisayar | `Job:zOS:Member`, `Job:zOS:InStreamJCL` | z/OS JCL |
| SLA | `Job:SLAManagement` | Bir iş akışının hizmet seviyesini izler |

**Eklenti iş tipleri** (yaklaşık 150, kategoriye göre): ERP (SAP, PeopleSoft, JD Edwards, Oracle), veri bütünleştirme
(Informatica, DataStage, Talend, ADF, Glue, Fivetran, ...), veri işleme (Databricks, Snowflake, BigQuery, EMR,
Hadoop, DBT, ...), bulut hesaplama (AWS Lambda, Batch, EC2, Azure Functions, GCP Cloud Run, ...), kapsayıcı
(Kubernetes, ECS), iş akışı (Airflow, Step Functions, Logic Apps, ...), mesajlaşma (Kafka, IBM MQ, RabbitMQ, SQS),
CI/CD (Jenkins, GitHub Actions, Azure DevOps), altyapı kodu (Terraform, Ansible AWX, CloudFormation), yedekleme
(Veeam, NetBackup, Rubrik), RPA (UiPath, Automation Anywhere), raporlama (Power BI, Tableau, Qlik) ve son
sürümlerde yapay zekâ ajanları (Bedrock, Vertex AI, LangGraph, CrewAI). Bunların her biri, bağlantı bilgisini
tutan bir **bağlantı profili** ile birlikte tanımlanır.

Saydıkların bu tabloyla örtüşüyor: exe tetikleme `Command` ya da `Script`, dosya izleme `FileWatcher`, veritabanı
işleri `Database:*`. Sahada bunlara en sık eklenenler dosya aktarımı, SAP ve `Dummy`.

Her iş tipinde ortak olan tanım alanları da var: klasör ve uygulama, host ya da host grubu, çalıştıran kullanıcı,
takvim ve zamanlama, giriş ve çıkış koşulları (event), kaynaklar (havuz ve kilit), değişkenler, bildirimler,
yeniden deneme ve "çıktıda şu geçerse başarısız say" kuralları. Vardiya'nın bugünkü şablonu bunların bir alt
kümesini taşıyor (Bölüm 3).

## 2. JS7'de hangileri tanımlanabiliyor

JS7'de dört iş sınıfı var: kabuk işleri (işletim sisteminin kabuğu; exe, betik, Python, PowerShell), JITL işleri
(JS7 ile gelen Java şablonları), kullanıcının yazdığı Java işleri ve GraalVM üzerinde JavaScript işleri. JITL
şablon ailesi: veritabanı, dosya işlemleri, dosya aktarımı, dosya izleme, e-posta, SSH, REST API, SAP, şifreleme,
izleme, raporlama, bakım, envanter, geçmiş ve müdahale işleri.

| Control-M | JS7 karşılığı | Durum |
| --- | --- | --- |
| `Command`, `Script`, `EmbeddedScript` | Kabuk işi (betik tanımın içinde ya da dosyada) | Tam |
| `FileWatcher:Create` | File Order Source (dosya gelince iş akışını başlatır) ya da JITL dosya izleme işi | Tam |
| `FileWatcher:Delete` | JITL dosya izleme ve dosya işlemleri | Kısmen; doğrulanmalı |
| `Database:SQLScript`, `EmbeddedQuery` | JITL `SQLExecutorJob` (JDBC, her veritabanı) | Tam |
| `Database:StoredProcedure` | `SQLExecutorJob`; Oracle için `PLSQLJob`, `SQLPLUSJob` | Tam |
| `Database:MSSQL:AgentJob`, `SSIS` | `SQLExecutorJob` ile `msdb.sp_start_job`, kabuk işiyle `dtexec` | Dolaylı |
| `FileTransfer` | JITL dosya aktarımı (YADE: FTP, FTPS, SFTP, WebDAV, SMB) | Tam |
| `WebServices` REST | JITL REST API işi JS7'nin kendi API'si için; genel HTTP için kabukta `curl` | Dolaylı |
| `Dummy` | `exit 0` döndüren kabuk işi ya da işsiz iş akışı dalı | Dolaylı |
| SAP | JITL SAP işleri | Var; SAP sistemi gerekir, sınanmadı |
| Agentless SSH host | JITL `SSHJob` | Tam |
| (Control-M'de ayrı tip değil) E-posta | JITL `MailJob` | JS7'de fazladan |
| Bulut ve veri eklentileri, Kubernetes, Airflow, ... | Yok; kabuk işinden ürünün komut satırıyla | Dolaylı |
| z/OS | Yok | Yok |
| `SLAManagement` | Yok; bildirim ve izleme işleri kısmen | Yok |

Zamanlama tarafında karşılıklar laboratuvarda zaten kullanılıyor: koşul ve event için duyuru panoları, kaynak için
Resource Lock, takvim ve sipariş tarihi için Daily Plan, döngüsel çalışma için Cycle, yeniden deneme için Retry.

Kısacası: sahadaki işlerin çoğunu oluşturan **komut, betik, dosya izleme, veritabanı, dosya aktarımı, SSH ve boş
iş** JS7'de doğrudan ya da küçük bir dolanmayla tanımlanabiliyor. Ürüne bağlı eklenti tipleri ve z/OS
tanımlanamıyor.

## 3. Vardiya'da bugün olan ve eklenmesi gerekenler

**Güncelleme (14 Kasım 2026, sürüm 0.3):** aşağıdaki tablonun ilk beş satırı yapıldı. Şablon artık altı tip
tanıyor (`komut`, `dosya_izleme`, `veritabani`, `dosya_aktarimi`, `ssh`, `bos`) ve üç tipe özel alan taşıyor
(`baglanti`, `hedef`, `sure_siniri`). Çekirdek denetimleri tipin istediği alanları, bağlantı profilinin varlığını ve
türünü, dosya izlemenin süre sınırını, aktarımda kaynak ile hedefin aynı olmasını, boş işte komut yazılmasını ve
herhangi bir alana yazılmış parolayı yakalıyor. Bench'e iki aile eklendi: `yeni-tip` (beş tipten biriyle geçerli
yeni iş) ve `t-tip` (o tipin kendi tuzağı). JS7 bağdaştırıcısı tipe özel alanları meta veri olarak taşıyor ama işi
hâlâ kabuk işi olarak kuruyor; `SQLExecutorJob` ve dosya aktarımına eşleme yapılmadı. "Ortak" satırı (yeniden
deneme, çıktı kuralı) yapılmadı.

İlk durum şuydu: şablon iki tip tanıyordu, `komut` ve `dosya_izleme`, ve bench'teki bütün senaryolar bu iki
tipleydi. Her tip, talebe yeni zorunlu alanlar ve yeni tanım hataları getiriyor:

| Tip | Talepte bulunması gereken | Tuzak (doğru hamle iade) |
| --- | --- | --- |
| `veritabani` | Bağlantı profili adı, SQL dosyası ya da yordam adı, şema | Talebe parola yazılmış; profil ortamda yok; yordam başka şemada; üretim veritabanına test profiliyle |
| `dosya_aktarimi` | Kaynak ve hedef bağlantı profili, yollar, yön, sonrası (sil, taşı) | Hedef yol kaynakla aynı; joker karakter yanlışlıkla bütün dizini kapsıyor; dosya izleme işi olmadan aktarım |
| `dosya_izleme` (genişletilmiş) | Yol, tarama aralığı, süre sınırı, oluşma ya da silinme | Süre sınırı yok (iş sonsuza dek bekler); yol desen değil sabit ad ama dosya adı tarih taşıyor |
| `ssh` | Agentless host, bağlantı profili, komut | Host agent'lı tanımlıyken SSH istenmiş |
| `bos` (Dummy) | Yalnızca koşullar | Komut yazılmış; bağımlısı olmayan boş iş |
| Ortak | Yeniden deneme, çıktı kuralı, kaynak | Sınırsız yeniden deneme; yükleme işinde temizliksiz yeniden deneme |

Bunlar kodla denetlenebilir (alan var mı, profil var mı, parola var mı); model gerekmez. Modelin işi yine dil:
açıklamada "eski dosyaları silsin" yazıyorsa aktarım sonrası eyleminin ne olması gerektiği gibi.

## 4. Dünyada benchmark var mı

### İş tanımı, değişikliği, silinmesi ve kaydı

**Bulunamadı.** Toplu iş zamanlayıcılarında tanım taleplerini (yeni iş, değişiklik, kaldırma, denetim kaydıyla
kapatma, gerekçeli iade) ölçen açık bir benchmark yok. BMC'nin Control-M AI özellikleri (Jett, AI Workflow
Creator, planlama pilotu) için yayımlanmış bir doğruluk ölçümü de yok; belgede yalnızca "yanlış sonuç
verebilir" uyarısı var.

En yakın işler:

| Çalışma | Ne ölçüyor | Bizden farkı |
| --- | --- | --- |
| WorFBench | Doğal dilden çizge biçiminde iş akışı üretimi | Zamanlayıcı semantiği yok (takvim, koşul, host); iade, kayıt yok |
| SWE-InfraBench, Multi-IaC-Bench | Altyapı kodunda (CDK, Terraform, CloudFormation) ekleme ve değişiklik | Bulut kaynakları; tuzak talepler ve iade yok |
| "Don't Let the Model Write the YAML" (Ağustos 2026) | Kubernetes alan değişikliklerini modelin niyetinden deterministik editörle uygulamak; 83 görev | Yaklaşımı Vardiya'nınkiyle aynı: model niyet çıkarır, kod uygular. Değişikliğin doğru olup olmadığını insana bırakıyor; biz tuzak taleplerle bunu da ölçüyoruz |

Scheduler Admin Bench bu boşluğu dolduruyor. Konum cümlesi şimdilik doğru: tanım talepleri için batch
zamanlayıcı benchmarkı yok.

### Olay, teşhis ve müdahale

Bu alanda çok iş var, ama hepsi mikroservis, Kubernetes ya da veritabanı dünyasında; **hiçbiri toplu iş
zamanlayıcısında değil.**

| Benchmark | Ölçek | Ne ölçüyor | Not |
| --- | --- | --- | --- |
| ITBench (IBM, ICML 2025) | 102 senaryo: SRE, güvenlik (CISO), maliyet (FinOps) | Canlı ortamda teşhis ve düzeltme | En iyi ajanlar SRE senaryolarının ~%11'ini çözüyor |
| AIOpsLab (Microsoft) | 48 problem | Algılama, yerelleştirme, kök neden, düzeltme | Ajan-bulut arayüzünün kaynağı |
| OpenRCA ve OpenRCA 2.0 | Tarihsel telemetri | Kök neden kümesini bulmak, adım adım nedensellik | 2.0'da 11 öncü modelin ortalaması %20,7 |
| Cloud-OpsBench (Mart 2026) | 452 arıza | Kubernetes'in sayısal ikizinde teşhis | Yeniden oynatılabilir; bizim emülatör fikrine en yakın |
| SREGym | Canlı | SRE ajanları | |
| ORCA-bench (Temmuz 2026) | 1.079 görev, 195'i olaysız kontrol | Belirsiz kullanıcı şikâyetinden kök neden | En iyi doğruluk %25 (orta), %10 (zor); uydurma oranı %7 ile %40 |
| DBA-Bench (2026) | Üretim benzeri veritabanı | Veritabanı operasyon ajanları | |

Bunlardan alınacak dersler, Vardiya'nın olay tarafı için:

- **Olaysız kontrol görevleri şart.** ORCA-bench görevlerin %18'ini olaysız tutuyor; doğru cevap "sorun yok".
  Vardiya'nın arıza tarafında bu sınıf var ama tek senaryo.
- **Uydurma ayrı ölçülmeli.** Kök nedeni yanlış bulmak ile olmayan bir kök neden icat etmek farklı hatalar.
- **Sonuç puanı yetmiyor.** OpenRCA 2.0, doğru servisi bulup belirtiye bağlayamayan ajanları ayırmak için adım
  adım etiket kullanıyor. Bizdeki karşılığı: kök neden işi ve oraya giden zincir.
- **Yeniden oynatılabilir ikiz.** Cloud-OpsBench'in sayısal ikizi, Vardiya'nın deterministik emülatörüyle aynı
  fikir; canlı ortam benchmarkları tekrar edilemiyor.

## 5. Geçmişi çizgeye yazmak ve olaydan önce davranmak

### Bulunanlar

- **Bankacılıkta eski sistemlerin kök neden analizi** (arXiv 2411.13017): olay ve log verisinden kurulan bir bilgi
  çizgesini sorgulayan belirti ajanı, "beş neden" ajanı ve bulguyu geçmiş olay örüntüleriyle karşılaştıran
  sınıflandırma ajanı. Olay sonrası incelemelerin bulguların %95'ini doğruladığını bildiriyor. Senin anlattığın
  yapıya en yakın yayımlanmış iş bu, ve bankacılık bağlamında.
- **SynergyRCA** (Kubernetes): model ilgili kaynağı seçiyor, sonra çizge veritabanını sorguluyor; %90 doğruluk,
  teşhis başına ~2 dakika.
- **Grafana'nın denemesi**: bilgi çizgesi bağlamı verilen ajan 16 tekrarın 15'inde doğru kök nedeni buldu, ham
  telemetriyle 1'inde. Tek olay tipi, satıcı denemesi.
- **GraphMind**: bulut veritabanı olaylarında çizge üzerinde gezinen ajan; RCACopilot gibi önceki sistemlerle
  karşılaştırıyor.
- **Toplu iş arızası tahmini**: HPC işlerinde çizge evrişim ağıyla "iş bitecek mi" sınıflandırması; bulut toplu
  iş izlerinde DAG benzerliğiyle iş sınıflandırma. Toplu iş bağımlılık çizgesi üzerinde, geçmiş çalışma
  etiketleriyle olay tahmini yapan bir makale bulunamadı.
- **Patentler**: tahmine dayalı toplu iş arızası tespiti ve giderimi (US 11656932), SLA'yı geciktiren işlerin
  çizgede geriye doğru yerelleştirilmesi (US 12373250), toplu iş etkinliğini gerçek zamanlı gözleme ve tahmin
  (US 12190166). Alan ticari olarak sahiplenilmiş; açık yayından önce bakılmalı (01 belgesi, Bölüm 4).
- **Satıcı iddiaları**: Digitate ignio, Broadcom Automic ve Rocket Software toplu iş gecikmesini ve SLA ihlalini
  önceden tahmin ettiklerini söylüyor (Rocket: %90 doğruluk, ortalama 4 saat önceden). Bağımsız ölçüm yok.
- **Gerçekçi veri**: Alibaba cluster-trace-v2018, 4 milyon toplu işin görev DAG'larını ve arıza istatistiklerini
  8 günlük bir pencerede veriyor. Emülatördeki süre dağılımlarını ve DAG biçimlerini gerçek veriye yaslamak için
  kullanılabilir.

### Vardiya'ya nasıl girer

Önerdiğin yapı, Vardiya'nın "model okur, kod denetler" yöntemine oturuyor. Çizgeyi ve sayıları kod tutar ve
hesaplar; model, kodun çıkardığı küçük alt çizgeyi okuyup açıklar ve önerir. Model çizgeyi kendisi gezmez.

**Çizge** (olay defterinin bugünkü özet zincirli tablosunun üstüne):

| Düğüm | Kenar |
| --- | --- |
| İş, sürüm (her tanım değişikliği) | bekler, kaynak paylaşır, aynı tabloya yazar (gizli bağımlılık) |
| Çalışma (her sipariş: süre, sonuç, bekleme nedeni) | ait olduğu iş ve sürüm, aynı gün çalışan öncüller |
| Hata imzası (şablonlaştırılmış log satırı) | görüldüğü çalışmalar |
| Talep ve değişiklik | değiştirdiği iş, kapatan, sonrasındaki ilk çalışma |
| Olay | kök neden işi, etkilenen işler, yapılan müdahale, doğrulandı mı |

**Üç kullanım ve her birinde iş bölümü:**

| Görev | Kod | Model |
| --- | --- | --- |
| Olay anında teşhis | İlk arıza yalıtımı, hata imzasını defterde arama, son değişiklikle bağıntı; aday kök nedenler ve kanıtları | Kanıtlara bakıp aday seçer, operatöre gerekçe yazar; kanıtı olmayan aday kabul edilmez |
| Olaydan önce uyarı | Gün tipine göre süre dağılımı, eğilim (Theil-Sen), kırılma (CUSUM), kritik yol üzerinde Monte Carlo ile SLA risk olasılığı; değişiklik sonrası ilk çalışmaların izlenmesi | Riskli olanları önceliklendirir, talep sahibine ya da nöbetçiye ne yazılacağını hazırlar |
| Gerektiğinde müdahale | Politika çekirdeği, etki alanı, idempotans sınıfı, emülatörde ileri sarma | Önerilen müdahaleyi seçer; uygulamayı kod yapar, yetki seviyesi izin verirse |

### Bunu ölçmek: bench'in ikinci hattı

Dünyada toplu iş için olay benchmarkı olmadığından bunu da biz kurmalıyız. Tasarım, mevcut bench'in kurallarını
izler:

- **Zamana göre bölünmüş geçmiş.** Senaryo üreteci bir sitenin 60-90 günlük çalışma geçmişini üretir (Alibaba
  izinden alınan süre dağılımlarıyla). Defter ilk dilimle dolar, ölçüm son dilimde yapılır; defter sınav
  sorularını göremez.
- **Görev aileleri.** Olay anı (bugünkü arıza aileleri ve 01 belgesi Bölüm 3'teki on iki satır), olaydan önce
  (yarın SLA kaçacak mı, hangi iş yüzünden; değişiklik sonrası riskli iş; yavaşlayan iş), olaysız kontrol (doğru
  cevap "uyarı yok").
- **Ölçüler.** Olay anında mevcut hüküm sınıfları ve uydurma oranı. Olaydan önce kesinlik, duyarlılık, uyarının
  ne kadar önce verildiği ve yanlış alarm başına bedel. Müdahalede gereksiz müdahale oranı.
- **Kollar.** Ham model; harness, defter boş (soğuk); harness, defter dolu (ılık); defter yerine düz metin geçmiş
  (plasebo: kazanç çizgeden mi, yalnızca bilgiden mi).

Beklenen sonuç, harness'in burada da küçük modeli taşıması: hesabı kod yaptığı için modelin işi "şu üç adaydan
hangisi, neden" sorusuna iniyor. Bu henüz bir hipotez; ölçülmedi.

## 6. Doğrulanamayanlar ve senden gerekenler

- **Forum taraması yapılamadı.** BMC topluluk forumu girişe kapalı. Hesabın varsa, Claude'un tarayıcı panelinde
  kendin giriş yaparsan oradaki konuları okuyup sahadaki en sık arıza ve tanım hatalarını çıkarabilirim. Parolanı
  ben girmem.
- **Sahadaki iş tipi dağılımı.** Kendi ortamınızda iş tiplerinin oranı (komut, dosya izleme, veritabanı, aktarım,
  SAP) Bölüm 3'teki sırayı belirler. Kabaca bir sayı yeter.
- **JS7 eşlemesi.** "Tam" yazılanlar belgeye göre; laboratuvarda yalnızca kabuk işi ve duyuru panoları denendi.
  `SQLExecutorJob`, dosya aktarımı ve File Order Source laboratuvarda sınanmalı.
- **Satıcı ve makale rakamları** kaynakların kendi iddiaları.

## 7. Forumlarda ne olmuş: on üç yıllık soru arşivi

BMC'nin kendi topluluk forumu girişsiz okunamıyor (sayfalar 403 ve 404 döndürüyor). Herkese açık en büyük arşiv
Stack Overflow'daki `control-m` etiketi: 2011'den 2025'e **214 soru**, yıllara göre 2018'de en yoğun (27), 2023'ten
sonra azalıyor. Sorular Stack Exchange'in açık API'siyle indirildi, konularına göre ayrıldı ve en çok okunanların
cevapları okundu. Bir soru birden çok konuya girebilir.

| Konu | Soru | En çok okunanlardan |
| --- | --- | --- |
| Betik, kabuk, Windows, Unix | 53 | PowerShell işi tanımlamak, betikte iş adını almak |
| Hata durumu, çıkış kodu, Ended Not OK | 35 | OSCOMPSTAT değerleri, ilk iş hata verince devam etmek |
| Takvim, sipariş, ODATE, New Day | 34 | ODATE ile RDATE farkı, döngüsel işin yeni güne taşması |
| Bağımlılık ve koşul | 21 | Aylık ve günlük iş arasında koşul, bir koşulu kimin kullandığı |
| Dosya izleme ve aktarım | 20 | Dosya adında boşluk, dosya izleme işini bulmak |
| Komut satırı ve API | 19 | İşi elle çalıştırmak, Automation API |
| Agent, host, bağlantı | 17 | Host grubu, Kubernetes'te agent |
| Değişkenler | 12 | YYYYMM, auto-edit biçimleri |
| Taşıma ve dışa aktarma | 11 | Bütün işleri dışa aktarmak, AWS'ye geçiş |
| Uyarı ve bildirim | 10 | "Belli saate kadar başlamazsa e-posta", klasörde herhangi bir iş düşerse uyarı |
| Veritabanı işleri | 10 | Saklı yordamın hatası Control-M'e gelmiyor |

Sorulardan çıkan ve doğrudan Vardiya'ya taşınan arıza örüntüleri:

| Örüntü | Forumda | Neden önemli | Vardiya'da |
| --- | --- | --- | --- |
| İş başarılı görünüyor ama veri eksik | Saklı yordamın hatası çıkış koduna yansımıyor; pyodbc ile çağrılan yordamda commit yok | Sahte yeşilin ders kitabı örneği: zincir yeşil, veri bozuk | Geçmiş üretecinde `sessiz` türü; kök neden yordama yapılan değişiklik |
| Servis hesabının parolası değişti | Parolayı değiştiren kişi işlerin kırılacağını bilmiyor; agent parolayı kendi deposunda tutuyor | Aynı anda birçok iş düşer; tek tek bakan nöbetçi ortak nedeni geç görür | `parola` türü; çizge aynı kullanıcıyı paylaşan işleri bir arada gösterir |
| Aynı tabloya aynı anda yazan işler | Dört iş aynı tabloya ekliyor, kilit hatası; doğru cevap kaynak (Resource) tanımlamak | Yeniden çalıştırmak o geceyi kurtarır, hata geri gelir | `kilit` türü; analiz "bu çözüm daha önce tutmadı" der |
| İş bitmiyor | .bat bittiği halde iş kapanmıyor: başlattığı alt süreç hâlâ açık | Asılı mı yavaş mı ayrımı | `takili` türü |
| Döngüsel iş yeni güne taşıyor | New Day'de önceki günün kopyası hâlâ çalışırken yenisi başlıyor | Mükerrer çalışma | Henüz yok (aday tuzak ailesi) |
| Döngüsel iş hata verip durmuyor | Hata verdikçe yeniden çalışıyor | Hata sessizce büyür | Henüz yok |
| Aylık iş ile günlük iş arasında koşul | Farklı takvimli iki işi bağlamak | Vardiya'nın 0.2'de eklediği takvim uyumu denetiminin sahadaki karşılığı | `E_CAL_DEP` ve `t-uyumsuz` |
| Koşul adına sayı eklenmiş | Bağımsız akış olarak sipariş edilince koşul adına ek geliyor, ardıl iş sonsuza dek bekliyor | Tanımda her şey doğru görünür | Henüz yok |
| İş planlamada var, izlemede yok | İş sipariş edilmemiş; takvimi o gün için seçmiyor | "Neden çalışmadı" sorusunun en sık cevabı | Talep tarafında sonraki çalışma günleri gösteriliyor |
| Belli saate kadar başlamazsa haber ver | Öncül uzun sürünce iş geç başlıyor | Olaydan önce uyarı ihtiyacının kendisi | Erken uyarılar: yavaşlama eğilimi |

Bu tablonun ilk dört satırı ve "dosya gelmedi", "agent yanıt vermiyor", "disk doldu", "değişiklik sonrası hata"
yerel hata çizgesinin örnek geçmişinde birer olay türü olarak duruyor (`vardiya/gecmis.py`, `CATALOG`).

Sınırlar: Stack Overflow soruları çoğunlukla geliştiricilerden geliyor, adminlerden değil; BMC topluluğu ve
şirket içi deneyim farklı bir dağılım gösterebilir. Sorular sahadaki sıklığı değil, insanların takılıp sorduğu
şeyi gösteriyor.

### 7.1 BMC topluluğu (Control-M konusu)

14 Kasım 2026'da İlhan'ın hesabıyla girilerek okundu. Konu sayfası 5,95 bin takipçi ve 10,44 bin gönderi gösteriyor.
"Son etkinlik" listesinin 14 sayfasının 13'ü okundu (yaklaşık 260 gönderi): son bir yılın soruları ve blog yazıları,
2021'e kadar giden geliştirme istekleri (idea). Birkaç soru açılmak istenince site çok sık istek uyarısı (429) verdi;
tarama orada bırakıldı, soru içleri ve cevaplar okunamadı. Aşağıdakiler başlıklardan ve cevap sayılarından çıkıyor.

| Tema | Örnek başlıklar (cevap sayısı) | Vardiya için anlamı |
| --- | --- | --- |
| Sürüm yükseltme ve platform | Yükseltme ön kontrolü ODBC ve sqlcmd sürümünü bulamıyor; 9.0.21.300 sonrası viewpoint'ler kendiliğinden kapanıyor; Microsoft yamaları sonrası sorun; "CScript.exe 5.6 gerekli" hatası (15); Java 11, log4j, Oracle 26ai ve RHEL desteği; yükseltme sonrası arşiv sunucusu | Olayların önemli bir kısmı iş tanımından değil platform değişikliğinden geliyor: çizgede "değişiklik" yalnızca iş tanımı değil, yama ve yükseltme de olmalı |
| SaaS'a geçiş ve karma kurulum | Agent sürümlerini kendimiz yönetmek; AS/400 işlerini SaaS'a taşımak; 4.290 AS/400 işi için hacim sınırı; karma kurulumda felaket kurtarma testi; geçmişi SaaS arşivine taşımak; denetim kaydı saklamayı 90 günden 24 aya çıkarmak | Denetim kaydının uzun süre saklanması ve taşınabilmesi gerçek bir ihtiyaç; Vardiya'nın kaydı yerelde ve özet zincirli |
| Kimlik bilgisi ve güvenlik | CyberArk'taki parolaları CCM'e almak (8); gMSA hesabını "run as" yapamamak; MFT işinde "run as"ın bağlantı profili adına zorlanması ve ctmsec'in reddetmesi; tedarikçilerin anahtara geçmesi; SSL sonrası CCM'de hâlâ HTTP; agent'ın belli komutları çalıştırmasını engellemek; iki CVE sorusu | Parolanın talepte değil kasada durması (0.3'teki parola denetimi) doğru yön; bağlantı profili ile çalıştıran kullanıcı ilişkisi denetlenmeli |
| Zamanlama anlamı | Cuma sipariş edilip cumartesi biten işin koşulu yürütme değil sipariş tarihiyle ekleniyor, sonraki çalışma etkileniyor (8); Keep Active davranışı; işi gecikmeli sipariş etmek; çocuk iş ancak üç ebeveyn de başarılıysa; döngüsel işte TIME UNTIL sonrası LATESUB uyarısı; önceki yıl değişkeni (7) | Koşul ve sipariş tarihi (ODATE) hataları sahada sürüyor; bench'e "hafta sonuna taşan iş" ailesi eklenebilir |
| Kaynak bekleme | Nicel kaynak (QR) kullanan iş, kaynakların hepsi boşken bekliyor (27, en çok cevaplanan); z/OS'ta adında `$` olan kaynakta bekleme | Olay tarafında "kaynak bekliyor" ailesinin sahadaki karşılığı; en çok tartışılan konu |
| Agent ve sunucu işletimi | Agent başlarken pid dosyası bulunamıyor; SAP işleri çalıştıran agent'ta XT_*.log dosyaları 60 GB'ı geçip diski dolduruyor; listede hayalet host grupları; bütün agent'larda debug durumunu görmek; EM ile sunucunun eşzamanı bozuluyor | Hata çizgesindeki "disk doldu" türünün sahadaki bir nedeni: agent'ın kendi logları |
| Tanım bütünlüğü ve denetim | Kaydetmeden üst üste değişiklik yapınca aynı adla mükerrer iş kaydı oluşuyor; son 7 günün tanım değişikliklerini almak; döngüsel iş tekrar tekrar düşse de tek olay kaydı açmak; aylık hata sayısı raporu | Vardiya'nın talep masası ve olay çizgesinin doğrudan karşıladığı ihtiyaçlar |
| Geliştirme istekleri (2021-2026) | İzleme ekranında "Ended OK" ile "Set OK" işleri ayırt edilsin; denetim raporunda iş sürüm geçmişi; değişiklik geçmişinde güncel sürüm; hata olunca hizmet masasıyla daha iyi bütünleşme; iş yükü için "ne olurdu" tahmin senaryoları; dinamik tahmin; JVM kullanımını izleme; iş alanı taleplerinden önce not zorunlu olsun; her sürümün bilinen sorunlarının tam listesi | Kullanıcıların istediklerinin çoğu Vardiya'nın tasarımında var: zorla başarılı sayılan işi (sahte yeşil) ayırmak, sürüm geçmişi, zorunlu talep şablonu, emülatörle ileri sarma |

En çok öne çıkan iki gözlem:

- **"Set OK" ile gerçekten başarılı işi ayırma isteği** (2022'den beri açık) Vardiya'nın sahte yeşil kavramının sahadaki
  karşılığı. İzleme ekranı bu ikisini aynı gösteriyor; aşağı akışta veri hatasının kaynağı buradan kayboluyor.
- **En çok cevaplanan soru kaynak beklemesi** (27 cevap). Olay tarafının ilk yeni ailesi olarak bu seçilmeli.

Sınırlar: yalnızca başlıklar ve cevap sayıları okundu; son etkinlik listesi bütün forumun küçük bir kesiti ve son bir
yıla ağırlık veriyor.

Sonradan okunan bir soru (14 Kasım 2026, tek sayfa): **cuma sipariş edilip cumartesi biten işin koşulu sipariş
tarihiyle ekleniyor, cumartesi sipariş edilen ardıl iş bekleyip kalıyor** (8 cevap, 126 görüntülenme). BMC'nin ve
kullanıcıların önerdiği çözümler: iki işi aynı sipariş tarihiyle aynı akışta sipariş etmek; koşulu "tarihsiz" (No
Date) üretip ardıl bitince silmek; ya da koşul tarihine +1 gün kaydırma vermek. Soran kişi "herhangi bir tarih"
seçeneğini denemiş, ardıl yine beklemiş; konu çözülmemiş görünüyor. Vardiya'ya karşılığı: farklı sipariş sıklığındaki
iki işi bağlayan talepte (haftalık ile günlük, ya da gece yarısını geçen öncül) sipariş tarihi uyarısı; takvim uyumu
denetiminin (`E_CAL_DEP`) bir sonraki adımı.

Aynı sayfanın "öne çıkan bilgi makaleleri" kutusunda agent tarafı hatalar görünüyor: "failed to write submit message
to AM data pipe" (hata 232), sertifika yolu bulunamadı (SunCertPathBuilderException), SAP önbellek dosyalarının
silinmemesi ve gereken güvenlik duvarı portları. Bunların ilk ikisi hata çizgesinde "agent iletişimi" işaretlerine
eklendi; üçüncüsü disk dolma uyarısının bir başka nedeni.

**Düzeltme (aynı gün).** Başlıktan çıkardığım bir sonuç yanlış çıktı: "CScript.exe 5.6 gerekli" hatası (15 cevap)
işlerin yama sonrası bozulması değil, Control-M masaüstü istemcisinin kurulumunda çıkan bir hata; BMC'nin bilgi
makalesine göre nedeni Windows bölgesel ayarları. Yama sınıfındaki örnek hata satırı gerçek bir iş hatasıyla
(uygulama başlatılamadı, 0xc0000142) değiştirildi. Ders: başlıktan sınıf çıkarmak yetmiyor, içerik okunmalı.

**Konu içi okumalar (dakikada en çok bir sayfa).** SAP işleri çalıştıran agent'ta XT_*.log dosyalarının 60 GB'ı
geçmesi: cevaba göre dosyayı SAP extractor süreci yazıyor; extractor yeniden başlatılınca (shut-xt, start-xt) yeni log
açılıyor ve eski silinebiliyor; büyümenin olağan nedeni silinmiş bir bağlantı profiline bağlı kalan olaylar. Soran kişi
yeniden başlattıktan sonra yeni logun yine büyüdüğünü, aynı host grubundaki öbür SAP agent'ında böyle bir dosya
olmadığını yazmış; kök neden kapanmamış. Disk sınıfının nedeni ve müdahalesi buna göre genişletildi.

"Failed to write submit message to AM data pipe, error 232" (BMC bilgi makalesi, 2.514 görüntülenme): agent'ın iç
iletişim hatası; bir sürümde düzeltilmiş bilinen bir hata, ayrıca agent'ta Java yolu güncelleme betiği çalıştırıldıktan
sonra da görülüyor. Agent sınıfının nedeni ve müdahalesine "yakın zamanda Java ya da agent değişikliği" eklendi; bu
sınıf zaten sunucu değişikliği kanıtına bakıyor.

Parolaların CyberArk'tan alınması (9 cevap) ve ona bağlı bir 2020 sorusu: CyberArk'ın otomatik parola dönüşü "Run As"
kullanıcılarına "<" ve ">" içeren parolalar göndermiş, Control-M bunları kabul etmediği için büyük bir kesinti yaşanmış;
cevaplarda öneri, yeni parolayı Control-M'e yazdıktan sonra CCM'den sınamak. Parola sınıfının nedeni ve müdahalesi buna
göre genişletildi. Buradan çıkan bir olaydan önce uyarısı fikri: aynı kök nedenli olaylar düzenli aralıkla
tekrarlıyorsa (örnek geçmişte parola dönüşü 64 günde bir) bir sonrakinin tarihi tahmin edilebilir.

"New Day sonrası sipariş edilmeyen işler" araması 18.875 sonuç döndürdü; ilk sıradaki bilgi makaleleri: bir User Daily'nin
eksik sipariş ettiği işleri bulup toplu sipariş etmek (5.614 görüntülenme), New Day sürecini hızlandırmak, New Day'i yeniden
çalıştırmak, 9.0.21'e yükseltmeden sonra gateway'in "Formatting AJF / No Sync" durumunda takılması ve yine yükseltmeden
sonra döngüsel işlerin sipariş edilip agent'a gönderilmemesi. Plan sınıfı bunlarla dolduruldu; sınıf sunucu değişikliği
kanıtına da bakıyor.

### 7.2 Başka zamanlayıcılarda aynı sınıflar

Çözücülerin bir ürüne değil bir arıza sınıfına yazıldığını sınamak için aynı sınıflar başka zamanlayıcıların
sorularında da sayıldı: Stack Overflow'da `autosys` etiketinin en çok oy alan 300 sorusu ve `airflow` etiketinde
takılma, hata, zaman aşımı ve kuyruk sözcükleriyle aranmış 857 soru. Sayılar anahtar sözcükle yapıldı, kaba
ölçüdür; bir soru birden çok sınıfa girebilir.

| Arıza sınıfı | Control-M (214) | AutoSys (300) | Airflow (857) | Vardiya'da |
| --- | --- | --- | --- | --- |
| Bağımlılık ya da koşul bekliyor | %16 | %43 | %44 | Kısmen (takvim uyumu, öncül hatası) |
| Takılı, bitmeyen iş | %8 | %10 | %38 | Var |
| Kaynak ya da kuyruk bekleme | %2 | %2 | %35 | Var |
| Yeniden deneme ve yeniden çalıştırma | %2 | %3 | %33 | Kısmen |
| Zaman aşımı | %0 | %2 | %30 | **0.3'te eklendi** |
| Takvim, tatil, zaman dilimi | %6 | %13 | %30 | Kısmen |
| Sipariş tarihi, mantıksal tarih (ODATE, execution_date) | %3 | %0 | %28 | **0.3'te eklendi** |
| Parola ve kimlik | %6 | %2 | %18 | Var |
| Kilit, eşzamanlı yazma | %0 | %1 | %10 | Var |
| Mükerrer ya da üst üste çalışma | %2 | %2 | %10 | **0.3'te eklendi** |
| Dosya gelmedi, dosya izleme | %4 | %8 | %3 | Var |
| Plan yüklenmedi (New Day, günlük plan) | %1 | %0 | %1 | Bilgi olarak eklendi |

Çıkan sonuç: ürünlerin dili farklı ama arıza sınıfları aynı. Control-M'deki ODATE ile Airflow'daki `execution_date`,
Control-M'deki kaynak havuzu ile Airflow'daki `pool` ve `max_active_tasks`, AutoSys'teki `term_run_time` ile Airflow'daki
`execution_timeout` aynı sınıfın farklı adları. Bu yüzden her sınıfın tanınması ürün bağımsız işaretlerle yapılıyor
(`gecmis.SIGNS`) ve olay bench'inin `test` bölümünde hatalar AutoSys ve Airflow diliyle de yazıldı.

JS7'nin herkese açık hata kayıtları (GitHub, 14 kayıt) aynı sınıfları gösteriyor: agent'ın başlamaması, güncelleme
sonrası Controller'ın düşmesi, iptal edilen siparişlerin "iptal ediliyor" durumunda takılı kalması, SMB aktarımının
60 dakikada kopması, adında boşluk olan dosyanın aktarılamaması (aynı sorun Control-M sorularında dosya izlemede de var).

BMC topluluğunda en çok cevaplanan kaynak bekleme sorusunun (27 cevap) açıklaması: bekleme bilgisi boş görünüyor, iş
günlüğünde "Wait Resource (code 5120)" var; iş bir kez bekletilip serbest bırakılınca (hold, free) yürümüş. Aynı aramada
çıkan bilgi makaleleri: iş durum kodlarının anlamları, kaynak kilit tablosunda eksik satır yüzünden sunucunun
başlamaması, bekleme bilgisinin izleme ekranında görünmemesi. Kaynak bekleme çözücüsünün önerisi buna göre güncellendi:
önce bekleme nedenini doğrula, kaynaklar boşsa işi bir kez bekletip serbest bırak, asılı kayıt varsa onu serbest
bırak, havuz sınırını büyütme.

Kaynaklar (bölüm 7):

- [BMC Community: Control-M konusu (giriş gerekir)](https://community.bmc.com/s/topic/0TO3n000000WJUCGA4/controlm)
- [Stack Exchange API, control-m etiketi](https://api.stackexchange.com/docs/questions)
- [Aynı tabloya yazan işler ve kilit](https://stackoverflow.com/questions/6910999/scheduling-issues-with-control-m)
- [Saklı yordamın hatası Control-M'e gelmiyor](https://stackoverflow.com/questions/67971977/control-m-does-not-get-error-from-stored-procedure)
- [Yordam çalıştı ama veri eksik](https://stackoverflow.com/questions/43537010/data-are-not-fully-written-to-database-when-run-control-m-python-job-executing-s)
- [Servis hesabının parolası değişince](https://stackoverflow.com/questions/40583259/control-m-batch-job-started-throwing-an-error-after-service-account-password-get)
- [.bat bittiği halde iş bitmiyor](https://stackoverflow.com/questions/15813159/control-m-job-not-ending-after-bat-finishes)
- [Döngüsel işin yeni güne taşması](https://stackoverflow.com/questions/40853745/control-m-avoid-cyclic-job-from-run-before-prev-days-complete)
- [Döngüsel iş hata verip durmuyor](https://stackoverflow.com/questions/46011693/control-m-cyclic-job-keeps-running-even-after-failure)
- [Aylık ve günlük iş arasında koşul](https://stackoverflow.com/questions/18328457/control-m-add-condition-between-a-monthly-and-a-daily-job)
- [Koşul adına eklenen sayı](https://stackoverflow.com/questions/66812246/control-m-out-condition-added-with-number-at-the-end)
- [İş planlamada var, izlemede yok](https://stackoverflow.com/questions/29526867/control-m-job-appears-in-planning-but-not-in-monitoring)
- [Ön koşul beklerken iş ne kadar planda kalır](https://stackoverflow.com/questions/63931524/how-long-does-a-control-m-job-stays-in-waiting-state-for-the-pre-requisites-to-b)
- [Belli saate kadar başlamazsa uyarı](https://stackoverflow.com/questions/54533685/control-m-email-alert-for-when-the-job-is-not-triggered-by-spefic-time)

## 8. Yerel hata çizgesi (sürüm 0.3)

Bölüm 5'teki tasarımın ilk hali kodda: `vardiya/graph.py` (SQLite üzerinde küçük bir özellik çizgesi, yalnızca
standart kütüphane), `vardiya/gecmis.py` (bir sitenin 90 günlük geçmişini üretir), `vardiya/cozumle.py` (çözümleme
ve erken uyarı). Önyüzde "Olaylar ve kök neden" ile "Erken uyarılar" bölümleri bunları gösteriyor.

- **Hepsi yerel.** Çizge bir SQLite dosyasında ya da bellekte durur; hiçbir şey makineden çıkmaz.
- **Kod kanıt toplar ve sıralar.** Bir hata için: hata imzası (sayılar, yollar ve tırnaklı değerler çıkarılmış
  şablon), aynı gün hata veren işlerin paylaştığı sunucu, kullanıcı, bağlantı ya da tablo, hatadan önceki üç gündeki
  tanım değişiklikleri, hata veren öncüller, aynı imzanın geçmişteki olayları, kök nedenleri, yapılan müdahale ve
  müdahalenin tutup tutmadığı. Bunlardan aday kök nedenler puanlanır.
- **Model yalnızca okur ve seçer.** Model bağlıysa kanıtı okuyup adaylardan birini seçer ve gerekçe yazar; listede
  olmayan bir aday reddedilir. Model bağlı değilken kodun sıralaması geçerlidir.
- **Geçmişten ders.** Aynı kök nedenli bir hata daha önce iki kez "yeniden çalıştır" ile kapatılıp geri geldiyse
  analiz bunu söyler ve doğrulanmış bir çözüm önerir.
- **Erken uyarı.** Süre eğilimi (Theil-Sen), aynı hatanın haftanın aynı gününde tekrarı ve kök nedeni giderilmeden
  kapatılmış olaylar.

Ölçüm: örnek geçmişteki 16 olayın 16'sında kodun ilk adayı, olayın kurulduğu kök nedendir. Bu bir başarı ölçüsü
değil, bağlantıların doğru kurulduğunun sınamasıdır: geçmişi ve hata kataloğunu aynı el yazdı. Gerçek bir ölçüm
için bench'in ikinci hattı (bölüm 5) ve gerçek bir zamanlayıcının geçmişi gerekiyor.

### 8.1 Forumdan gelen adminlik yetenekleri (sürüm 0.3)

Bölüm 7'deki sorunlar harness'e genelleştirilmiş çözücü olarak yüklendi: her olay sınıfı için hangi kanıta
bakılacağı, hangi adayların çıkacağı ve hangi müdahalenin işe yarayıp hangisinin yaramadığı. Küçük modele kalan iş
yalnızca adaylar arasında seçim ve gerekçe.

| Sorun (kaynak) | Harness'teki yetenek |
| --- | --- |
| Kaynaklar boşken iş kaynak bekliyor (BMC, 27 cevap) | Çizgede kaynak düğümleri; hata satırı kaynağı adlandırınca aday; çözüm: asılı kaydı serbest bırak, havuz sınırını yükseltme |
| Yama ya da yükseltme sonrası işler bozuluyor (BMC: MS yamaları sonrası sorun) | Sunucu düzeyinde değişiklik düğümü; hatadan önceki üç günde o sunucuya gelen yama aday olur |
| "Set OK" ile "gerçekten başarılı" ayrılmıyor (BMC, 2022'den beri açık istek) | Elle başarılı sayılan çalışmalar ayrı işaretli; ardılda veri hatası çıkınca ilk aday o çalışma; Raporlar sayfasında liste |
| Agent'ın kendi logları diski dolduruyor (BMC: XT_*.log 60 GB) | Sunucu başına disk serisi; eğilimle dolma süresi tahmini; 21 gün içinde dolacaksa erken uyarı |
| Döngüsel iş her düşüşte yeni olay açıyor (BMC) | Aynı iş ve aynı hata için açık olay varsa yeni olay açılmaz, çalışma ona eklenir |
| Son 7 günün tanım değişiklikleri, aylık hata raporu (BMC) | Raporlar: son değişiklikler, aylık hata sayıları, en uzun süren ve en çok zaman alan işler |
| Kontroller yokken girmiş tanımlar | Tanım sağlığı taraması: her iş yeni talep gibi denetlenir; takvim uyumsuzluğu, süre sınırsız dosya izleme, tanımdaki parola, aynı komutu çalıştıran iki iş |
| Kilit, parola dönüşü, saklı yordamın hatayı yutması, bitmeyen iş (Stack Overflow) | Bölüm 8'deki çözücüler |

Arıza sınıfları kod değil veri: `skills/olay-siniflari/SKILL.md` her sınıf için işaretleri, nedeni, doğru müdahaleyi, zararlı müdahaleleri ve bakılacak kanıt sorgularını tutuyor. Yeni bir sınıf eklemek kod yazmayı gerektirmiyor; listede olmayan bir kanıt sorgusuna başvuran sınıf yüklenmiyor. Her hata türü bir üründeki tek bir hata satırına değil, işaretlerine göre tanınıyor: kilit
için "lock", "resource busy", "55P03"; parola için "logon failure", "1326" gibi.

### 8.2 Olay bench'i: küçük model tek başına ve harness içinde

`python -m vardiya olay run --split test --model ollama:qwen3:8b`. Her vaka örnek geçmişteki bir olay; doğru kök neden
ve doğru müdahale bilinir. Üç kol aynı bilgiyle çalışır:

- **kod:** harness'in kodu, ilk aday ve önerilen müdahale.
- **raw_llm:** model tek başına; başarısız çalışma, iş, son 90 günün bütün hataları, değişiklikleri, Set OK'leri ve
  olayları düz metin olarak, varlık ve müdahale listeleriyle verilir.
- **harness_llm:** kod kanıtı toplar ve adayları sıralar, model birini seçer; müdahale seçilen adaydan gelir.

Puan: kök neden doğru mu, müdahale doğru mu, zararlı mı (Set OK, ya da yeniden çalıştırmanın veri bozacağı
olaylarda yeniden çalıştırma).

Ezbere karşı iki bölüm var. `dev`: çözücülerin yazıldığı adlar ve hata satırları. `test`: bütün iş, sunucu,
kullanıcı, tablo ve kaynak adları değiştirilmiş, her hata başka bir ürünün diliyle yazılmış (PostgreSQL kilidi,
Windows 1326 oturum hatası gibi).

İlk sonuç, yalnızca kod kolu: `dev` 22 olayın 22sinde, `test` 22sinin 22sinde doğru kök neden ve doğru müdahale (on dört arıza sınıfı).

Sınır: `test` bölümünün yeni adlarını ve hata yazımlarını da çözücüleri yazan el, aynı oturumda yazdı. Bu, adlara
ve tek bir hata satırına bağımlılığı sınıyor ama bağımsız bir sınama değil. Sıradaki adım: hata yazımlarını başka bir
modele yazdırmak (gün ifadelerinde `ext2` ile yapıldığı gibi) ve gerçek bir zamanlayıcının geçmişi.

## Kaynaklar

- [BMC: Automation API iş tipleri kod başvurusu (Control-M SaaS)](https://documents.bmc.com/supportu/controlm-saas/en-US/Documentation/API_CodeRef_JobTypes.htm)
- [BMC: Automation API iş tipleri (9.0.21)](https://docs.bmc.com/docs/automation-api/9021/job-types-1123726045.html)
- [Control-M Python istemcisi: iş tipleri](https://controlm.github.io/ctm-python-client/notebooks/jobtypes.html)
- [BMC: Control-M AI yetenekleri](https://documents.bmc.com/supportu/controlm-saas/en-US/Documentation/AI_Capabilities.htm)
- [BMC: Jett AI Assistant](https://documents.bmc.com/supportu/controlm-saas/en-US/Documentation/AI_Jett.htm)
- [SOS: JS7 iş sınıfları](https://kb.sos-berlin.com/display/JS7/JS7+-+Job+Classes)
- [SOS: JS7 iş şablonları ve JITL aileleri](https://kb.sos-berlin.com/display/JS7/JS7+-+Job+Templates)
- [SOS: JITL SQLExecutorJob](https://kb.sos-berlin.com/display/JS7/JS7+-+JITL+SQLExecutorJob)
- [SOS: JITL PLSQLJob](https://kb.sos-berlin.com/display/JS7/JS7+-+JITL+PLSQLJob)
- [SOS: JITL SQLPLUSJob](https://kb.sos-berlin.com/display/JS7/JS7+-+JITL+SQLPLUSJob)
- [SOS: JITL MailJob](https://kb.sos-berlin.com/display/JS7/JS7+-+JITL+MailJob)
- [SOS: JITL işlerinde kimlik deposu](https://kb.sos-berlin.com/display/JS7/JS7+-+Use+of+Credential+Store+with+JITL+Jobs)
- [JobScheduler, SourceForge](https://sourceforge.net/projects/jobscheduler/)
- [WorFBench](https://www.emergentmind.com/topics/worfbench-62d87cd5-dd6b-4000-80ec-cd6917dee44d)
- [SWE-InfraBench](https://www.alphaxiv.org/abs/2606.05249)
- [Multi-IaC-Bench](https://arxiv.org/pdf/2509.05303.pdf)
- [Don't Let the Model Write the YAML](https://www.alphaxiv.org/abs/2609.00227.md)
- [ITBench (ICML 2025)](https://proceedings.mlr.press/v267/jha25a.html)
- [AIOpsLab](https://arxiv.org/html/2501.06706v1)
- [Cloud-OpsBench](https://arxiv.org/html/2603.00468)
- [Çok veri kümeli mikroservis arıza teşhisi benchmarkı](https://arxiv.org/pdf/2606.29193)
- [ORCA-bench](https://www.alphaxiv.org/abs/2607.28545)
- [DBA-Bench](https://www.alphaxiv.org/abs/2607.22165)
- [Bankacılıkta eski sistemlerde üretken yapay zekâyla kök neden analizi](https://arxiv.org/pdf/2411.13017)
- [SynergyRCA: StateGraph ve LLM ile Kubernetes kök neden analizi](https://arxiv.org/html/2506.02490v1)
- [Grafana: LLM'e bağlam olarak bilgi çizgesi](https://grafana.com/blog/knowledge-graph-as-context-for-llms-demonstrating-decisive-rca-and-faster-production-performance)
- [GraphMind](https://www.alphaxiv.org/abs/2605.17617.md)
- [HPC işlerinde GCN ile iş sonucu tahmini](https://kdd.cs.ksu.edu/Publications/Conference/bose2021hpcgcn.pdf)
- [Küme işlerinin sonucunu tahmin için öznitelik seçimi](https://arxiv.org/pdf/2012.07982)
- [USPTO 11656932: tahmine dayalı toplu iş arızası tespiti](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11656932)
- [USPTO 12373250: gecikmeye katkı yapan işlerin yerelleştirilmesi](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12373250)
- [USPTO 12190166: toplu iş etkinliğini gözleme ve tahmin](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12190166)
- [Digitate: SLA tahmin ajanı](https://digitate.com/ai-agents/ai-agent-for-business-sla-predictions/)
- [Broadcom Automic: SAP SLA'larında tahmine dayalı analitik](https://academy.broadcom.com/blog/automation/automic-automation/predictive-analytics-gaining-certainty-for-mission-critical-sap-slas)
- [Rocket Software: SLA ihlallerini önceden tahmin](https://www.rocketsoftware.com/en-us/insights/sla-breaches-ai)
- [Alibaba cluster-trace-v2018](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2018/trace_2018.md)
- [Kamu bulutlarında toplu iş yükü izleri](https://arxiv.org/pdf/2111.08759)
