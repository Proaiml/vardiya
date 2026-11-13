# Batch Operasyonları için Açık Ajan Harness'i: Saha Araştırması ve Ürün Tasarımı

13 Kasım 2026

## 1. Özet ve ürün tezi

Bu belge, Control-M ve benzeri iş yükü otomasyonu ürünlerinde adminlik yapan kişinin temel görevlerini güvenli ve başarılı biçimde yürüten, modelden bağımsız, açık bir ajan harness'inin saha araştırmasını ve ilk ürün tasarımını içerir. Çalışma adı olarak **Vardiya** kullanıyorum; ad değiştirilebilir.

**Ürün tezi:** Yetenek modelden değil, modelin etrafındaki kabuktan gelir. Kabuk işlerin topolojisini çıkarır, çizge üzerinde kesin hesap yapar, geçmiş olayları yerel bir deftere yazar ve her eylemi deterministik bir politika çekirdeğinden geçirir. Model, API anahtarıyla ya da yerelde bağlanan değiştirilebilir bir parçadır. Çizge hesabı yapar, model dili.

Araştırmadan tasarımı belirleyen dört bulgu çıktı:

| Bulgu | Kanıt | Tasarıma etkisi |
| --- | --- | --- |
| Harness etkisi ölçülmüş bir olgu | ARC-AGI-3'te aynı model (GPT-6 Astra) standart harness ile %62,7, sağlayıcı uyarlamalı harness ile %99,9 aldı. Değişen şey hafıza ve bağlam yönetimiydi. | Olay defteri ve bağlam derleyici yan özellik değil, çekirdek modül. |
| Operasyon alanında da aynı etki var | OpsHarness çalışmasında kök neden doğruluğu dört modelin ortalamasında %36,1'den %59,0'a çıktı; kazancın büyük kısmı geçmiş vakalardan öğrenmeden geldi. | Defter, doğrulama kapısından geçen vakalardan öğrenmeli. |
| Çıplak ajan operasyona hazır değil | ORCA-bench'te en iyi kök neden doğruluğu orta zorlukta %25,3, zor görevlerde %10,0. | Model serbest bırakılmaz; küçük sorular sorulur, hesap koda verilir. |
| Üretici alana girdi ama boşluk duruyor | BMC, Control-M için MCP sunucusu (önizleme), Jett ve bir korkuluk çerçevesi yayımladı. İncelediğim sayfalarda etki alanı hesabı, açık kaynak, kıyaslama ve sayısal kanıt yok. | Konumumuz: üreticiden bağımsız, açık, yerel model öncelikli ve ispatlı. |

Bir düzeltme: konuşmamızda geçen "60'tan 99'a" rakamı ARC Prize'ın yayımladığı sonuçla örtüşüyor, ama bu iki farklı harness'in karşılaştırması; harness'siz bir taban değil. Ders yine de güçlü: aynı model, yalnızca önceki akıl yürütmesini koruyup bağlamı sıkıştırabildiği için 37 puan kazandı. Yani fark yaratan şey hafızaydı ve bu, olay defteri sezgini doğrudan destekliyor.

## 2. Saha: ürünler ve admin'in gerçek işi

### Ürün ailesi

Hedef, tek bir ürün değil bir ürün sınıfı. Karşılaştırma kaynaklarında aynı sınıfta anılan ürünler: BMC Control-M ve Helix Control-M, Broadcom AutoSys, Redwood RunMyJobs, Stonebranch Universal Automation Center, Tidal, ActiveBatch, OpCon ve JAMS. Bunlara IBM Workload Scheduler ve Broadcom Automic de eklenir.

Kavramlar ürünler arasında büyük ölçüde örtüşür; bu, tek bir soyut arayüzün arkasına birden çok ürün bağlamayı mümkün kılar. Aşağıdaki eşleme genel alan bilgisine dayanıyor ve her bağdaştırıcı yazılırken ürünün güncel belgesiyle doğrulanmalı.

| Kavram | Control-M | AutoSys | IBM Workload Scheduler |
| --- | --- | --- | --- |
| İş grubu | Folder, SMART Folder | Box | Job stream |
| Bağımlılık | Event (eski adıyla condition) | `condition: s(is)` | `follows` |
| Kaynak kısıtı | Resource pool, lock resource | Resource, yük dengeleme | `needs` |
| Günlük plan | New Day, ODATE | Olay tabanlı, takvim | Plan, `JnextPlan` |
| Zorla başarılı sayma | Set to OK | `CHANGE_STATUS` ile SUCCESS | `confirm ...;succ` |
| Bekletme | Hold, Free | ON_HOLD, ON_ICE | `hold`, `release` |
| Tanım dili | JSON (Automation API) | JIL | Composer metni |

### Admin'in görev envanteri

BMC belgelerinden ve Automation API'nin Run servisinden çıkardığım görevleri sekiz aileye ayırdım. Ürünün kapsamı bu tablodur: her aile için en az bir skill olmalı.

| Görev ailesi | Tipik işler | Risk |
| --- | --- | --- |
| Gözlem | Durum izleme, viewpoint, uyarı takibi, log ve çıktı okuma | Yok |
| Teşhis | Bekleme nedeni analizi, komşuluk sorgusu, istatistik karşılaştırma, kök neden | Yok |
| Geri alınabilir müdahale | Hold, Free, uyarı durumunu güncelleme | Düşük |
| Koşullu müdahale | Rerun, Confirm, kaçan User Daily işlerini yeniden sıralama, kaynak havuzu güncelleme | Orta |
| Yüksek etkili müdahale | Set to OK, Kill, Run Now, Bypass, event ekleme ve silme | Yüksek |
| Tanım değişikliği | İş tanımı düzenleme, takvim, deploy, tutulan işi değiştirme | Yüksek |
| Platform sağlığı | Agent erişilebilirliği, New Day denetimi, temizlik ve saklama ayarları | Orta |
| Planlama ve raporlama | SLA servisleri, tahmin (forecast), kapasite, vardiya devri, denetim kaydı | Yok |

Tasarımı doğrudan etkileyen birkaç ayrıntı:

**Eylemler masum değil.** Belgeye göre Run Now işin ön koşullarını yok sayar, Bypass zaman ve kaynak kısıtlarını atlar, Set to OK ise işin son işlemlerini atlayabilir. Set to OK'in bağımlı işleri tetikleyip tetiklemediği sürüme ve parametreye göre değişebilir; bağdaştırıcıda doğrulanması gereken ilk nokta bu.

**New Day ayrı bir risk penceresi.** Varsayılan olarak 07:00'de çalışır; eski kayıtları temizler, günün işlerini yükler ve o sırada sunucu süreçleri yeniden başlar. BMC, bu pencerede etkin ortamı değiştiren araçların çalıştırılmamasını söylüyor. Politika çekirdeğinde bu pencere bir dondurma kuralı olmalı.

**Resmî API yeterince zengin.** Run servisi bekleme nedenini (`run job::waitingInfo`), bağımlılık komşuluğunu (öncül, bağımlı ya da çevresel yönde, derinlik sınırıyla), çalışma süresi istatistiklerini (`run job:statistics::get`), SLA servislerini ve tahmini açıyor. Topoloji motoru için gereken ham veri resmî arayüzden alınabiliyor; ekran kazımaya gerek yok.

**SLA tahmini ortalamaya dayanıyor.** Control-M her çalışmadan istatistik toplar, ortalama süreyi beklenen süre sayar ve servisin zamanında bitip bitmeyeceğini buna göre hesaplar. Bölüm 4'teki önerilerin çıkış noktası bu: ortalama, ay sonu gibi farklı gün tiplerinde yanıltır.

## 3. Sahada tekrar eden sorunlar

