# Bileşik (compound) olay kalıpları: batch zamanlayıcılar

Her madde: Belirti -> Nedenler (etkileşim) -> Doğru sıra -> Tehlikeli kısa yol.
Kaynak etiketi: [kaynak: URL] = dış kaynağa dayanıyor; [sentez] = bu çalışmanın birleştirmesi, tek bir kaynakta birebir yok.
Tüm adımlar için sıra kuralı: önce teşhis (salt okuma), sonra en küçük geri alınabilir müdahale, sonra doğrulama, en son yeniden çalıştırma.

---

**1. Disk dolu + downstream job zorla OK işaretlendi**
- Belirti: Job "başarılı" görünüyor ama çıktı dosyası eksik; sonraki adımlar boş veriyle çalışıyor.
- Neden: (a) agent kök diski dolu, yazma sessiz başarısız oluyor; (b) biri downstream'i "success" yaparak zinciri kırdı.
- Doğru sıra: `df -h`, `df -i` ile kök neden; dolu dizini büyüt/temizle; çıktıyı doğrula; yalnız sonra upstream'i yeniden çalıştır.
- Tehlikeli kısa yol: Downstream'i elle success yapıp devam etmek (mark success). Eksik veriyle üretim raporu çıkar.
- Kaynak: Slurm node'u kök disk dolunca DRAIN olur, sinfo -R nedeni gösterir [kaynak: https://support.crusoecloud.com/hc/en-us/articles/52235931715611-How-To-Recover-a-Slurm-Node-Drained-Due-to-Full-Root-Disk]. Zincirin kırılması [sentez].

**2. Disk dolu + Airflow log'ları büyüyor + task'lar kuyrukta kalıyor**
- Belirti: Task'lar queued/scheduled, worker boş görünüyor.
- Neden: (a) log dizini doldu; (b) yarım kalan (zombie) task'lar pool slot'unu tutuyor.
- Doğru sıra: disk ve inode kontrolü; zombie/çalışan task'ların durumunu oku; slot'un gerçekten boşaldığını doğrula; sonra clear.
- Tehlikeli kısa yol: Scheduler'ı hemen yeniden başlatmak (zombie'ler ve log kanıtı kaybolur; disk hâlâ dolu).
- Kaynak: Zombie task'ların slot tutması ve birbirini besleyen gecikme [kaynak: https://oneuptime.com/blog/post/2026-02-17-how-to-fix-zombie-tasks-and-scheduler-lag-in-cloud-composer/markdown]. Log ile disk dolması [sentez].

