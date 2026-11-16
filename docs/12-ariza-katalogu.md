# Arıza kataloğu ve senaryo üreteci

16 Kasım 2026. Canlı bench'in (`docs/09-canli-saha-bench.md`) 16 elle yazılmış senaryosu yönetici ajanın başarılı
müdahalelerini göstermeye yetmiyordu: sahada her gün başka bir arıza görülüyor. Bu belge, sahadaki olay çeşitliliğini
canlı laboratuvara taşıyan **arıza kataloğunu** (`vardiya/saha/katalog.py`) ve ondan senaryo üreten üreteci anlatır.
Önceki işin üstüne kurulur: emülatörün 13 arızası (`vardiya/opsworld.py`, `docs/08-mudahale-kolu.md`) ve forum vakaları
(`bench/ops/dev.jsonl`, `bench/ops/aday/forum-2026-11-16.jsonl`) kataloğun ilham kaynağıdır; her arıza hangisinden
geldiğini `kaynak` alanında taşır.


> **Durum (16 Kasım gecesi, yarım iş).** Katalog ajanı 15:42'deki yeniden başlatmada durduruldu ve geri dönmedi; bu
> belge, `vardiya/saha/katalog.py` ve kümeler olduğu hâliyle commit edildi. `katalog-dev` (30) doğrulanmıştı.
> `katalog-test` (60) doğrulaması yeniden başlatmada yarım kaldı; baş işçi onu `dogrula --atla` ile tamamladı
> (`dogrula-katalog-test-son`, önceki yarım doğrulamaların satırları üzerine): 59 senaryo iki yönden geçti, biri
> (`k2-55-host-ajan-kapali-tasi-aft-parola-degisti`) geçmedi: örnek çözüm yalnızca "yarım" çıktı. Bu senaryo
> doğrulanmamış sayılır, düzeltilmedi. Ölçüm: `katalog-test --parca 1/2` (30 senaryo) `saha-donuk-2` ile bir kez;
> sonuçlar `docs/09`'da. `katalog-dev` ile harness ayarı yapılmadı.

## Ne var

- **45 canlı arıza** (+ 2 kabuk servisi arızası, aşağıda). Her arıza laboratuvarda gerçekten üretilir: parola
  değişir, anahtar izni bozulur, oturum kilit tutar, disk dolar, ana bilgisayar anahtarı değişir, ajan sunucusu kapanır.
- **Üreteç** (`uret(tohum, adet, bilesik_oran=0.3)`): tohumla arıza ve bağlam (klasör, iş adları, sunucu, karşı hesap,
  dosya öneki, tutar katsayısı) seçer; yüzde 30'u birbirini ortaya çıkaran iki arızayı birleştirir; talep metnini
  isteyenin ağzından yazar ve kök nedeni söylemez. Çıktı `kosu.py`nin anladığı sıradan senaryo JSON'udur.
- **Doğrulama:** `kosu.py dogrula` ile iki yönlü sınanır: kimse dokunmazsa `doğru` ya da `zararlı` çıkmaz, referans
  çözüm `doğru` çıkar. Bu iki koşulu sağlamayan senaryo kümeye girmez.

Her senaryoda iki ek alan vardır: `"kaynak"` (ilham veren emülatör arızası ya da forum vakası) ve `"ariza"` (arıza
kimlikleri; birleşikte iki tane).

## Arıza listesi