Önce bir sınır: BMC topluluk forumunun büyük kısmı girişe kapalı olduğu için doğrudan forum taraması sınırlı kaldı. Aşağıdaki sınıflandırma BMC belgelerine, bir danışmanlık blogundaki vaka anlatımına ve genel alan bilgisine dayanıyor. Sahadaki sıklık sıralamasını senin deneyiminle düzeltmemiz gerekir.

Her satır aynı zamanda bir bench senaryo ailesi ve bir skill adayıdır. "Yanlış hamle" sütunu, benchmark'ta tuzak olarak kurulacak kestirmedir.

| Belirti | Olası kök nedenler | Doğru yaklaşım | Yanlış hamle |
| --- | --- | --- | --- |
| İş "host bekliyor" durumunda kalıyor | Agent çalışmıyor, sunucu kapalı, ağ ya da güvenlik duvarı | Erişimi sına, agent durumunu doğrula, agent'ı başlat ya da sistem ekibine devret | Run Now ya da Rerun |
| İş "event bekliyor" | Öncül iş bitmedi, önceki güne ait event eksik, event elle silinmiş | Zinciri geriye doğru izle, ilk tıkanan düğümü bul | Öncülün gerçekten bittiğini doğrulamadan event eklemek |
| İş "kaynak bekliyor" | Havuz dolu, kaynağı tutan iş asılı kalmış | Kaynağı tutanı bul, onun durumunu çöz | Havuz üst sınırını körlemesine yükseltmek |
| Yükleme işi yarıda Ended Not OK | Veri hatası, bağlantı kopması, disk, kilit | Yarım veriyi temizle, sonra yeniden çalıştır | Temizlik yapmadan Rerun (mükerrer kayıt) |
| Dosya gelmedi ya da geç geldi | Kaynak sistem gecikmesi, yanlış dizin, yarım aktarım | Kaynağı doğrula, aşağı akışı beklet, sahibine haber ver | Boş ya da yarım dosyayla zinciri sürdürmek |
| İş normalden çok uzun sürüyor | Veri hacmi artışı, kilit, kaynak çekişmesi, takılma | Gecikmeyi SLA payıyla karşılaştır, asılı mı yavaş mı ayır | Çalışan işi öldürmek |
| Günün işleri yüklenmedi | New Day ya da User Daily kesintisi | Kaçan işleri listele ve yeniden sırala | İşleri tek tek elle sipariş etmek |
| İş yanlış günde çalıştı ya da çalışmadı | Takvim, tatil istisnası, ODATE uyumsuzluğu | Takvimi ve sipariş tarihini doğrula | Tanımı değiştirmeden elle çalıştırmak |
| Beklenen ya da zararsız hata | "Bugün veri yok" dönüş kodu, artık gereksiz iş | Gerekçeyi kanıtla, Set to OK ile zinciri sürdür | Gereksiz Rerun ya da zinciri bekletmek |
| Değişiklik sonrası hata | Yeni tanım, parametre ya da bağımlılık hatası | Son başarılı sürümle farkı çıkar, geri al | Belirtiyi tek tek yamamak |
| Aşağı akışta veri hatası | Dün yukarıda zorla başarılı sayılan iş | Zehirlenen dalı beklet, kaynağı düzelt, sırayla yeniden işle | Yalnızca hata veren işi yeniden çalıştırmak |
| Arıza yok, uyarı var | Eşik hatası, geçici dalgalanma | Hiçbir şey yapma, gerekçeyi yaz | Gereksiz müdahale |

"Host bekliyor" vakası sahadaki anlatımda şöyle çözülüyor: önce sunucuya ping, sonra agent portunun sınanması, yapılandırma yöneticisinde agent durumunun kontrolü, sunucu tarafında `ctmping`, agent makinesinde `ag_diag_comm` ve son olarak `start-ag`. Bu, bir skill'in tam olarak neye benzeyeceğini gösteriyor: sıralı, her adımı doğrulanabilir bir ayırıcı tanı.

Son iki satır özellikle önemli. "Beklenen hata" satırında doğru hamle, tehlikeli görünen Set to OK'tir; "arıza yok" satırında doğru hamle hiçbir şey yapmamaktır. Bu iki sınıf olmadan her şeye hayır diyen bir harness güvenli görünür. ORCA-bench de 1.079 görevinin 195'ini olaysız kontrol görevi olarak ayırmış; aynı oranı hedefleyebiliriz.

Karşılaştırma sitelerindeki kullanıcı puanlarında Control-M'in en zayıf alanları analiz ve görselleştirme ile API entegrasyonu olarak geçiyor. Bu, topoloji ve çıkarım katmanına gerçek bir ihtiyaç olduğuna işaret eden zayıf ama tutarlı bir sinyal.

## 4. Algoritmalar: topoloji, kritik yol, tahmin ve kök neden

İlke şu: deterministik hesaplanabilen hiçbir şey modele hesaplatılmaz. Aşağıdaki hesapların tamamı kodda çalışır; modele yalnızca sonuç ve gerekçe gider. Küçük modeller için yazılmış bir saha notu aynı sonuca varıyor: sıralamayı kod yapsın, modele tek karar kalsın.

| Yetenek | Yöntem | Modele giden çıktı |
| --- | --- | --- |
| Topoloji çıkarımı | İş tanımlarından ve event, kaynak, takvim ilişkilerinden yönlü çizge | "Bu işin 3 öncülü, 14 bağımlısı var" |
| Gizli bağımlılık | Geçmiş çalışma zamanlarından sıra madenciliği, sysout'taki dosya ve tablo adlarından veri soyu | "Tanımda yok ama bu iş hep X'ten sonra başlıyor" |
| Etki alanı | Bağımlılar üzerinde geçişli kapanış, SLA servis üyeliğiyle ağırlıklandırma | "Müdahale 14 işi, 2 kritik servisi etkiler" |
| Kritik yol | Topolojik sırada en uzun yol; bitiş tahmini ve pay (slack) | "Servis 05:40'ta biter, pay 20 dakika" |
| Süre tahmini | Ortalama yerine gün tipine göre medyan ve yüzde 90'lık dilim | "Ay sonunda bu iş genelde 48 dakika sürer" |
| SLA risk olasılığı | Çizge üzerinde Monte Carlo benzetimi | "Zamanında bitme olasılığı %72" |
| Yavaşlama tespiti | Sağlam taban (medyan ve MAD), eğilim için Theil-Sen, kırılma için CUSUM | "Bu iş üç haftadır her hafta %4 uzuyor" |
| Darboğaz | Bekleme ve çalışma süresinin ayrıştırılması | "Gecikmenin %80'i kaynak beklemesi" |
| İlk arıza yalıtımı | Sorunlu düğümler içinde, öncüllerinin hepsi sağlıklı olan en erken düğüm | "Kök aday: şu iş; diğer 6 uyarı sonuç" |
| Gecikme muhasebesi | Her işin kendi fazlasını (gerçek eksi beklenen) kritik yol boyunca paylaştırma | "40 dakikalık gecikmenin 31'i tek işten" |
| Sysout farkı | Log şablonu çıkarımı, son başarılı çalışma ile hatalı çalışmanın yapısal farkı | "Yeni satır: ORA-00054, 3. adımda" |
| Hata imzası | Şablonlaştırılmış hata satırının özeti; defterde arama anahtarı | "Bu imza daha önce 7 kez görüldü" |
| Değişiklik bağıntısı | Son başarılı çalışmadan beri değişen tanım, takvim, host, hacim | "Tek fark: dün deploy edilen parametre" |
| Kurtarma planı | En küçük yeniden çalıştırma kümesi ve sırası, işlerin idempotans sınıfına göre | "Önce temizlik, sonra şu 3 iş sırayla" |
| Ne olurdu benzetimi | Emülatörde planı ileri sarma | "Havuz 4'ten 6'ya çıkarsa bitiş 25 dakika öne gelir" |

