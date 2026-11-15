---
name: genel-yetenekler
description: Urunden bagimsiz sunucu yonetimi yetenekleri (Linux/Unix kabugu, SSH, Windows PowerShell, WinRM, kayit defteri, surecler, servisler, disk, ag, sertifika, saat, izinler). Zamanlayici sorunlari cogu zaman altindaki isletim sisteminde cozulur.
kind: general_skills
skills:
  surec_inceleme:
    title: Calisan surecleri bulmak, ne yaptiklarini gormek ve gerekirse sonlandirmak (gorev yoneticisi)
    classes: [takili, sinyal, kilit, kaynak, host]
    triggers: [process, surec, task manager, gorev yoneticisi, pid, hung, askida, takili, executing, zombie, defunct, cpu]
    check_unix: ps -ef | grep <ad>; ps -o pid,ppid,stat,etime,cmd -p <pid>; top -b -n1 | head -20; pstree -p <pid>; ls -l /proc/<pid>/cwd; cat /proc/<pid>/status
    check_windows: Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 Id,ProcessName,CPU,WS; Get-CimInstance Win32_Process -Filter "ProcessId=<pid>" | Select-Object ProcessId,ParentProcessId,CommandLine,CreationDate; tasklist /v /fi "PID eq <pid>"
    fix_unix: once kill -TERM <pid> ile kibarca durdur, birkac saniye bekle, ancak yanit yoksa kill -KILL <pid>; zombi (Z) surec oldurulemez, ebeveynini (ppid) bul ve onu duzelt
    fix_windows: Stop-Process -Id <pid> (yanit yoksa -Force) ya da taskkill /PID <pid> /T ile alt surecleriyle birlikte sonlandir
    caution: sureci oldurmeden once hangi ise ait oldugunu ve yarim kalan yazmanin veriyi bozup bozmayacagini dogrula; zamanlayicinin kendi sureclerini (agent, tracker, sunucu) elle oldurme, urun komutuyla durdur
  servis_yonetimi:
    title: Bir servisin durumunu, baslama tipini ve calistigi hesabi gormek ve yeniden baslatmak
    classes: [host, parola, windows_yetki, yama]
    triggers: [service, servis, systemctl, daemon, start, stop, restart, yeniden baslat, startup type, logon account, servis hesabi, unavailable]
    check_unix: systemctl status <servis> --no-pager; systemctl is-enabled <servis>; journalctl -u <servis> --since -2h --no-pager | tail -50; systemctl cat <servis>
    check_windows: Get-Service -Name <servis> | Format-List Name,Status,StartType; Get-CimInstance Win32_Service -Filter "Name='<servis>'" | Select-Object Name,State,StartMode,StartName,PathName; sc.exe qc <servis>; sc.exe queryex <servis>
    fix_unix: systemctl restart <servis> ve hemen ardindan status ile acildigini dogrula; acilista baslamasi gerekiyorsa systemctl enable <servis>
    fix_windows: Restart-Service -Name <servis>; baslama tipi icin Set-Service -Name <servis> -StartupType Automatic; servis hesabinin parolasi degistiyse sc.exe config <servis> obj= <hesap> password= <parola> yerine Services konsolundan ya da kasadan guncelle
    caution: servisi yeniden baslatmadan once uzerinde calisan isleri dusun; parolayi komut satirina acik yazma, gecmise ve denetim kaydina dusmesin
  disk_alani:
    title: Dolan diski bulmak ve guvenli yer acmak
    classes: [disk, dosya]
    triggers: [disk, no space left, space, yer, dolu, full, quota, kota, inode, df, du, enospc]
    check_unix: df -h; df -i (inode); du -xh --max-depth=1 <dizin> | sort -h | tail; find <dizin> -xdev -type f -size +500M -mtime +7 -ls; lsof +L1 (silinmis ama acik dosyalar)
    check_windows: Get-Volume | Select-Object DriveLetter,SizeRemaining,Size; Get-ChildItem <dizin> -Recurse -File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 20 FullName,Length,LastWriteTime
    fix_unix: once neyin buyudugunu bul; eski gunlukleri sikistir ya da arsive tasi, donusum (logrotate) kur; silinmis ama acik dosyanin yerini acmak icin onu tutan sureci uygun zamanda yeniden baslat
    fix_windows: eski gunlukleri ve gecici dosyalari tasi ya da sil (Remove-Item yalniz dogruladigin yolda); Disk Cleanup; buyumeyi durduran donusum ayarini yap
    caution: rm -rf ile toptan silme; veri dosyalarini, veritabani dosyalarini ve zamanlayicinin calisan is ciktilarini silme; once listele, sonra tek tek sil
  bellek_ve_oom:
    title: Bellek yetmezligini ve OOM-killer ile oldurulen surecleri bulmak
    classes: [sinyal, kaynak, os_siniri]
    triggers: [memory, bellek, oom, out of memory, killed, 137, sigkill, swap, ram]
    check_unix: free -m; dmesg -T | grep -i -E 'killed process|out of memory'; journalctl -k --since -6h | grep -i oom; cat /sys/fs/cgroup/memory.max (konteyner siniri); vmstat 5 3
    check_windows: Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory,TotalVisibleMemorySize; Get-Process | Sort-Object WS -Descending | Select-Object -First 10 ProcessName,Id,WS; Get-WinEvent -FilterHashtable @{LogName='System';Id=2004} -MaxEvents 5 (kaynak tukenmesi)
    fix_unix: isi daha buyuk bellekli hosta tasi ya da ayni anda calisan agir isleri bir kaynakla sirala; konteyner ya da cgroup sinirini isin gercek ihtiyacina gore ayarla
    fix_windows: bellek tuketen sureci bul; isi baska hosta ya da sakin saate tasi; sayfa dosyasini artirmak gecici cozumdur
    caution: OOM ile dusen isi oldugu gibi yeniden calistirma, ayni yerde yine duser; swap'i kapatma
  ag_baglanti:
    title: Bir hosta ya da porta ulasilip ulasilamadigini adim adim sinamak
    classes: [host, senkron, aktarim, port_cakismasi]
    triggers: [connection refused, connection timed out, timeout, unreachable, ulasilam, network, ag, firewall, guvenlik duvari, port, telnet, ping, no route]
    check_unix: ping -c3 <host>; getent hosts <host>; nc -vz <host> <port>; curl -v telnet://<host>:<port>; traceroute -T -p <port> <host>; ss -tnp | grep <port>
    check_windows: Test-NetConnection <host> -Port <port>; Resolve-DnsName <host>; Get-NetTCPConnection -RemotePort <port> -ErrorAction SilentlyContinue; tracert <host>
    fix_unix: ad cozumlemesi bozuksa DNS ya da /etc/hosts; port kapaliysa karsi tarafta servis acik mi; acik ama ulasilmiyorsa guvenlik duvari kuralini ag ekibine kaynak, hedef ve portla birlikte bildir
    fix_windows: ayni sira; Windows Guvenlik Duvari kurali icin Get-NetFirewallRule ile mevcut kurallara bak, gerekirse ag ekibiyle tek port icin kural ac
    caution: guvenlik duvarini toptan kapatma; sorunu sinamak icin bile tum portlari acma
  dns_ad_cozumleme:
    title: Host adinin dogru ve tutarli cozuldugunu dogrulamak (kisa ad, FQDN, ters kayit)
    classes: [host, parola, senkron]
    triggers: [dns, hostname, host adi, fqdn, kisa ad, short name, resolve, cozumle, nslookup, unknown host, name or service not known]
    check_unix: hostname; hostname -f; getent hosts <ad>; dig +short <ad>; dig +short -x <ip>; cat /etc/hosts; cat /etc/resolv.conf
    check_windows: hostname; [System.Net.Dns]::GetHostEntry('<ad>'); Resolve-DnsName <ad>; Resolve-DnsName <ip>; Get-Content C:\Windows\System32\drivers\etc\hosts
    fix_unix: zamanlayicida tanimli ad ile hostun cozdugu ad birebir ayni olmali; ileri ve ters kaydi DNS ekibiyle duzelt; gecici olarak /etc/hosts kullanirsan kaydini tut
    fix_windows: ayni; Clear-DnsClientCache ile onbellegi temizleyip yeniden sina
    caution: hosts dosyasina kalici ve belgelenmemis kayitlar ekleme; bir hostu iki farkli adla tanimlama
  ssh_erisim:
    title: SSH ile baglanti, anahtar ve host anahtari sorunlarini cozmek
    classes: [aktarim, host, parola]
    triggers: [ssh, sftp, scp, permission denied, publickey, host key, known_hosts, authorized_keys, key exchange, kex, algorithm negotiation]
    check_unix: ssh -vvv -o BatchMode=yes <kullanici>@<host> exit; ssh-keyscan -p <port> <host>; ls -ld ~/.ssh; ls -l ~/.ssh/authorized_keys; sshd -T | grep -i -E 'kex|hostkey|pubkey' (sunucuda); grep sshd /var/log/secure ya da journalctl -u sshd
    check_windows: ssh -vvv <kullanici>@<host> (Windows OpenSSH); Get-Service sshd; icacls $env:ProgramData\ssh\administrators_authorized_keys
    fix_unix: ~/.ssh 700 ve authorized_keys 600, sahibi kullanici olmali; host anahtari degistiyse once degisikligin mesru oldugunu dogrula, sonra ssh-keygen -R <host> ve yeni anahtari al; algoritma uyusmazliginda iki tarafin desteklediklerini -vvv ciktisindan karsilastir
    fix_windows: yonetici kullanicilarin anahtari administrators_authorized_keys dosyasinda ve izni yalniz SYSTEM ve Administrators olmali
    caution: StrictHostKeyChecking=no ile host anahtari kontrolunu kapatma; anahtar izinlerini 777 yapma
  winrm_powershell_uzak:
    title: WinRM ve PowerShell Remoting ile Windows hostunu uzaktan yonetmek
    classes: [host, windows_yetki]
    triggers: [winrm, powershell remoting, invoke-command, enter-pssession, wsman, 5985, 5986, remote powershell, uzak powershell, kerberos, trustedhosts]
    check_unix: (yonetim makinesinden) pwsh -c "Test-WSMan <host>"; nc -vz <host> 5985
    check_windows: Test-WSMan <host>; Test-NetConnection <host> -Port 5985; winrm get winrm/config/client; Get-Item WSMan:\localhost\Client\TrustedHosts; Invoke-Command -ComputerName <host> -ScriptBlock { hostname; whoami }
    fix_unix: hedefte WinRM acik degilse Windows yoneticisinden etkinlestirmesini iste
    fix_windows: hedefte Enable-PSRemoting -Force (yonetici); alan disi hostta HTTPS (5986) dinleyici ve sertifika kullan; TrustedHosts'a yalniz gereken hostu ekle; komutlari Invoke-Command -ScriptBlock ile tek seferde gonder
    caution: TrustedHosts'u * yapma; AllowUnencrypted'i acma; kimlik bilgisini betige yazma, Get-Credential ya da kasa kullan
  kayit_defteri:
    title: Windows kayit defterini okumak ve yedekleyerek degistirmek
    classes: [windows_yetki, yama, host, ortam_farki]
    triggers: [registry, kayit defteri, regedit, reg query, hklm, hkey, hkcu, anahtar, registry key]
    check_unix: (uygulanmaz)
    check_windows: Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\<servis>'; reg query "HKLM\SOFTWARE\<yol>" /s; Get-ChildItem 'HKLM:\SOFTWARE\<yol>'
    fix_unix: (uygulanmaz)
    fix_windows: once reg export "HKLM\<yol>" yedek.reg ile yedek al; sonra Set-ItemProperty -Path 'HKLM:\<yol>' -Name <ad> -Value <deger>; degisiklikten sonra ilgili servisi yeniden baslat ve geri donus icin yedegi sakla
    caution: yedeksiz degistirme; urunun kendi aracinin yaptigi isi elle kayit defterinden yapma; HKLM degisikligi tum makineyi etkiler
  windows_kullanici_haklari:
    title: Windows kullanici haklarini (Local Security Policy) ve grup uyeliklerini dogrulamak
    classes: [windows_yetki, parola]
    triggers: [user rights, kullanici haklari, log on as a batch job, log on as a service, replace a process level token, secpol, 1314, 1385, logon failure, access is denied, erisim reddedildi]
    check_unix: (uygulanmaz)
    check_windows: whoami /priv; whoami /groups; secedit /export /cfg C:\temp\secpol.inf ve SeBatchLogonRight, SeServiceLogonRight, SeAssignPrimaryTokenPrivilege satirlari; net localgroup Administrators; gpresult /r (grup ilkesi)
    fix_unix: (uygulanmaz)
    fix_windows: eksik hakki secpol.msc > Local Policies > User Rights Assignment ile ver (alan ilkesi eziyorsa grup ilkesi yoneticisine); hak degisikliginden sonra hesabin yeniden oturum acmasi ya da servisin yeniden baslamasi gerekir
    caution: hesabi Administrators'a ekleyerek gecistirme; Deny log on haklarini kontrol etmeden hak ekleme
  dosya_izinleri:
    title: Dosya ve dizin izinlerini, sahipligini ve ACL'leri dogrulamak
    classes: [windows_yetki, dosya, ortam_farki, host]
    triggers: [permission denied, izin, erisim reddedildi, access denied, owner, sahip, chmod, chown, icacls, acl, read-only, salt okunur]
    check_unix: id <kullanici>; ls -ld <yol> ve ust dizinleri (namei -l <yol>); getfacl <yol>; lsattr <dosya>; mount | grep <bolum> (ro mu)
    check_windows: icacls <yol>; Get-Acl <yol> | Format-List; (Get-Item <yol>).Attributes
    fix_unix: dosyayi isi calistiran kullaniciya ait yap (chown) ya da gruba okuma/yazma ver (chmod g+rw); yolun her ust dizininde x izni gerekir
    fix_windows: icacls <yol> /grant <hesap>:(M) gibi en dar izni ver; devralma bozuksa /inheritance:e
    caution: chmod 777 ya da Everyone:F verme; guvenlik taramasi bu tur izinleri zayiflik sayar
  ortam_degiskenleri:
    title: Elle calisan komutun zamanlayicida calismamasini (ortam farkini) cozmek
    classes: [ortam_farki, dosya]
    triggers: [command not found, not recognized, works manually, elle calisiyor, path, environment, ortam, profile, profil, .bashrc, env, mapped drive, surucu eslemesi]
    check_unix: zamanlayicinin calistirdigi ortami gor: is icinde env | sort ve which <komut>; elle calisan oturumla karsilastir; kullanicinin .profile ve .bashrc farki (etkilesimli olmayan kabuk .bashrc okumaz)
    check_windows: is icinde set ve where <komut>; elle oturumda ayni; eslenmis surucu (net use) toplu oturumda yoktur, UNC yolu kullan
    fix_unix: komutlari tam yolla yaz ya da betigin basinda gereken PATH ve degiskenleri acikca tanimla (. /home/<k>/.profile); dil ve saat dilimi icin LANG, TZ
    fix_windows: tam yol ya da UNC yolu kullan; kullanici profili gerekiyorsa agent'in Logon As User ayari ve kullanici parolasi
    caution: isi root ya da yonetici olarak calistirarak gecistirme
  kaynak_sinirlari:
    title: Isletim sistemi sinirlarini (acik dosya, surec sayisi, cekirdek parametreleri) bulmak ve artirmak
    classes: [os_siniri, kaynak, host]
    triggers: [too many open files, ulimit, nofile, nproc, max user processes, resource temporarily unavailable, fork, limit, sinir, descriptor]
    check_unix: ulimit -a (isi calistiran kullaniciyla); cat /proc/<pid>/limits; ls /proc/<pid>/fd | wc -l; cat /etc/security/limits.conf /etc/security/limits.d/*; systemctl show <servis> -p LimitNOFILE
    check_windows: Get-Process -Id <pid> | Select-Object Handles,Threads; (Get-Counter '\Process(*)\Handle Count').CounterSamples | Sort-Object CookedValue -Descending | Select-Object -First 5
    fix_unix: limits.conf ya da systemd birimindeki LimitNOFILE ve LimitNPROC degerini urunun onerdigi degere (cogu zaman en az 4096) cikar; surec yeniden basladiktan sonra /proc/<pid>/limits ile dogrula
    fix_windows: tutamak sizdiran sureci bul ve yeniden baslat; kalici cozum icin ureticiye bildir
    caution: sinirlari sinirsiz (unlimited) yapma; sizintiyi gizler
  sertifika_inceleme:
    title: Sertifikanin suresini, zincirini ve guven deposunu incelemek
    classes: [sertifika, aktarim]
    triggers: [certificate, sertifika, ssl, tls, expired, suresi dolmus, handshake, pkix, unable to get local issuer, truststore, keystore, keytool, x509]
    check_unix: openssl s_client -connect <host>:<port> -servername <host> -showcerts </dev/null; openssl x509 -in <dosya> -noout -subject -issuer -enddate; keytool -list -v -keystore <depo> | grep -E 'Alias|Valid|Owner|Issuer'
    check_windows: Get-ChildItem Cert:\LocalMachine\My | Select-Object Subject,NotAfter,Thumbprint; certutil -verify <dosya>; Test-NetConnection <host> -Port <port>
    fix_unix: suresi dolani yenile; zincirde ara sertifika eksikse sunucu tarafinda zinciri tamamla; istemci guvenmiyorsa kok ya da ara CA'yi kullanilan guven deposuna keytool -importcert ile ekle; ilgili sureci yeniden baslat
    fix_windows: sertifikayi uygun depoya (LocalMachine\My ya da Root) aktar; ozel anahtar erisimini servis hesabina ver
    caution: SSL'i ya da sertifika dogrulamasini kapatma; bitis tarihlerini izlemeye al
  saat_senkronu:
    title: Sistem saatini, saat dilimini ve zaman esitlemesini dogrulamak
    classes: [saat_dilimi, senkron, sertifika, tarih]
    triggers: [time, saat, clock, ntp, chrony, timezone, saat dilimi, dst, yaz saati, drift, skew, w32tm, utc]
    check_unix: timedatectl; chronyc tracking ya da ntpq -p; date; date -u; echo $TZ; ls -l /etc/localtime
    check_windows: w32tm /query /status; w32tm /query /source; tzutil /g; Get-Date; [System.TimeZoneInfo]::Local
    fix_unix: zaman esitlemesini (chronyd) etkinlestir; saat dilimini timedatectl set-timezone ile tum hostlarda tutarli yap; Java kullanan urunlerde JRE saat dilimi verisi de guncel olmali
    fix_windows: w32tm /resync; saat dilimi tzutil /s ile; alan uyesi hostta saat kaynagi alan denetleyicisidir
    caution: calisan bir zamanlayici sunucusunda saati elle ileri geri alma; New Day ve dongusel isler karisir
  gunluk_inceleme:
    title: Sistem ve uygulama gunluklerinde sorunun izini bulmak
    classes: [host, sessiz, takili, yama, senkron]
    triggers: [log, gunluk, journal, event viewer, olay goruntuleyici, syslog, messages, error, hata, event id]
    check_unix: journalctl --since '<saat>' --until '<saat>' --no-pager | grep -i <anahtar>; tail -n 200 /var/log/messages; grep -i <anahtar> <urun gunlugu>; zaman damgasina gore olaydan once ilk hatayi bul
    check_windows: Get-WinEvent -FilterHashtable @{LogName='System','Application';StartTime=(Get-Date).AddHours(-2)} | Where-Object LevelDisplayName -in 'Error','Warning' | Select-Object -First 50 TimeCreated,ProviderName,Id,Message
    fix_unix: (teshis yetenegi) bulunan ilk hatayi ilgili sinifin cozumuyle eslestir
    fix_windows: (teshis yetenegi) ayni
    caution: en son hataya degil, zincirin ilk hatasina bak; gunlukleri temizleyerek yer acma, kanit kaybolur
  port_kullanimi:
    title: Bir portu hangi surecin tuttugunu bulmak
    classes: [port_cakismasi, host, senkron]
    triggers: [address already in use, port in use, port, bind, listen, dinle, eaddrinuse, cakisma, conflict, netstat]
    check_unix: ss -ltnp | grep :<port>; lsof -i :<port>; fuser <port>/tcp
    check_windows: Get-NetTCPConnection -LocalPort <port> | Select-Object LocalAddress,State,OwningProcess; Get-Process -Id <pid>; netstat -ano | findstr :<port>
    fix_unix: portu tutan surec beklenmeyen bir uygulamaysa onu tasi ya da urune baska port ver; ayni urunun eski bir sureci kaldiysa urun komutuyla durdur
    fix_windows: ayni
    caution: portu tutan sureci kimin oldugunu bilmeden oldurme
  dosya_kilidi:
    title: Bir dosyayi ya da tabloyu kimin kilitledigini bulmak
    classes: [kilit, dosya, takili]
    triggers: [lock, kilit, locked, being used by another process, text file busy, in use, kullaniliyor, sharing violation, ora-00054, deadlock]
    check_unix: lsof <dosya>; fuser -v <dosya>; veritabaninda kilit sorgusu (ornegin pg_locks, v$locked_object) DBA ile
    check_windows: openfiles /query /fo table (once openfiles /local on); Get-SmbOpenFile | Where-Object Path -like '*<ad>*'; handle.exe <ad> (Sysinternals, varsa)
    fix_unix: kilidi tutan sureci ve sahibini bul; is bitince serbest kalacaksa bekle; asili kaldiysa sahibiyle konusarak sureci durdur; tekrarlaniyorsa isleri zamanlayicida bir kaynakla sirala
    fix_windows: ayni; paylasimdaki acik dosyayi Close-SmbOpenFile ile kapatmak son caredir
    caution: kilitli dosyayi silip yeniden olusturma; veritabani kilidini DBA'siz oldurme
  zamanlanmis_gorevler:
    title: Isletim sisteminin kendi zamanlayicisini (cron, systemd timer, Windows Gorev Zamanlayici) incelemek
    classes: [zaman, mukerrer, plan]
    triggers: [cron, crontab, timer, scheduled task, gorev zamanlayici, task scheduler, schtasks, at, anacron]
    check_unix: crontab -l -u <kullanici>; ls /etc/cron.d /etc/cron.daily; systemctl list-timers --all; grep CRON /var/log/cron ya da journalctl -u cron
    check_windows: Get-ScheduledTask | Where-Object State -ne 'Disabled' | Select-Object TaskPath,TaskName,State; Get-ScheduledTaskInfo -TaskName <ad>; schtasks /query /tn <ad> /v /fo list
    fix_unix: ayni isi hem cron hem urun calistiriyorsa birini kapat; zamanlamayi tek yerde tut
    fix_windows: gorevi Disable-ScheduledTask ile kapat, silmeden once tanimini Export-ScheduledTask ile yedekle
    caution: baskasinin gorevini silme; once kimin kurdugunu bul
  paket_ve_surum:
    title: Kurulu yazilim surumunu, yamalari ve son degisiklikleri bulmak
    classes: [yama, degisiklik]
    triggers: [version, surum, patch, yama, upgrade, yukselt, update, guncelleme, after upgrade, yamadan sonra, hotfix, kb]
    check_unix: rpm -qa --last | head -30 ya da grep ' install \| upgrade ' /var/log/dpkg.log; uname -a; cat /etc/os-release; java -version; urunun kendi surum komutu
    check_windows: Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 15; Get-CimInstance Win32_Product -Filter "Name like '%<ad>%'" | Select-Object Name,Version (yavas) ya da kurulu programlar listesi: Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninst*\* | Select-Object DisplayName,DisplayVersion; [Environment]::OSVersion
    fix_unix: sorunun baslama zamanini son degisiklikle karsilastir; urun uyumluluk tablosuna bak; gerekiyorsa degisikligi geri almayi degisiklik yonetimiyle planla
    fix_windows: ayni; bir yamanin geri alinmasi gerekiyorsa bunu degisiklik kaydiyla ve Windows yoneticisiyle planla
    caution: uyumluluk tablosuna bakmadan isletim sistemi ya da Java yukseltme; uretimde geri donus plani olmadan yama kaldirma
  java_ortami:
    title: Urunun kullandigi Java'yi, bellek ayarini ve guven deposunu bulmak
    classes: [sertifika, sinyal, yama, aktarim]
    triggers: [java, jre, jdk, jvm, heap, xmx, outofmemoryerror, cacerts, keytool, java_home, hs_err]
    check_unix: urun dizinindeki JRE baglantisini bul (ls -l <urun>/JRE*); <jre>/bin/java -version; ps -ef | grep java ile calisan -Xmx degerleri; hs_err_pid*.log dosyalari
    check_windows: Get-CimInstance Win32_Process -Filter "Name='java.exe'" | Select-Object ProcessId,CommandLine; <jre>\bin\java -version
    fix_unix: urunun kendi JRE'sini kullan; bellek ayarini urunun yapilandirma dosyasindan ve destek yonlendirmesiyle degistir; guvenilecek CA'yi urunun kullandigi depoya ekle (sistemin cacerts'i degil olabilir)
    fix_windows: ayni
    caution: urunun JRE'sini sistem Java'siyla degistirme; heap degerini rastgele buyutme
  kullanici_ve_parola:
    title: Hesabin kilitli, suresi dolmus ya da parolasi degismis olup olmadigini bulmak
    classes: [parola, windows_yetki]
    triggers: [password, parola, expired, suresi dolmus, locked, kilitli hesap, account locked, logon failure, authentication failed, kimlik dogrulama]
    check_unix: chage -l <kullanici>; passwd -S <kullanici>; faillock --user <kullanici> ya da pam_tally2; id <kullanici>; grep <kullanici> /var/log/secure
    check_windows: net user <kullanici> /domain; Get-LocalUser <kullanici> | Select-Object Name,Enabled,PasswordExpires,PasswordLastSet; Get-ADUser <kullanici> -Properties LockedOut,PasswordLastSet,PasswordExpired (AD modulu varsa)
    fix_unix: kilidi kaldirmak ve parolayi yenilemek hesap sahibinin ya da kimlik ekibinin isidir; yeni parolayi urunun parola deposuna urun komutuyla gir
    fix_windows: ayni; servis hesabiysa servislerde ve zamanlayicinin parola kaydinda da guncelle
    caution: parolayi betige, is tanimina ya da destek kaydina yazma; servis hesabini 'parola hic dolmasin' yapmak icin kimlik ekibinin onayi gerekir
  paylasim_ve_baglama:
    title: Ag paylasimlarini (NFS, SMB) ve baglama noktalarini dogrulamak
    classes: [dosya, ortam_farki, aktarim, disk]
    triggers: [nfs, smb, cifs, share, paylasim, mount, bagla, unc, mapped drive, stale file handle, network path, ag yolu]
    check_unix: mount | grep -E 'nfs|cifs'; df -h <yol>; showmount -e <sunucu>; ls <yol> (stale file handle var mi)
    check_windows: Get-SmbMapping; net use; Test-Path \\<sunucu>\<paylasim>; Get-SmbConnection
    fix_unix: bozuk baglamayi umount -l ve yeniden mount ile onar; kalici baglama /etc/fstab ya da automount ile
    fix_windows: isler toplu oturumda calistigi icin surucu harfi yerine UNC yolu kullan; servis hesabinin paylasimda izni olmali
    caution: baglama noktasinin altinda calisan isleri dusurmeden zorla ayirma
  arsiv_ve_aktarim:
    title: Dosyalari guvenle tasimak, sikistirmak ve butunlugunu dogrulamak
    classes: [aktarim, dosya, disk]
    triggers: [copy, kopyala, transfer, aktarim, checksum, md5, sha256, size, boyut, partial, yarim dosya, tar, zip, gzip]
    check_unix: ls -l <dosya>; sha256sum <dosya>; stat <dosya>; lsof <dosya> (hala yaziliyor mu)
    check_windows: Get-FileHash <dosya> -Algorithm SHA256; Get-Item <dosya> | Select-Object Length,LastWriteTime
    fix_unix: yarim dosyayi okumamak icin gecici adla yazip sonra yeniden adlandirma ya da tamamlanma isaret dosyasi kullan; boyut ve ozetle karsilastir
    fix_windows: robocopy <kaynak> <hedef> <dosya> /Z /R:3 /W:10; ozetle dogrula
    caution: dogrulamasiz uzerine yazma; aktarim dogrulamasini kapatarak hatayi gizleme
  veritabani_istemci:
    title: Veritabanina baglanip durum, kilit ve alan bilgisini okumak
    classes: [veritabani, kilit, disk]
    triggers: [database, veritabani, sql, oracle, postgres, postgresql, mssql, sqlplus, psql, sqlcmd, tablespace, connection, ora-]
    check_unix: psql -c 'select now()' ve pg_stat_activity, pg_locks; sqlplus ile v$session ve dba_free_space (DBA yetkisiyle); baglanti dizesinin dogrulugu
    check_windows: sqlcmd -S <sunucu> -Q "SELECT @@VERSION"; sys.dm_exec_requests ve sys.dm_tran_locks
    fix_unix: yalniz okuma sorgulari; kilit, alan ve parametre degisikligini DBA yapar
    fix_windows: ayni
    caution: uretim veritabaninda elle UPDATE, DELETE ya da oturum oldurme yapma
  etkilesimli_betik:
    title: Kullanicidan girdi bekledigi icin takilan betigi bulmak (zamanlayicida klavye yoktur)
    classes: [takili, sessiz]
    triggers: [hangs, takili, executing, read-host, pause, prompt, input, girdi, interactive, etkilesimli, press any key, y/n, password prompt]
    check_unix: is ciktisinin son satirlarina bak (soru mu soruyor); betikte read, select, passwd, ssh ya da sudo parola sorgusu var mi; ps -o pid,stat,wchan -p <pid> ile surec okuma bekliyor mu; ls -l /proc/<pid>/fd/0
    check_windows: betikte Read-Host, Pause, Get-Credential, choice, set /p var mi; is ciktisinin sonunda 'Press any key' ya da onay sorusu var mi; Get-CimInstance Win32_Process ile surecin hala yasadigini dogrula
    fix_unix: etkilesimi kaldir: girdiyi parametreyle ya da dosyayla ver, ssh icin -o BatchMode=yes ve anahtar, sudo icin parolasiz kural; betigi stdin </dev/null ile calistir ki girdi beklerse hemen hata versin
    fix_windows: Read-Host ve Pause'u kaldir, degerleri parametreyle ver; PowerShell'i -NonInteractive ile cagir; onay isteyen komutlara -Confirm:$false ya da /y ver; asili sureci sonlandirip isi yeniden calistir
    caution: takili isi OK sayma; parolayi betige acik yazarak etkilesimi kaldirma
  windows_olay_kimlikleri:
    title: Windows olay kimliklerinden sorunun turunu cikarmak
    classes: [windows_yetki, host, parola, yama]
    triggers: [event id, olay kimligi, event viewer, 7000, 7009, 7031, 7034, 4625, 4740, 1000, 6008, service control manager]
    check_unix: (uygulanmaz)
    check_windows: Get-WinEvent -FilterHashtable @{LogName='System';Id=7000,7009,7031,7034,6008} -MaxEvents 20; Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625,4740} -MaxEvents 20; Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000} -MaxEvents 10
    fix_unix: (uygulanmaz)
    fix_windows: 7000/7009 servis baslamadi (hesap, parola, zaman asimi); 7031/7034 servis beklenmedik durdu; 4625 basarisiz oturum, 4740 hesap kilitlendi; 1000 uygulama coktu; 6008 beklenmeyen kapanma; olayi ilgili sinifin cozumuyle eslestir
    caution: olay gunluklerini temizleme
  yeniden_baslatma_dogrulama:
    title: Duzeltmeden sonra yeniden baslatip gercekten duzeldigini dogrulamak
    classes: [host, takili, sinyal, disk, sertifika, parola, kaynak]
    triggers: [restart, yeniden baslat, rerun, yeniden calistir, verify, dogrula, after fix, duzelttikten sonra]
    check_unix: duzeltmeden once belirtiyi kaydet (hata satiri, durum); duzeltmeden sonra ayni komutu tekrar calistir ve farki karsilastir
    check_windows: ayni
    fix_unix: once en kucuk birimi yeniden baslat (is, sonra servis, en son host); her adimdan sonra durumu dogrula; is basarili bitince ardillarin da yurudugunu ve gecmiste ayni hatanin tekrar edip etmedigini kontrol et
    fix_windows: ayni
    caution: hostu yeniden baslatmayi ilk care yapma; ayni hata ikinci kez cikiyorsa yeniden baslatmayi tekrarlama, nedeni ara
---

# Genel yetenekler

Zamanlayici sorunlarinin buyuk kismi urunun icinde degil, altindaki isletim sisteminde cozulur: dolan disk, kilitli
hesap, kapali port, yanlis saat, eksik Windows hakki, suresi dolmus sertifika. Bu beceri o katmanin yeteneklerini
urunden bagimsiz olarak toplar; bir olay sinifi eslesince ona bagli genel yetenekler de ajana verilir.

| Alan | Anlami |
| --- | --- |
| `classes` | Bu yetenegin yardim ettigi olay siniflari; sinif eslesince yetenek de verilir |
| `triggers` | Istekte gecince yetenegi getiren sozcukler; en az iki tanesi gecmelidir |
| `check_unix`, `check_windows` | Yalniz okuma, teshis komutlari |
| `fix_unix`, `fix_windows` | Duzeltme yolu; yazma eylemi erisim katmaninin duzey kurallarina tabidir |
| `caution` | Bu iste zararli ya da yanlis olan yollar |

Komutlar okuma ve teshis icindir; yazan her eylem `vardiya/erisim.py` uzerinden, izin listesi, duzey ve denetim
kaydiyla calisir. Uzak masaustu (RDP) bir otomasyon arayuzu degildir; yalniz grafik arayuzle yapilabilen is bir
insana devredilir.