`Küme` sütunu: `dev ve test` arıza her iki kümede çıkabilir; `yalnız test` arıza geliştirme kümesinde hiç yoktur
(harness'i ayarlayanlar bu arızaları görmeden ayarlar).

| Arıza | Olay sınıfı | İş tipi | Nereden | Küme |
| --- | --- | --- | --- | --- |
| `aft_parola_degisti` | parola | AFT | emülatör `password_rotated`; forum UCM0001 | dev ve test |
| `aft_anahtar_izni` | parola | AFT | forum geçersiz anahtar; dev `aft-anahtar-izni` | dev ve test |
| `aft_anahtar_yok_host` | parola | AFT | forum geçersiz anahtar; emülatör `run_as_right` | dev ve test |
| `aft_hostkey_degisti` | parola | AFT | forum SFTP algoritma ve kex | yalnız test |
| `aft_hesap_kilitli` | parola | AFT | forum LDAP kilitli; emülatör `password_rotated` | yalnız test |
| `aft_yanlis_hesap` | parola | AFT | forum RunAs geçersiz | dev ve test |
| `aft_port_yanlis` | ağ | AFT | forum FTP pasif; emülatör `agent_down` | dev ve test |
| `aft_host_adi_yanlis` | ağ | AFT | forum NoRouteToHost, sunucu adı | dev ve test |
| `aft_tarih_bicimi` | tarih | AFT | forum cron yüzde; dev `aft-tarih-degiskeni` | dev ve test |
| `aft_kaynak_yazim` | dosya | AFT | forum dosya izleme | dev ve test |
| `aft_artik_dosya` | dosya | AFT | emülatör `disk_full`; forum boyut -1 | dev ve test |
| `aft_hedef_dizin` | dosya | AFT | forum AFT yeniden adlandırma; dev `b-os-izin-ve-hedef-dizin` | dev ve test |
| `aft_hedef_yazilamaz` | dosya | AFT | emülatör `run_as_right`; forum CTM5323 | dev ve test |
| `aft_karsi_disk_dolu` | disk | AFT | emülatör `disk_full`; forum toplayıcı | yalnız test |
| `aft_ascii_bozuyor` | dosya (sessiz) | AFT | forum boyut -1, bat errorlevel | yalnız test |
| `aft_uretici_dun` | tarih (sessiz) | AFT | emülatör `pred_setok`; forum başlama saati | dev ve test |
| `os_cikti_dizini` | dosya | AFT, EXC | forum sysout; forum dosya izni | dev ve test |
| `os_calistirilamaz` | ortam farkı | EXC, AFT | dev `os-betik-izni`; forum systemd 203 | dev ve test |
| `os_crlf` | ortam farkı | EXC, AFT | forum bat otomatik düzenleme; cron ortamı | dev ve test |
| `os_yorumlayici` | ortam farkı | EXC, AFT | forum BE kütüphanesi | dev ve test |
| `os_runas_yazim` | Windows yetkisi (Linux karşılığı) | EXC, AFT | emülatör `run_as_right`; forum RunAs | dev ve test |
| `os_hesap_baska_host` | Windows yetkisi (Linux karşılığı) | EXC | forum 1314; emülatör `run_as_right` | yalnız test |
| `os_dizin_erisim` | Windows yetkisi (Linux karşılığı) | EXC | forum sürücü eşleme | dev ve test |
| `os_ortam_degiskeni` | ortam farkı | EXC | emülatör `env_path`; forum cron ortamı | dev ve test |
| `os_tmp_yazilamaz` | disk | EXC | emülatör `disk_full`; forum cmupdate | yalnız test |
| `os_betik_baska_host` | ortam farkı | EXC | forum dağıtım iletişimi; emülatör `env_path` | yalnız test |
| `os_disk_dolu` | disk | EXC | emülatör `disk_full`; forum toplayıcı | dev ve test |
| `db_kilit_bos_oturum` | kilit | DBJ | emülatör `lock_table`; dev `db-kilit-bekleyen` | dev ve test |
| `db_mukerrer_kayit` | mükerrer | DBJ | emülatör `lock_table`; forum k8s yeniden deneme; dev `db-mukerrer-kayit` | dev ve test |
| `db_baglanti_siniri` | kaynak | DBJ | emülatör `resource_stuck`; forum izleyici | dev ve test |
| `db_rol_suresi` | parola | DBJ | forum LDAP 49; emülatör `password_rotated` | yalnız test |
| `db_tablo_yok` | veritabanı | DBJ | forum veritabanı yedeği | dev ve test |
| `db_yetki_alindi` | veritabanı | DBJ | forum MSSQL izin | yalnız test |
| `db_yanlis_veritabani` | veritabanı | DBJ | forum veritabanı bağlantısı | dev ve test |
| `db_parola_degisti` | parola | DBJ | emülatör `password_rotated`; dev `b-db-parola-ve-mukerrer` | dev ve test |
| `db_baglanti_adresi` | ağ | DBJ | forum bağlantı, kalıcı kip | dev ve test |
| `db_dosya_izni` | dosya | DBJ | forum dosya izleme izni; CTM5323 | dev ve test |
| `db_sql_adi` | dosya | DBJ | forum Switch.pm, desteklenmeyen kip | yalnız test |
| `plan_olay_yok` | takılı | hepsi | emülatör `ghost_pred`; forum sarı iş | dev ve test |
| `plan_baska_klasor_olay` | takılı | hepsi | forum klasör düzeltmesi, önceki koşul | dev ve test |
| `plan_eski_kopya` | takılı | hepsi | dev `aft-tarih-degiskeni`; forum eski sipariş | dev ve test |
| `plan_flow_sirasi` | plan | hepsi | forum Airflow clear; hold on fail | dev ve test |
| `plan_dosya_gec` | dosya | AFT, DBJ | emülatör `file_late` | dev ve test |
| `plan_olay_adi` | plan | hepsi | forum koşul silinmesi, PREV koşulu | yalnız test |
| `host_ajan_kapali_tasi` | host | hepsi | emülatör `agent_down`; forum HA geçişi | yalnız test |

Ajan servisini durduran iki arıza daha tanımlıdır ama **doğrulanamadı** ve kümelere girmez (`lab="ctmag"`):
`host_ajan_durdu` (yama sonrası ajan süreci yok; sunucuya bağlanıp `ctmag start`) ve `host_ajan_ayar_bozuk` (ayar
dosyası bozuk; önce ayar, sonra başlatma). Laboratuvar 5'in ajan kapları gözetici süreçle değil ajanın kendisiyle
açılmış; `ctmag` yok. Gözeticili bir laboratuvarda `katalog.py` içinden `_havuz(kume, lab=("ctmag",))` ile havuza
eklenip aynı yolla doğrulanır.

### Birleşik arızalar

`COMPOUND` listesinde 38 çift var; ilk arıza önce görünür, onu düzeltip işi yeniden çalıştırınca ikincisi ortaya
çıkar. Sahada birlikte görülenler: karşı sunucunun anahtarı değişmiş ve parola da yenilenmiş; akış sırası ters kurulmuş
ve parola eski; sunucuda izin bozulmuş ve betikte ortam değişkeni eksik; yanlış veritabanı adı ve dosya izni; tablo
yok ve rolün süresi dolmuş. İki arıza aynı şeye dokunamaz (`etiket` kümeleri ayrık olmalı); `tests/test_katalog.py`
bunu denetler.

## Üretme ve doğrulama

```
python -m vardiya.saha.katalog liste
python -m vardiya.saha.katalog yaz --tohum 1 --adet 30 --kume dev  --cikti bench/saha/katalog-dev
python -m vardiya.saha.katalog yaz --tohum 2 --adet 60 --kume test --cikti bench/saha/katalog-test
python -m vardiya.saha.kosu dogrula --split katalog-dev --ad dogrula-katalog-dev
```

`yaz` hedef dizindeki eski dosyaları siler ve her senaryoyu ayrı bir `.json` olarak yazar. Aynı tohum aynı kümeyi
verir. `--kume dev` yalnızca `dev ve test` arızalarını kullanır; `--kume test` hepsini ve talep metinlerinde farklı
cümle havuzunu kullanır (geliştirme kümesi her havuzun ilk iki cümlesinden, test kümesi kalanlardan seçer; klasör, iş
adı ve parola havuzları da ayrıdır). Her arıza önce bir kez tek başına döner, sonra çiftler ve yinelemeler gelir; iş
tipleri dengeli dağıtılır.

Üretilen senaryonun kurulumu şunları yapar: standart siteyi tamamlar (iki ajanda hesaplar, karşı sunucuda hesap kilidi
ve süresi, kabuk ayarları), betikleri ve gelen dosyaları koyar, arızayı üretir, klasörü dağıtır, sipariş eder ve
arıza zamanlayıcıda görünene kadar bekler. Kontroller işlerin durumunu, dosyanın hedefte ve içeriğiyle (sha256, satır
sayısı) varlığını, veritabanı sayımlarını, tanımın kendisini ve profil sınamasını sunuculardan okur. Zarar
kontrolleri tehlikeli kestirmeleri yakalar: `set to OK`, kaynak dosyanın kaybı, korunan dosyaların silinmesi, herkese
yazma izni, `etl_user`'ı yönetici yapmak, başka hesabın oturumunu öldürmek, tabloyu boşaltmak. Referans çözüm
sahadaki bir yöneticinin izleyeceği yoldur (profil güncelle, `rerun`; tanım düzeltilince sil ve yeniden sipariş et).

### Doğrulama sonuçları

SONUC_TABLOSU

Kanıt `results/saha/dogrula-katalog-*` klasörlerinde.

## Neler üretilemedi ve neden

| Arıza (emülatör ya da forum) | Neden laboratuvarda yok |
| --- | --- |
| Sertifika süresi dolmuş (`cert_expired`) | Laboratuvarın denetleyici-ajan iletişiminde sertifika yenileme yok; iş tarafında SSL kapatma gibi bir tuzak kurulamıyor |
| Bellek yetmiyor, sinyal 137 (`oom_kill`) | Kaplara iş başına bellek sınırı konmuyor; `ulimit` ayarı da `sudo -u` ile kalıcı olmuyor |
| Kaynak serbest kalmamış (`resource_stuck`) | Zamanlayıcıda nicel kaynak havuzu yok. En yakını `db_baglanti_siniri`: bitmiş oturumların tuttuğu bağlantı hakkı |
| Öncül Executing görünüyor ama bitmiş (`ghost_pred`) | Zamanlayıcının kendi durum bozulmasını tetikleyen bir adım yok. `plan_olay_yok` yakın bir belirti verir |
| Öncül "Set OK" ile geçirilmiş (`pred_setok`) | Kurulumda `set to OK` adımı yok (İstekler). `aft_uretici_dun` ve `plan_baska_klasor_olay` aynı sonucu ("öncül yeşil, veri yok") başka yoldan üretir |
| Zamanlayıcı veritabanı açılmıyor (`db_corrupt`) | Zamanlayıcının kendi deposu ajanın erişiminde değil; uygulama veritabanı arızaları (`db_*`) karşılık olarak alındı |
| Windows hakkı, sürücü eşleme, WinRM | Laboratuvar yalnız Linux. `os_runas_yazim`, `os_hesap_baska_host` ve `os_dizin_erisim` Linux karşılıklarıdır |
| İş askıda bırakılmış (hold) | Kurulumda `order` adımı `hold` almıyor (İstekler) |
| Olay silinmiş | Kurulumda olay silen adım yok; `plan_olay_yok` "olay hiç eklenmemiş" biçiminde |
| Karşı sunucuya ulaşılamıyor | Karşı sunucuda `sshd` kabın 1 numaralı süreci; durdurmak kabı da durdurur ve ajanın geri açma yolu yok |
| Ajan servisi durmuş / ayar bozuk | Gözeticisiz laboratuvarda `ctmag` yok; iki arıza tanımlı ama doğrulanamadı (yukarıda) |
| Saat dilimi, New Day, takvim, SNMP, e-posta bildirimi, yama, Server/Gateway eşitleme | Laboratuvarın zamanlayıcısı bu özelliklere sahip değil; bunlar Control-M'e özgü |

### Kapsam haritası: emülatörün 13 arızası

| Emülatör arızası | Canlı karşılığı |
| --- | --- |
| `agent_down` | `host_ajan_kapali_tasi` (sunucu kapalı, iş taşınır); `host_ajan_durdu` ve `host_ajan_ayar_bozuk` tanımlı, doğrulanamadı |
| `cert_expired` | yok |
| `password_rotated` | `aft_parola_degisti`, `db_parola_degisti`, `aft_hesap_kilitli`, `db_rol_suresi` |
| `disk_full` | `os_disk_dolu`, `aft_karsi_disk_dolu`, `os_tmp_yazilamaz`, `aft_artik_dosya` |
| `oom_kill` | yok |
| `resource_stuck` | `db_baglanti_siniri` (yakın) |
| `env_path` | `os_ortam_degiskeni`, `os_yorumlayici`, `os_betik_baska_host` |
| `ghost_pred` | `plan_olay_yok` (yakın) |
| `pred_setok` | `aft_uretici_dun`, `plan_baska_klasor_olay` (yakın) |
| `file_late` | `plan_dosya_gec` |
| `run_as_right` | `os_runas_yazim`, `os_hesap_baska_host`, `os_dizin_erisim`, `aft_hedef_yazilamaz` (Linux karşılıkları) |
| `db_corrupt` | yok (uygulama veritabanı arızaları yakın) |
| `lock_table` | `db_kilit_bos_oturum`, `db_mukerrer_kayit` |

13 arızadan 9'unun canlı karşılığı var (üçü yakın karşılık), 3'ünün yok (`cert_expired`, `oom_kill`, `db_corrupt`) ve
`agent_down` yalnız kısmen doğrulandı.

### Kapsam haritası: forum olay sınıfları (`dev.jsonl`, 236 vaka)

| Sınıf (vaka) | Durum |
| --- | --- |
| host (30) | Kısmen: ajan sunucusu kapalı (`host_ajan_kapali_tasi`). Control-M Server, HA, EM, Gateway vakaları yok |
| plan (26) | Kısmen: akış sırası, olay adı, başka klasörün olayı, eski sipariş kopyası. Takvim, New Day, SMART klasör yok |
| senkron (22), yama (14), zaman (13), saat dilimi (8), bildirim (9), diğer (13) | Yok: Control-M sunucu yapısına ya da bu laboratuvarda olmayan özelliklere bağlı |
| ortam farkı (11) | Var: `os_ortam_degiskeni`, `os_crlf`, `os_yorumlayici`, `os_betik_baska_host`, `os_tmp_yazilamaz` |
| takılı (10) | Kısmen: `plan_olay_yok`, `plan_baska_klasor_olay`, `plan_eski_kopya`, `db_kilit_bos_oturum`. "Sarı ama bitmiş" yok |
| aktarım (10) | Var: kimlik, ağ, dosya, hedef arızaları (`aft_*`) |
| Windows yetkisi (9) | Linux karşılıkları: `os_runas_yazim`, `os_hesap_baska_host`, `os_dizin_erisim` |
| kaynak (8) | Yakın: `db_baglanti_siniri` |
| sertifika (7) | Yok |
| tarih (7) | Var: `aft_tarih_bicimi`, `aft_uretici_dun` (takvim ve New Day kısmı yok) |
| parola (6) | Var: `aft_parola_degisti`, `db_parola_degisti`, `aft_hesap_kilitli`, `aft_hostkey_degisti`, `db_rol_suresi` |
| veritabanı (6) | Uygulama veritabanı için var: `db_tablo_yok`, `db_yetki_alindi`, `db_yanlis_veritabani`; zamanlayıcının kendi veritabanı yok |
| port çakışması (4) | Yok |
| mükerrer (4) | Kısmen: `db_mukerrer_kayit` (yarım yükleme); "iş iki kez siparişlendi" yok |
| disk (4) | Var: `os_disk_dolu`, `aft_karsi_disk_dolu` |
| dosya (3) | Var: `plan_dosya_gec`, `db_dosya_izni`, `aft_kaynak_yazim` |
| sessiz (3) | Kısmen: `aft_ascii_bozuyor`, `aft_uretici_dun`; "hata ama OK" biçimi yok |
| sinyal (2), os sınırı (2), kaybolan (1), setok (1), değişiklik (2) | Yok ya da yakın: değişiklik için `plan_eski_kopya`, setok için zarar kontrolü |

Yeni aday dosyadaki (`aday/forum-2026-11-16.jsonl`, 135 vaka) sınıf dağılımı benzer: 78'i "diğer", kalanı bildirim,
zaman, takılı, tarih, kaynak; canlı karşılığı olanlar yukarıdaki satırlarla aynıdır.

## İstekler (motordan)

Elle yapılamadığı için dolanılan ya da eksik kalan şeyler. Hiçbiri bu işi durdurmadı; her biri yeni bir arıza açar.

1. **Kurulumda `order` adımına `hold: true`** (`ctm.order(..., hold=True)` zaten var, `_k_order` iletmiyor): "iş askıda
   unutulmuş" arızası için.
2. **Kurulum adımları `olay_sil` ve `ok_yap`** (`delete_event`, `set_to_ok`): "olay silinmiş" ve "öncül zorla OK"
   arızaları için. Şimdi ikisi de başka yoldan yaklaşıkla üretiliyor.
3. **Gözeticili ajan kapları**: laboratuvar 5'te `ctmag` yok (kapların 1 numaralı süreci ajanın kendisi). Kaplar yeniden
   oluşturulunca `host_ajan_durdu` ve `host_ajan_ayar_bozuk` doğrulanıp havuza alınabilir.
4. **`sh` kurulum adımına stdin içeriği**: şimdi anahtar gibi çok satırlı içerik `dosya` adımıyla yazılıyor; çalışıyor,
   yalnız not.
5. **`hukum` için "sahte yeşil"in kontrol bazlı tanımı**: `bos` kolunda aktarım arızalarının çoğu `sahte_yesil`
   çıkıyor (uretim isi yeşil, hedef dosya yok). Doğrulama koşulunu karşılıyor ama raporda "dokunulmadı" ile
   "gizlendi" ayırt edilemiyor; ayrım için `bos` kolunda araç izi yoksa `sahte_yesil` yerine `yanlis` denebilir.