**3. Pool slot tükenmesi + slot sızıntısı (deferred tetikleyici)**
- Belirti: Pool "dolu" ama hiçbir task çalışmıyor.
- Neden: (a) pool kapasitesi düşük; (b) deferred/trigger olayı sonrası slot sızıyor.
- Doğru sıra: pool get ile kullanım; hangi task'ların slot tuttuğunu bul; sızıntıyı temizle (clear); kapasiteyi kalıcı artır.
- Tehlikeli kısa yol: Pool slot sayısını rastgele büyütmek (sızıntıyı gizler, upstream'i ezer).
- Kaynak: [kaynak: https://github.com/apache/airflow/issues/36998] (slot sızıntısı raporu) ve [kaynak: https://datadriven.io/airflow-task-stuck-in-queued]. Birleşim [sentez].

**4. Parola rotasyonu + servis/agent yeniden başlatması (yama sonrası)**
- Belirti: Yama sonrası agent yeniden başladığında job'lar "authentication failed" ile düşüyor.
- Neden: (a) credential rotasyonu yapıldı ama agent'ın saklı kimliği güncellenmedi; (b) yeniden başlatma saklı oturumu/ortam değişkenini sıfırladı.
- Doğru sıra: önce `systemctl status` ile birimi ve günlüğü oku; yeni kimliği servise uygula; sonra restart; sonra tek bir test job'u.
- Tehlikeli kısa yol: Eski parolayı geri koymak (güvenlik ihlali) ya da tüm job'ları toplu yeniden kuyruğa atmak.
- Kaynak: [sentez]. Systemd komutları [kaynak: https://www.freedesktop.org/software/systemd/man/latest/systemctl.html].

**5. Sertifika süresi dolumu + HA failover**
- Belirti: Failover sonrası yedek düğüm bağlanamıyor, iş kuyruğu donuyor.
- Neden: (a) birincil sertifika süresi dolmuş; (b) yedek de aynı sertifika zincirini kullanıyor; failover bunu gizledi.
- Doğru sıra: `Test-NetConnection -Port` ile TLS/port kontrolü; sertifika tarihini oku; yenilenmiş sertifikayı her iki düğüme dağıt; sonra failover'ı test et.
- Tehlikeli kısa yol: TLS doğrulamasını kapatmak ya da failover'ı geri almadan bırakmak.
- Kaynak: [sentez].

**6. Saat dilimi/DST + döngüsel job çakışması**
- Belirti: Gece job'u iki kez çalıştı ya da hiç çalışmadı.
- Neden: (a) zamanlama yerel saatle, sistem UTC'de; (b) DST geçişinde aynı saat iki kez ya da hiç gelmedi; (c) önceki run bitmemişken yenisi başladı.
- Doğru sıra: zamanlayıcının saat dilimini doğrula; `concurrencyPolicy`/`max_active_runs` eşdeğerini kontrol et; sonra gecikme limitini ayarla.
- Tehlikeli kısa yol: Yinelenen run'ları elle silmek; `Replace` politikasıyla çalışan işi öldürmek.
- Kaynak: Kubernetes CronJob'da timeZone alanı ve concurrencyPolicy (Forbid/Replace) [kaynak: https://jorijn.com/en/knowledge-base/kubernetes/deployments/kubernetes-jobs-cronjobs-batch-workloads/] [kaynak: https://docs.redhat.com/ja/documentation/red_hat_build_of_microshift/4.14/html/api_reference/cronjob-batch-v1]. Birleşim [sentez].

**7. Missed schedule + startingDeadlineSeconds yokken dur**
- Belirti: Zamanlanmış iş bir süre hiç başlamıyor.
- Neden: (a) controller çok sayıda kaçırılmış zamanlamayı sayıyor; (b) startingDeadlineSeconds tanımsız.
- Doğru sıra: CronJob'un `suspend` ve son başarılı zamanını oku; deadline'ı ayarla; kaçırılanı elle `create job --from` ile tek seferlik çalıştır.
- Tehlikeli kısa yol: Tüm birikmiş run'ları birden tetiklemek (yük patlar).
- Kaynak: Kaçırılan zamanlama eşiği (100) [kaynak: https://cronuru.com/guides/kubernetes-cronjob]. Komut [kaynak: https://kubernetes.io/docs/reference/generated/kubectl/kubectl-commands].

**8. Node drain + pod'lar yeniden planlanamıyor (kaynak yetersizliği)**
- Belirti: Bakım için drain edilen node'un pod'ları Pending'de kalıyor.
- Neden: (a) başka node'larda kaynak yetersiz; (b) PodDisruptionBudget engelliyor; (c) emptyDir kullanan pod'lar `--delete-emptydir-data` olmadan reddediliyor.
- Doğru sıra: `kubectl get events`, node kapasitesini oku; gerekiyorsa önce kapasite ekle; sonra `drain` (uygun bayraklarla).
- Tehlikeli kısa yol: `--force` ile zorla drain; bu, controller'sız pod'ları kalıcı siler.
- Kaynak: drain bayrakları [kaynak: https://kubernetes.io/docs/reference/kubectl/generated/kubectl_drain/]. Birleşim [sentez].

**9. Slurm node drain (disk dolu) + iş yeniden kuyruğa**
- Belirti: Node DRAIN, işler PENDING ve "ReqNodeNotAvail".
- Neden: (a) kök disk dolu; (b) hata sonrası iş çalışan node'da kaldı ve kesildi.
- Doğru sıra: `scontrol show node <node>` ile neden; diski temizle; node durumunu doğrula; sonra `State=RESUME`; kesilen işleri `requeue` ile geri al.
- Tehlikeli kısa yol: Node'u diski düzeltmeden RESUME etmek; yeni işler aynı hatada düşer.
- Kaynak: [kaynak: https://support.crusoecloud.com/hc/en-us/articles/52235931715611-How-To-Recover-a-Slurm-Node-Drained-Due-to-Full-Root-Disk] [kaynak: https://slurm.schedmd.com/scontrol.html].

**10. Slurm çalışan iş + süre sınırı yetersiz + checkpoint yok**
- Belirti: İş TIMEOUT ile bitti, sonuç yazılmadı.
- Neden: (a) TimeLimit kısa; (b) uygulama checkpoint yazmıyor; requeue ilerlemeyi kaybettiriyor.
- Doğru sıra: `sacct -j` ile TIMEOUT doğrula; TimeLimit'i yalnızca yetkiyle artır; sonra iş planını düzelt.
- Tehlikeli kısa yol: İşi iptal edip (scancel) sıfırdan göndermek; ilerleme kaybolur.
- Kaynak: `scontrol update JobId=... TimeLimit+=` ve requeue davranışı [kaynak: https://slurm.schedmd.com/scontrol.html].

**11. AutoSys sendevent ile hold + başlama koşulu**
- Belirti: "Hold'u kaldırdım" ama job başlamadı ya da tersi, başka job'lar da başladı.
- Neden: (a) JOB_OFF_HOLD koşullar sağlanırsa başlatır; (b) bağımlı job'lar hâlâ bekliyor.
- Doğru sıra: `autorep -J <job> -q` ile koşulları oku; bağımlılıkları kontrol et; sonra off_hold.
- Tehlikeli kısa yol: FORCE_STARTJOB ile koşulları atlamak.
- Kaynak: [kaynak: https://knowledge.broadcom.com/external/article/397509/jobs-that-were-on-hold-are-running.html].

**12. AutoSys scheduler kapalı + sendevent "başarılı" dönüyor**
- Belirti: Script sendevent'in 0 döndüğünü görüp "tamam" diyor; job çalışmıyor.
- Neden: (a) sendevent yalnızca olayı veritabanına yazar, scheduler çalışmıyorsa işlenmez; (b) sendevent çıkış kodu hedef durumu garanti etmiyor.
- Doğru sıra: scheduler durumunu kontrol et; olayın işlendiğini `autorep` ile doğrula; sonra sonucu raporla.
- Tehlikeli kısa yol: Çıkış kodu 0 diye başarı kabul etmek.
- Kaynak: [kaynak: https://knowledge.broadcom.com/external/article/441090/sendevent-returns-exit-code-0-regardless.html] [kaynak: https://knowledge.broadcom.com/external/article/259721/can-an-autosys-job-be-started-manually-u.html].

**13. Hata yayılımı: upstream failed, downstream upstream_failed**
- Belirti: Onlarca task "upstream_failed", tek bir hata görünür.
- Neden: (a) tek kök neden; (b) clear ile downstream seçimi yanlış (-d kapsamı geniş).
- Doğru sıra: `states-for-dag-run` ile kök task'ı bul; kök nedeni düzelt; sadece kök task'ı ve gerekli downstream'i temizle.
- Tehlikeli kısa yol: Tüm DAG'ı clear etmek; idempotent olmayan yan etkiler (ör. iki kez ödeme) tekrarlanır.
- Kaynak: clear bayrakları [kaynak: https://airflow.apache.org/docs/apache-airflow/stable/cli-and-env-variables-ref.html]. Yan etki riski [sentez].

**14. Yeniden çalıştırma + idempotent olmayan job**
- Belirti: Temizle-yeniden çalıştır sonrası veri çift yazıldı.
- Neden: (a) job idempotent değil; (b) önceki kısmi yazım temizlenmedi.
- Doğru sıra: önce hedef tabloda/dizinde kısmi çıktıyı tespit et; temizle; sonra yeniden çalıştır.
- Tehlikeli kısa yol: Sadece "retry" butonuna basmak.
- Kaynak: [sentez].

**15. Paralel run + kilit dosyası (stale lock)**
- Belirti: Job "zaten çalışıyor" diye çıkıyor, hiçbir süreç yok.
- Neden: (a) önceki düğüm çöktü ve kilit kaldı; (b) zamanlayıcı aynı anda iki run başlattı.
- Doğru sıra: sürecin gerçekten çalışmadığını doğrula (ps/tasklist); kilidi kaldır; sonra tek run.
- Tehlikeli kısa yol: Kilidi sormadan silmek ve yinelenen run'ı başlatmak.
- Kaynak: [sentez].

**16. Yük altında JS7 order askıya + kill sinyali**
- Belirti: Askıya alınan order sonrası task hâlâ çalışıyor ya da veri yarım.
- Neden: (a) Kill=false ise SIGTERM; uygulama sinyali yakalamıyor; (b) suspend ile iş kaynakları bırakılıyor ama kilitler kalıyor.
- Doğru sıra: order durumunu oku; SIGTERM ile bekle; gerekirse Kill; sonra resume.
- Tehlikeli kısa yol: Hemen cancel (SIGKILL) ile order'ı kaldırmak.
- Kaynak: [kaynak: https://www.powershellgallery.com/packages/JS7/2.0.11.0/Content/functions%5CSuspend%20JS7Order.ps1] [kaynak: https://www.powershellgallery.com/packages/JS7/2.0.19.0/Content/functions%5CStop%20JS7Order.ps1].

**17. Windows servis yeniden başlatma + açık işler**
- Belirti: Agent servisi yeniden başlatıldıktan sonra çalışan job'lar kayboldu.
- Neden: (a) servis durdurulunca alt süreçler de sonlandı; (b) Get-WinEvent'te hata olayları önceden oluşmuştu, yeniden başlatma sorunu gizledi.
- Doğru sıra: `Get-WinEvent` ile hata olaylarını kaydet; `Restart-Service -WhatIf` ile etkiyi gör; sonra restart; sonra servis durumunu doğrula.
- Tehlikeli kısa yol: Olayları temizlemeden ve kanıt almadan yeniden başlatmak.
- Kaynak: [kaynak: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/restart-service] [kaynak: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.diagnostics/get-winevent].

**18. Ağ kesintisi + timeout yeniden deneme fırtınası**
- Belirti: Ağ düzeldi ama yüzlerce job aynı anda yeniden denemeye çalışıyor, hedef sistem çöküyor.
- Neden: (a) retry sayısız ve sabit gecikmeli; (b) kuyrukta concurrency sınırı yok.
- Doğru sıra: `Test-NetConnection` ile bağlantıyı doğrula; pool/throttle sınırını düşür; retry'ı kademeli aç.
- Tehlikeli kısa yol: Tüm bekleyen job'ları tek seferde serbest bırakmak.
- Kaynak: [sentez].

**19. Sürüm yükseltme + yeni zamanlama davranışı**
- Belirti: Yükseltmeden sonra job'lar iki kez çalışıyor.
- Neden: (a) yeni sürümde varsayılan concurrencyPolicy farklı (Allow); (b) eski ve yeni zamanlayıcı aynı anda aktif.
- Doğru sıra: CronJob politikasını oku; eski zamanlayıcıyı durdur; sonra yeni tanımı uygula.
- Tehlikeli kısa yol: İki zamanlayıcıyı birlikte bırakmak.
- Kaynak: varsayılan Allow [kaynak: https://docs.redhat.com/ja/documentation/red_hat_build_of_microshift/4.14/html/api_reference/cronjob-batch-v1]; geçiş riski [sentez].

**20. Cron + root olmayan kullanıcı + PATH farkı**
- Belirti: Elle çalışan betik cron'da çalışmıyor.
- Neden: (a) cron ortamı PATH'i kısıtlı; (b) farklı kullanıcının izinleri/ortam değişkenleri yok.
- Doğru sıra: `crontab -u <user> -l` ile tanımı gör; `journalctl` ile hatayı bul; ortamı betikte sabitle.
- Tehlikeli kısa yol: `crontab -r` ile tüm crontab'ı silip yeniden yazmak.
- Kaynak: crontab bayrakları [kaynak: https://man7.org/linux/man-pages/man1/crontab.1.html]. Birleşim [sentez].

**21. Scheduler yeniden başlatma + kaçırılan olaylar**
- Belirti: Scheduler restart sonrası bazı job'lar hiç tetiklenmedi.
- Neden: (a) scheduler kapalıyken gelen olaylar işlenmedi; (b) catch-up kapalı.
- Doğru sıra: scheduler durumunu ve kaçırılan zamanları listele; gerekirse elle tetikle.
- Tehlikeli kısa yol: catchup ile tüm geçmiş dönemi birden çalıştırmak.
- Kaynak: scheduler kapalıyken olayların işlenmemesi [kaynak: https://knowledge.broadcom.com/external/article/259721/can-an-autosys-job-be-started-manually-u.html]. Catch-up riski [sentez].

---

Not: Tüm komutlar [dosya other_actions.json] içinde kaynak URL ile listelenmiştir. Doğrulanamayan sözdizimleri orada "doğrulanamadı" olarak işaretlidir.
