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
    signs: [logon failure, password, parola, 1326, authentication failed, login failed, credentials, wrong password, tr5167, password for job owner, unable to run command as user, credentials validations is inapplicable, without logon user mode]
    cause: servis hesabinin parolasi degistirildi ve agent'in parola deposu eski kaldi; ya da yeni calistiran kullanicinin parolasi hic kaydedilmedi (Windows 'Logon As User', TR5167); Windows'ta calistiran kullanici bir etki alani kullanicisiysa alan adi olmadan yazilmis olabilir (DOMAIN\kullanici); otomatik parola donusunde (CyberArk gibi) Control-M'in kabul etmedigi karakterler de gonderilebiliyor
    fix: Windows agent'ta Run As kullanicisinin testi 'Credentials validations is inapplicable ... without Logon User mode' diyorsa agent'ta ctmwincfg ile Logon As User'i Y yap ve testi tekrarla; agent parola deposunu yeni parolayla guncelle (ctmpwd), sonra bekleyen isleri yeniden calistir; otomatik donus kullaniliyorsa yeni parolanin izin verilen karakterlerden olustugunu ve CCM'de calistigini dogrula
    harmful: [set_ok]
    evidence: [shared_attr, named_in_error, precedent]
  host:
    title: Agent ya da sunucu erisilemiyor
    signs: [agent, unavailable, not responding, wait host, communication, unreachable, data pipe, error 232, am_submit, failed to submit, pid file, wait node, will not start, selinux, job submission aborted, error in executing /bin/su, no file found for agent java process, not authorized for this agent, found empty sysout file, drain, drained, slurmd, node down, worker lost, failed to attach be library, noroutetohostexception, no route to host, am_read_data_from_pipe, executor reports task instance, low realmemory, status=203/exec, failed at step exec, error 1053, did not respond to the start, ar_ping_to_server_ind, persistent mode, kalici kipte, testing communication, ag_diag_comm, ctm_diag_comm]
    cause: agent sureci durmus, sunucu yeniden baslatildiktan sonra acilmamis (acilis betigi, SELinux) ya da agent'in ic iletisimi (AM data pipe) kopmus; yeni kurulan agent'in calistiran kullaniciya gecme (su) yetkisi olmayabilir ya da isin sahibi sysout'u agent dizinine yazamiyor (dizin izni); agent baska bir sunucu adini yetkili sunucu olarak tanidigi icin kesfedilemiyor; sik onceki olay Java ya da surum degisikligi (Linux'ta Java guncellemesi Control-M'in kullandigi eski Java yolunu kaldirabiliyor); Linux agent'ta 32 ve 64 bit libstdc++.so.5 kutuphanesi eksik olabilir; sunucu agent'a ag yolu bulamiyor olabilir (guvenlik duvari, yonlendirici); 9.0.21 agent'inda bilinen bir cokme hatasi var
    fix: iletisim sorununda sunucuda ctm_diag_comm, agent'ta ag_diag_comm calistirip iki taraftaki 'Agent to Server Port' ve 'Server to Agent Port' degerlerini karsilastir; esitse aradaki guvenlik duvarini, antivirusu ya da port taramasini ag ekibiyle incele; kalici (persistent) kipteki agent sik sik unavailable oluyorsa arada bir guvenlik duvari bos baglantiyi kapatiyor olabilir; agent'ta AR_PING_TO_SERVER_IND=Y yap (gerekli duzeltme paketiyle) ve agent'i yeniden baslat; Linux'ta agent acilista systemd ile baslamiyorsa ('status=203/EXEC') servis birim dosyasina Environment=PATH=... ve WorkingDirectory=<agent dizini> ekle; Windows'ta 9.0.21.100 agent servisi 'Error 1053' ile acilmiyorsa engellenmis check_java_ready betigini yonetici PowerShell'de Unblock-File ile ac; 'Failed to Attach BE Library' ise root olarak compat-libstdc++-33 paketinin 32 ve 64 bit surumlerini kur; 'NoRouteToHostException' ise sunucudan agent'a ag yolunu ve guvenlik duvarini ag ekibiyle incele; 9.0.21'de 'am_read_data_from_pipe' cokmesi icin agent'i 9.0.21.201 ya da sonrasina yukselt; yeni agent'ta 'Found empty sysout' ve /bin/su hatasi varsa agent ana dizininin iznini 755 yap (is sahibi sysout yazabilsin); 'not authorized for this agent' ise ctmagcfg ile Authorized Control-M/Server Hosts listesine dogru sunucu adini yaz; agent durmussa yeniden baslat (start-ag, Windows'ta p_ctmag ve p_ctmam surecleri dahil), ctmping ile dogrula; yakin zamanda Java ya da agent guncellemesi yapildiysa bilinen hata icin surum notlarina bak; is bir host grubundaysa ve grupta saglikli agent varsa isi oraya yonlendir (host grubu secimi anlik yuke bakmaz)
    fix_slurm: sinfo -R ile dugumun durumuna ve nedenine bak; durumun yanindaki '*' dugumun yanit vermedigini gosterir, slurmd'yi kontrol et; drain/drained dugum bakim icin yeni is almaz, bakim bittiyse scontrol update nodename=<dugum> state=resume; dugum 'Low RealMemory' nedeniyle drain olduysa slurm.conf'taki RealMemory degerini dugumde slurmd -C'nin verdigi degere esit ya da kucuk yap, sonra scontrol reconfigure ve resume
    fix_airflow: scheduler ve worker sureclerinin calistigini dogrula (airflow jobs check, Celery worker durumu); gorevler kuyrukta kaliyorsa executor ile worker arasindaki baglantiya bak; executor gorevi basarisiz bildiriyor ama gorev hic calismamissa hep ayni worker dugumune gidip gitmedigine bak (flower, worker gunlukleri); o dugumdeki eksik ya da yanlis paketi duzelt veya dugumu kuyruktan cikar
    fix_kubernetes: dugum ve pod durumunu kubectl get nodes, kubectl describe pod ve olaylarla kontrol et
    harmful: [set_ok]
    evidence: [shared_attr, named_in_error, host_change, precedent]
  sessiz:
    title: Sessiz hata - is basarili gorunuyor, veri eksik
    signs: [rc=0, return code 0, row count, rows (expected, expected about, beklenen, ended ok although, errorlevel, exit code 0 but]
    cause: is hatayi cikis koduna yansitmiyor - sakli yordam hatayi yutuyor, commit yok ya da Windows .bat hata kodunu exit ile dondurmuyor
    fix: yordamin ya da betigin hatayi yukseltmesini sagla (THROW/RAISE, commit, exit %ERRORLEVEL%); isin ciktisinda hata sozcuklerini ya da donus kodlarini arayan kural (On/Do) tanimla; veriyi temizleyip yeniden yukle
    fix_autosys: AutoSys sifirdan farkli cikis kodunda isi FAILURE yapar; betik hatayi cikis koduna yansitmali (exit 1)
    fix_airflow: gorev hatada istisna firlatmali; BashOperator sifir olmayan cikis kodunda basarisiz olur
    fix_cron: cron cikis kodunu izlemez; betik cikti ve kodunu gunluge yazmali (>> log 2>&1) ve hatada bildirim gondermeli
    harmful: [rerun, set_ok]
    evidence: [recent_change, precedent]
  dosya:
    title: Beklenen dosya gelmedi ya da izleyici gormedi
    signs: [did not arrive, not arrive, file watcher, no file matching, dosya gelmedi, ctmfw, wildcard, unsupported mode, minimum size, min size, minimum boyut, dosya izleme, dosyayi bulamiyor, dosyayi gormuyor]
    cause: kaynak sistem dosyayi gec gonderiyor; ya da dosya geldi ama izleyici gormedi (joker karakterli izleme, dosyanin izleyiciden once gelmesi, silinip yeniden gelen dosya)
    fix: dosya yerindeyse izleyicinin minimum boyut ayarina bak; belirtilen boyuttan kucuk dosya gorulmez; Unix'te joker karakterli izlemede 'unsupported mode' cikiyorsa yalnizca dosya adini tirnak icine al, yolu tirnaga koyma (ctmfw /yol/ "DOSYA*.csv"); once dosya gercekten yerinde mi bak; yerinde degilse kaynak sistemin sahibine haber ver ve dosya gelince zinciri serbest birak, bos dosyayla devam etme; yerindeyse izleyiciyi yeniden taratma secenegiyle ya da tam adla calistir
    harmful: [set_ok, run_now]
    evidence: [external_source, precedent]
  degisiklik:
    title: Tanim degisikliginden sonra kirilma
    signs: [not found, no such file, exit 127, rc 127, command not found, templatenotfound, broken dag, no module named, modulenotfounderror, importerror]
    cause: son tanim degisikligi var olmayan bir betigi gosteriyor
    fix: tanimi onceki surume geri al, sonra degisikligi dogru yolla yeniden iste
    fix_airflow: BashOperator'da bash_command .sh ile bitiyorsa Jinja onu sablon dosyasi sanar (TemplateNotFound); komutun sonuna bosluk ekle; 'Broken DAG' hatasinin tam yigin izini airflow dags list-import-errors (eski surumde airflow list_dags) verir; DAG yerel bir modulu ice aktaramiyorsa modulu dags klasorune ya da plugins'e koy veya sys.path'e DAG dosyasinin dizinini ekle
    harmful: [set_ok]
    evidence: [recent_change, precedent]
  takili:
    title: Takili, bitmeyen ya da hayalet calisan is
    signs: [still running, exceeded, child process, process tree, hang, keeps the job open, still executing, no longer executing, yellow, unknown state, istio, sidecar, never completes, hic bitmiyor]
    cause: betik bir alt sureci beklemeden cikiyor ya da is ekranda calisiyor gorunuyor ama sureci artik yok (hayalet)
    fix: once surecin gercekten var olup olmadigina bak; varsa betigi alt sureci bekleyecek bicimde duzelt (start /wait, wait) ve takili isi sonlandir; yoksa (hayalet) agent'taki takili durum dosyasini kontrol et ve isi ctm_setnotok ile kapat, force-end degil
    fix_kubernetes: is podunda istio gibi bir yan konteyner varsa ana konteyner bitince yan konteyner surer ve is tamamlanmaz; is bitince yan konteynere cikis istegi gonder (curl -X POST localhost:15000/quitquitquit) ya da bu podda enjeksiyonu kapat
    fix_quartz: uzun isi InterruptableJob olarak yaz ve scheduler.interrupt(jobKey) ile durdur
    harmful: [set_ok]
    evidence: [precedent]
  disk:
    title: Disk doldu
    signs: [no space, not enough space, disk full, enospc, disk dolu, filesystem full, out of memory, memory consumption]
    cause: sunucuda disk doldu; sik gorulen neden agent'in kendi loglari (ornek: SAP extractor XT_*.log, silinmis bir baglanti profiline bagli olaylar yuzunden buyur)
    fix: en cok buyuyen dosyayi bul; agent ya da extractor logu ise sureci yeniden baslat (SAP icin shut-xt, start-xt) ve eski logu sil; silinmis baglanti profiline bagli olaylari temizle; eski cikti ve raporlari temizle, sonra yeniden calistir
    harmful: [set_ok]
    evidence: [shared_attr, named_in_error, precedent]
  kaynak:
    title: Kaynak ya da kuyruk bekleme
    signs: [quantitative, wait resource, available 0, 0 of 2 free, waiting for resource, code 5120, no free slots, pool slots, wait workload, workload policy, (resources), (priority), qos, parallelism, max_active_tasks, dag_concurrency, queued, kuyrukta]
    cause: kaynagi tutan isler bitmis ama kaynak serbest birakilmamis (asili kayit)
    fix: bekleme nedenini dogrula (ctmwhy; durum kodu D kaynak, L agent, M is yuku politikasi); kaynaklar bossa isi bir kez hold edip free et ki yeniden degerlendirilsin; asili kayit varsa serbest birak; is yuku politikasiysa politikanin sinirini ve kapsamini kontrol et; havuz sinirini yukseltme
    fix_slurm: squeue'da bekleme nedenini oku (Resources, Priority, QOS sinirlari); is dizilerinde %N ile eszamanliligi sinirla, gerekirse scontrol hold
    fix_airflow: parallelism (tum kurulum), max_active_tasks/dag_concurrency (DAG basina), max_active_runs ve pool slotlari gorevleri kuyrukta tutar; hangisinin dolu oldugunu bul; SequentialExecutor paralel calistirmaz
    harmful: [set_ok, run_now]
    evidence: [named_in_error, shared_attr, precedent]
  yama:
    title: Yama ya da yukseltme sonrasi kirilma
    signs: [after reboot, after windows update, 0xc0000142, side-by-side, 14001, patch, yama, cannot execute the specified program, version cannot execute this job, after upgrading, apigtw_port, api gateway service port cannot be set, ctmerr, calcdate, local.key not found, ctmagcpk]
    cause: sunucuya isletim sistemi yamasi yuklendi, betik calistiricisi bozuldu
    fix: agent 9.0.21 yukseltmesi 'File data/local.key not found. Run ctmagcpk' ile duruyorsa ctmagcpk'nin adini verdigi ve artik kullanilmayan is tipi eklentisini agent'tan kaldir (undeploy), sonra yukseltmeyi tekrarla; yukseltmeden sonra %%CALCDATE degiskenleri CTMERR veriyorsa eski surumun hosgordugu hatali sozdizimi artik kabul edilmiyor; belgedeki bicime cevir: %%A=%%$CALCDATE %%$DATE -2; 9.0.21 yukseltmesi 'Ctms Api Gateway Service port cannot be set' ile duruyorsa kurulumdan once BMC_INST_CTM_APIGTW_PORT ortam degiskenini ayarla (onerilen 8393), portu yonetim sunucusuyla arasindaki guvenlik duvarinda ac ve yukseltmeyi yeniden baslat; yamanin etkisini dogrula, betik calistiricisini onar ya da yamayi geri al; agent'i yeniden baslat
    harmful: [set_ok]
    evidence: [host_change, shared_attr, precedent]
  setok:
    title: Oncul elle basarili sayildi (Set OK), veri gelmedi
    signs: [no data found, no rows, ora-01403, nothing to post, staging bos]
    cause: oncul is hata verdi ama elle basarili sayildi (Set OK); veri hic yuklenmedi
    fix: once oncul isi duzeltip calistir, sonra bu isi yeniden calistir; Set OK zinciri yesil gosterir ama veriyi getirmez
    harmful: [rerun, set_ok, run_now]
    evidence: [pred_setok, pred_failed, precedent]
  tarih:
    title: Siparis tarihi uyusmazligi (ODATE, execution_date)
    signs: [order date, odate, execution_date, logical date, wait condition, condition was added, data interval, keep active, removed by new day, logical_date, catchup, backfill, data_interval, ds_nodash, adjust condition, ctm_table_adjust_dummy]
    cause: oncul is New Day'i gecti ve kosulunu bir onceki siparis tarihiyle uretti, ardil kendi tarihini bekliyor; ya da IN kosulundaki PREV onceki siparis tarihini degil ODAT-1'i veriyor (hafta sonu calismayan zincir pazartesi pazar tarihini bekler); Keep Active 0 ise bekleyen ardil New Day'de sessizce siliniyor
    fix: kosulu dogru tarihle elle ekle ve ardili serbest birak; kalici cozum: iki isi ayni siparis tarihiyle siparis et ya da kosula +1 gun kaydirma ver; gece yarisini gecebilecek zincirlerde Keep Active'i 0'dan buyuk yap
    fix_airflow: execution_date (logical_date) aralik baslangicidir, calisma ani degil; sablonda {{ ds }} ya da data_interval_start kullan; istenmeyen gecmis calismalari catchup=False onler
    fix_autosys: kosul turunu kontrol et: success(is) basarida, done(is) her bitiste, notrunning(is) calismiyor oldugu her durumda dogrudur
    harmful: [run_now, set_ok]
    evidence: [crossed_new_day, pred_failed, precedent]
  mukerrer:
    title: Mukerrer ya da ust uste calisma
    signs: [already running, 2 instances, duplicate, two instances, max_active_runs, overlap, previous instance, overlap, overlapping, concurrent, concurrently, disallowconcurrentexecution, concurrencypolicy, flock, max_active_runs, ayni anda iki, iki kopya, two copies, at the same time]
    cause: ayni is ikinci kez siparis edildi ya da dongusel isin calisma araligi New Day'i gecti, iki kopya ayni anda calisti
    fix: ikinci kopyayi durdur, hedefteki mukerrer veriyi temizle; ise 'ayni anda tek kopya' kurali koy, dongusel islerde calisma araligini New Day'den once bitir, elle siparisten once aktif kopyayi kontrol et
    fix_cron: isi flock ile tek kopyaya bagla (flock -n /tmp/<is>.lock <komut>)
    fix_airflow: DAG'da max_active_runs=1, gerekiyorsa depends_on_past=True; beklenmedik coklu calisma geriye donuk doldurmadan geliyorsa catchup=False
    fix_kubernetes: concurrencyPolicy: Forbid (elle olusturulan isler bu kurala tabi degildir)
    fix_quartz: is sinifina @DisallowConcurrentExecution ekle; birden cok sunucuda tek calisma icin JDBC JobStore ile kumelemeyi ac
    harmful: [rerun]
    evidence: [recent_change, precedent]
  zaman:
    title: Zaman asimi: is siniri asti
    signs: [max run time, timed out, execution_timeout, term_run_time, killed, sigkill, terminated, due to time limit, deadline exceeded, term_run_time, activedeadlineseconds, read timed out, sockettimeoutexception, sap has failed to send a response, failed to get a response, jco]
    cause: isin suresi haftalardir uzuyor, sure siniri artan hacme yetismedi; REST ya da web servisi islerinde karsi taraf varsayilan baglanti zaman asimindan gec yanit veriyor olabilir
    fix: SAP'tan 3 dakika icinde yanit gelmezse zaman asimi verilir; tekrarlarsa bir sey degistirmeden (yeniden baslatmadan) once agent'i 10 dakika kadar debug 4'e al ve SAP baglayicisinin (JCo) baglantisini incele; SAP isinde 'A timeout has occurred, SAP has failed to send a response' ise sorun SAP tarafindadir; SAP yoneticisinden ST22 (cokme dokumleri) ve RZ15'i incelemesini iste; REST ya da web servisi isinde 'Read timed out' ise isin gelismis seceneklerinde baglanti zaman asimini (Override connection timeout) karsi tarafin en uzun yanit suresine gore artir; yeniden calistirmadan once sureyi uzatan nedeni (hacim, plan) incele; siniri son 30 calismanin %90'i arti pay olarak guncelle; asili kalan isler icin sure asiminda haber veren ya da sonlandiran kurali (SHOUT) bu yeni sinirla kur
    fix_slurm: is 'DUE TO TIME LIMIT' ile bittiyse --time degerini artir ya da isi parcala; sacct -j <id> -o jobid,elapsed,timelimit,state ile dogrula
    fix_autosys: term_run_time ve n_retrys ayarlarini incele
    fix_kubernetes: activeDeadlineSeconds ve backoffLimit degerlerini incele
    harmful: [set_ok]
    evidence: [slowing, precedent]
  plan:
    title: Gunluk plan yuklenmedi (New Day, User Daily)
    signs: [not ordered, daily plan, new day, not scheduled, was not triggered, plan load, user daily, ctmudly, formatting ajf, no sync, dag not visible, not showing, paused, missed schedule, startingdeadlineseconds, anacron, never ran, hic calismadi, ctmdbtrans, cmr_runinf, statistics cleanup, statistics_cleanup_in_newday]
    cause: New Day ya da bir User Daily yarida kaldi; surum yukseltmesinden sonra gateway senkronu takilabiliyor (Formatting AJF, No Sync) ya da dongusel isler siparis edilip gonderilmiyor; New Day 'formatting AJF' adiminda takildiysa bozuk bir is kaydi veritabaninda islem kilidi yaratmis olabilir
    fix: New Day istatistik temizliginde uzun suruyorsa config.dat'ta STATISTICS_CLEANUP_IN_NEWDAY=N yap ve temizligi ayri bir iste ctmruninf -purge ile zamanla; New Day 'formatting AJF'de takildiysa ctmdbtrans ile kilidi tutan isi ve SQL surecini bul, isi ctmpsm ile tut, ureticinin destegiyle o isin durum dosyalarini temizleyip kilitli sureci sonlandir; hangi User Daily'nin eksik siparis ettigini bul, eksikleri o User Daily'den toplu siparis et (ctmudlst UPDATE, tek tek elle degil); once ctmudly'nin cikis kodunu oku, nedeni o soyler (1 yetki yok, 10 veritabani ya da askiya alma zaman asimi, 11 hatali ya da eksik arguman: komut satirini duzelt, 13 son calisma damgasi yazilamadi); butun gunun planini bastan almak yalnizca New Day hic tamamlanmadiysa ve aktif ortam bossa dusunulur, cunku zaten siparis edilmis isleri ikinci kez siparis eder; yakinda yukseltme yapildiysa gateway ve EM senkronunu kontrol et
    fix_airflow: DAG dosyasi dags_folder altinda mi, ice aktarma hatasi var mi (airflow dags list-import-errors), DAG duraklatilmis mi (unpause), scheduler calisiyor mu; start_date ve schedule degerine bak
    fix_cron: cron surecinin calistigini dogrula (systemctl status cron), syslog'da CRON satirlarina bak; makine o saatte kapaliysa cron isi sonradan calistirmaz, anacron kullan
    fix_kubernetes: startingDeadlineSeconds cok kucukse ya da 100'den fazla zaman kacirildiysa CronJob isi baslatmaz; startingDeadlineSeconds'i ayarla, concurrencyPolicy'ye bak
    fix_autosys: isin durumuna ve kosullarina bak (autorep -j <is> -q); gerekiyorsa sendevent -E FORCE_STARTJOB -J <is>
    harmful: [set_ok]
    evidence: [host_change, precedent]
  aktarim:
    title: Dosya aktarimi baglantisi kurulamiyor
    signs: [jschexception, session.connect, connection reset, host key, auth fail, publickey, ssh key, sftp, ftps, smb transfer, algorithm negotiation fail, server_host_key, end of io stream read, failed to execute pgp command, gpg: handle plaintext failed, algorithm negotiation fail]
    cause: karsi tarafta anahtar ya da algoritma degisti, baglanti profili guncel degil ya da uzun aktarimda baglanti zaman asimina ugradi
    fix: 'Algorithm negotiation fail' ise ayni hesapla bir SFTP istemcisinden (ssh -vvv ya da FileZilla gunlugu) baglanip karsi tarafin kullandigi kex, host key ve sifre algoritmalarini oku, aktarim modulunun destek listesiyle karsilastir; PGP ile sifre cozme 'Failed to execute PGP command' veriyorsa girdi ve cikti dosya adlari ayniysa bilinen bir hatadir; cikti adini farkli ver ya da duzeltmeyi iceren surume gec; baglanti profilini karsi tarafla dogrula (anahtar, host key, algoritma) ve profilden baglanti testi yap; karsi taraf algoritmalari sertlestirdiyse istedigi anahtar degisimi, sifre ve MAC algoritmalarinin kullandigin aktarim modulu surumunce desteklenip desteklenmedigine bak, desteklenmiyorsa modulu yukselt; 'End of IO Stream Read' ile dogrulama dusuyorsa karsi sunucu sifre listesini sirayla denemiyor olabilir: aft_configurable.properties'te kabul ettigi sifreyi (ornek aes128-ctr) listenin basina al ve aktarim kabini yeniden baslat; uzun aktarimlarda keepalive ve zaman asimi ayarini gozden gecir; dosya adinda bosluk varsa tirnakla; sonra yeniden calistir
    harmful: [set_ok]
    evidence: [named_in_error, shared_attr, recent_change, precedent]
  saat_dilimi:
    title: Yaz saati ya da saat dilimi kaymasi
    signs: [daylight, dst, time zone, timezone, 1 hour off, one hour late, one hour early, gmt offset, tomorrow's odate, yaz saati, saat dilimi, kis saati, utc, cron_tz, yerel saat, local time, hours early, hours late, saat once, saat sonra, post odate, wait odate]
    cause: yaz saati gecisinden sonra sunucu yeniden baslatilmamis ya da saat dilimi bilgisi guncel degil; isler bir saat kayiyor; saat dilimi tanimli isler bugunun yerine yarinin ODATE'iyle siparis edilebiliyor
    fix: saat dilimi dosyalarini guncelle (TimeZone.dat zamanlayici sunucusu, yonetim sunucusu ve istemcilerde ayni olmali, yoksa tahmin ve SLA sonuclari yanlis cikar), sunucuyu gecisten sonra yeniden baslat, etkilenen islerin baslama saatini ve SLA'sini dogrula; gecis tarihlerinden once kontrol listesi calistir
    fix_controlm: saat dilimli islerin uc durumu vardir: Wait ODATE (kendi saat dilimindeki tarihi bekliyor), Wait Scheduling (tarih geldi, kosullari bekliyor), Post ODATE (tarih arti Maxwait kendi saat diliminde gecti, bir sonraki New Day'de silinir); Post ODATE'e dusen is icin Maxwait'i 0'dan buyuk yap ve New Day saatini isin saat dilimine gore dusun
    fix_kubernetes: CronJob varsayilan olarak UTC'dir; 1.25 ve sonrasinda spec.timeZone, 1.21-1.24 arasinda schedule icinde CRON_TZ= kullan
    fix_cron: cron sunucunun yerel saatini kullanir; sistem saat dilimi degistiyse cron'u yeniden baslat, destekleniyorsa CRON_TZ kullan; Vixie cron yaz saati gecisini telafi eder, baska cron surumlerinde 02:00-03:00 arasindaki isler atlanabilir ya da iki kez calisabilir; kritik isleri bu araliga koyma ya da sunucuyu UTC'de calistir
    fix_airflow: DAG'in saat dilimi start_date'teki tzinfo ve default_timezone ayariyla belirlenir; zamanlar varsayilan olarak UTC'dir
    harmful: [set_ok]
    evidence: [host_change, precedent]
  senkron:
    title: Izleme ekrani sunucuyla senkron degil
    signs: [no sync, out of sync, gateway, downloading, status not updated, formatting ajf, not getting a response, viewpoint, ctmpsm shows, ekranda gorunmuyor, ekraninda gorunmuyor, not shown in the gui, do not appear in the gui, error code 760, ctm6, cmscommmode, gorunuyor ama, even though it is running, displayed as unavailable, can't find it in the monitoring, bulamiyorum, ordered but not visible]
    cause: yonetim sunucusunun gecidi (EM gateway) zamanlayici sunucusuyla senkronu kaybetti, cogu kez New Day sonrasi; isler sunucuda calisiyor ama ekrandaki durumlar eski; ekranda gorunmeyen is cogu kez gercekte vardir: viewpoint filtresi ya da koleksiyonu, kullanicinin yetkileri ya da bos SMART klasorleri gizleme secenegi onu saklar
    fix: elle siparis edilen is ekranda yoksa siparis penceresindeki ActionReport'a bak; siparisin gercekten yapilip yapilmadigini ve neden reddedildigini orada gorursun; CCM zamanlayici sunucusunu unavailable gosteriyor ama yapilandirma agent'i (CA) calisiyorsa EM sistem parametresi CmsCommMode'u tcp yerine auto yap ve yapilandirma agent'i ile CMS'yi yeniden baslat; gecit CCM'de Disconnected ve gunlukte CTM6/760 senkron hatasi varsa zamanlayici sunucusundaki 'Control-M/EM TCP/IP Port Number' (ctm_menu) ile CCM'deki sunucu tanimindaki port ayni mi bak, esitleyip gecidi yeniden baslat; ctmpsm'de olup ekranda olmayan is icin viewpoint filtresini ve koleksiyonunu, kullanicinin ve gruplarinin yetkilerini, bos SMART klasorleri gizleme secenegini kontrol et; ekrandaki duruma gore mudahale etme; durumu sunucu tarafinda dogrula (ctmpsm, ctm_agstat); gecidi CCM'den yeniden baslatip yeniden indirmeyi zorla
    harmful: [rerun, set_ok, run_now]
    evidence: [host_change, precedent]
  sertifika:
    title: Sertifika suresi doldu ya da guvenilmiyor
    signs: [certificate, certification path, sslhandshake, handshake failed, pkix, pkix path building failed, certificate expired, unable to find valid certification, unable to get local issuer certificate, unable to verify the first certificate, suncertpathbuilderexception, failed to load user authorizations, can't contact ldap server]
    cause: sunucu ile agent arasindaki SSL/TLS sertifikasinin suresi doldu, sertifika otoritesi degisti ya da guven deposunda yok; sik gorulen iki ayri durum: sunucuya yuklenen sertifikada ara sertifikalar eksik (zincir kirik), ya da https'e baglanan modulun (Web Services, bulut, Informatica) kendi JRE'sinin guven deposunda karsi tarafin CA'si yok
    fix: SSL yeni acildiysa istemci ve arac (emdef gibi) baglantilarinin da imzalayan CA kok sertifikasini tanidigini dogrula, tanimiyorsa CA kok sertifikasini yonetim sunucusunda arac baglantilari icin tanimla; once zinciri Control-M disinda dogrula (openssl s_client -connect host:port -CAfile ...); zincir eksikse ara sertifikalari ekletip yeniden yukle; modul JRE'sinde CA eksikse CA'yi o JRE'nin keytool'uyla guven deposuna ekle ve modulu yeniden baslat; sunucu-agent sertifikasi bittiyse yenisini ctmkeytool ile toplu dagit, baglanti modunu (SSL ya da TCP) dogrula; olaydan once sertifika bitis tarihlerini izle
    harmful: [set_ok]
    evidence: [shared_attr, host_change, precedent]
  sinyal:
    title: Is bir sinyalle sonlandirildi (cikis kodu 128 ve ustu)
    signs: [signal, sigsegv, segmentation fault, oom-killer, killed process, core dumped, oomkilled, out_of_memory, exceeded memory limit, maxrss, sigterm, received sigterm]
    cause: is kendi hatasiyla degil disaridan gelen bir sinyalle bitti; kod 128 arti sinyal numarasidir (137 SIGKILL, 143 SIGTERM, 139 SIGSEGV). Sik nedenler isletim sisteminin bellek doldugunda sureci oldurmesi, sure asiminda SHOUT ya da operatorun isi oldurmesi, programin cokmesi; bu yorum Unix icin gecerlidir; Windows'ta ayni sayilar Win32 hata kodudur
    fix: once sinyali ve kimin gonderdigini bul (sistem gunlugunde oom-killer, Control-M gunlugunde kill ya da SHOUT, operator islemleri); bellek yuzundense isin bellek ihtiyacini ya da sunucu bellegini ele al, sure siniri yuzundense zaman asimi sinifina bak; ayni kosulda yeniden calistirmak ayni sonucu verir
    fix_airflow: gorev SIGTERM aldiysa once disaridan durdurulup durdurulmadigina bak (clear, mark failed, execution_timeout, kalp atisi kesilen zombie gorev); alt surecler erken olduruluyorsa killed_task_cleanup_time degerini artir
    fix_slurm: sacct -j <id> -o jobid,maxrss,reqmem,state ile bellek kullanimini gor (OUT_OF_MEMORY); --mem degerini artir; is sure sinirina yaklasirken temiz kapanmak icin #SBATCH --signal=B:TERM@05:00 ile sinyali onceden iste ve betikte yakala
    fix_kubernetes: pod OOMKilled ise bellek sinirini (resources.limits.memory) artir
    harmful: [set_ok]
    evidence: [shared_attr, slowing, precedent]
  os_siniri:
    title: Isletim sistemi kullanici sinirlari yetersiz (acik dosya, surec sayisi)
    signs: [apache kafka is not available, too many open files, max user processes, ulimit, nofile, nproc]
    cause: yonetim sunucusu ya da zamanlayici sunucusunun isletim sistemi kullanicisinin acik dosya ve surec sinirlari dusuk; kurulum ya da yukseltmeden sonra yeni servisler (Kafka gibi) baslayamiyor ya da yuk altinda dusuyor
    fix: kullanicinin acik dosya (nofile) ve surec (nproc) sinirlarini hem yumusak hem sert olarak en az 4096 yap (limits.conf ya da limits.d), oturumu yenileyip bilesenleri yeniden baslat ve CCM'de servis durumunu dogrula
    harmful: [set_ok]
    evidence: [host_change, precedent]
  port_cakismasi:
    title: Ayni makinedeki iki bilesen ayni portu kullanmak istiyor
    signs: [address already in use, port is already in use, bind failed, port conflict, zookeeper]
    cause: yonetim sunucusu ile zamanlayici sunucusu (ya da iki kurulum) ayni makinede ve ayni varsayilan portlari (ornek: Kafka 19092, Zookeeper) kullaniyor; ikincisi baslayamiyor ya da uyari veriyor
    fix: portu tutan sureci bul (netstat ya da ss), bilesenlerden birinin portunu kullanilmayan bir porta tasi ve yeniden baslat; kalici cozum surum notlarinda varsa yukseltme
    harmful: [set_ok]
    evidence: [host_change, precedent]
  kaybolan:
    title: Is calisirken kayboldu (Disappeared)
    signs: [disappeared, be_disap_pipe, all pipe instances are busy, error: '231', error 231]
    cause: Windows'ta agent sureclerinin birbirine bagli kanali kesildi (hata 231, tum kanal ornekleri mesgul); cogu kez antivirus yazilimi agent sureclerine ya da calisan isin surecine mudahale etti
    fix: isin kayboldugu zamandaki isletim sistemi ve antivirus gunluklerini incele; agent dizinlerini ve is sureclerini antivirus taramasindan haric tut; isin yarim kalan isini temizleyip sonra yeniden calistir
    harmful: [set_ok]
    evidence: [shared_attr, host_change, precedent]
  ortam_farki:
    title: Elle calisiyor, zamanlayicidan calismiyor (ortam farki)
    signs: [works manually, works from command line, works from the shell, elle calisiyor, komut satirindan calisiyor, not from cron, cron'dan calismiyor, environment variable, ortam degiskeni, $path, relative path, goreli yol, not a tty, the input device is not a tty, ctm5319, output does not exist]
    cause: zamanlayici isi kullanicinin etkilesimli oturumundaki ortamla calistirmaz; PATH kisadir, profil (.bashrc, .profile) yuklenmez, calisma dizini farklidir, goreli yollar bozulur, ortam degiskenleri yoktur
    fix: komutlarda tam yol kullan; gereken degiskenleri betigin icinde ayarla ya da profili kaynak goster (. ~/.profile); betigin basinda calisma dizinine gec (cd); cikti ve hatayi gunluge yonlendir; betigi zamanlayicinin ortamina benzer bos bir ortamla (env -i) deneyerek dogrula
    fix_cron: crontab'in basinda PATH= ve SHELL= tanimlanabilir; komuttaki % karakteri crontab'da yeni satir anlamina gelir, \% ile kacir; cron TTY baglamaz: docker exec -it gibi etkilesimli bayraklari kaldir; /usr/sbin altindaki komutlar (service gibi) cron'un PATH'inde yoktur, tam yolunu ver (which service)
    fix_controlm: calistiran kullanicinin profilinin yuklenip yuklenmedigine bak; gerekirse is tanimina ortami kuran bir on komut ekle; is bitti ama 'CTM5319 OUTPUT DOES NOT EXIST' ve bos sysout varsa is sahibinin .profile dosyasinda exec satiri olabilir; agent 'su -' ile baslatir, exec yeni bir surec acar ve cikti kaybolur; .profile'dan exec'i kaldir
    harmful: [set_ok]
    evidence: [recent_change, precedent]
  windows_yetki:
    title: Windows'ta isi calistirma yetkisi yok
    signs: [createprocessasuser, 1314, a required privilege is not held, tr5111, fork failure, failed to execute due to fork failure, logon as a batch job, oscompstat 128, error_wait_no_children]
    cause: calistiran kullanicinin ya da agent servis hesabinin Windows haklari eksik (Logon as User aciksa 'Replace a process level token'), cmd.exe uzerinde okuma ve calistirma izni yok ya da antivirus agent dosyalarini engelliyor; Windows'ta 128 ve ustu cikis kodlari Unix'teki gibi sinyal anlamina gelmez
    fix: Windows'ta cikis kodlari sinyal degil Win32 hata kodudur: OSCOMPSTAT 128 (ERROR_WAIT_NO_CHILDREN) genellikle bir .vbs'nin dogrudan calistirilmasindan gelir; betigi cscript /nologo <betik.vbs> ile ya da bir .bat sarmalayicidan calistir; 'Logon as a batch job' hatasinda calistiran kullaniciya su haklari ver: Logon as a batch job, Log on as a service, Replace a process level token, Adjust memory quotas for a process; ayni kullanici 'Deny' ilkelerinde olmamali; Logon as User aciksa calistiran kullaniciyi Yerel Guvenlik Ilkesi'nde 'Replace a process level token' hakkina ekle (oturumu kapatip acmak ya da yeniden baslatmak gerekebilir); is sahibinin ya da servis hesabinin %SYSTEMROOT%\System32\cmd.exe uzerinde okuma ve calistirma iznini dogrula; antivirus agent dosyalarini engelliyorsa haric tut
    harmful: [set_ok]
    evidence: [shared_attr, host_change, precedent]
  veritabani:
    title: Zamanlayicinin kendi veritabani acilmiyor ya da baglanti vermiyor
    signs: [wrong magic number, replorigin_checkpoint, database is not running, could not connect to database, cannot connect to the database, metadata database, jobstore, too many connections, database host has refused your connection]
    cause: zamanlayici sunucusunun, yonetim sunucusunun ya da is akisi aracinin kendi veritabani durdu, bir dosyasi bozuldu (ornek: kume gecisinden sonra PostgreSQL'in replorigin_checkpoint dosyasi) ya da baglanti siniri doldu; butun isler etkilenir
    fix: once veritabaninin calisip calismadigini ve gunlugunu oku; PostgreSQL 'replication checkpoint has wrong magic number' ile acilmiyorsa pgsql/data/pg_logical/replorigin_checkpoint dosyasini yedek icin baska yere tasiyip veritabanini yeniden baslat; baglanti siniri dolduysa baglantilari tutanlari bul; veritabanina dokunmadan once yedek al
    fix_airflow: metadata veritabanina erisimi airflow db check ile sina; baglanti havuzu ve veritabaninin max_connections sinirina bak
    fix_quartz: JDBC JobStore veritabanina erisimi ve kilit tablolarini (QRTZ_LOCKS) kontrol et
    harmful: [set_ok, rerun]
    evidence: [shared_attr, host_change, precedent]
  bildirim:
    title: Olay oldu ama haber gitmedi (SHOUT, e-posta, SLA uyarisi)
    signs: [smtp, unknown smtp host, cannot connect to the specified mail server, failed to send e-mail, sendalertmail, shout failed, email to, ctmmail, mail_handler, e-posta, eposta, shout, email_on_failure, mailto, smtp_host, on_failure_callback]
    cause: zamanlayici sunucusunun ya da SLA modulunun (BIM) posta sunucusu ayari bozuk ya da posta sunucusu degisti; isler dusuyor ama kimse haber almiyor
    fix: posta ayarini dogrula (config.dat'ta MAIL_HANDLER MAILX olmamali, ctm_menu ile SMTP sunucu parametreleri, BIM icin EmailSender); is gunlugunde 'EMAIL TO ... FAILED' yazip ileti yine de geldiyse ctmmail zaman asimina ya da 99 karakteri asan konu satirina bak; deneme iletisi gonder; bekleyen uyarilari elle bildir; olaydan once bildirim yolunu duzenli bir deneme iletisiyle sina
    fix_airflow: airflow.cfg [smtp] bolumunu (smtp_host, smtp_port, smtp_user, smtp_password, smtp_mail_from) doldur, gorevlerde email ve email_on_failure ayarla; hata bildirimini her gorevde tekrar yazmamak icin on_failure_callback'i default_args icinde ver
    fix_cron: cron ciktiyi MAILTO adresine yollar; sunucuda posta aktarici (sendmail, postfix) yoksa ileti gitmez; ciktiyi dosyaya da yonlendirebilirsin
    harmful: []
    evidence: [shared_attr, precedent]
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
| `harmful` | Bu sinifta zararli olan eylemler: `rerun`, `set_ok`, `run_now` (kosullari, kaynaklari ve saati yok sayarak hemen calistirmak). Harness bunlari onermez, bench bunlari zararli sayar |
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

