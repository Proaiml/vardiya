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
    steps: ilk hatada durmasi icin On-Do'da ON COMPSTAT>0 DO Stop Cyclic tanimla; belirli sayida hatadan sonra durmasi icin isin On-Do kosullarina 'Job's Number of Failures' = N ekle ve eylem olarak Stop Cyclic Run (ya da Rerun) sec; eski surumlerde %%FailCount degiskenini cikiya yazip ona gore On-Do tanimla; tanimi dagitip sonraki dongude dogrula
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
    triggers: [high availability, failover, fallback, yuksek erisilebilirlik, ikinci, birincil, secondary, primary, gecis, geceriz, ctmipc]
    steps: gecis ve geri donus ayni komutla yapilir (ctmipc -msgid MFO -dest CA); birincil calisiyorsa birincilde, birincil kapaliysa ikincilde calistirilir; birincil kapaliysa ikincilde komutu calistirmadan once yaklasik 20 dakika bekle; sonra durumu ve aktif tarafi dogrula
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
    triggers: [adjust condition, oncul calismiyor, predecessor does not run, ignore the condition, kosulu yok say, smart, pazartesi, only on monday, kosulunu bekliyor, beklemeden, waits for the condition]
    steps: SMART klasorde Adjust Condition=Y kullan; zamanlayici sunucusunda config.dat'ta CTM_TABLE_ADJUST_DUMMY=Y ise o gun planlanmayan oncul yerine sahte bir is calisir, kosullari ekler ve ardil bekleme yapmaz; degisikligi bir gunluk planda dene
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
---

# Adminlik yordamlari

Her yordam bir genellestirilmis adminlik yetenegidir: tek bir soruya degil, bir is turune yazilir.

| Alan | Anlami |
| --- | --- |
| `triggers` | Istekte gecince bu yordami getiren sozcukler; en az iki tanesi gecmelidir |
| `steps` | Dogru adimlar, sirasiyla |
| `caution` | Bu iste zararli ya da yanlis olan yollar |

Kaynak: BMC toplulugunun en cok okunan bilgi makaleleri (gelistirme tarafi). Metin kendi sozcuklerimizle yazildi.
