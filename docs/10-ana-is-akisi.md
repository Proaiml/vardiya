# Ana iş akışı ve nasıl ilerlenecek

16 Kasım 2026. Bu belge projenin geri kalanının nasıl yürütüleceğini anlatır: hedef, bugünkü durum, kim ne yapar,
aşamalar, kurallar ve "bitti" ölçütü. Çalışan herkes (orkestratör, işçi ajanlar) işe başlamadan önce bunu okur.

## Hedef

Usta'nın (harness içindeki yönetici ajanın) ürünü uçtan uca yönetebildiğini ve aynı modelin yardımsız hâlinden
belirgin biçimde üstün olduğunu, gerçek ortamda yapılmış ve kanıtı saklanmış denemelerle göstermek. Kapsam: yeni iş
tanımlama, çok işli ve çok tipli akışlar, tek talepte birden çok iş, var olan tanımı değiştirme, arıza teşhisi ve
giderme, yönetim işleri. En çok kullanılan iş tipleri: dosya aktarımı (AFT), komut ve betik (EXC), veritabanı (DBJ, DBO).

## Bugünkü durum

- **Ortam.** Canlı laboratuvar kurulu ve üç kopya çalışıyor (`docs/09-canli-saha-bench.md`). Zamanlayıcı JS7; yönetici
  ortamla Control-M Automation API sözdizimiyle konuşur. Gerçek Control-M kurulamadı: BMC'nin indirme sitesi kullanıcının
  hesabına açık değil. Hesaba şirketin abonelik numarası ve PIN'i girilirse açılır; o zamana kadar testler JS7'de.
- **Bench.** 16 geliştirme ve 30 gizli test senaryosu; hepsi iki yönden sınandı (kimse dokunmazsa doğru çıkmıyor,
  örnek çözümle doğru çıkıyor). Test kümesini harness'i görmeyen ayrı bir ajan yazdı.
- **Harness.** Usta'nın saha katmanı `saha-donuk-1` etiketiyle donduruldu.
- **İlk ölçüm (sürüyor).** Doğruluk iki kolda da tavana yakın: en hafif model yardımsız hâlde de senaryoların
  neredeyse tamamını çözüyor. Fark hızda: Usta aynı işi belirgin daha az adımda bitiriyor ve adım bütçesi daraldıkça
  fark açılıyor. Kart metnini modele vermek tek başına fark yaratmıyor; kazanç harness'in kendisinden geliyor.
- **Açık sorun.** Senaryolar doğruluk farkını göstermeye yetecek kadar zor değil. "Çok daha üstün" iddiası için daha
  zor koşullar gerekiyor (aşağıda Aşama 2 ve 3).

## Kim ne yapar

| Rol | Kim | İş |
| --- | --- | --- |
| Orkestratör | Ana oturum | Yönü belirler, işi dağıtır, ara sonuçları denetler, çözülemeyen sorunda devreye girer, kullanıcıya rapor verir. Kendisi mümkün olduğunca az iş yapar |
| Baş işçi | Opus ajanı | Ağır işler: ölçüm koşuları, zor küme, harness geliştirme, analiz, belgeler, commit |
| Senaryo yazarı | Sonnet ajanı | Gizli test senaryoları; harness'i ve kartları görmeden yazar ve sınar |
| Okuyucu | Haiku ajanı | BMC forumunu okur, taslak vaka çıkarır |

İşçi ajan ilerlemesini `docs/ilerleme.md` dosyasına yazar (ne yapıldı, ne ölçüldü, sırada ne var, takılınan yer).
Orkestratör bu dosyadan izler.

## Aşamalar

**Aşama 1: eldeki ölçümü tamamla.** Süren koşular biter; model servisinin kestiği bölümler yeniden koşulur. Gizli
test kümesi üç modelle (hafif model, hydrogen, zayıf model) ve üç kolla (yardımsız, kart metni, Usta) ölçülür. Çıktı:
`docs/09` içindeki sonuç bölümü, kanıt dosyaları, arayüzde görünen koşular.

**Aşama 2: kriz bütçesi.** Aynı senaryolar sıkı adım bütçesiyle (10 ve 15 adım) yeniden koşulur; bütçe iki kola da
baştan söylenir. Soru: süre darken kim işi bitirebiliyor? Çıktı: bütçeye göre doğruluk tablosu.

**Aşama 3: zor küme.** Gerçek sahaya daha yakın, daha zor senaryolar: konuyu adıyla söylemeyen talepler, kök nedeni
başka klasörde olan arızalar, aynı anda birkaç başarısız iş ve yanıltıcı ipuçları, çok işli kalabalık site, 8-10 işli
ayrıntılı tanım talepleri, kurum standardına uyması gereken tanımlar. Geliştirme yarısı harness'i ayarlamak için,
gizli yarısı ölçmek için. Gizli yarıyı yine harness'i görmeyen bir ajan yazar. Harness bu aşamada gelişirse yeni bir
etiketle dondurulur ve sonuçlar ilk dondurulan sürümden ayrı raporlanır.

**Aşama 4: rapor ve teslim.** Sonuç tabloları, eşli karşılaştırma, sınırlar, kanıtın nerede durduğu; README, devir
notu ve arayüz güncellenir; her şey commit edilip gönderilir.

**Aşama 5 (kullanıcıya bağlı): gerçek Control-M.** Yetki gelince Workbench imajı kurulur, `ctm_aapi.py` bağdaştırıcısı
gerçek sisteme karşı doğrulanır ve aynı senaryolar orada koşulur.