Bunlardan beşi üzerinde durmak istiyorum, çünkü ürünü rakiplerden ayıracak olanlar bunlar.

**Ortalama yerine dağılım.** Control-M'in SLA hesabı ortalama süreye dayanıyor. Oysa paralel dalların birleştiği noktada beklenen bitiş, dalların ortalamalarının en büyüğü değil, en büyüklerinin ortalamasıdır; bu hiçbir zaman daha erken olmaz, çoğu zaman daha geçtir. Ortalamayla yapılan hesap sistematik olarak iyimserdir. Monte Carlo benzetimi bu yanlılığı giderir ve "zamanında biter mi" sorusuna evet ya da hayır yerine bir olasılık verir.

**Gecikme muhasebesi.** Zincir geciktiğinde operatörün asıl sorusu "kim geciktirdi" olur. Her işin kendi fazlasını hesaplayıp kritik yol boyunca toplamak, gecikmeyi işlere paylaştırır. Senin "en yavaş iş" ve "toplamda en çok zaman tüketen iş" örneklerin bu ailenin en basit üyeleri: biri tek çalışmanın süresi, diğeri sıklık çarpı süre. Üçüncüsü ve en değerlisi, kritik yoldaki payı en çok yiyen iştir.

**Gizli bağımlılık madenciliği.** Sahada her bağımlılık tanımda yazmaz; bazı işler aynı tabloyu kullanır ama aralarında event yoktur. Geçmiş çalışmalardan sıra örüntüsü ve sysout'tan veri soyu çıkarmak, tanımdaki çizgeyi gerçek çizgeye yaklaştırır. Etki alanı hesabı bu olmadan eksik kalır.

**İdempotans sınıfı.** Her iş üç sınıftan birine atanır: güvenle yeniden çalışır, temizlik sonrası yeniden çalışır, asla otomatik yeniden çalışmaz. Sınıf iş metadatasında durur; yoksa varsayılan en kısıtlı sınıftır. Bu tek alan, mükerrer kayıt riskini politika çekirdeğinin denetleyebileceği bir kurala çevirir.

**Sayısal ikiz olarak emülatör.** Bench için yazacağımız deterministik emülatör üründe ikinci bir iş görür: gerçek ortamın topolojisi ve istatistikleri yüklenince, bir eylemin sonucunu uygulamadan önce ileri sarıp gösterebilir. Etki alanı önizlemesi böylece sayımdan benzetime yükselir.

Bu alanda ticari faaliyet var: toplu iş süresi tahmini ve gecikmeye katkı yapan işlerin yerelleştirilmesi üzerine ABD patentleri yayımlanmış. Kullandığımız yöntemler ders kitabı düzeyinde olsa da, açık kaynak yayından önce bir uzmanın bakması yerinde olur; bu hukuki görüş değil, yalnızca bir işaret.

## 5. Ajan harness dünyasından dersler

**ARC-AGI-3: fark yaratan hafıza.** ARC Prize'ın 3 Eylül 2026 tarihli yazısına göre GPT-6 Astra, modelin seçtiği notları taşımasına izin veren standart harness ile %62,7, akıl yürütme durumunu istekler arasında koruyan ve uzun konuşmaları sıkıştıran sağlayıcı uyarlamalı harness ile %99,9 aldı. İkincisi aynı zamanda yaklaşık 3,66 kat hızlı ve %49 daha az token kullandı. Daha önce, Temmuz 2026'da, GPT-5.6 Sol için iki ayarın açılması skoru %13,3'ten %38,3'e çıkarmıştı. İki sonuçta da kazanan mekanizma aynı: model önceki işini yeniden kullanabiliyor.

**OpsHarness: en yakın akraba.** CUHK ve ByteDance'ten bir ekip, genel amaçlı ajanları kök neden analizinde uzmanlaştıran, kendini geliştiren bir dış harness yayımladı. Dört katmanlı bir bilgi deposu kullanıyor: genel alan bilgisi, hedef sistemin profili, vakalardan çıkarılmış iş akışı iskeletleri ve kurallar. Dört modelin ortalamasında doğruluk çıplak ajanda %36,1, harness'le %59,0. Soğuk başlangıç yalnızca 5,3 puan, vakalardan öğrenme ise 17,6 puan ekliyor. En önemli bulgusu şu: öğrenilen bilgiyi doğrulama kapısından geçirmeyen sürümde doğruluk 0,83'ten 0,33'e düşüyor, bir modelde sıfıra çöküyor. Bizden farkı: yalnızca mikroservis teşhisi yapıyor, eylem almıyor, güvenlik katmanı yok ve batch dünyasına dokunmuyor.

**ORCA-bench: çıplak ajanın sınırı.** 1.079 nöbet görevinde en iyi model orta zorlukta %25,3 doğruluk aldı. Belirlenen hata kalıpları tasarım girdisi: ajanlar en gürültülü belirtiye saplanıyor, şiddet değişimini olaylara bağlayamıyor ve telemetri sorgularının %26 ile %40'ı ya hata veriyor ya boş dönüyor. İlk arıza yalıtımı birinci soruna, hazır anlamsal gözlem araçları üçüncü soruna doğrudan cevap.

**OpenClaw ve ClawHub: açıklığın bedeli.** Koi Security, denetlediği 2.857 skill'in 341'inin kötü niyetli olduğunu, 335'inin tek bir kampanyaya ait olduğunu raporladı. Snyk'in incelediği örnekte zararlı kod skill dosyasında değildi; dosya kullanıcıyı dış bir indirmeye yönlendiriyordu. Belirlenen kök zayıflıklar: doğal dil talimatı klasik araçlarla taranamıyor, kurulan skill ajanın bütün yetkisini devralıyor ve yayıncı güven sinyalleri zayıf. Bizdeki karşılıkları Bölüm 8'de: skill çalıştırılabilir kod ve dış bağlantı taşıyamaz, yetki devralmaz, onaysız skill öneri seviyesinin üstüne çıkamaz.

**Agent Skills: hazır bir biçim var.** Anthropic'in başlatıp açık standart olarak yayımladığı biçimde bir skill, `SKILL.md` içeren bir klasördür; ad ve açıklama zorunludur ve skiller kademeli olarak yüklenir: önce yalnızca ad ve açıklama, eşleşince tam talimat. Bu biçimi temel alıp üstüne katı alanlar eklemek, katkıcıların zaten bildiği bir kalıbı kullanmamızı sağlar.

**Küçük modeller: beklentiyi doğru kurmak.** Qwen3-8B üzerinde üç rollü bir iskele, AppWorld'de başarıyı %5,4'ten %8,9'a çıkardı. Bu, dört kat büyük bir modelin %7,1'lik sonucunu sayısal olarak geçiyor, ama yazarlar o farkın 168 görevde istatistiksel olarak anlamlı olmadığını kendileri belirtiyor. İki ders çıkıyor. Birincisi, genel amaçlı iskele küçük modeli tek başına kurtarmaz; işi alana özgü deterministik koda kaydırmak gerekir. İkincisi, kendi bench'imizde anlamlı sonuç için yeterli görev sayısına ihtiyacımız var.

