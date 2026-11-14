---
name: olay-siniflari
description: Zamanlayici ariza siniflari; her sinif icin isaretler, neden, dogru mudahale, zararli mudahaleler ve bakilacak kanitlar.
kind: incident_classes
classes:
  kilit:
    title: Kilit, ayni tabloya eszamanli yazma
    signs: [lock, resource busy, nowait, deadlock, kilit, ora-00054, 55p03, timeout period exceeded]
    cause: ayni tabloya ayni anda yazan iki is
    fix: iki isi ortak bir kilit kaynagina bagla (Control-M: Resource, JS7: Resource Lock); yeniden calistirma yalnizca o geceyi kurtarir
    harmful: [rerun]
    evidence: [named_in_error, shared_attr, precedent]
  parola:
    title: Parola ya da kimlik bilgisi degisti
    signs: [logon failure, password, parola, 1326, authentication failed, login failed, credentials, wrong password]
    cause: servis hesabinin parolasi degistirildi ve agent'in parola deposu eski kaldi; otomatik parola donusunde (CyberArk gibi) Control-M'in kabul etmedigi karakterler de gonderilebiliyor
    fix: agent parola deposunu yeni parolayla guncelle (ctmpwd), sonra bekleyen isleri yeniden calistir; otomatik donus kullaniliyorsa yeni parolanin izin verilen karakterlerden olustugunu ve CCM'de calistigini dogrula
    harmful: [set_ok]
    evidence: [shared_attr, named_in_error, precedent]
  host:
    title: Agent ya da sunucu erisilemiyor
    signs: [agent, unavailable, not responding, wait host, communication, unreachable, data pipe, error 232, am_submit, certification path, sslhandshake, failed to submit]
    cause: agent sureci durmus ya da agent'in ic iletisimi (AM data pipe) kopmus; sik onceki olay agent'ta Java ya da surum degisikligi
    fix: agent'i yeniden baslat (start-ag, Windows'ta p_ctmag ve p_ctmam surecleri dahil), ctmping ile dogrula; yakin zamanda Java ya da agent guncellemesi yapildiysa bilinen hata icin surum notlarina bak
    harmful: [set_ok]
    evidence: [shared_attr, named_in_error, host_change, precedent]
  sessiz:
    title: Sessiz hata - is basarili gorunuyor, veri eksik
    signs: [rc=0, return code 0, row count, rows (expected, expected about, beklenen, ended ok although, errorlevel, exit code 0 but]
    cause: is hatayi cikis koduna yansitmiyor - sakli yordam hatayi yutuyor, commit yok ya da Windows .bat hata kodunu exit ile dondurmuyor
    fix: yordamin ya da betigin hatayi yukseltmesini sagla (THROW/RAISE, commit, exit %ERRORLEVEL%); isin ciktisinda hata sozcuklerini ya da donus kodlarini arayan kural (On/Do) tanimla; veriyi temizleyip yeniden yukle
    harmful: [rerun, set_ok]
    evidence: [recent_change, precedent]
  dosya:
    title: Beklenen dosya gelmedi
    signs: [did not arrive, not arrive, file watcher, no file matching, dosya gelmedi]
    cause: kaynak sistem dosyayi gec gonderiyor
    fix: kaynak sistemin sahibine haber ver; dosya gelince zinciri serbest birak, bos dosyayla devam etme
    harmful: [set_ok]
    evidence: [external_source, precedent]
  degisiklik:
    title: Tanim degisikliginden sonra kirilma
    signs: [not found, no such file, exit 127, rc 127, command not found]
    cause: son tanim degisikligi var olmayan bir betigi gosteriyor
    fix: tanimi onceki surume geri al, sonra degisikligi dogru yolla yeniden iste
    harmful: [set_ok]
    evidence: [recent_change, precedent]
  takili:
    title: Takili, bitmeyen ya da hayalet calisan is
    signs: [still running, exceeded, child process, process tree, hang, keeps the job open, still executing, no longer executing, yellow]
    cause: betik bir alt sureci beklemeden cikiyor ya da is ekranda calisiyor gorunuyor ama sureci artik yok (hayalet)
    fix: once surecin gercekten var olup olmadigina bak; varsa betigi alt sureci bekleyecek bicimde duzelt (start /wait, wait) ve takili isi sonlandir; yoksa (hayalet) agent'taki takili durum dosyasini kontrol et ve isi ctm_setnotok ile kapat, force-end degil
    harmful: [set_ok]
    evidence: [precedent]
  disk:
    title: Disk doldu
    signs: [no space, not enough space, disk full, enospc, disk dolu, filesystem full]
    cause: sunucuda disk doldu; sik gorulen neden agent'in kendi loglari (ornek: SAP extractor XT_*.log, silinmis bir baglanti profiline bagli olaylar yuzunden buyur)
    fix: en cok buyuyen dosyayi bul; agent ya da extractor logu ise sureci yeniden baslat (SAP icin shut-xt, start-xt) ve eski logu sil; silinmis baglanti profiline bagli olaylari temizle; eski cikti ve raporlari temizle, sonra yeniden calistir
    harmful: [set_ok]
    evidence: [shared_attr, named_in_error, precedent]
  kaynak:
    title: Kaynak ya da kuyruk bekleme
    signs: [quantitative, wait resource, available 0, 0 of 2 free, waiting for resource, code 5120, no free slots, pool slots]
    cause: kaynagi tutan isler bitmis ama kaynak serbest birakilmamis (asili kayit)
    fix: bekleme nedenini dogrula (ctmwhy, is gunlugunde Wait Resource kodu 5120); kaynaklar bossa isi bir kez hold edip free et ki yeniden degerlendirilsin; asili kayit varsa serbest birak; havuz sinirini yukseltme
    harmful: [set_ok]
    evidence: [named_in_error, shared_attr, precedent]
  yama:
    title: Yama ya da yukseltme sonrasi kirilma
    signs: [after reboot, after windows update, 0xc0000142, side-by-side, 14001, patch, yama, cannot execute the specified program, version cannot execute this job, after upgrading]
    cause: sunucuya isletim sistemi yamasi yuklendi, betik calistiricisi bozuldu
    fix: yamanin etkisini dogrula, betik calistiricisini onar ya da yamayi geri al; agent'i yeniden baslat
    harmful: [set_ok]
    evidence: [host_change, shared_attr, precedent]
  setok:
    title: Oncul elle basarili sayildi (Set OK), veri gelmedi
    signs: [no data found, no rows, ora-01403, nothing to post, staging bos]
    cause: oncul is hata verdi ama elle basarili sayildi (Set OK); veri hic yuklenmedi
    fix: once oncul isi duzeltip calistir, sonra bu isi yeniden calistir; Set OK zinciri yesil gosterir ama veriyi getirmez
    harmful: [rerun, set_ok]
    evidence: [pred_setok, pred_failed, precedent]
  tarih:
    title: Siparis tarihi uyusmazligi (ODATE, execution_date)
    signs: [order date, odate, execution_date, logical date, wait condition, condition was added, data interval]
    cause: oncul is New Day'i gecti; kosulunu bir onceki siparis tarihiyle uretti, ardil kendi tarihini bekliyor
    fix: kosulu dogru tarihle elle ekle ve ardili serbest birak; kalici cozum: iki isi ayni siparis tarihiyle siparis et ya da kosula +1 gun kaydirma ver
    harmful: [set_ok]
    evidence: [crossed_new_day, pred_failed, precedent]
  mukerrer:
    title: Mukerrer ya da ust uste calisma
    signs: [already running, 2 instances, duplicate, two instances, max_active_runs, overlap, previous instance]
    cause: ayni is ikinci kez siparis edildi, iki kopya ayni anda calisti
    fix: ikinci kopyayi durdur, hedefteki mukerrer veriyi temizle; ise 'ayni anda tek kopya' kurali koy ve elle siparisten once aktif kopyayi kontrol et
    harmful: [rerun]
    evidence: [recent_change, precedent]
  zaman:
    title: Zaman asimi: is siniri asti
    signs: [max run time, timed out, execution_timeout, term_run_time, killed, sigkill, terminated]
    cause: isin suresi haftalardir uzuyor, sure siniri artan hacme yetismedi
    fix: yeniden calistirmadan once sureyi uzatan nedeni (hacim, plan) incele; siniri son 30 calismanin %90'i arti pay olarak guncelle; asili kalan isler icin sure asiminda haber veren ya da sonlandiran kurali (SHOUT) bu yeni sinirla kur
    harmful: [set_ok]
    evidence: [slowing, precedent]
  plan:
    title: Gunluk plan yuklenmedi (New Day, User Daily)
    signs: [not ordered, daily plan, new day, not scheduled, was not triggered, plan load, user daily, ctmudly, formatting ajf, no sync]
    cause: New Day ya da bir User Daily yarida kaldi; surum yukseltmesinden sonra gateway senkronu takilabiliyor (Formatting AJF, No Sync) ya da dongusel isler siparis edilip gonderilmiyor
    fix: hangi User Daily'nin eksik siparis ettigini bul, eksikleri o User Daily'den toplu siparis et (tek tek elle degil); gerekirse New Day'i yeniden calistir; yakinda yukseltme yapildiysa gateway ve EM senkronunu kontrol et
    harmful: [set_ok]
    evidence: [host_change, precedent]
  aktarim:
    title: Dosya aktarimi baglantisi kurulamiyor
    signs: [jschexception, session.connect, connection reset, host key, auth fail, publickey, ssh key, sftp, ftps, smb transfer]
    cause: karsi tarafta anahtar ya da algoritma degisti, baglanti profili guncel degil ya da uzun aktarimda baglanti zaman asimina ugradi
    fix: baglanti profilini karsi tarafla dogrula (anahtar, host key, algoritma) ve profilden baglanti testi yap; uzun aktarimlarda keepalive ve zaman asimi ayarini gozden gecir; dosya adinda bosluk varsa tirnakla; sonra yeniden calistir
    harmful: [set_ok]
    evidence: [named_in_error, shared_attr, recent_change, precedent]
  saat_dilimi:
    title: Yaz saati ya da saat dilimi kaymasi
    signs: [daylight, dst, time zone, timezone, 1 hour off, one hour late, one hour early, gmt offset]
    cause: yaz saati gecisinden sonra sunucu yeniden baslatilmamis ya da saat dilimi bilgisi guncel degil; isler bir saat kayiyor
    fix: saat dilimi dosyalarini guncelle, sunucuyu gecisten sonra yeniden baslat, etkilenen islerin baslama saatini ve SLA'sini dogrula; gecis tarihlerinden once kontrol listesi calistir
    harmful: [set_ok]
    evidence: [host_change, precedent]
---

# Olay siniflari

Her sinif bir genellestirilmis cozucudur: tek bir hataya degil, bir ariza sinifina yazilir ve urun dili ne olursa
olsun ayni sinifi tanir.

## Alanlar

| Alan | Anlami |
| --- | --- |
| `signs` | Hata satirinda sinifi ele veren sozcukler; buyuk-kucuk harf ayrilmaz. Control-M, AutoSys, Airflow, JS7 ve veritabani dilinden ornekler birlikte yazilir |
| `cause` | Sinifin olagan kok nedeni, operatorun okuyacagi dille |
| `fix` | Dogru mudahale. Gecmiste ayni kok nedende dogrulanmis bir cozum varsa o once gelir |
| `harmful` | Bu sinifta zararli olan eylemler: `rerun`, `set_ok`. Harness bunlari onermez, bench bunlari zararli sayar |
| `evidence` | Bu sinifta hangi kanit sorgularina bakilacagi |

## Kanit sorgulari

| Ad | Ne yapar |
| --- | --- |
| `shared_attr` | Ayni gun hata veren islerin paylastigi sunucu, kullanici, baglanti, tablo ya da kaynak |
| `named_in_error` | Hata satirinin adiyla soyledigi tablo, sunucu, kullanici ya da kaynak |
| `recent_change` | Hatadan once uc gun icinde bu iste yapilan tanim degisikligi ya da elle siparis |
| `host_change` | Hatadan once uc gun icinde isin sunucusuna gelen yama ya da yukseltme |
| `pred_failed` | Ayni gun hata veren oncul is |
| `pred_setok` | Ayni gun hata verip elle basarili sayilan oncul calisma |
| `crossed_new_day` | New Day'i (07:00) gecerek biten oncul calisma |
| `slowing` | Isin suresinin egilimle uzamasi (Theil-Sen) |
| `precedent` | Ayni hata imzasinin gecmisteki olaylari, kok nedenleri ve yapilanin tutup tutmadigi |
| `external_source` | Neden zamanlayicinin disinda: kaynak sistem, karsi taraf |

## Yeni sinif eklemek

Bir sinif ekleyip `python -m vardiya olay run --split test` ile olcun. Sinif bir kod degil veridir: isaretleri,
nedeni, mudahaleyi ve kanit sorgularini yazarsiniz; kanit sorgularinin kendisi harness'in kodundadir ve listede
olmayan bir sorguya basvuran sinif yuklenmez.

