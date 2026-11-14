# İş Tipleri, Benchmarklar ve Olaydan Önce Davranmak

14 Kasım 2026. Üç soruya cevap: (1) Control-M'de hangi iş tipleri var, JS7'de kaçı tanımlanabiliyor, Vardiya'da
kaçı var; (2) dünyada iş tanımı, değişikliği, silinmesi ve kaydı için ya da adminlik olayları için bir benchmark
var mı; (3) geçmişi bir çizgeye yazıp modele bağlam olarak vermek ve olaydan önce tahmin yapmak için ne biliniyor,
Vardiya'ya nasıl girer.

Kaynaklar sonda. Ürün belgeleri resmî sayfalardan okundu; makale ve satıcı rakamları kaynağın kendi iddiasıdır,
bağımsız doğrulanmadı. BMC topluluk forumu girişe kapalı olduğu için forum taraması yapılamadı (Bölüm 6).

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