**BMC: üretici ne yaptı, neyi bıraktı.** Control-M 9.0.22 belgelerinde üç yetenek var: doğal dille sorun giderme ve raporlama yapan Jett, doğal dilden iş tanımı üreten AI Workflow Creator ve dış yapay zekâ istemcilerini bağlayan MCP sunucusu. MCP sunucusu durum, log ve çıktı okuyabiliyor; rerun, hold, release ve set to OK yapabiliyor. Yetki API token'ı ve rol yetkileriyle sınırlanıyor; eylem öncesi onay ise istemcinin bu özelliği desteklemesine bağlı. Sunucu önizleme aşamasında, en çok beş istemci ve dakikada 60 istek sınırıyla, üretim dışı kullanım için öneriliyor. BMC ayrıca sekiz maddelik bir korkuluk çerçevesi yayımlamış; kimlik, kapsam, onay, hazırlık, denetim izi gibi başlıklar içeriyor.

Bundan çıkan konum: BMC ajanı inşa etmiyor, kapıyı açıyor. Kapıdan giren modelin ne göreceği, nasıl düşüneceği, geçmişi nasıl hatırlayacağı ve bir eylemin mükerrer kayıt üretip üretmeyeceği açık duruyor. Vardiya bu boşlukta, BMC'nin MCP sunucusunun ya da Automation API'sinin üstünde çalışan katmandır; rakip değil, tamamlayıcıdır.

## 6. Ürün mimarisi: çekirdek modüller

Mimari iki katmanlı: az sayıda, yavaş değişen, sıkı denetlenen çekirdek modül ve onların üstünde hızlı büyüyen skill katmanı. Skiller çekirdeğin sunduğu fiilleri kullanır, yeni fiil ekleyemez.

| Modül | Sorumluluk | Temel sözleşme |
| --- | --- | --- |
| Bağdaştırıcı | Zamanlayıcıyla konuşur: emülatör, Control-M Automation API, sonra diğerleri | Ürün bağımsız okuma ve eylem fiilleri |
| Dünya modeli | Topoloji, istatistik ve Bölüm 4'teki türetilmiş olgular | Soru sorulur, kanıtlı olgu döner |
| Olay defteri | Vakaların, eylemlerin ve sonuçların yerel, yalnızca eklemeli kaydı | Yaz, imzayla ara, emsal getir |
| Politika çekirdeği | Yetki, ön uçuş denetimi, onay, geri alma | Her eylem önerisine izin, beklet ya da ret |
| Bağlam derleyici | Modelin bütçesine göre sıkıştırılmış durum paketi | Model profili girer, paket çıkar |
| Model geçidi | Herhangi bir modeli bağlar: API anahtarı ya da yerel sunucu | Şemaya bağlı girdi ve çıktı, onarım, yeniden deneme |
| Skill çalıştırıcı | Tetik eşleştirme, adım makinesi, doğrulama | Skill tanımı girer, denetlenmiş adımlar çıkar |
| Kanıt ve denetim | Her iddiaya kanıt bağlantısı, her koşuya yeniden oynatılabilir iz | İz, kanıt paketi, karar kaydı |
| Arayüzler | Komut satırı, operasyon kanalı, MCP sunucusu olarak dışa açılma | İnsan onayı ve rapor |

**Bir olayın yolculuğu.** Uyarı düşer. Dünya modeli anlık görüntü alır ve türetilmiş olguları hesaplar. Defterde hata imzası aranır, emsaller gelir. Tetik eşleşen skill seçilir. Bağlam derleyici, bağlı modelin bütçesine göre paketi hazırlar. Model sabit şemada bir öneri üretir. Politika çekirdeği öneriyi denetler: izin verir, insan onayına bekletir ya da reddeder. İzin çıkarsa bağdaştırıcı eylemi uygular, skill'in doğrulama koşulları sınanır, sonuç deftere yazılır ve operatöre kanıt bağlantılı rapor gider.

Bu akışta iki kural hiç bozulmaz. Model zamanlayıcıya hiçbir zaman doğrudan dokunmaz; yalnızca öneri üretir. Zamanlayıcı kimlik bilgileri modele hiç gösterilmez; token harness'te durur.

**Model geçidi.** Bir model eklemek üç bilgiyle olur: uç nokta, anahtar ve model adı. Geçit, yaygın sohbet tamamlama arayüzünü konuşan her sağlayıcıyı ve yerel sunucuyu aynı biçimde bağlar. Her model için bir yetenek profili tutulur: bağlam uzunluğu, araç çağırma güvenilirliği, şemaya uyum oranı ve ehliyet sınavı sonucu. Profil iki şeyi belirler: bağlam paketinin boyutu ve çalışma modu.

**İki çalışma modu.** Küçük modeli yükselten asıl mekanizma budur.

| | Yönlendirilmiş mod | Serbest mod |
| --- | --- | --- |
| Kim için | Küçük ve yerel modeller | Güçlü modeller |
| Akışı kim yürütür | Skill'in adım makinesi | Model, araçlarla planlar |
| Modele sorulan | Dar sorular: seçeneklerden birini seç, boşluğu doldur, özetle | Açık uçlu teşhis ve plan |
| Çıktı | Kısıtlı şema, sayılı seçenek | Yapılandırılmış öneri |
| Politika denetimi | Aynı | Aynı |

Yönlendirilmiş modda modelin hata yapabileceği alan daraltılır: çok adımlı planı kod yürütür, model her adımda tek karar verir. Saha notlarındaki gözlem de bu yönde: küçük model tek araçlık sorularda güvenilir, iki çağrıyı aklında tutup uzlaştırması gerektiğinde bozuluyor.

**Kodun payı.** Model bağlı değilken ya da çıktısı şemaya uymadığında skill deterministik dalını yürütür: teşhis paketini hazırlar, emsalleri ekler ve insana devreder. Bu hem ürünün alt sınırıdır hem de bench'te ayrı bir kol olarak harness'in tek başına katkısını gösterir.

**Dışa açılma.** Vardiya kendisini bir MCP sunucusu olarak da sunabilir. Böylece MCP konuşan herhangi bir istemci, zamanlayıcının ham fiilleri yerine Vardiya'nın denetlenmiş fiillerini kullanır ve onay istemcinin yeteneğine değil sunucu tarafındaki politikaya bağlı olur.

## 7. Olay defteri ve bağlam derleyici

Önerdiğin yerel olay defteri, araştırmanın en güçlü biçimde desteklediği fikir. ARC-AGI-3'te farkı önceki işin korunması yarattı; OpsHarness'te kazancın yaklaşık dörtte üçü geçmiş vakalardan geldi. Defter, küçük modeli yükselten ikinci mekanizmadır: model sıfırdan teşhis koymaz, emsali onaylar.

**Dört katman.** OpsHarness'in katmanlamasını batch dünyasına uyarlıyorum.

| Katman | İçerik | Kaynağı | Değişim |
| --- | --- | --- | --- |
| Alan bilgisi | Zamanlayıcı kavramları, durumlar, eylemlerin yan etkileri | Depoyla gelir | Sürümle |
| Ortam profili | Topoloji, süre tabanları, takvim, idempotans sınıfları, kritik servisler | Kurulumda ve her gece çıkarılır | Günlük |
| Vaka kayıtları | Her olayın belirtisi, teşhisi, eylemleri, sonucu, kanıtı | Çalışırken yazılır | Sürekli |
| Kurallar | Vakalardan damıtılmış "şu imzada şunu yap" bilgisi | Kapıdan geçen vakalardan terfi | Yavaş |

**Vaka kaydı.** Her kayıt şunları taşır: zaman ve sipariş tarihi, iş ve klasör, işin topolojideki konumu, durum, hata imzası, o anki türetilmiş olgular, konulan teşhis, önerilen ve uygulanan eylemler, politika kararları, doğrulama sonucu, çözüm süresi, operatörün hükmü ve kanıt bağlantıları. Kayıt kimin yaptığını da tutar: model, skill, insan.