## Kurallar

- Ölçülen kümeye bakarak harness ayarlanmaz. Harness yalnızca geliştirme kümelerindeki bulgularla değişir; her
  değişiklikten sonra yeni etiket, sonuçlarda hangi etiketle ölçüldüğü yazılır.
- Yardımsız model ile Usta aynı araçlara ve aynı el kitabına sahiptir; harness modelin ulaşamadığı veriyi görmez.
- Sonuç olduğu gibi yazılır: fark yoksa "fark yok" denir, kesilen ya da kurulamayan bölüm sayısı verilir.
- Bir laboratuvar kopyasında aynı anda tek koşu (kilit dosyası bunu zorlar). Koşu temiz durdurulacaksa
  `results/saha/durum/DUR` dosyası kullanılır.
- Makine kuralları: `python.exe` süreçleri öldürülmez; ekran kartı kullanılmaz (modeller Antigravity üzerinden);
  `Desktop\harness` (Nöbetçi) deposuna dokunulmaz; başka projelerin Docker imajları silinmez.
- Her bölümün kanıtı `results/saha/<koşu>/` altında saklanır ve commit edilir.

## Yayın ölçütleri (16 Kasım 2026, İlhan)

Depo Apache 2.0 lisansıyla ancak aşağıdaki dördü gerçek ortamda, kanıtıyla gösterildiğinde herkese açılır. Kapı takvim
değil ölçüttür: gösterilemeyen madde açık yazılır ve yayın bekler.

| # | Beklenti | Nasıl ölçülür | Bugün |
| --- | --- | --- | --- |
| 1 | Karmaşık işleri ve birden çok ardıl işi tanımlar | Zor kümedeki 8-10 işli, çok tipli, klasörler arası olaylı tanım talepleri; her istek bir kontrol. Usta ile yardımsız model aynı senaryolarda | İlk kümede 5 işli akışlar var; iki kol da doğru, Usta çok daha az adımda. Zor küme yazılıyor |
| 2 | Karmaşık olanlar dahil sorunları zarar vermeden çözer | Bileşik ve yanıltıcı arızalarda doğru oranı; zararlı ve sahte yeşil sayısı Usta'da sıfır | İlk kümede zarar yok, doğruluk iki kolda da tavanda. Fark zor kümede aranacak |
| 3 | Kendi graf modeliyle sorunu oluşmadan fark eder | Canlı sitede öncü belirti senaryoları (dolmakta olan disk, süresi dolmak üzere hesap ya da anahtar, uzayan iş süresi, tekrarlayan hata imzası): arıza çıkmadan önce doğru uyarı ve yanlış alarm sayısı; yardımsız modelle karşılaştırma | Graf modeli metin bench'inde ön teşhis yapıyor; canlı ortamda erken uyarı kolu YOK |
| 4 | Kriz anında çok hızlı çözer; örnek: bir sunucuda ajan durmuş, sunucuya uzaktan bağlanıp ajanı yeniden başlatır | Adım bütçeli koşular; ajanın gerçekten durduğu ve sunucuya bağlanıp yeniden başlatılması gereken senaryolar | Adım bütçesi tablosu var (8 adımda Usta 9/13, yardımsız 2/13). Laboratuvarda ajan yeniden başlatılamıyor; senaryo işi başka ajana taşıyor |

"Ciddi atılım" şöyle okunur: aynı senaryolarda eşli karşılaştırmada fark açık olmalı (zor kümede en az 20 puan ya da
işaret testinde p < 0,05) ve Usta hiçbir senaryoda zarar vermemeli. Fark yalnızca hızda çıkarsa bu açıkça söylenir ve
yayın kararı İlhan'a bırakılır.

Uzaktan bağlantı: laboratuvar sunucuları Linux olduğu için canlı denemede bağlantı SSH ile yapılır. WinRM aynı eylemin
Windows karşılığıdır; Usta'nın genel yeteneklerinde yordamı vardır ama gerçek bir Windows sunucusu olmadan canlı
denenemez. Bu sınır raporda yazılır.

Bu ölçütler iki yeni iş doğurur (Aşama 3'e eklenir):

- **Ajan yeniden başlatma.** Ajan sunucularında ajan süreci, kap kapanmadan durdurulup başlatılabilmeli (bir hizmet
  betiği ve gözetici süreç); "ajan durdu" senaryoları: sunucuya bağlan, neden durduğunu bul, yeniden başlat, bağlandığını
  doğrula, bekleyen işleri yürüt.
- **Erken uyarı kolu.** Canlı siteden okunan geçmiş (iş süreleri, hata imzaları, disk doluluğu, hesap ve anahtar
  süreleri) çizgeye işlenir; mevcut graf modeli (`vardiya/gnn.py`) ve erken uyarı kodu bunun üstünde çalışır; öncü
  belirti senaryolarıyla ölçülür.

## "Bitti" ölçütü

1. Gizli test kümesinde üç model ve üç kolla tam ölçüm, kesilen bölümler tamamlanmış.
2. Kriz bütçesi koşulu ölçülmüş.
3. Zor küme yazılmış, sınanmış ve ölçülmüş; doğruluk farkı varsa gösterilmiş, yoksa açıkça söylenmiş.
4. Her senaryonun gerçekten koşulduğu ve hükmün sunucudan okunan değerlere dayandığı kanıt dosyalarından ve
   arayüzden görülebiliyor.
5. Belgeler ve depo güncel.
