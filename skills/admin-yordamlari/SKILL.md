---
name: admin-yordamlari
description: Zamanlayici yoneticisinin sik yaptigi islerin dogru yordamlari; her biri hangi sozcuklerle istendigi, adimlari ve kacinilacaklariyla.
kind: admin_procedures
procedures:
  ajf_toplu_islem:
    title: Bir klasorun aktif islerini komut satirindan tutmak, oldurmek, silmek
    triggers: [ctmpsm, hold, kill, delete, aktif is, active job, ajf, klasor, folder, toplu, tum isler, all jobs, komut satiri, command line]
    steps: once listele (ctmpsm -LISTAJFFLD <klasor>, tum AJF icin ctmpsm -LISTALL ALL); her isi once tut (ctmpsm -UPDATEAJF <orderid> HOLD); calisanlari oldur (ctmkilljob -ORDERID <orderid>); gerekirse tutulanlari sil (ctmpsm -UPDATEAJF <orderid> DELETE); bunu bir betikle listenin uzerinden yap ve sonucu yeniden listeleyerek dogrula
    caution: tek bir klasor icin tum aktif ortami temizleme ya da New Day'i yeniden calistirma; silmeden once tut, cunku silinen isin ardillari kosulsuz kalir
  powershell_calistirma:
    title: Windows agent'inda PowerShell betigi calistirmak
    triggers: [powershell, ps1, .ps1, windows]
    steps: isi OS tipinde tanimla ve komut olarak powershell.exe -File <betik.ps1> [parametreler] yaz (ya da .bat/.cmd icinden cagir); betigin sonunda exit $LASTEXITCODE ile cikis kodunu dondur ki hata NOTOK olarak gorunsun; 9.0.21 ve sonrasinda OS is tipinin PowerShell secenegini kullanabilirsin
    caution: makinenin tamamini Unrestricted calistirma politikasina alma; gerekiyorsa yalnizca o cagri icin -ExecutionPolicy Bypass kullan
  agent_root_kipi:
    title: Unix agent'ini root ya da root olmayan kipe almak
    triggers: [root, non_root, non-root, start-ag, agent kullanicisi, agent user, set_agent_mode, baska kullanici]
    steps: agent'i calistiran kullaniciyla durdur (shut-ag); root olarak set_agent_mode aracini calistirip istenen kipi sec; agent'i baslat (start-ag) ve surecin hangi kullaniciyla calistigini ps ile dogrula
    caution: dosya izinlerini 777 yapmak ya da sudo ile her seye izin vermek cozum degildir
  hayalet_is_kapatma:
    title: Bitmis ama hala Executing (sari) gorunen isi kapatmak
    triggers: [executing, sari, yellow, hala calisiyor, still running, no longer executing, hayalet, ghost]
    steps: once agent'ta surecin gercekten olmadigini dogrula (ps ya da gorev yoneticisi); 9.0.22 ve sonrasinda ctm_setnotok -orderid <36 tabanli orderid> ile isi NOTOK yap; daha eski surumlerde force_end_job betigi; sonra ardillarin neyi bekledigine bakip durumu sahibine bildir
    caution: isi Set OK yapma; is gercekten basarili mi bilinmiyor, ardillar eksik veriyle calisir
  aktif_ortamda_tutmak:
    title: Hata alan isi ertesi gunlerde de aktif ortamda tutmak
    triggers: [maxwait, keep active, new day'de siliniyor, removed by new day, aktif ortamda, ertesi gun, next day, kac gun, new day]
    steps: isin Keep Active For (Maxwait) degerini kac gun kalacaksa o kadar yap; NOTOK biten ya da hic calismamis is bu kadar gun aktif ortamda kalir, sonra silinir; 99 suresiz tutar
    caution: New Day'i kapatmak ya da ertelemek cozum degildir
  ssl_zincir_testi:
    title: Bir SSL baglantisinin sertifika zincirini Control-M disinda sinamak
    triggers: [openssl, ssl, ldap, ldaps, 636, issuer, zincir, chain, verify error]
    steps: sunucudan openssl s_client -connect <host>:<port> -CAfile <ca dosyasi> calistir; verify error num=20 (yerel ihracci yok) ya da num=21 (ilk sertifika dogrulanamadi) ara sertifikalarin eksik oldugunu gosterir; guvenlik ekibinden tam zinciri iste, yukle, testi tekrarla
    caution: dogrulamayi kapatmak ya da SSL'i kaldirmak cozum degildir
  jre_guven_deposu:
    title: Bir modulun Java guven deposuna CA sertifikasi eklemek
    triggers: [keytool, keystore, truststore, cacerts, suncertpathbuilderexception, certification path, web services, https]
    steps: hangi JRE'nin kullanildigini bul (ornek: agent altinda ctm/cm/JRE); karsi tarafin CA (kok ve ara) sertifikalarini al; o JRE'nin keytool'uyla cacerts deposuna ekle (keytool -importcert -alias <ad> -file <ca.crt> -keystore <JRE>/lib/security/cacerts); modulu yeniden baslat ve baglanti profilini yeniden dogrula
    caution: http'ye inmek ya da tum sertifikalara guvenmek cozum degildir
  eksik_siparis:
    title: New Day ya da bir User Daily'den sonra eksik siparis edilen isleri bulmak
    triggers: [user daily, ctmudly, ctmudlst, eksik siparis, not ordered, missing jobs, siparis edilmedi]
    steps: hangi User Daily'nin calistigini ve son calisma tarihini kontrol et (ctmudlst LIST); eksik isleri tek tek degil, o User Daily'yi yeniden siparis ederek tamamla (once ctmudlst UPDATE <user daily> <onceki tarih>, sonra ctmudly <user daily>); sonucu aktif ortamda say
    caution: ayni gun icin zaten siparis edilmis isler varsa yeniden siparis mukerrer calisma yaratir; once kontrol et
---

# Adminlik yordamlari

Her yordam bir genellestirilmis adminlik yetenegidir: tek bir soruya degil, bir is turune yazilir.

| Alan | Anlami |
| --- | --- |
| `triggers` | Istekte gecince bu yordami getiren sozcukler; en az iki tanesi gecmelidir |
| `steps` | Dogru adimlar, sirasiyla |
| `caution` | Bu iste zararli ya da yanlis olan yollar |

Kaynak: BMC toplulugunun en cok okunan bilgi makaleleri (gelistirme tarafi). Metin kendi sozcuklerimizle yazildi.