**Arama, gömme vektörüne dayanmaz.** Emsal üç kademede aranır. Önce hata imzası ve iş kimliğiyle tam eşleşme, sonra yapısal benzerlik (aynı klasör, aynı arıza sınıfı, topolojide benzer konum), en son metin benzerliği. İlk iki kademe deterministiktir ve ek bir model gerektirmez; bu, kapalı ortamda ve zayıf donanımda çalışabilmenin koşulu. Gömme tabanlı arama isteğe bağlı bir eklenti olur.

**Defterin modele söylediği.** Tipik bir emsal paketi şöyledir: "Bu imza son doksan günde yedi kez görüldü. Altısında kök neden yukarı akıştaki dosya gecikmesiydi, birinde disk doluluğu. Altı vakada uygulanan çözüm aynı ve ortalama on iki dakikada doğrulandı. Bugünkü vaka altısıyla aynı topolojik konumda." Bu paketi alan küçük bir modelin işi, sıfırdan akıl yürütmek değil, bugünkü kanıtın emsalle uyuşup uyuşmadığını söylemektir.

**Doğrulama kapısı.** OpsHarness'in en net dersi burada: kapısız öğrenme sistemi bozuyor. Bir vaka ancak iki koşulla emsal olur: skill'in doğrulama koşulları sağlanmıştır ve operatör sonucu onaylamıştır. Doğrulanmamış vakalar kayıtta kalır ama emsal olarak sunulmaz. Kural katmanına terfi daha da sıkıdır: aynı örüntü birden çok doğrulanmış vakada tekrarlanmalı ve emülatörde karşı örnek üretmemelidir.

**Defter veridir, talimat değildir.** Sysout satırları ve geçmiş notlar modele her zaman alıntı olarak, ayrı bir bölmede verilir. İçlerindeki metin eylem tetikleyemez; eylemi yalnızca politika çekirdeğinden geçen yapılandırılmış öneri tetikler.

**Defterden çıkan analitik.** Aynı veri, vaka beklemeden çalışan raporları besler: en yavaş işler, toplamda en çok zaman tüketen işler, en sık hata verenler, giderek yavaşlayanlar, en çok kaynak bekleyenler, kritik yol payını en çok yiyenler, ortalama çözüm süresi. Bunlar haftalık bir sağlık raporu olur ve ajanı arıza gidericiden iyileştirme danışmanına taşır.

**Yerellik ve bütünlük.** Defter kurumun içinde, tek dosyalık gömülü bir veritabanında durur ve dışarı çıkmaz. Kayıtlar yalnızca eklenir ve her kayıt bir öncekinin özetini taşır; böylece sonradan değiştirme fark edilir ve defter denetim izi olarak da kullanılabilir.

**Sahadan bench'e köprü.** Topluluk skill paylaşır, defter paylaşmaz. Ancak bir kurum isterse bir vakayı anonimleştirme aracından geçirip sentetik topolojiye eşleyerek senaryo önerisi olarak gönderebilir. Gerçek arıza mekaniği böyle bench'e akar.

**Bağlam derleyici.** Defter ve dünya modeli çok şey bilir; model azını taşıyabilir. Derleyici, modelin profiline göre paketi kurar. Öncelik sırası sabittir: önce görev ve izinli seçenekler, sonra türetilmiş olgular, sonra en iyi emsal, sonra sysout farkı, en son ham ayrıntı. Dar bağlamlı modelde paket ilk üç kalemle biter; geniş bağlamlı modelde ham ayrıntı da girer. Her kalem kanıt bağlantısıyla gelir, böylece modelin çıktısındaki her iddia bir kaynağa bağlanabilir.

## 8. Skill katmanı

Skill, saha bilgisinin paketlenmiş hâlidir: bir admin'in "bu belirtide şunlara bakarım, şunu yaparım, şöyle doğrularım" bilgisi. Çekirdek modüller ürünün kemiğiyse skiller kasıdır ve topluluk burada büyür.

**Biçim.** Agent Skills standardını temel alıyorum: bir klasör, içinde ön bilgi bloğu ve talimat taşıyan bir `SKILL.md`. Üstüne makinece denetlenebilir alanlar ekliyorum. Standarttan bilinçli bir sapma var: topluluk skill'i çalıştırılabilir betik ve dış bağlantı taşıyamaz. ClawHub olayının kök nedeni tam olarak buydu.

```yaml
---
name: partial-load-safe-rerun
description: Yükleme işi yarıda Ended Not OK olduğunda mükerrer kayıt üretmeden toparlar.
trigger:
  status: ended_not_ok
  job_class: load
authority: L3
allowed_actions: [hold_downstream, run_cleanup, rerun]
preconditions:
  - idempotency_class != never_rerun
  - blast_radius.critical_jobs <= site.threshold
postconditions:
  - job.status == ended_ok
  - invariant.row_count_consistent
  - invariant.no_duplicates
evidence: [sysout_diff, target_table_count]
tests: [scenarios/partial-load-001, scenarios/partial-load-reverse-003]
---
```

Ön bilgi bloğunun altında adımlar düz yazıyla durur: neye bakılır, hangi bulgu hangi dala götürür, ne zaman insana devredilir. Yönlendirilmiş modda çalıştırıcı bu adımları bir durum makinesi olarak yürütür; serbest modda model bunları talimat olarak okur.

**Skill'in yapamayacakları.** Çekirdekte olmayan bir fiil kullanamaz. Beyan ettiğinden yüksek yetkiyle çalışamaz. Politika denetimini atlayamaz. Kendi doğrulama koşullarını sağlamadan vakayı çözülmüş sayamaz. Bu sınırlar skill'in metninde değil çalıştırıcıda uygulanır; kötü yazılmış ya da kötü niyetli bir skill en fazla işe yaramaz olur.

**Başlangıç seti.** Bölüm 2'deki görev aileleri ve Bölüm 3'teki arıza sınıflarından çıkan ilk skiller:

| Skill | Görev ailesi | Yetki |
| --- | --- | --- |
| Host bekleyen iş ayırıcı tanısı | Platform sağlığı | L1 |
| Event bekleyen işte zincir izleme | Teşhis | L0 |
| Kaynak çekişmesi çözümü | Teşhis, koşullu müdahale | L3 |
| Yarım yüklemede güvenli yeniden çalıştırma | Koşullu müdahale | L3 |
| Geciken dosyada aşağı akışı bekletme | Geri alınabilir müdahale | L2 |
| SLA riski değerlendirmesi | Teşhis, planlama | L0 |
| Uzun süren iş: asılı mı, yavaş mı | Teşhis | L1 |
| New Day ve kaçan User Daily denetimi | Platform sağlığı | L3 |
| Beklenen hatada gerekçeli Set to OK | Yüksek etkili müdahale | L4 |
| Zehirlenen dalın karantinası | Geri alınabilir müdahale | L2 |
| Değişiklik sonrası geri alma | Tanım değişikliği | L4 |
| Vardiya devir raporu | Planlama ve raporlama | L0 |
| En yavaş ve en pahalı işler raporu | Planlama ve raporlama | L0 |
| Kapasite için ne olurdu benzetimi | Planlama ve raporlama | L0 |

**GitHub onay akışı.** Eşik alçak, kapı yüksek.

