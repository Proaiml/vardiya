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
  araclari_baska_kullaniciyla:
    title: Agent araclarini (ctmfw gibi) agent kullanicisi olmayan biriyle calistirmak
    triggers: [ctmfw, command not found, utility, arac, other user, baska kullanici, non control-m user, agent kullanicisi olmayan]
    steps: o kullanicinin ortamini agent'inkine bagla (agent'in profil betigini kaynak gostermek, PATH'e agent'in exe dizinini eklemek); urun belgesindeki 'Running Control-M/Agent utilities as other users' adimlarini o surum icin uygula; araci o kullaniciyla deneyip dogrula
    caution: araci calistirmak icin isi agent kullanicisina ya da root'a gecirmek, ya da dizinleri herkese yazilabilir yapmak cozum degildir
  web_onbellek_temizligi:
    title: Control-M Web'de 'Whitelabel Error Page' ya da is gunlugunde 404
    triggers: [whitelabel, error page, 404, control-m web, web server, web sunucusu]
    steps: once tarayici onbellegini temizle; duzelmediyse yapilandirma agent'ini durdur (stop_config_agent), web sunucusunu durdur (stop_web_server), em remove_webapps calistir, yapilandirma agent'ini baslat (web sunucusu onunla gelir) ve sayfayi yeniden ac
    caution: yonetim sunucusunu yeniden kurmak ya da veritabanina dokunmak gerekmez
  dongusel_hata_siniri:
    title: Dongusel isi belirli sayida hatadan sonra durdurmak ya da bir kez yeniden calistirmak
    triggers: [cyclic, dongusel, number of failures, kac kez, fails for, stop cyclic, hata sayisi, ust uste, times in a row, consecutive, hata alinca, dongu devam, durmasini, stop when it fails]
    steps: dongusel isin hatada ne yaptigi once sunucunun genel CYCLIC_RERUN ayarina baglidir (varsayilan hatada da devam eder); tek bir is icin ilk hatada durmasi icin On-Do'da ON COMPSTAT>0 DO Stop Cyclic tanimla; belirli sayida hatadan sonra durmasi icin isin On-Do kosullarina 'Job's Number of Failures' = N ekle ve eylem olarak Stop Cyclic Run (ya da Rerun) sec; eski surumlerde %%FailCount degiskenini cikiya yazip ona gore On-Do tanimla; tanimi dagitip sonraki dongude dogrula
    caution: dongusel is hata alsa da bir sonraki donguye planlanir; hata sinirini koymadan donguyu elle durdurup birakmak ertesi gun sorunu tekrarlar
  cron_sorun_giderme:
    title: Cron isi calismiyor, nereden baslanir
    triggers: [cron, crontab, calismiyor, not running, not working, troubleshoot, syslog]
    steps: cron sureci calisiyor mu bak (systemctl status cron ya da ps aux | grep cron); syslog'da CRON satirlarina bak (grep CRON /var/log/syslog ya da /var/log/cron); crontab -e ile kaydedince yeniden baslatma gerekmez; ciktiyi ve hatayi yakala (>> /tmp/is.log 2>&1); ortam farki icin tam yollar ve gereken degiskenler; komuttaki % karakterini \% ile kacir; betik calistirilabilir mi (chmod +x)
    caution: /var/spool altindaki crontab dosyalarini elle duzenleme, crontab -e kullan
  cron_kacirilan:
    title: Makine kapaliyken kacirilan cron isleri
    triggers: [cron, shutdown, kapali, missed, kacirdi, anacron, reboot, kapatildi]
    steps: cron kapali makinede kacirilan isi sonradan calistirmaz; gunluk ve haftalik isler icin anacron kullan (/etc/anacrontab, /etc/cron.daily)
    caution: kacirilan isi elle calistirmadan once yarim kalan bir calisma var mi bak
  airflow_gorev_yeniden:
    title: Airflow'da hata alan gorevi yeniden calistirmak
    triggers: [airflow, clear, failed task, yeniden calistir, rerun, restart a failed task, gorev]
    steps: arayuzde DAG calismasinda gorevi secip Clear de (gerekiyorsa asagi akisla birlikte) ya da airflow tasks clear <dag> -t <gorev> -s <baslangic> -e <bitis>; scheduler temizlenen gorevi hic calismamis gibi yeniden calistirir
    caution: DAG'i silip yeniden eklemek calisma gecmisini kaybettirir
  airflow_backfill:
    title: Airflow'un gecmis tarihleri doldurmasini (backfill) onlemek ya da yonetmek
    triggers: [airflow, backfill, catchup, gecmis, start_date, old dates, eski tarihler, past runs, yuzlerce calisma, many runs]
    steps: DAG'da catchup=False (ya da airflow.cfg'de catchup_by_default=False); start_date sabit ve gecmiste olmali, datetime.now() gibi degisken olmamali; yalniz disaridan tetiklenecek DAG icin schedule=None, bir kez icin @once
    caution: istenmeyen calismalari silmeden once hangi tarihlerin calistigina bak; veri yazan gorevler cift yazmis olabilir
  airflow_dag_gorunmuyor:
    title: Airflow DAG'i arayuzde gorunmuyor ya da calismiyor
    triggers: [airflow, dag, not visible, gorunmuyor, not showing, missing, import error, list-import-errors]
    steps: dosya airflow.cfg'deki dags_folder altinda mi; airflow dags list-import-errors ile ice aktarma hatasi var mi; scheduler calisiyor ve klasoru taradi mi (dag_dir_list_interval); DAG duraklatilmissa unpause
    caution: veritabanini sifirlamak (airflow db reset) gecmisi siler, gerekmez
  airflow_paralellik:
    title: Airflow gorevleri paralel calismiyor ya da kuyrukta bekliyor
    triggers: [airflow, parallel, paralel, parallelism, concurrency, queued, max_active, pool]
    steps: parallelism kurulum genelini, max_active_tasks (eski dag_concurrency) DAG basini, max_active_runs DAG calismasi sayisini sinirlar; pool slotlarina bak; SequentialExecutor paralel calistirmaz, LocalExecutor ya da CeleryExecutor gerekir
    caution: sinirlari kaynaklari olcmeden buyutmek veritabani ve worker'lari bogar
  slurm_dugum:
    title: Slurm dugumu drain, down ya da yanit vermiyor
    triggers: [slurm, sinfo, drain, drained, node, dugum, idle*, not responding, scontrol]
    steps: sinfo -R ile nedeni gor; drain bakim icindir, calisan isler surer ama yeni is gelmez, bakim bitince scontrol update nodename=<dugum> state=resume; durumun yanindaki '*' dugumun yanit vermiyor (not responding) oldugunu gosterir, dugumdeki slurmd surecini ve ag baglantisini kontrol et
    caution: down durumu dugumdeki calisan isleri oldurur; bakim icin drain kullan
  slurm_is_bilgisi:
    title: Slurm isinin durumu, bellek ve sure kullanimi
    triggers: [slurm, sacct, sstat, seff, memory, bellek, finished job, bitmis is, cpu time, maxrss]
    steps: bitmis is icin sacct -j <id> -o jobid,state,elapsed,maxrss,reqmem,exitcode; calisan is icin sstat; ozet icin seff <id>; calisan isin ciktisi icin sattach ya da --output dosyasi
    caution: bellek siniri asildiysa yeniden gondermeden once --mem degerini olculen MaxRSS'e gore ayarla
  autosys_durum:
    title: AutoSys isinin durumunu degistirmek, zorla baslatmak, tanimini guncellemek
    triggers: [autosys, sendevent, change_status, inactive, force_startjob, jil, box, terminated, autorep]
    steps: durumu degistirmek icin sendevent -E CHANGE_STATUS -s <DURUM> -J <is> (ornek: -s INACTIVE, -s SUCCESS, -s FAILURE); zorla baslatmak icin sendevent -E FORCE_STARTJOB -J <is>; tanimi JIL'de update_job ile degistir (box_name bos birakilirsa is kutudan cikar); sonucu autorep -j <is> ile dogrula
    caution: FORCE_STARTJOB kosullari yok sayar; once ardillarin neyi bekledigine bak
  k8s_cronjob:
    title: Kubernetes CronJob ayarlari (yeniden deneme, ust uste binme, kacirma, saat dilimi)
    triggers: [kubernetes, cronjob, kubectl, startingdeadlineseconds, concurrencypolicy, backofflimit, restartpolicy, batch/v1]
    steps: yeniden denemeyi kapatmak icin backoffLimit: 0 ve restartPolicy: Never; ust uste binmeyi onlemek icin concurrencyPolicy: Forbid; kacirilan zamanlar icin startingDeadlineSeconds; saat dilimi icin spec.timeZone (1.25 ve sonrasi); apiVersion batch/v1 1.21 ve sonrasinda, oncesinde batch/v1beta1
    caution: elle olusturulan isler (kubectl create job --from=cronjob/...) concurrencyPolicy'ye tabi degildir
  quartz_is:
    title: Quartz isleri (ust uste binme, kumeleme, yeniden deneme, durdurma)
    triggers: [quartz, disallowconcurrentexecution, jobexecutionexception, interruptablejob, jobstore, trigger, already exists, scheduler]
    steps: ayni isin ust uste calismamasi icin @DisallowConcurrentExecution; birden cok sunucuda tek calisma icin JDBC JobStore ile kumeleme; hatada yeniden denemek icin JobExecutionException ile refireImmediately (sinirli sayida); calisan isi durdurmak icin InterruptableJob ve scheduler.interrupt(jobKey); 'already exists' hatasinda once checkExists ve deleteJob ya da replace
    caution: sinirsiz refireImmediately hatali isi sonsuz donguye sokar
  em_saglik:
    title: Yonetim sunucusu (EM) bilesenlerinin calisip calismadigini denetlemek
    triggers: [enterprise manager, yonetim sunucusu, gateway, gecit, gui server, gui sunucusu, emgtw, emguisrv, health, saglik, bilesen, component, calistigini]
    steps: bilesen sureclerini bil (emmaintag yapilandirma agent'i, emcms, emguisrv GUI sunucusu, emgtw her veri merkezi icin gecit, GCS, BIM, Forecast, web sunucusu); ctl araciyla bilesenlere istek gonder ve calistiklarini sorgula (ornek: ctl -type GUI_Server -name <ad> -cmd ping); izlemeyi bu sureclere kur
    caution: gecit ya da GUI sunucusu dusuk diye tum yonetim sunucusunu yeniden baslatma; once hangi bilesen oldugunu bul
  ha_elle_gecis:
    title: Yuksek erisilebilirlikte zamanlayici sunucusunu elle ikinciye gecirmek ve geri almak
    triggers: [high availability, failover, fallback, yuksek erisilebilirlik, ikinci, birincil, secondary, primary, gecis, geceriz, ctmipc, emcha, hangs, askida]
    steps: zamanlayici sunucusunda gecis ve geri donus ayni komutla yapilir (ctmipc -msgid MFO -dest CA); yonetim sunucusu (EM) HA'sinda iki dugum arasinda guvenlik duvari varsa gecis duser: duzeltme paketini uygula ve bilesen portlarini HostPort ile sabitleyip yalnizca onlari ac; birincil calisiyorsa birincilde, birincil kapaliysa ikincilde calistirilir; birincil kapaliysa ikincilde komutu calistirmadan once yaklasik 20 dakika bekle; sonra durumu ve aktif tarafi dogrula; EM gecisi CCM'de askida kalirsa birincil dugumde em emcha -restore primary (yalniz ikincil erisilebilirse orada em emcha -restore secondary) ile dugumu geri yukle
    caution: iki tarafin ayni anda aktif olmasi veritabanini bozar; birincilin gercekten kapali oldugundan emin ol; hangi hostun etkin oldugunu ctmha -ACTION IS_ACTIVE (IS_PRIMARY, IS_HA) ile sor; EM'de otomatik gecis tum EM bilesenleri yanit vermediginde olur, gecici olarak kapatmak icin ikincideki Configuration Agent'i durdur ya da CCM'de gecis kipini Manual yap
  pg_yedek:
    title: Zamanlayici ya da yonetim sunucusunun PostgreSQL veritabanini yedeklemek
    triggers: [backup, yedek, postgres, postgresql, database, veritabani, dbuhotbackup, dbucoldbackup, restore]
    steps: urunun kendi araclarini kullan: calisirken DBUHotBackup, durdurulmusken DBUColdBackup; geri yukleme icin DBUHotRestore ve DBUColdRestore; veritabani sahibi kullaniciyla calisan bir betik yazip zamanla ve yedeklerin geri yuklenebildigini duzenli dene
    caution: veritabani dosyalarini calisirken dosya kopyasiyla almak tutarsiz yedek verir
  airflow_tetikleme_kurali:
    title: Airflow'da bir gorev hata alsa da sonraki gorevin calismasi ya da DAG'in hatali sayilmasi
    triggers: [airflow, trigger rule, trigger_rule, all_done, all_success, one_failed, cleanup, temizlik, mark dag failed, dag run failed]
    steps: varsayilan all_success'tir, ust gorevlerden biri hata alirsa alttaki calismaz; hata olsa da calismasi gereken temizlik gorevine trigger_rule=all_done ver; temizlik gorevi basarili oldugu icin DAG calismasi basarili gorunuyorsa sona all_done ile calisan ve diger gorevlerin durumuna bakip hata yukselten bir kontrol gorevi ekle
    caution: hatayi gizlemek icin gorevleri basarili isaretleme
  autosys_tek_test:
    title: AutoSys isini ardillari tetiklenmeden tek basina denemek
    triggers: [autosys, dependents, ardil, without running, tek basina, in isolation, test the job, on_ice, force_startjob]
    steps: once ardillari sendevent -E JOB_ON_ICE -J <ardil> ile buza al (ya da JOB_ON_HOLD); isi sendevent -E FORCE_STARTJOB -J <is> ile baslat (zaten calisan bir is FORCE_STARTJOB'u yok sayar); deneme bitince ardillari JOB_OFF_ICE ile geri al ve durumlari autorep ile dogrula
    caution: ardillari SUCCESS yapmak onlarin ardillarini da tetikler ve kayitlari yaniltir; buz ya da beklet kullan
  slurm_kesinti:
    title: Slurm'de isin kesintiye ya da sure sinirina karsi korunmasi
    triggers: [slurm, preemption, preempt, requeue, cancelled, iptal, time limit, signal, scavenge]
    steps: oncelik nedeniyle kesilen isin yeniden kuyruga girmesi icin #SBATCH --requeue (kumede PreemptMode=requeue ya da JobRequeue=1 olmali, scontrol show config ile bak); sure sinirindan once temiz kapanma icin #SBATCH --signal=B:TERM@05:00 ve betikte sinyali yakalayip ara durumu kaydet
    caution: yeniden kuyruga alinan is bastan baslar; is ara durumdan devam edecek bicimde yazilmadiysa ciktilari ezebilir
  kosul_ayarlama:
    title: Oncul o gun calismiyorken ardilin kosulu beklemeden calismasi (Adjust Condition)
    triggers: [adjust condition, oncul calismiyor, predecessor does not run, ignore the condition, kosulu yok say, smart, pazartesi, only on monday, kosulunu bekliyor, beklemeden, waits for the condition, her gun calismayan, calismadigi gunlerde, cikis kosul, ardillar bekliyor]
    steps: SMART klasorde Adjust Condition=Y kullan; klasor duzeyinde ayni davranis icin config.dat'a CTM_FOLDER_ADJUST_DUMMY Y ekle (9.0 oncesinde CTM_GROUP_ADJUST_DUMMY) ve sunucuyu yeniden baslat; zamanlayici sunucusunda config.dat'ta CTM_TABLE_ADJUST_DUMMY=Y ise o gun planlanmayan oncul yerine sahte bir is calisir, kosullari ekler ve ardil bekleme yapmaz; degisikligi bir gunluk planda dene
    caution: sahte is oncunun Actions sekmesindeki eylemleri de yapar (kosul ekleme, bildirim); bunu bilerek ac
  kalici_baglanti:
    title: Sunucu ile agent arasinda guvenlik duvari varken kalici baglanti
    triggers: [persistent, kalici baglanti, transient, firewall, guvenlik duvari, server to agent port, tek yonlu, one direction, sunucudan agent'a, from server to agent, iletisim]
    steps: ag ekibinden sunucudan agent'a giden portu iki yonlu actir (port ctm_menu > Parameter Customization > Parameters for Communicating with Specific Agent Platforms altinda); ayni menuden o agent icin baglanti tipini Persistent yap; agent'i yeniden baslatip iletisimi dogrula
    caution: tum portlari acmak gerekmez; yalnizca ilgili portu
  dongusel_kacirilan:
    title: Belirli saatlerde calisan dongusel isin kacirdigi calismayi telafi etmek
    triggers: [cyclic, dongusel, missed, kacirdi, kacirilan, specific times, belirli saat, telafi, compensate, tolerance]
    steps: belirli saatlerde calisan dongusel is saati gecmis bir calismayi sonradan telafi etmez; telafi istiyorsan listeye sonraki saatlere kisa aralikli ek saatler ekle, Maximum Rerun ile toplam calisma sayisini sinirla ve Tolerance ile gec kalan saatin ne kadar sonra hala calisabilecegini ayarla
    caution: telafi calismalari ayni veriyi iki kez isleyebilir; is tekrar calismaya dayanikli degilse telafiyi elle ve kontrollu yap
  uyari_eposta:
    title: Yonetim sunucusundaki uyarilari (agent erisilemez gibi) e-postayla iletmek
    triggers: [alert, uyari, alerts console, e-posta, email, unavailability, erisilemez, snmp, sendalarmtoscript]
    steps: CCM'de EM sistem parametrelerinin gelismis sekmesinde SendSnmp=1 ve SendAlarmToScript=<betigin tam yolu> yap; betik gelen uyari alanlarini ayristirip e-posta gondersin; parametrelerden sonra ilgili EM bilesenlerini yeniden baslat ve deneme uyarisiyla dogrula
    caution: her uyariyi e-postaya cevirmek gurultu yaratir; betikte yalnizca istenen uyari turlerini ilet
  aktif_ortam_temizligi:
    title: Zamanlayici sunucusunun aktif ortamini tamamen bosaltmak
    triggers: [clean up the active environment, aktif ortami temizle, aktif ortami bosalt, empty the ajf, tum isleri sil, all jobs conditions and resources]
    steps: bu islem aktif ortamdaki butun isleri, kosullari, degiskenleri, kontrol ve sayisal kaynaklari siler; yalnizca bilincli olarak (test ortami, felaket sonrasi temiz baslangic) ve degisiklik onayiyla yapilir; once sayisal kaynaklari ve gerekli kosullari disari aktar, sunucunun belgelenmis temizleme adimlarini uygula, sonra kaynaklari geri tanimla ve planlari yeniden siparis et
    caution: tek bir klasor ya da birkac takili is icin bu yol kullanilmaz; once ctmpsm ile yalnizca ilgili isleri tut ve sil
  klasor_hata_kosulu:
    title: Bir alt klasordeki herhangi bir is hata alinca baska bir akisi tetiklemek
    triggers: [sub folder, alt klasor, smart folder, ended not ok, folder ended, klasor hata, herhangi bir is, any job fails]
    steps: 'When Folder Ended Not OK' ancak klasordeki butun isler bittikten sonra (basarili ya da degil) devreye girer; herhangi bir isin hatasinda hemen tetiklemek istiyorsan her ise hata durumunda kosul ekleyen bir On-Do tanimla ya da hizmet akisini BIM ile izleyip hata aninda kosul ekletmeyi kullan
    caution: klasor seviyesindeki kosul ani bir hata bildirimi icin uygun degildir
  run_now_smart:
    title: SMART klasordeki bir isi hemen calistirmak (Run Now calismiyor)
    triggers: [run now, simdi calistir, smart folder, smart klasor, cyclic folder, container, kosullari atladi ama]
    steps: Run Now isin kosullarini ve zaman penceresini atlar ama is bir SMART klasorun icindeyse klasor de calisir durumda (zaman penceresi icinde) olmalidir; klasor penceresi disindaysa klasoru de serbest birak ya da isi klasorden bagimsiz olarak siparis et
    caution: Run Now kosullari atladigi icin oncul tamamlanmadan veri eksik calisabilir; once onculun durumuna bak
  aapi_baglanti:
    title: Automation API'ye baglanilamiyor (zaman asimi)
    triggers: [automation api, ctm session login, aapi, 8443, api access, zaman asimi, timeout, rest api]
    steps: Automation API yonetim sunucusuna guvenli portla (varsayilan 8443) baglanir, arayuz ise 18080'i kullanir; arayuz calisip API calismiyorsa istemciden telnet <em sunucusu> 8443 ile portu dene; kapaliysa guvenlik duvarini actir; web sunucusunda SSL'in acik ve sertifikanin istemcide guvenilir oldugunu dogrula
    caution: API icin sertifika dogrulamasini kapatmak gecici bir deneme olabilir, kalici cozum degildir
  klasor_kilidi:
    title: Baska bir kullanicinin calisma alaninda kilitli (checked out) klasoru acmak
    triggers: [checked out, kilitli klasor, locked by another user, exclusive, workspace, calisma alani, folder is currently locked, take ownership]
    steps: Planning > Folders'ta klasoru sec, Used By ile kilidi tutan calisma alanini gor; o calisma alanini Take Ownership ile al ya da kilidi tutan kisiden klasoru check-in etmesini iste; calisma alani artik gerekmiyorsa silmek de kilidi kaldirir
    caution: baskasinin calisma alanini almak ya da silmek onun kaydedilmemis degisikliklerini kaybettirebilir; once sahibine sor
  sunucu_adi:
    title: Zamanlayici sunucusunun agent'lara kendini tanittigi adi degistirmek
    triggers: [hostname, sunucu adi, host adi, alias, cname, virtual name, local ip host interface name, makine adi, takma ad, dns, kendini tanit, tanitmasi]
    steps: ctm_menu > Parameter Customization > Basic Communication altindaki 'Local IP host interface name' degerini yeni ada cevir (ad sunucunun kendi IP'sine cozulmeli); agent'larin yetkili sunucu listesine de yeni adi ekle (ctmagcfg); sunucuyu yeniden baslatip agent'larla iletisimi dogrula
    caution: agent'larda yetkili sunucu adi guncellenmeden degistirilirse agent'lar 'not authorized' der
  agent_otomatik_kesif:
    title: Agent'larin sunucuda kendiliginden kesfedilmesini kapatmak
    triggers: [autodiscover, otomatik kesif, automatically discovered, discovering, kendiliginden, host_autodiscover, kesfedilip, kesfediliyor, istemedigimiz agent]
    steps: config.dat'a HOST_AUTODISCOVER N ekle; ctmipc -DEST ALL -MSGID CFG ile yapilandirmayi yenile; yanlislikla kesfedilmis agent'lari sil ve yeniden gorunmediklerini dogrula
    caution: kesfi kapatinca yeni agent'lari elle tanitmak gerekir
  tek_tekrar_bildirim:
    title: Isi hatada bir kez yeniden calistirip yalnizca ikinci hatada bildirim gondermek
    triggers: [rerun on failure, bir kez yeniden, tek tekrar, ilk hatada bildirim gitmesin, notification only, ikinci hatada, sadece tekrar basarisiz olursa, bir kez yeniden, e-posta gitmesin, ikinci deneme, basarisiz olursa]
    steps: isi dongusel tanimla: 5 dakikada bir, bitisten itibaren (from end), Maximum Reruns=2; On-Do: is OK bitince Stop Cyclic; 'Job's Number of Failures' = 2 olunca e-posta gonder ve gerekiyorsa kosul ekle
    caution: temizlik adimi olmayan yukleme islerinde otomatik tekrar mukerrer veri yazabilir
  agent_discovering_sil:
    title: Discovering durumunda kalan agent'i devre disi birakip silmek
    triggers: [discovering, agent sil, delete the agent, kesif durumunda, disable the agent, ctm_agstat, discovering durumunda, listeden, kaldiririz, artik var olmayan]
    steps: once agent'in gercekten gereksiz oldugunu dogrula; sunucuda ctm_agstat -AGSTAT <agent dugum adi> R D ile Disabled yap; sonra ctm_menu ya da CCM'den sil
    caution: gecici iletisim sorunu yuzunden Discovering'de kalan bir uretim agent'ini silme; once iletisimi tani
  pg_parola_sifirlama:
    title: Zamanlayicinin PostgreSQL yonetici kullanicisinin kaybolan parolasini sifirlamak
    triggers: [postgres password, postgres parola, lost the password, parolayi kaybettik, dba password, reset the password, pg_hba, postgres kullanici, parolasini kaybettik]
    steps: tum zamanlayici ve yonetim sunucusu sureclerini durdur; kurulum dizinlerinin (Windows'ta kayit defterinin) yedegini al; PostgreSQL'i gecici olarak isletim sistemi kullanicisina parolasiz giris verecek bicimde ayarla (pg_hba.conf), baglanip ALTER USER postgres WITH PASSWORD '...' calistir; kimlik dogrulama ayarini eski haline getir ve surecleri baslat
    caution: parolasiz giris ayarini acik birakma; isin sonunda mutlaka geri al
  aktarim_dosya_adi:
    title: Aktarilan dosyanin adina tarih ve saat eklemek
    triggers: [rename, yeniden adlandir, dosya adina tarih, date and time in the file name, after completion, aktarim sonrasi, file transfer, dosya aktarim]
    steps: dosya aktarim isinin Advanced > General > After Completion bolumunde, aktarim modulunun aktarim sonunda doldurdugu degiskenleri (dosya adi, tarih, saat) kullanarak yeniden adlandirma tanimla; degisken adlarini modulun yonetici kilavuzundan al ve once bir deneme isinde dogrula
    caution: hedefte ayni adla dosya varsa ustune yazmamak icin tarih-saat bicimini benzersiz sec
  global_degisken_degeri:
    title: Tek bir global degiskenin degerini komut satirindan gormek
    triggers: [global variable, global degisken, ctmvar, ctmstvar, degiskenin degeri, value of a specific]
    steps: ctmvar -action LIST tum global degiskenleri listeler; tek birinin degeri icin ctmstvar 0 "%%DEGISKEN_ADI" kullan (0: belirli bir siparis numarasi olmadan)
    caution: degeri degistirmeden once onu kullanan isleri kontrol et
  ajf_zaman_listesi:
    title: Aktif ortamdaki islerin baslama ve bitis saatlerini komut satirindan listelemek
    triggers: [ctmpsm, started time, ended time, baslama saati, bitis saati, listall, active jobs file, aktif ortam listesi]
    steps: zamanlayici sunucusunda ctmpsm -LISTALL TIME ile aktif ortamdaki islerin durumunu, baslama ve bitis saatini al; ciktiyi dosyaya yonlendirip rapora donustur
    caution: buyuk ortamlarda sik calistirmak sunucuya yuk bindirir; zamanlanmis bir iste seyrek calistir
  ai_proxy:
    title: Application Integrator islerini bir proxy uzerinden web servisine baglamak
    triggers: [proxy, application integrator, ai job, rest job, web service, vekil sunucu, aicm.properties]
    steps: tasarim arayuzu icin AI web arayuzunde Settings > Proxy ayarlarini doldur; islerin calismasi icin agent'ta CM/AP/data/AI altinda (surume gore yol degisir) aicm.properties dosyasina proxy host ve port degerlerini yaz ve modulu yeniden baslat
    caution: proxy kimlik bilgilerini dosyaya acik metin olarak yazma; kurumun gizli bilgi kasasi ya da baglanti profili kullan
  agent_windows_yonetici:
    title: Windows agent'ini baska servisleri baslatabilecek bir yonetici hesabiyla calistirmak
    triggers: [local system, yerel sistem, windows service, servis baslat, start other services, administrator, yonetici hesabi, this account]
    steps: varsayilan LOCAL SYSTEM hesabi baska Windows servislerini baslatamaz; bir yonetici hesabi ac ya da mevcut birini sec, Yerel Guvenlik Ilkesi'nde (secpol.msc) gereken haklari ver (Log on as a service, Replace a process level token, Adjust memory quotas); agent servisinin Log On sekmesinde This Account olarak bu hesabi yaz; hesabin agent surucusunde List Folder Contents izni oldugunu dogrula; servisi yeniden baslat
    caution: hesabin parolasi degisirse servis de guncellenmeli; parola donusu olan hesaplarda bunu unutma
  gecit_debug:
    title: Calisan bir yonetim sunucusu gecidinde yeniden baslatmadan hata ayiklama kaydini acmak
    triggers: [gateway, gecit, debug, hata ayiklama, control shell, without cycling, yeniden baslatmadan]
    steps: CCM'de sorunlu gecide sag tikla, Control-M/EM Control Shell'i ac ve debug seviyesini ayarlayan komutlari sirayla gonder; sorunu yeniden uretip gunlugu topla; isin sonunda debug seviyesini geri al
    caution: yuksek debug seviyesi diski hizla doldurur; uzun sure acik birakma
  destek_verisi_toplama:
    title: Destek vakasi icin sistem ve gunluk verisini toplamak
    triggers: [support case, destek vakasi, destek, collect, topla, em_data_collector, diagnostic, tani verisi, logs]
    steps: her bilesende urunun kendi toplama aracini calistir (yonetim sunucusunda em_data_collector, zamanlayici sunucusunda ve agent'ta karsiliklari); ciktiyi hcu_package altinda bul; sorunun yasandigi zaman araligini ve is adini vakaya ekle
    caution: veritabani parolalarini vaka metnine yazma; araci sorun tazeyken calistir, gunlukler donmeden once
  rapor_komut_satiri:
    title: Raporu komut satirindan (Automation API) calistirmak
    triggers: [report, rapor, command line, komut satiri, automation api, ctm reporting, cli]
    steps: CLI'nin kurulu oldugunu dogrula (agent kurulu hostta hazir gelir, degilse Automation API CLI'yi ayrica kur); ortami tanimla (ctm env add); rapor komutunu rapor adi ve cikti bicimiyle calistir; gerekiyorsa bunu bir Control-M isine koy
    caution: kullanici parolasini betige acik yazma; ortam tanimini ya da anahtarli girisi kullan
  agent_elle_kaldirma:
    title: Yarim kalan ya da bozuk agent kurulumunu elle temizlemek
    triggers: [uninstall, kaldir, failed installation, yarim kalan kurulum, yarida kaldi, kurulum, installation, manually, elle, rollback, geri alinamadi, temizle]
    steps: agent'i durdur ve hic agent sureci kalmadigini dogrula; Unix'te sistem yoneticisiyle agent kullanicisini ve ev dizinini silip yeniden yarat; Windows'ta servis adlarini not et (ctmag, ctmfw_service; sunucuda ControlM_Server ve ControlM_Configuration_Agent), kayit defterini yedekle, sc delete ile servisleri kaldir, kayit anahtarlarini ve kurulum dizinini temizle; sonra agent'i yeniden kur
    caution: kayit defterini yedeksiz duzenleme; ayni makinedeki baska bir agent'in servisini silme
  takvim_aktarma:
    title: Takvimleri disa aktarmak ve ice almak
    triggers: [calendar, takvim, exportdefcal, defcal, export, disa aktar, import, ice al]
    steps: arguman XML'ini veri merkezi ve takvim adlariyla hazirla; exportdefcal ile disa aktar; dosyayi duzenle; defcal ile hedefe ice al; hedefte takvimi acip gunleri dogrula
    caution: kaynak ve hedef ayni surum ve fix pack olmali; farkli surumler arasi tasimada bu araclari kullanma, takvim tanimlari bozulabilir
  s3_iam_rolu:
    title: Dosya aktariminda S3'e anahtar yerine IAM rolu ile baglanmak
    triggers: [s3, iam, role, rol, aws, access key, managed file transfer, mft]
    steps: MFT surumunun 9.0.20.100 ya da ustu oldugunu dogrula; IAM kullanicisi ve ustlenilecek rol icin gerekli politikalari tanimlat; S3 baglanti profiline ek parametre olarak s3.role.arn (ve oturum adi) ekle; profili dogrula
    caution: kalici erisim anahtarlarini betiklere ya da is tanimlarina yazma
  onay_takvimi:
    title: Isi belirli gunlerde ama tatiller haric calistirmak
    triggers: [holiday, tatil, except, haric, confirmation calendar, onay takvimi, weekday, hafta ici]
    steps: tatiller disindaki gunleri secen normal bir takvim olustur ve kaydet; is tanimina hafta gunlerini ve diger temel zamanlamayi ver; More bolumunde bu takvimi Confirmation Calendar olarak sec; is planini (ya da forecast) acip tatil gunlerinde siparis olmadigini dogrula
    caution: tatil gunlerini elle tutarak ya da isi o gun silerek cozmeye calisma; ertesi yil unutulur
  em_veritabani_disa_aktarma:
    title: Yonetim sunucusu (EM) verisini disa aktarmak, is gecmisi dahil
    triggers: [em util, export, disa aktar, backup, yedek, history, gecmis, statistics, istatistik]
    steps: em util ile -export -type all calistir (tanimlar ve ayarlar); is calisma gecmisi ve istatistikleri bu tipe dahil degildir, ayrica -type history ile disa aktar; iki dosyayi da hedefte ice alip dogrula
    caution: yalniz -type all ile alinan yedek gecmisi icermez; canli veritabani dosyalarini dosya kopyasiyla yedekleme
  veritabani_yedekleme:
    title: Zamanlayici veritabanlarini dogru yedeklemek
    triggers: [backup, yedek, database, veritabani, cold, hot, soguk, sicak, recover, geri yukle]
    steps: urunun yedekleme araclarini kullan; soguk yedek icin uygulamayi durdurup al, kesintisiz gerekiyorsa urunun desteklenen cevrimici yedegini (arsiv gunlukleriyle) kullan; geri yuklemeyi test ortaminda duzenli dene
    caution: veritabani calisirken dosyalarini kopyalayarak yedek alma, tutarlilik bozulur ve geri yukleme calismaz
  rjx_parametreleri:
    title: Uzak host (agentsiz) baglanti davranisini ayarlamak
    triggers: [rjx, remote host, uzak host, agentless, agentsiz, ssh, wmi, reconnect, timeout]
    steps: CCM'de uzak hostu yoneten agent'i sec, System Parameters'i ac ve RJX ile filtrele; baglanti kipi, yeniden deneme sayisi, zaman asimi ve SFTP ile ilgili RJX_* degerlerini degistir; bir test isiyle dogrula
    caution: yeniden deneme ve zaman asimini cok buyutmek kopan baglantiyi gizler; once neden koptuguna bak
  windows_coklu_agent:
    title: Ayni Windows hostuna ikinci agent kurmak
    triggers: [multiple agents, birden fazla agent, second agent, ikinci agent, windows, upgrade, ayni host]
    steps: ikinci agent'in ilkiyle ayni surumde oldugunu dogrula (9.0.21.100 oncesinde farkli surum desteklenmez); kurulumda yeni ornek secenegini ve farkli port ile ad ver; iki agent'i da CCM'de ayri ayri dogrula
    caution: farkli surumden ikinci agent kurmaya calisma, kurulum ilkini yukseltmeye kalkar ve DLL cakismasi olur
  windows_bat_degiskenleri:
    title: Windows .bat betiginde Control-M degiskenlerini kullanmak
    triggers: [.bat, batch, degisken, variable, autoedit, odate, jobname]
    steps: agent'ta ctmagcfg ile AutoEdit Inline=Y yap ki is tanimindaki kullanici degiskenleri betige ortam degiskeni olarak gelsin; ODATE ve JOBNAME gibi sistem degiskenleri de gerekiyorsa sunucuda config.dat'ta AUTOEDIT_INC_SEC=SYSTEM ayarla; betikte %DEGISKEN% bicimiyle oku ve bir test isiyle dogrula
    caution: degerleri betige sabit yazarak gecistirme
  mft_coklu_ornek:
    title: Ayni hostta ikinci dosya aktarim (MFT) ornegi calistirmak
    triggers: [mft, managed file transfer, ikinci, second, ornek, instance, ayni host, same host, port, karisik]
    steps: ikinci ornegin hub_config.properties dosyasinda server.port, management.port ve hub.http-port degerlerini ve konteyner portlarini ilk ornekten farkli, bos portlara al; ornegi yeniden baslat; CCM'de iki ornegin bilgisinin ayrildigini dogrula
    caution: iki ornegi ayni portlarla birakma; CCM yanlis bilgi gosterir
  mft_bos_parola:
    title: Yukseltmeden sonra dosya aktarim profillerindeki parolalarin bos gorunmesi
    triggers: [mft, aft, baglanti profili, connection profile, parola, password, bos, blank, empty, yukselt, upgrade]
    steps: aft_configurable.properties'te localPasswordAlgorithm satirinin tek oldugunu dogrula; fts_config.properties ve accounts.xml'deki parolalarin ayni algoritmayla (Blowfish ya da AES) sifrelendigine bak; tutarsizligi giderip parolalari CCM'den yeniden gir ve profilleri dogrula
    caution: algoritma satirlarini neye yol actigini bilmeden silme; once dosyalarin yedegini al
  s3_profil_izinleri:
    title: S3 baglanti profilinin dogrulanmamasi ya da bucket listesinin bos gelmesi
    triggers: [s3, bucket, listing, listeleme, no data found, dogrula, validate, izin, permission]
    steps: profildeki kullanicinin IAM politikasinda s3:ListAllMyBuckets ve s3:GetBucketLocation izinlerinin olup olmadigini AWS yoneticisiyle kontrol et; eksikse politikaya eklet; profili yeniden dogrula
    caution: sorunu cozmek icin kullaniciya tam yetki (s3:*) verme; yalniz gereken izinleri ekle
  em_yuksek_cpu:
    title: Yukseltmeden sonra yonetim sunucusunda CPU'nun surekli yuksek olmasi
    triggers: [cpu, %100, yuksek, high, mikroservis, microservice, java, em, yonetim sunucusu, yavas]
    steps: once makinenin surumun istedigi CPU ve bellek gereksinimini karsiladigini dogrula; hangi surecin tukettigini bul; Java mikroservisleriyse EM_HOME/services/context altindaki tanimlara -XX:+UseSerialGC ekle; EM'yi yeniden baslat ve CPU'yu izle
    caution: Xms ve Xmx degerlerini destek yonlendirmesi olmadan degistirme
  mft_pano_guncellenmiyor:
    title: Dosya aktarim panosunun ya da aktarim sunucusu durumunun guncellenmemesi
    triggers: [mft, pano, panosu, dashboard, guncellenmiyor, no updates, gorunmuyor, durum, status, aktarim]
    steps: agent'ta ctmagcfg ile Logical Agent Name'in sunucunun agent'i tanidigi adla birebir ayni oldugunu dogrula; aft_configurable.properties'teki agentname ve ctmshostname degerlerini ve agentname.dat'i ayni ada esitle; agent'i yeniden baslat ve yeni bir aktarimin panoda gorundugunu kontrol et
    caution: panoyu duzeltmek icin MFT'yi yeniden kurma
  aktarim_boyut_dogrulama:
    title: Aktarim sonrasi boyut dogrulamasinin dusmesi
    triggers: [boyut, size, dogrulama, validation, verify, -1, aktarim, transfer, ftp, mft]
    steps: hedefteki dosyanin gercek boyutuna elle bak; gunlukte hedef boyutu -1 ise karsi FTP sunucusu boyut bilgisini vermiyordur, FTP sunucusu yoneticisiyle duzelt; duzelmiyorsa hesapta 'Verify destination file size' secenegini bilerek kapat ve riski kaydet; aktarimi yeniden calistir
    caution: isi OK sayarak gecme; boyut dogrulamasi tamamen kalkmis olur
  ajf_silinmeyen_klasor:
    title: Suresi gecen SMART klasorlerin ve islerin New Day'de AJF'ten silinmemesi
    triggers: [keep active, silinmiyor, not deleted, not removed, ajf, smart klasor, smart folder, new day, kaliyor]
    steps: klasorun ya da isin DAYSKEEPINNOTOK (Keep Days if NOT OK) ile tanimli olup olmadigina bak; bilinen urun hatasidir (9.0.21.100'de duzeldi); gecici cozum: silinmis kaydi geri al (undelete), Keep Days if NOT OK degerini 0 yap, kaydet ve yeniden sil; kalici cozum icin yamayi uygula
    caution: silmeden once OK yapma; klasor HOLD'da kalir
  uzak_host_sysout:
    title: Uzak host (WMI) isleri basarili oldugu halde NOTOK bitiyor
    triggers: [wmi, uzak host, remote host, agentless, sysout, oscompstat 1, notok, basarili, successful]
    steps: agent'in proclog'unda 'Cannot map remote sysout directory' gibi satirlara bak; uzak hostta SYSOUT paylasiminin tanimli oldugunu ve agent'in kullandigi hesabin bu paylasima yazma izni oldugunu dogrula; izni yalniz o hesaba ver; bir test isiyle dogrula
    caution: paylasima herkese tam izin verme; isi OK sayarak gecme
  ca_baslamiyor:
    title: Zamanlayici sunucusunun yapilandirma ajani (CA) baslamiyor
    triggers: [start_ca, yapilandirma ajani, configuration agent, acilmiyor, does not start, baslamiyor, ca gunlugu, thread, is parcacik]
    steps: proclog'daki CA gunlugune bak; is parcaciklarinin kalkmasini beklerken sure doluyorsa shut_ca ile durdur, sunucunun data dizinindeki config.dat'a THREAD_STATE_RETRY_SLEEP 1000 satirini ekle (HA'da etkin dugumde) ve start_ca ile yeniden baslat; CCM'de CA'nin gorundugunu dogrula
    caution: config.dat'i yedeksiz degistirme
  mft_pgp_cozme:
    title: Dosya aktariminda PGP sifre cozmenin zaman asimina dusmesi ya da parolayi tekrar sormasi
    triggers: [gnupg, gpg, pgp, sifre cozme, decrypt, decryption, zaman asimi, timeout, passphrase, parola soruluyor, pinentry]
    steps: GnuPG surumune bak (2.1 ve sonrasi parolayi pinentry ile sorar); gpg-agent.conf dosyasina (yoksa olustur) allow-loopback-pinentry satirini ekle; MFT'nin PGP sablon komutuna --pinentry-mode loopback ekle; gpg-agent'i yeniden baslat ve test aktarimiyla dogrula
    caution: sifrelemeyi kaldirarak ya da parolayi duz metin dosyada herkese acik birakarak cozme
  sap_eski_durum_dosyalari:
    title: SAP islerinin Unknown kalmasi, gecikmesi ya da coktan bitmis islerin hala izlenmesi
    triggers: [sap, unknown, gecikiyor, delayed, coktan bitmis, already finished, izleniyor, tracked, tracking, executing, status]
    steps: agent'in ctm/status dizinindeki en eski durum dosyalarindan SAP is adlarini al; SAP'te (SM37) bu islerin bittigini dogrula; agent'i durdur; yalniz SAP'te bittigi dogrulanan islerin durum dosyalarini kaldir; agent'i baslat ve izlemenin normale dondugunu kontrol et
    caution: tum durum dosyalarini toptan silme; hala calisan islerin izi kaybolur
  gomulu_betik_degisken:
    title: Gomulu betikli (embedded script) iste Control-M degiskeni kullanmak
    triggers: [gomulu betik, embedded script, embedded, degisken, variable, autoedit, cozulmuyor, not resolved, odate]
    steps: gomulu betigin icinde %%degisken dogrudan cozulmez; is taniminda %%PARM1=%%$ODATE gibi bir parametre tanimla; betikte bu degeri parametre olarak oku ($1 ya da %1); test isiyle dogrula
    caution: degeri betige sabit yazarak gecistirme
  dongusel_hata_sonrasi:
    title: Dongusel isin NOTOK'tan sonra bir sonraki aralikta yeniden calismaya donmesi
    triggers: [dongusel, cyclic, notok, yeniden calismaya, sonraki aralik, next interval, stopcycl, stop cyclic, cyclic_rerun]
    steps: bu urunun varsayilan davranisidir; sunucu genelinde config.dat'taki CYCLIC_RERUN parametresi NOTOK'tan sonra dongunun surup surmeyecegini belirler (z/OS'ta da ayni ad); is bazinda istenmiyorsa On NOTOK icin Stop Cyclic tanimla
    caution: genel parametreyi degistirmek butun dongusel isleri etkiler; once kac isin etkilenecegini listele
  dongusel_bagimli_is:
    title: Gunde birden fazla calisan oncul ve ardilda ardilin yalniz bir kez calismasi
    triggers: [gunde iki kez, twice a day, birden fazla, bagimli, dependent, bir kez tetikleniyor, only once, dongusel, cyclic, kosul, condition]
    steps: ilk calismada uretilen kosul ardilin ilk calismasinda tuketilir ve ikinci kez uretilmez; iki isi ayni dongusel aralikla tanimla; ardil her calismadan sonra kosulu silsin (DO COND -) ve oncul her calismada kosulu yeniden eklesin; bir test gunuyle iki calismayi dogrula
    caution: ardili her gun elle calistirarak gecistirme
  logon_as_user_haklari:
    title: Logon As User acildiktan sonra islerin log ve cikti olusturamadan dusmesi
    triggers: [logon as user, log on as user, fix pack, parola tanimladik, log, cikti olusturamadan, job failed, fork failure, windows agent]
    steps: kullanicinin parolasinin CCM ya da ctmpwd ile tanimli oldugunu dogrula; kullaniciya Yerel Guvenlik Ilkesi'nde 'log on as a batch job' ve 'replace a process level token' haklarini ver; agent servisini yeniden baslat ve bir test isiyle dogrula
    caution: kullaniciyi yerel yoneticiler grubuna ekleyerek gecistirme
  beklenmedik_gelecek_odate:
    title: Islerin kimse zorlamadan gelecek bir ODATE ile siparis edilmesi
    triggers: [yarinin odate, gelecek odate, future odate, tomorrow, siparis edildi, zorlamadi, not forced, new day, ileri tarih]
    steps: isin ya da ust SMART klasorun saat dilimi alanina bak; saat dilimi ileri siparis yapar (is bir gun once siparis edilir, 48 saat kalir); bu istenmiyorsa saat dilimini kaldir; tanimin sunucuya yuklenen surumunu da kontrol et
    caution: ODATE'i elle degistirerek gecistirme; davranis her gun tekrarlanir
  nicel_kaynak_beklemede:
    title: Nicel kaynakla sinirlanan islerin ilk grup bittikten sonra da beklemede kalmasi
    triggers: [nicel kaynak, quantitative, paralel, parallel, beklemede, waiting, bittikten sonra, stuck, takili, max]
    steps: ecaqrtab LIST <kaynak> ile kullanilan ve en buyuk miktara bak; biten islerin tuttugu ve birakilmamis kayitlari bul, isleri dogrulayip asili kayitlari serbest birak; bekleyen islerde 'Why' ile gercek bekleme nedenine bak (kaynak mi, kosul mu, zaman mi)
    caution: kaynagi sinirsiz yaparak gecistirme; sinirin amaci yuku korumaktir
  user_daily_ileri_tarih:
    title: User Daily'nin ertesi gunun islerini onceden yukleyip New Day'e kadar bekletmesi
    triggers: [user daily, ctmudly, ertesi gun, next day, yuklesin, load, baslamasin, wait until, new day'e kadar, gelecek]
    steps: ctmudly -DAILY_NAME <ad> -odate <yyyymmdd> -odate_option run_date ile siparis et; isler siparis edilir ama ODATE gelene kadar calismaz; bekleyen islerin lisans sayimina girdigini hesaba kat
    caution: ayni gunun islerini iki kez yuklememek icin User Daily'nin zamanlamasini dogrula
  zos_executing_temizlik:
    title: z/OS'ta bitmis ama Executing gorunen isi AJF'ten temizlemek
    triggers: [z/os, zos, mainframe, executing, ctmcajf, ajf, jes2, stuck]
    steps: once JES2'de isin sysout'u HELD mi bak, oyleyse serbest birak ve durumun guncellenmesini bekle; degilse CTMCAJF CLEANUP ile isi DELETED durumuna al (monitor acik kalabilir), New Day fiziksel olarak siler; COMPRESS yalniz monitor kapaliyken
    caution: monitor calisirken COMPRESS calistirma
  uyari_bastirma:
    title: Yukseltmeden sonra gelen istenmeyen uyarilari kapatmak
    triggers: [alert, uyari, suppress, bastir, kapat, alert manager, global alert, gas, message id, mesaj kimligi]
    steps: kapatilacak uyarinin mesaj kimligini is gunlugunden ya da sunucunun data dizinindeki dbs_msgtbl ve dbs_ag_msgtbl dosyalarindan bul; config.dat'in yedegini al; ALERT_ON_MESSAGE ayarinda bu kimlikleri kapat; sunucunun ayari yeniden okumasini sagla ve uyarinin artik gelmedigini dogrula
    caution: uyarilari toptan kapatma; yalniz gercekten gereksiz olan kimlikleri kapat
  veritabani_sorgu_satiri:
    title: Zamanlayici veritabanina komut satirindan baglanmak
    triggers: [database, veritabani, sql, psql, command line, komut satiri, em_sql, login, baglan, query, sorgu]
    steps: zamanlayici sunucusunda sunucu kullanicisiyla sql komutunu calistir (ya da ctm_menu > Troubleshooting > Interactive SQL); yonetim sunucusunda Windows'ta em_sql -U <dbo> -P, Unix'te em psql -U <dbo> -d <veritabani>; yalniz okuma sorgulari calistir
    caution: urun tablolarinda elle UPDATE ya da DELETE yapma; destek yonlendirmesi olmadan veriyi degistirme
  mft_gecmis_saklama:
    title: Dosya aktarim panosundaki gecmisin saklama suresini ayarlamak
    triggers: [mft, transfer history, aktarim gecmisi, dashboard, pano, retention, saklama, days to keep]
    steps: varsayilan 30 gun ya da 7 milyon kayittir; CCM'de EM sistem parametresi olarak MFTDaysToKeep ve MFTRecordsToKeep'i (bilesen tipi CMS) elle ekle ve degerini ver; temizlik araligini da gerekiyorsa ayarla; EM veritabani buyumesini izle
    caution: saklama suresini cok uzatmak EM veritabanini buyutur
  uyari_betige_yonlendirme:
    title: Yonetim sunucusu uyarilarini bir betige ya da izleme aracina gondermek
    triggers: [alert, uyari, alarm, snmp, sendalarmtoscript, monitoring tool, izleme araci]
    steps: CCM'de EM sistem parametrelerinde SendSnmp'yi betik secenegine al ve SendAlarmToScript'e betigin tam yolunu yaz; gecidi yeniden baslat; betik uyari alanlarini argumanlardan ($* ya da %*) okur; bir test uyarisiyla dogrula
    caution: betik yavas ya da takilirsa uyarilar birikir; betigi kisa tut, agir isi baska surece birak
  host_grubu_dagitimi:
    title: Host grubundaki islerin agent'lara nasil dagitildigini anlamak
    triggers: [host group, host grubu, node group, nodegroup, round robin, dagitim, distribution, ayni agent, same agent]
    steps: sunucu host grubunda zaman damgasina gore round robin uygular, en eski damgali host once secilir; ayni hostu tek basina hedefleyen isler o hostun damgasini guncelleyip sirayi bozar; dengeli dagilim isteniyorsa isleri yalniz grubu hedefleyecek bicimde tanimla ve dagilimi raporla dogrula
    caution: dagilim bozuk diye hostlari gruptan cikarip eklemek sorunu cozmez
  kontrol_kaynagi_komut:
    title: Kontrol kaynaklarini komut satirindan gormek ve yonetmek
    triggers: [control resource, kontrol kaynagi, ecactltb, ecaqrtab, quantitative, add, delete, command line]
    steps: dagitik Control-M'de kontrol kaynaklarini ecactltb ile yalniz goruntuleyebilirsin, ekleme ve silme komutu yoktur; nicel kaynaklar icin ecaqrtab ile ekle, sil, guncelle; kontrol kaynagini tutan isi bulup onu yonet
    caution: kontrol kaynagini serbest birakmak icin onu tutan calisan isi oldurme; once neden tuttugunu bul
  sap_ic_hata:
    title: SAP isinin SAP tarafindaki ic hatayla dusmesini incelemek
    triggers: [sap, bapi, bapi_xbp, error code, internal problem, abap, xbp]
    steps: hatanin oldugu saati not et; SAP Basis ile SM21 (sistem gunlugu), RZ15 (XMI gunlugu) ve ST22 (ABAP dokumu) kayitlarina bak; SAP tarafindaki neden giderilince isi yeniden calistir
    caution: SAP tarafi hatasini Control-M'de basarili sayip gecme
  pg_bakim:
    title: Gomulu PostgreSQL veritabaninin bakimini izlemek
    triggers: [postgresql, postgres, vacuum, autovacuum, bakim, maintenance, health, saglik, dbustatus]
    steps: autovacuum varsayilan olarak aciktir; DBUStatus ile durumu, veritabani ve disk buyumesini duzenli izle; uzun suren islemleri ve kilitleri kontrol et; agir bakimi (VACUUM FULL, yeniden indeksleme) yalniz bakim penceresinde ve once yedek alarak yap
    caution: is saatinde VACUUM FULL calistirma, tablolari kilitler
  ortak_degisken_dosyasi:
    title: Bircok isin okuyacagi ortak degisken dosyasi tanimlamak
    triggers: [libmemsym, ortak, central, merkezi, degisken dosyasi, variable file, variables, autoedit]
    steps: her satirda bir atama olan bir metin dosyasi yaz (ornegin %%a=5); is tanimlarinda %%LIBMEMSYM=<tam yol> ver; yol buyuk kucuk harf duyarlidir ve dosya isi calistiran taraftan okunabilir olmali; bir test isiyle degerleri dogrula
    caution: dosyaya parola yazma; dosyayi degistirmek onu okuyan butun isleri etkiler
  takvim_goreli_gun:
    title: Isi bir takvimin ilk, son ya da n'inci is gununde calistirmak
    triggers: [first work day, last work day, ilk is gunu, son is gunu, calendar, takvim, relative, goreli, month end, ay sonu]
    steps: Schedule'da Based on Calendar'i sec; Relative Calendar Days from Start/End of Month/Period'u sec; takvimi ver ve Order only on calendar days'i isaretle; ilk gun icin 1, sondan ilk gun icin -1 gibi gun numarasini sec; forecast ile dogrula
    caution: ay sonu gunlerini her ay elle tutarak cozme
  sql_ciktisi:
    title: Veritabani isinin SQL ciktisini is ciktisinda gormek
    triggers: [databases, veritabani isi, sql output, sql ciktisi, job output, is ciktisi, append]
    steps: Databases is tanimindaki Job Output bolumunde 'Append SQL output to Job Output' secenegini isaretle ve bicimi Text yap; isi yeniden calistirip ciktiyi kontrol et
    caution: cok buyuk sonuc kumelerini ciktiya eklemek ciktiyi sisirir; gerekiyorsa sorguyu sinirla
  ondo_metin_eslesme:
    title: Is ciktisinda bir metni On/Do ile yakalamak
    triggers: [on/do, on do, on statement, statement, code, ciktida, output, string, metin, yakala]
    steps: On satirinda Statement komutun kendisiyle (ya da * ile her satirla), Code ise ayni satirdaki ciktiyla eslesir; aranan metin bir sonraki komuttan once tek satirda olmali; joker karakterleri (*) metnin iki yanina koy; bir test isiyle eslesmeyi dogrula
    caution: cok genis desen (*Fail*) beklenmeyen satirlari da yakalar; deseni olabildigince dar tut
  new_day_yeniden:
    title: New Day'i yeniden calistirmak ya da ertelemek
    triggers: [new day, yeni gun, newday, rerun, yeniden calistir, restart, ertele, defer, delay, geciktir]
    steps: yarida kalan New Day'i sunucu yoneticisi olarak ctm_menu > Troubleshooting > Restart New Day ile yeniden baslat; ertelemek gerekiyorsa ctmsys > System Parameters'ta Day Time'i ileri al (en fazla ~24 saat), daha uzun erteleme icin sunucu kapali tutulur; sonra siparislerin tamam oldugunu ctmudchk ya da AJF ile dogrula; New Day'in bir gunde kac kez calistigini ctmlog listesiyle kontrol et, birden fazla calistiysa mukerrer siparisleri tutup sil
    caution: New Day'i ust uste iki kez calistirma, mukerrer siparis olur; Day Time degisikligi butun ODATE'leri etkiler
  new_day_hizlandirma:
    title: Uzun suren New Day'i hizlandirmak
    triggers: [new day, yeni gun, newday, slow, yavas, uzun suruyor, long, optimize, hizlandir]
    steps: ctmlog ile New Day'in hangi adimda uzadigini bul; sureyi cogu zaman veritabani belirler: veritabani sunucusunun yukunu, ayni sunucudaki diger ornekleri, depolama gecikmesini ve sanal makinenin asiri paylastirilmis kaynaklarini kontrol et; on New Day suresi yetmiyorsa PRE_NEWDAY_TIME'i artir; AJF'te birikmis eski isleri (Keep Active, NOTOK kalanlar) azalt; istatistik ve gecmis temizligi gibi agir adimlari dokumantasyondaki parametrelerle sinirla; veritabaninin bakimli oldugunu dogrula
    caution: adimlari bilmeden kapatma; gunluk temizligi kapatmak AJF'i buyutur
  agent_portlari:
    title: Ayni hosttaki agent'larin ve guvenlik duvarinin portlari
    triggers: [port, ports, agent, firewall, guvenlik duvari, multiple agents, birden fazla agent, unique, benzersiz, 7005, 7006]
    steps: ayni hosttaki her agent'in portlari benzersiz olmali (sunucu-agent 7006, agent-sunucu 7005, uzak yardimci RU_COMM_PORT 8000 ve kalici baglanti kipinde AR_* portlari); guvenlik duvarinda yalniz sunucu-agent, agent-sunucu ve uzak yardimci portlari acilir; ctmagcfg ile degerleri dogrula
    caution: iki agent'a ayni portu verme; guvenlik duvarinda gereksiz port acma
  mft_tls_surumu:
    title: Dosya aktariminda en dusuk TLS surumunu zorlamak
    triggers: [tls, tlsv1.2, tls 1.2, minimum, en dusuk, ssl version, protocol, mft]
    steps: agent'ta cm/AFT/data altindaki ftpssl_config.properties ve fts_config.properties dosyalarinin yedegini al; izin verilen protokol satirini yalniz TLSv1.2 (ve ustu) olacak sekilde ac; MFT'yi yeniden baslat; karsi sunucuyla bir test aktarimi yap
    caution: TLS'i kapatip duz FTP'ye donme; karsi taraf desteklemiyorsa once onu yukselttir
  sakli_yordam_donus_kodu:
    title: Veritabani isinde sakli yordamin donus kodunu isin sonucuna yansitmak
    triggers: [stored procedure, sakli yordam, return code, donus kodu, exit code, cikis kodu, databases, return_value]
    steps: yordamin RETURN_VALUE ya da OUTPUT degiskenini is tanimindaki Databases sekmesinde bir global degiskene esle; ya da ciktida arayan On/Do kuraliyla kodu belirle; yordam hatayi THROW ya da RAISERROR ile yukseltsin ki is NOTOK bitsin
    caution: yordamin hatayi yutmasina izin verip isi basarili saymak sessiz hataya yol acar
  pg_ha_kullanici_adi:
    title: PostgreSQL yuksek erisilebilirlik kurulumunda replikasyonun 'zaten calisan sureç' diye durmasi
    triggers: [postgresql, postgres, replication, replikasyon, high availability, yuksek erisilebilirlik, already running, secondary, ikinci]
    steps: ayni makinedeki baska bir postgres surecinin yolunda ya da kullanici adinda Control-M kullanici adinin alt dize olarak gecip gecmedigine bak (ornegin ctm9 ve emctm9); geciyorsa farkli bir Control-M kullanicisi ya da farkli kurulum yolu kullan
    caution: diger urunun postgres surecini oldurme
  denetim_raporu:
    title: Kullanicilarin nereden ve ne zaman giris yaptigini ya da bir kosulu kimin degistirdigini raporlamak
    triggers: [audit, denetim, login, giris, who, kim, report, rapor, condition, kosul]
    steps: CCM'de EM sistem parametrelerinde denetimi (auditing) ac; Reporting Facility'de Audit kategorisinde Custom Audit raporu olustur ve islem tipine (Login User, kosul ekleme/silme) gore filtrele
    caution: denetim kapaliyken gecmise donuk bilgi yoktur; denetimi kalici acik tut
  gecit_durum_izleme:
    title: Yonetim sunucusu gecidinin Disconnected ya da No Sync olmasini izleyip haber vermek
    triggers: [gateway, gecit, disconnected, no sync, monitor, izle, alert, uyari, life_check, notification]
    steps: EM sahibi hesabiyla em ctl -mcs -C Gateway -all -cmdstr LIFE_CHECK komutunu calistiran kucuk bir betik yaz; durum Connected degilse e-posta ya da izleme aracina haber ver; betigi Control-M disindan da bagimsiz zamanla (izlenen sistemin kendisi dusebilir)
    caution: izleyiciyi yalniz izlenen zamanlayicinin icine koyma
  gecit_portu:
    title: Gecidin dinledigi portu sabitlemek (guvenlik duvari arkasi)
    triggers: [gateway, gecit, port, firewall, guvenlik duvari, hostportlist, static, sabit, listen, dinle]
    steps: CCM'de EM sistem parametrelerinin Advanced bolumunde gtw tipindeki HostPortList parametresine sabit port ya da aralik ver; guvenlik duvarinda yalniz o portlari actir; gecidi yeniden baslat ve baglantiyi dogrula
    caution: araligi gereksiz genis tutma
  yamada_kapatma_sirasi:
    title: Yuksek erisilebilir ya da dagitik kurulumda yama ve fix pack uygularken surecleri kapatma sirasi
    triggers: [fix pack, fixpack, patch, yama, upgrade, yukselt, high availability, distributed, dagitik, shut down, kapat]
    steps: once ikincil ya da dagitik dugumlerin Configuration Agent'larini, sonra birincil EM ve sunucu bilesenlerini kapat; yamayi birincide uygula, sonra ikincilde; birincili baslatip saglikli oldugunu dogrula, en son ikincilleri baslat
    caution: iki dugumu ayni anda farkli surumlerde calistirma; yamadan once yedek al
  kalip_politika_cli:
    title: Is yuku politikasini komut satirindan acip kapatmak
    triggers: [workload policy, is yuku politikasi, workload, policy, activate, deactivate, cli, komut satiri]
    steps: EM cli yardimcisini -WORKLOAD_ACTIVATE <politika adi> Y ya da N ile calistir (9.0.00 FP1 ve sonrasi); degisikligi CCM'de ya da izleme ekraninda dogrula; gerekiyorsa bunu zamanlanmis bir ise koy
    caution: politikayi kapatmak bekleyen isleri birden saliverir; kaynak ve hedef sistemlerin yukunu dusun
  dr_gecisi:
    title: Zamanlayici sunucusunu felaket kurtarma (DR) sitesine gecirmek ve geri almak
    triggers: [disaster recovery, felaket, dr, failover, failback, site, oracle, mssql, replication, replikasyon]
    steps: once veritabaninin DR tarafina kopyalandigini ve ana sitede hicbir sunucu bileseninin calismadigini dogrula; DR sunucusunun veritabani baglanti ayarlarini kopya veritabanina gosterecek sekilde guncelle; DR'de sunucuyu baslat, agent'larin yeni sunucuya baglandigini ve EM'nin onu gordugunu dogrula; geri donuste ayni adimlari ters sirayla uygula
    caution: iki sitenin sunucusunu ayni anda calistirma; veritabani ayni anda iki yerden yazilirsa bozulur
  agent_gmsa:
    title: Windows agent servisini grup yonetimli servis hesabiyla (gMSA) calistirmak
    triggers: [gmsa, group managed service account, servis hesabi, service account, windows, agent, parola donusu]
    steps: agent 9.0.22 ya da ustu olmali; AD yoneticisi gMSA hesabini olusturup hosta yetki versin (Install-ADServiceAccount, Test-ADServiceAccount); agent servisinin Log On hesabini gMSA olarak ayarla (parola alani bos); gerekli kullanici haklarini ver ve servisi yeniden baslat
    caution: eski surumde gMSA kullanmaya calisma; servis acilmaz
  nfs_destegi:
    title: Zamanlayici bilesenlerini ag dosya sistemine kurmak
    triggers: [nfs, gpfs, cifs, smb, network file system, ag dosya sistemi, shared, paylasim, install]
    steps: urun yalniz NFS surum 3'u (surume gore kismen ya da tam) destekler; GPFS ve CIFS/SMB uzerine kurulum desteklenmez; kurulum ve calisma dizinlerini yerel diske koy, paylasimi yalniz veri icin kullan
    caution: desteklenmeyen dosya sisteminde gecici dosya ve kilit sorunlari cikar
  yeniden_deneme_tasarimi:
    title: Dusen isi belirli bir saatte, gecikmeyle ya da sinirli sayida yeniden calistirmak
    triggers: [rerun, yeniden calistir, retry, tekrar dene, failed, dustu, dusunce, delay, gecikme, specific time, belirli saat, bir kez daha, kopya, cyclic, dongusel]
    steps: belirli saatte yeniden deneme icin isi o saatlerde (ornegin 21:00 ve 23:00) dongusel tanimla ve OK bitince On/Do ile Stop Cyclic yap; gecikmeli ve sinirli deneme icin is tanimindaki rerun ayarini kullan (sondan itibaren aralik, en cok N deneme; deneme sayisina ilk calisma dahil degildir); dongusel isin hata sonrasi hemen tekrar denemesini istemiyorsan Actions'taki NOTOK yeniden calistirma adimini kaldir, dongusellik kalir
    caution: birbirini tetikleyen On/Do kurallari (OK'ta rerun, NOTOK'ta OK say) beklenmeyen dongulere yol acar; isi OK sayarak uyari bastirma
  hata_sayisina_gore_uyari:
    title: Ilk hatalarda sessiz kalip yalniz N'inci hatada ya da son denemede uyari vermek
    triggers: [alert, uyari, mail, e-posta, failure count, hata sayisi, second failure, ikinci hata, fourth, runcount, last run, son calisma, only when]
    steps: isin On/Do bolumunde hata sayisi (number of failures) N'e esitken ya da RUNCOUNT son denemeye esit ve is NOTOK iken shout ya da mail tanimla; sayac is OK bitince sifirlanir; genel uyari parametresini kapatmak yerine is bazinda cozumu tercih et
    caution: 'alert on abend' parametresini genel olarak kapatmak butun islerin otomatik uyarisini kaldirir; tek is icin genel ayari degistirme
  smart_klasor_toplu_bildirim:
    title: SMART klasordeki dusen isler icin tek bir toplu e-posta gondermek
    triggers: [smart folder, smart klasor, smart table, single email, tek e-posta, toplu, all failed jobs, dusen isler, folder, klasor, notify]
    steps: klasordeki her isin On NOTOK'unda is adini klasor ya da global degiskene ekle (ornegin %%\HATALI=%%\HATALI. %%JOBNAME); klasorun kendi On/Do'sunda klasor bitince bu degiskeni iceren tek e-posta gonder; klasor bitiminde degiskeni sifirla
    caution: her is icin ayri mail tanimlayip toplu bildirimle birlikte cift bildirim uretme
  karsilikli_dislama:
    title: Bir grup is calisirken baska bir grubun baslamamasini saglamak
    triggers: [must not start, baslamamali, while running, calisirken, mutual, exclusive, ozel, shared, paylasimli, control resource, kontrol kaynagi, ayni anda]
    steps: ortak bir kontrol kaynagi tanimla; aynı anda calisabilecek isler (A grubu) bu kaynagi Shared kipinde, onlar calisirken baslamamasi gereken isler (B grubu) Exclusive kipinde istesin; B, hicbir A kaynagi tutmazken baslar; davranisi bir test siparisiyle dogrula
    caution: bunu betikle kosul ekleyip silerek kurmak yarim kalan islerde kosulu asili birakir; urunun kaynak mekanizmasini kullan
  hata_sonrasi_bekletme:
    title: Bir is dusunce ona bagli islerin bir sonraki gune de gecmemesi icin kilit birakmak
    triggers: [control resource, kontrol kaynagi, not released, birakilmasin, fails, dusunce, hold, block, engelle, no date, stat]
    steps: kontrol kaynagi is bitince her durumda birakilir, bu ise yaramaz; bunun yerine tarihsiz (No Date, z/OS'ta STAT) bir kosul kullan: is OK bitince kosulu eklesin, NOTOK bitince silsin; bagli isler bu kosulu beklesin; sorun giderilince kosulu elle ekle
    caution: tarihsiz kosulu elle eklemeyi unutmak zinciri gunlerce durdurur; bunu bildirimle birlikte kur
  em_metrik_sorgulari:
    title: Gunluk basarili, basarisiz ve yuklenen is sayilarini raporlamak
    triggers: [report, rapor, metrics, metrik, number of jobs, is sayisi, per day, gunluk, failed, successful, loaded, sql]
    steps: hazir rapor yoksa EM veritabaninda yalniz okuma sorgusuyla gunluk sayilari cikar (is calisma gecmisi tablosunda ended_status 16 OK, 32 NOTOK); New Day'de yuklenen is sayisi icin is yuku raporlarini kullan; sorguyu zamanlanmis bir isle her gun calistir
    caution: EM veritabaninda yazma sorgusu calistirma; sorguyu yogun saatte calistirma
  new_day_dokunmadan_birikim:
    title: Birikmis isleri gunlerce AJF'te tutmak (New Day'i durdurmadan)
    triggers: [new day, yeni gun, backlog, birikmis, week, hafta, clears, siliyor, remove, keep, kalsin, maxwait, max wait]
    steps: New Day'i durdurma; birikmis islere MAXWAIT ver (ornegin 7 gun, 99 suresiz); yalniz NOTOK islerin kalmasi isteniyorsa Keep Days if NOT OK (DAYSKEEPINNOTOK) kullan; New Day sonrasinda islerin AJF'te durdugunu dogrula
    caution: New Day'i kapatmak siparisleri, temizligi ve tarih ilerlemesini durdurur
  tablo_ozel_user_daily:
    title: Bir tabloyu ya da isi New Day disinda kendi saatinde siparis etmek
    triggers: [user daily, ctmudly, specific, ozel, table, tablo, folder, klasor, own time, kendi saati, order, siparis, outside new day]
    steps: tablonun User Daily adini SYSTEM'den farkli bir ada (ornegin GECE2) al; o saatte ctmudly GECE2 calistiran bir is tanimla; ilk gun ctmudchk ile siparisin tam oldugunu dogrula; tek isler icin ctmorder kullan
    caution: ayni tabloyu hem SYSTEM hem ozel User Daily ile siparis etmek mukerrer is uretir
  basarisizlikta_ertesi_gun_bekle:
    title: Is dusunce ertesi gunun kopyasinin calismamasini saglamak
    triggers: [fails, dusunce, next day, ertesi gun, not ordered, siparis edilmesin, set to ok, previous day, onceki gun, prev]
    steps: isi kendine bagla: is OK bitince bir kosul eklesin, ertesi gunun kopyasi bu kosulu PREV tarihle (her gun calismiyorsa ANY) beklesin; is dusunce kosul olusmaz ve ertesi gunun kopyasi bekler; sorun giderilip is OK yapilinca zincir kendiliginden yurur
    caution: kosulu elle eklemek sorunu gizler; once nedeni coz
  ajandaki_isleri_yeni_hosta:
    title: Siparis edilmis isleri yeni bir agent'a tasimak
    triggers: [migrate, tasi, agent, host, machine, makine, already ordered, siparis edilmis, future, gelecek, new host, yeni host]
    steps: isler host grubu kullaniyorsa yalniz grubu guncelle (eski hostu cikar, yenisini ekle); dogrudan host adi kullaniyorsa siparis edilmis isleri tut ve sil, tanimi yeni hostla yukle ve yeniden siparis et ya da tek tek isin host alanini guncelle; sonra bir test isiyle dogrula
    caution: calisan isleri silme; eski hostu ajandaki isler bitmeden kapatma
  api_aktif_is_degistirme:
    title: Automation API ile siparis edilmis bir isin ozelligini degistirmek
    triggers: [automation api, rest, api, modify, degistir, ordered job, aktif is, 415, unsupported media type, from time]
    steps: once get ile isin tum tanimini al; istenen alani (ornegin from time) bu tanimda degistir; tanimin tamamini form-data (multipart) olarak modify ucuna gonder; isin yeni degerini get ile dogrula
    caution: yalniz degisen alani ham JSON olarak gondermek 415 verir; artimli degisiklik desteklenmez
  beklenen_hatayi_guvenle_ok:
    title: Beklenen hatayla biten isi OK gosterip ardillarin yalniz gercek basarida baslamasini saglamak
    triggers: [expected failure, beklenen hata, set to ok, ok gorunsun, successors, ardillar, should not start, baslamasin, sequence, zincir]
    steps: A isine iki kosul ver: OUT kosulu A1-OK ve yalniz OK bitince eklenen ikinci kosul A2-OK (On OK: Add condition); A'nin NOTOK'unda Set OK kullanilabilir; ardil B hem A1-OK hem A2-OK beklesin; boylece A ekranda OK gorunur ama B yalniz gercek basarida baslar; bir test ile her iki yolu dogrula
    caution: yalniz Set OK yapmak ardillari beklenmeyen hataya ragmen baslatir; ikinci kosulu atlama
  kontrollu_baslatma:
    title: Ani kapanmadan sonra islerin hemen kalkmasini engelleyip kontrollu baslatmak
    triggers: [hard down, crash, coktu, ani kapanma, after restart, yeniden baslayinca, jobs take off, hemen calismasin, verify first, once dogrula]
    steps: sunucu acilmadan once ya da acilir acilmaz nicel kaynaklarin en buyuk degerini ecaqrtab ile 0'a cek ya da agent'lari kapali tut; disk, veritabani ve bagli sistemlerin saglam oldugunu dogrula; AJF'teki yarim kalmis isleri gozden gecir; sonra kaynaklari eski degerine al ya da agent'lari sirayla ac
    caution: dogrulamadan tum isleri serbest birakma; yarim kalmis isleri kor yeniden calistirma
  zaman_penceresinde_durdur:
    title: Dongusel ya da duzenli isleri belirli bir saat araliginda durdurmak
    triggers: [stop between, arasinda durdur, arasi, calismamasini, time window, zaman penceresi, maintenance, bakim, cyclic, dongusel, block, workload policy]
    steps: zamanlanmis bir is yuku politikasi (Workload Policy) tanimla ve o pencerede ilgili isleri 0 calisma sinirina cek; politika bitince isler kendiliginden devam eder; alternatif olarak pencerede bir isin tuttugu exclusive kontrol kaynagi
    caution: isi iki ayri tanima bolerek cozmek bakim zorlugu getirir
  dis_tetik_new_day:
    title: Dis uygulamanin kosul ekleyip is tetiklemesinin New Day sirasinda basarisiz olmasi
    triggers: [ctmcontb, ctmvar, external application, dis uygulama, add condition, kosul ekle, new day, ndp, fails, basarisiz]
    steps: urun New Day calisirken yardimci araclari reddeder; cagiran uygulamaya hata kodunu yakalayip birkac dakika sonra yeniden deneyen bir dongu ekle; mumkunse cagrilari New Day penceresinin disina planla; reddedilen cagrilari gunluge yaz
    caution: hatayi yok sayip devam etmek tetiklenmesi gereken isleri sessizce kacirir
---

# Adminlik yordamlari

Her yordam bir genellestirilmis adminlik yetenegidir: tek bir soruya degil, bir is turune yazilir.

| Alan | Anlami |
| --- | --- |
| `triggers` | Istekte gecince bu yordami getiren sozcukler; en az iki tanesi gecmelidir |
| `steps` | Dogru adimlar, sirasiyla |
| `caution` | Bu iste zararli ya da yanlis olan yollar |

Kaynak: BMC toplulugunun en cok okunan bilgi makaleleri (gelistirme tarafi). Metin kendi sozcuklerimizle yazildi.
