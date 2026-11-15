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
    caution: iki tarafin ayni anda aktif olmasi veritabanini bozar; birincilin gercekten kapali oldugundan emin ol
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
---

# Adminlik yordamlari

Her yordam bir genellestirilmis adminlik yetenegidir: tek bir soruya degil, bir is turune yazilir.

| Alan | Anlami |
| --- | --- |
| `triggers` | Istekte gecince bu yordami getiren sozcukler; en az iki tanesi gecmelidir |
| `steps` | Dogru adimlar, sirasiyla |
| `caution` | Bu iste zararli ya da yanlis olan yollar |

Kaynak: BMC toplulugunun en cok okunan bilgi makaleleri (gelistirme tarafi). Metin kendi sozcuklerimizle yazildi.