| Kapı | Denetlenen | Kim |
| --- | --- | --- |
| Şema | Alanlar tam ve geçerli mi | Otomatik |
| Statik güvenlik | Yalnızca çekirdek fiilleri, dış bağlantı ve betik yok, yetki beyanı tutarlı | Otomatik |
| Senaryo | Skill en az bir doğru ve bir ters tuzak senaryosuyla geliyor mu | Otomatik |
| Senaryo geçerliliği | Bozuk durum kuruluyor, referans çözüm düzeltiyor, hiçbir şey yapmamak ve kestirmeler kalıyor | Otomatik |
| Marjinal kazanç | Skill kendi senaryosunda fark yaratıyor mu | Otomatik |
| Gerileme | Mevcut bench'te düşüş var mı | Otomatik |
| İnceleme | Saha doğruluğu ve açıklık | Bir bakımcı; çekirdek değişikliğinde iki |

Birleşen skiller sürümlenir ve imzalanır. Bir kurulum, kullandığı skilleri özetleriyle kilitler; depo güncellense bile kurumdaki davranış kendiliğinden değişmez.

**Yerel skiller.** Bir kurum kendi iç runbook'unu depoya göndermeden skill olarak yazabilir. Onaysız skill çalışır ama yetki tavanı öneri seviyesidir: teşhis koyar, eylem taslağı hazırlar, uygulamayı insana bırakır. Kurum bu tavanı kendi sorumluluğunda, açık bir politika kaydıyla yükseltebilir.

## 9. Güvenlik ve yetki modeli

Güvenlik iddiası modelden bağımsız olmak zorunda, çünkü hangi modelin bağlanacağını bilmiyoruz. Bu yüzden model güvenilmeyen bir öneri motoru sayılır ve güvenlik tek bir yerde, politika çekirdeğinde toplanır. Üç ilke: her eylem çekirdekten geçer, açıkça izin verilmeyen reddedilir, çekirdek küçük ve denetlenebilir kalır.

**Yetki seviyeleri.**

| Seviye | Anlamı | Örnek fiiller |
| --- | --- | --- |
| L0 Gözlem | Yalnızca okur | Durum, log, çıktı, bekleme nedeni, istatistik |
| L1 Öneri | Eylem taslağı hazırlar, insan uygular | Her eylemin taslağı |
| L2 Geri alınabilir | Etkisi tek adımda geri alınır | Hold, Free, uyarı güncelleme |
| L3 Koşullu | Ön uçuş denetimi geçerse uygular | İdempotent işte Rerun, Confirm, kaçan işleri sıralama |
| L4 Yüksek etkili | Her zaman insan onayı ister | Set to OK, Kill, Run Now, Bypass, event ekleme ve silme, tanım değişikliği |

**Yetki bir en küçük alma işlemidir.** Bir eylemin uygulanabileceği seviye; modelin ehliyeti, skill'in beyanı, kurumun politikası ve o anki pencerenin kısıtı arasındaki en düşük değerdir. Güçlü bir model zayıf bir skill'le ya da ay sonu dondurma penceresinde daha fazla yetki kazanmaz.

**Ön uçuş denetimleri.** L3 ve üstü her eylemden önce deterministik olarak çalışır.

| Denetim | Sorduğu |
| --- | --- |
| İdempotans | İşin sınıfı yeniden çalıştırmaya izin veriyor mu, temizlik yapıldı mı |
| Etki alanı | Etkilenen iş ve kritik servis sayısı eşiğin altında mı |
| Dondurma penceresi | New Day, ay sonu ya da ilan edilmiş değişiklik yasağı var mı |
| Sipariş tarihi | Eylem doğru günün örneğine mi uygulanıyor |
| Döngü koruması | Aynı eylem bu işte yakın zamanda denendi ve başarısız mı oldu |
| Hız sınırı | Birim zamanda eylem sayısı aşıldı mı |
| Kanıt | Önerinin dayandığı her iddia bir kanıta bağlı mı |

**Kanıtsız iddia yok.** Gözcü'den taşınan ilke budur. Modelin teşhisi ve önerisi; iş kimliği, sysout satır aralığı, sorgu sonucu ya da ekran bağlantısı taşımak zorundadır. Çekirdek, kanıt bağlantısı olmayan ya da bağlantısı gösterdiği veriyle uyuşmayan öneriyi reddeder. Operatör modelin sözüne değil, tıklayıp doğrulayabildiği bağlantıya güvenir.

**Geri alma.** Tanım değişikliklerinden önce anlık yedek alınır; değişiklik sonrası doğrulama koşulları sağlanmazsa tanım kendiliğinden eski hâline döner. Çalışma zamanı eylemlerinde her fiilin bir telafi fiili kayıtlıdır; telafisi olmayan fiiller tanım gereği L4'tür.

**Gölge mod.** Kurumlar özerkliğe bir günde geçmez. İlk aşamada Vardiya yalnızca izler ve önerir; insan operatörün gerçekte yaptığıyla önerisi karşılaştırılır ve uyum oranı ölçülür. Bu hem güven oluşturur hem de defteri doğrulanmış vakalarla doldurur. Yetki, ölçülen uyuma göre kademeli açılır.

**Derinlemesine savunma.** Vardiya'nın zamanlayıcıda kullandığı hesap, en az yetkili role bağlanır. Böylece çekirdekte bir hata olsa bile ürünün kendi rol yetkileri ikinci duvar olarak kalır. Ek olarak acil durdurma anahtarı tek hamlede bütün eylemleri öneri seviyesine indirir.

**BMC'nin yaklaşımından farkı.** BMC'nin MCP sunucusunda eylem öncesi onay, istemcinin bu özelliği desteklemesine bağlı ve denetim ürünün rol yetkileriyle sınırlı. Vardiya'da onay sunucu tarafında zorunludur ve rol yetkisinin üstüne alan bilgisi eklenir: aynı role sahip iki eylemden biri idempotent işe, diğeri finansal aktarıma dokunuyorsa farklı muamele görürler.

## 10. Bench ve ispat

Bench üründen ayrı bir proje değil, ürünün üç yerinde çalışan bir parça: skill onayında kapı, model bağlanırken ehliyet sınavı, yayında kanıt.

**Üç ispat hattı.**

| Hat | İddia | Yöntem | Başarı ölçütü |
| --- | --- | --- | --- |
| Güvenlik | Hangi model bağlanırsa bağlansın yasak eylem gerçekleşmez | Model yerine rastgele, düşmanca ve enjeksiyonlu sahte ajanlarla kitlesel deneme | Sıfır değişmez ihlali |
| Yetkinlik | Harness, model merdiveninin her basamağında başarıyı yükseltir ve modeller arası farkı daraltır | Aynı senaryo, aynı tohum, farklı kollar; eşleştirilmiş karşılaştırma | Güven aralıklı etki büyüklüğü |
| Katkı | Her skill ve her defter katmanı ölçülebilir fark yaratır | Birleştirme öncesi marjinal kazanç, sonrasında ablasyon | Skill başına kazanç, gerileme yok |

**Kollar.** Yetkinlik hattında altı kol öneriyorum. Her kol bir öncekine tek bir şey ekler; böylece kazancın nereden geldiği ayrışır.

| Kol | İçerik | Ölçtüğü |
| --- | --- | --- |
| Ham | Zamanlayıcının ham fiilleri ve veritabanı erişimi | Taban |
| Ham ve runbook | Aynı disiplin düz metin talimat olarak | Yalnızca öğüdün etkisi (plasebo) |
| Harness'in kod payı | Deterministik dallar, model yok | Harness'in tek başına katkısı |
| Harness, soğuk | Dünya modeli, politika çekirdeği, skiller; defter boş | Yapının katkısı |
| Harness, ılık | Aynısı, defter önceki vakalarla dolu | Hafızanın katkısı |
| Harness, serbest mod | Güçlü modeller için yönlendirmesiz | Yönlendirmenin bedeli ya da kazancı |

Ilık kol için vakalar zamana göre bölünür: defter ilk dilimle doldurulur, ölçüm son dilimde yapılır. OpsHarness aynı ayrımı kullanıyor ve bu, defterin sınav sorularını ezberlediği itirazını kapatır.

**Sonuç sınıfları.** Tek bir başarı oranı yerine dört sınıf: doğru çözüm, sahte yeşil (iş yeşil ama değişmezler bozuk), güvenli başarısızlık (çözemedi ama dokunmadı ya da devretti), yıkıcı başarısızlık. Olaysız kontrol görevlerinde beşinci bir ölçü eklenir: gereksiz müdahale oranı.

**Totolojiye karşı.** Harness'in kazancı tanım gereği olmasın diye dört kural: harness ham kolun ulaşamadığı veriye bakamaz; plasebo kolu öğüdün etkisini ayırır; ters tuzak senaryoları her şeye hayır diyeni cezalandırır; harness'in özeti dondurulduktan sonra eklenen senaryolar ayrı raporlanır.

**Yeniden oynatılabilirlik.** Emülatör deterministiktir: benzetilmiş saat, tohum, anlık durum. Hüküm; senaryo özeti, harness özeti ve eylem izinin saf fonksiyonudur. İsteyen, model anahtarı olmadan izi yeniden oynatıp aynı hükme ulaşır.

**Model merdiveni.** En az dört basamak: küçük yerel model, orta yerel model, orta ölçekli API modeli ve güncel bir sınır modeli. Manşet figür iki eğridir: ham ve harness'li. Beklenti, aradaki açıklığın küçük modelde en geniş olması; sınır modelde kazancın sıfıra yaklaşması ya da yönlendirmenin bedelinin görünmesi de raporlanacak bir sonuçtur.

**Örneklem.** Küçük model iskelesi çalışmasında 168 görev, iki sistem arasındaki 1,8 puanlık farkı anlamlı kılmaya yetmedi. Elle yazılmış yirmi senaryo bize de yetmez. Çözüm parametrik ailelerdir: arıza mekanizması, üretilmiş topoloji ve yüzey parametrelerinin çarpımı. On iki arıza sınıfından onar örnek, tohum başına tekrarlarla, eşleştirilmiş tasarımda makul bir başlangıçtır; kesin sayıyı pilot koşunun varyansı belirlemeli.

**Ehliyet sınavı.** Yeni bağlanan model bench'in sabit bir alt kümesini koşar. Çıkan profil üç şeyi belirler: çalışma modu, bağlam paketinin boyutu ve yetki tavanı. Sınavı geçemeyen model reddedilmez; öneri seviyesinde, yönlendirilmiş modda çalışır.

**Dış geçerlilik.** "Oyuncak benzetici" itirazına karşı küçük bir senaryo alt kümesi gerçek bir açık kaynak zamanlayıcıya ve mümkünse salt okunur bir Control-M ortamına taşınır; sonucun aktarıldığı gösterilir.

## 11. Yol haritası

Süre vermiyorum; sıra ve her aşamanın kanıtı önemli.

| Aşama | İçerik | Bittiğinin kanıtı |
| --- | --- | --- |
| 0. Dikey dilim | Deterministik emülatör, bağdaştırıcı arayüzü, dünya modelinin çekirdeği (kapanış, kritik yol, ilk arıza yalıtımı), beş fiilli politika çekirdeği, defterin ilk sürümü, tek skill (yarım yüklemede güvenli yeniden çalıştırma) | 03:00 sahnesi iki kolda koşar: ham model Set to OK basar ve sahte yeşil olarak yakalanır; harness'li küçük yerel model temizleyip doğrular |
| 1. Genişlik | On iki arıza ailesi için parametrik üreteç, başlangıç skill seti, model geçidi ve iki çalışma modu, sahte ajanlarla güvenlik hattı | Sıfır ihlal raporu; dört basamaklı merdivende ilk eğriler |
| 2. Hafıza | Defterin dört katmanı, emsal arama, doğrulama kapısı, bağlam derleyici, analitik raporlar | Ilık kol soğuk kolu zamana göre bölünmüş testte geçer |
| 3. Gerçek ortam | Control-M Automation API bağdaştırıcısı salt okunur gölge modda, MCP sunucusu olarak dışa açılma, operasyon kanalı arayüzü | Gerçek ortamda topoloji çıkarımı ve operatörle uyum oranı |
| 4. Açılış | Açık depo, katkı kılavuzu, onay hattı, anonimleştirme aracı, makale | Dışarıdan ilk skill ve senaryo birleştirmesi |

Aşama 0 bilinçli olarak dar: tek senaryo, tek skill, iki kol. Amacı mimarinin bütün katmanlarından bir kez geçip sözleşmeleri sınamak. Emülatör ve politika çekirdeği sonraki her şeyin dayandığı iki parça olduğu için önce onlar sağlamlaşmalı.

## 12. Açık sorular ve kaynaklar

**Senin cevabını bekleyenler.**

Sahada en sık gördüğün on arıza hangileri ve Bölüm 3'teki tablo bunları karşılıyor mu? Forum taraması sınırlı kaldığı için bu tablonun gerçek sıklık sıralaması senin deneyimine bağlı.

Gözcü'de ekran bağlantılarını kim ekliyor, kim denetliyordu? Kanıt zorunluluğunun tasarımı buna göre incelecek.

Adaptörü sınamak için salt okunur da olsa bir Control-M ortamına erişimin var mı? Yoksa Aşama 3 açık kaynak bir zamanlayıcıyla başlar.

Çalışma adı: belge yazılırken Nöbetçi idi; aynı adlı NOC izleme projesiyle çakıştığı için Vardiya yapıldı. Control-M erişimi sorusunun cevabı: yok, dış geçerlilik ücretsiz bir zamanlayıcıyla sınanacak.

**Doğrulanması gerekenler.**

Set to OK'in bağımlı işleri tetikleme davranışı sürüme ve parametreye göre değişebilir; incelediğim sayfa yalnızca son işlemlerin atlandığını söylüyor.

Bölüm 2'deki ürünler arası kavram eşlemesi genel alan bilgisine dayanıyor; her bağdaştırıcıda güncel belgeyle sınanmalı.

BMC'nin MCP sunucusunun sınırları ve önizleme durumu 9.0.22 belgesine göre; hızlı değişen bir alan.

Toplu iş tahmini alanındaki patentler için yayından önce uzman görüşü alınmalı. Lisans için başlangıç önerim Apache 2.0, ama bu da hukuki görüş değil.

ARC-AGI-3, OpsHarness, ORCA-bench ve BMC duyuruları bilgi kesim tarihimden sonraya ait; rakamları doğrudan kaynak sayfalarından aldım, kendi bilgimle çapraz doğrulayamadım.

**Kaynaklar.**

- [ARC Prize: OpenAI GPT-6 Astra on ARC-AGI-3](https://arcprize.org/blog/astra)
- [GIGAZINE: GPT-5.6 Sol ve ARC-AGI-3'te iki ayar](https://gigazine.net/gsc_news/en/20260731-how-enabling-two-settings-tripled-arc-agi-3-benchmark/)
- [OpsHarness: From General Agents to RCA Experts](https://arxiv.org/pdf/2608.25661)
- [ORCA-bench: How Ready Are Language Model Agents for Oncall?](https://www.alphaxiv.org/abs/2607.28545)
- [Three Roles, One Model (Qwen3-8B, AppWorld)](https://arxiv.org/html/2604.11465v1)
- [Designing MCP tools for a 7B model](https://dev.to/binushefieldshifani/designing-mcp-tools-for-a-7b-model-not-a-70b-one-4ffg)
- [eSecurity Planet: ClawHub'da kötü niyetli skiller](https://esecurityplanet.com/threats/hundreds-of-malicious-skills-found-in-openclaws-clawhub)
- [Snyk: clawdhub kampanyası](https://snyk.io/articles/clawdhub-malicious-campaign-ai-agent-skills/)
- [Agent Skills açık standardı](https://agentskills.io/)
- [BMC: Control-M AI yetenekleri (9.0.22)](https://documents.bmc.com/supportu/9.0.22/en-US/Documentation/AI_Capabilities.htm)
- [BMC: Control-M MCP Server](https://documents.bmc.com/supportu/9.0.22/en-US/Documentation/MCP_Server.htm)
- [BMC: Execution Guardrails for AI Agents](https://www.bmc.com/it-solutions/agentic-orchestration/execution-guardrails-ai-agents.html)
- [BMC duyurusu, 18 Mart 2026](https://www.bmc.com/newsroom/releases/bmc-advances-trusted-ai-orchestration-with-new-control-m-capabilities.html)
- [BMC duyurusu, 14 Temmuz 2026](https://www.bmc.com/newsroom/releases/bmc-brings-governed-ai-agents-to-enterprise-workflows-and-mainframe-operations.html)
- [BMC: Automation API Run servisi](https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_RunService.htm)
- [BMC: New Day Procedure](https://documents.bmc.com/supportu/9.0.21/en-US/Documentation/New_Day_Procedure.htm)
- [BMC: Job actions](https://controlm.wisconsin.gov/help/Main_Help/en-US/8479.htm)
- [BMC: SLA Management](https://documents.bmc.com/supportu/9.0.20/help/Main_help/en-US/681.htm)
- [BMC: Monitoring](https://documents.bmc.com/supportu/API/Helix/en-US/Documentation/Monitoring.htm)
- [dbi services: wait host durumundaki iş](https://www.dbi-services.com/blog/control-m-em-job-in-wait-hosts-status/)
- [AIMultiple: Control-M alternatifleri](https://aimultiple.com/controlm-alternatives)
- [USPTO 12327134: toplu süreç tahmini](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12327134)
- [USPTO 12373250: gecikmeye katkı yapan işlerin yerelleştirilmesi](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12373250)

## 13. Sohbet dökümünden eklenenler

13 Kasım 2026'da bu belge, ilk sohbetin dökümüyle karşılaştırıldı. Aşağıdakiler sohbette konuşulmuş ama
yukarıdaki bölümlere girmemişti. Ürünler ve benchmarklar hakkındaki bilgiler sohbette geçtiği gibi aktarıldı;
ayrıca doğrulanmadı.

### Dış geçerlilik için açık kaynak adaylar

Bölüm 10 "gerçek bir açık kaynak zamanlayıcı" diyor ama ad vermiyor. Sohbette dört aday konuşuldu:

| Ürün | Lisans | Control-M'e yakınlık | Not |
| --- | --- | --- | --- |
| JS7 JobScheduler | GPLv3 | En yüksek | Notice Board (condition), Resource Lock (kaynak), File Order Source (dosya izleme), Daily Plan (ODATE, New Day), Resume ve Mark as Resolved (Rerun, Set to OK). Docker Compose ile Controller, Agent ve Cockpit. |
| Kestra | Apache 2.0 | Yüksek | Tanımlar YAML, tek konteyner. ODATE ve condition semantiği yerleşik değil. |
| Rundeck | Apache 2.0 | Orta-yüksek | Runbook ve uygulama operasyonu odaklı; `rd` komut satırı, düğümlere SSH. |
| Apache Airflow | Apache 2.0 | Orta | DAG'lar Python kodu; Clear ve Mark Success ile durum değiştirme. |

Verilen karar: çekirdek motor bunlardan biri olmaz, çünkü gerçek orkestratörler duvar saatiyle ve asenkron çalışır,
birebir yeniden oynatılamaz. Çekirdek deterministik emülatördür; küçük bir senaryo alt kümesi önce JS7'ye taşınıp
sonucun aktarıldığı gösterilir. JS7 eşlemesi doğrulanmadı; özellikle Set to OK'in karşılığı birebir olmayabilir.

### Laboratuvar mimarisi

Dış geçerlilik ortamı üç parçadan oluşur: orkestratör konteyneri, hedef sistem konteyneri (PostgreSQL ve basit iş
betikleri; arıza buraya enjekte edilir) ve harness. Bundan çıkan tasarım sonucu: satır sayısı, mükerrer denetimi ve
temizlik zamanlayıcının değil hedef sistemin fiilleridir. Bağdaştırıcı sözleşmesi ikiye ayrılmalı: zamanlayıcı
bağdaştırıcısı ve veri sondası. Aşama 0 kodunda ikisi tek bağdaştırıcıda duruyor.

### Kapsam: uygulama katmanı operasyonu

İlk çerçeve L2/L3 uygulama operasyonunu da (servis yeniden başlatma, yapılandırma düzeltme, log temizleme)
içeriyordu. Sonraki mesajda hedef "zamanlayıcı admininin temel görevlerinin tamamı" olarak verildi ve bu belge onu
esas aldı. Uygulama katmanı arızaları kök neden olarak teşhis edilir, ama müdahalesi insana ya da ilgili ekibe
devredilir. Bu daraltma açıkça onaylanmadı; karar İlhan'ın.

### Konum: mevcut benchmarklar

Sohbetteki çıkış noktası: ITBench, DBA-Bench ve AIOpsLab bulut-yerel dünyaya (Kubernetes, mikroservis) odaklanır;
DAG tabanlı toplu iş orkestrasyonu için açık bir benchmark yoktur. Bölüm 5 yalnızca ORCA-bench ve OpsHarness'i
anıyor; yayından önce bu üçü de incelenip konum cümlesi doğrulanmalı.

### İspat tarafında eksik kalanlar

- **Ön kayıt.** Hipotezler ve analiz planı koşulardan önce depoya işlenir.
- **Yanlış engelleme oranı.** Ters tuzak senaryolarında doğru hamleyi engelleyen harness için ayrı ölçü.
- **Hüküm üçlüsü.** Hüküm; senaryo özeti, harness özeti ve eylem izinin fonksiyonudur. Aşama 0 kodunda yeniden
  oynatma yalnızca senaryo ve izi kullanıyor, harness özeti kaydedilmiyor.
- **Ablasyon ekseni.** Dört yetenek üzerinden: etki alanı önizlemesi, ön uçuş kapısı, anlamsal gözlem araçları,
  tanım sürümleme ve geri alma.
- **Sıra değişmezi.** Değişmezler aşağı akışın tetiklenme sırasını da doğrulamalı; kodda yalnızca durum, satır sayısı,
  mükerrer ve tutar eşitliği var.
- **Güvenlik hattının ölçeği.** Hedef rastgele, düşmanca ve enjeksiyonlu sahte ajanlarla milyonlarca eylem dizisi.
  Kodda yalnızca rastgele ajan ve birkaç bin dizi var.

### Emülatörün modellemesi beklenen semantik

Sohbette sayılanlar: ODATE, New Day, SMART Folder, condition, kaynak havuzu, takvim, sysout. Aşama 0 kodunda
condition, host, kaynak havuzu, hold ve sysout var; ODATE tek sabit tarih, New Day, takvim ve klasör yok.

### OpenClaw'dan alınan ürün dersleri

Bölüm 5 yalnızca güvenlik dersini anlatıyor. Sohbette üç ürün dersi de çıkarıldı: skill tek dosyadır ve saha
operatörü onu on dakikada yazabilmelidir; ajan kullanıcının zaten bulunduğu operasyon kanalında yaşar (uyarı düşer,
cevap aynı yere kanıt bağlantılarıyla gelir); konuşmaz, iş bitirir.
