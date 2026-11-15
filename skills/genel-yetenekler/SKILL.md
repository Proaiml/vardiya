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
  cikis_kodlari:
    title: Cikis kodunu ve sinyali okuyup arizanin turunu cikarmak
    classes: [sinyal, ortam_farki, sessiz, takili]
    triggers: [exit code, cikis kodu, return code, donus kodu, oscompstat, errorlevel, lastexitcode, 126, 127, 139, 143, segfault, segmentation fault, sigterm, sigsegv, 0xc0000005, 0xc0000135, 0xc0000142]
    check_unix: betigi ayni kullaniciyla elle calistirip echo $? ile kodu al; 1 genel hata, 2 yanlis kullanim, 126 dosya calistirilamiyor (izin ya da bicim), 127 komut bulunamadi (PATH), 128+N sinyal N ile sonlandi (130 SIGINT, 137 SIGKILL cogu zaman bellek ya da elle sonlandirma, 139 SIGSEGV, 143 SIGTERM), 255 cogu zaman ssh ya da aralik disi kod; kill -l <kod-128> sinyal adini verir; dmesg -T | tail -30 ile cekirdek iletilerine bak
    check_windows: echo %ERRORLEVEL% ya da $LASTEXITCODE; kodu onaltiliga cevir ('{0:X}' -f <kod>); 0xC0000005 erisim ihlali, 0xC000013A Ctrl+C ya da oturum kapanmasi, 0xC0000135 eksik DLL, 0xC0000142 DLL baslatilamadi (cogu zaman etkilesimsiz oturum), 0xC000007B yanlis mimaride kitaplik, 2 dosya bulunamadi, 5 erisim reddedildi, 1603 kurulum hatasi, 3010 yeniden baslatma bekliyor; net helpmsg <kod> metni verir; Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000} -MaxEvents 5
    fix_unix: kodun anlamina gore ilgili yetenege gec; 126 icin izin ve satir sonu, 127 icin PATH ve tam yol, 137 icin bellek, 139 icin cekirdek dokumu ve surum uyumu, 143 icin isi kimin durdurdugu (zaman asimi, kapanis, operator); betigin gercek kodu dondurdugunu dogrula (son komut, boru hatti, sarmalayici)
    fix_windows: 0xC0000135 ve 0xC000007B icin eksik ya da yanlis mimaride calisma zamani kitapligini kur; 0xC0000142 icin programin etkilesimsiz oturumda arayuz acmaya calismasini gider; 5 icin izin ve kullanici haklari; toplu betikte exit /b %ERRORLEVEL% ile kodu tasi
    caution: cikis kodunu yok sayma; kodu tasimayan sarmalayici (echo, boru hatti, call) gercek hatayi gizler
  satir_sonu_ve_kodlama:
    title: Satir sonu (CRLF), BOM ve karakter kodlamasi sorunlarini bulmak
    classes: [ortam_farki, degisiklik, sessiz]
    triggers: [bad interpreter, ^m, crlf, dos2unix, line ending, satir sonu, utf-8, encoding, kodlama, charset, codepage, kod sayfasi, chcp, nls_lang, locale, bozuk karakter, turkce karakter, garbled]
    check_unix: file <betik> (CRLF line terminators yaziyor mu); head -1 <betik> | od -c | head -2 (\r ve BOM 357 273 277); cat -A <betik> | head -5 (satir sonunda ^M); locale; echo $LANG $LC_ALL; veritabani istemcisinde echo $NLS_LANG
    check_windows: Format-Hex <dosya> | Select-Object -First 3 (EF BB BF BOM, 0D 0A satir sonu); chcp; [Console]::OutputEncoding; $PSDefaultParameterValues
    fix_unix: dos2unix <betik> ya da sed -i 's/\r$//' <betik>; BOM'u kaldir; betigin basinda LANG ve LC_ALL'i acikca ver (zamanlayici ortaminda bos gelebilir); dosyalari aktarirken ikili (binary) kip kullan
    fix_windows: betikleri BOM'suz UTF-8 ya da beklenen kod sayfasiyla kaydet; PowerShell'de -Encoding parametresini acikca ver; cmd icin chcp ile kod sayfasini betigin basinda ayarla
    caution: uretim betigini Windows duzenleyicisinde acip kaydetmek satir sonlarini degistirir; duzeltmeden once yedegini al
  selinux_ve_guvenlik_modulleri:
    title: SELinux, AppArmor ya da uygulama denetiminin isi engelleyip engellemedigini bulmak
    classes: [ortam_farki, windows_yetki, yama, host]
    triggers: [selinux, apparmor, avc, enforcing, getenforce, restorecon, auditd, audit.log, applocker, application control, uygulama denetimi]
    check_unix: getenforce; sestatus; ausearch -m avc -ts recent | tail -20; grep denied /var/log/audit/audit.log | tail; ls -Z <dosya>; ps -eZ | grep <surec>; AppArmor icin aa-status ve dmesg | grep -i apparmor
    check_windows: Get-AppLockerPolicy -Effective -Xml; Get-WinEvent -LogName 'Microsoft-Windows-AppLocker/EXE and DLL' -MaxEvents 20; Get-WinEvent -LogName 'Microsoft-Windows-CodeIntegrity/Operational' -MaxEvents 20
    fix_unix: reddeden kurali bul (audit2why < /var/log/audit/audit.log); yanlis etiketli dosyada restorecon -Rv <yol>; ozel dizin icin semanage fcontext ile kalici etiket; standart disi port icin semanage port; gerekiyorsa guvenlik ekibiyle dar bir ilke modulu
    fix_windows: uygulama denetimi engelliyorsa guvenlik ekibiyle ilgili yol ya da yayimci icin dar bir izin kurali tanimla
    caution: SELinux'u ya da uygulama denetimini toptan kapatma; gecici izinli kip yalniz kisa sureli teshis icindir ve kayda gecmelidir
  sudo_ve_yetki_yukseltme:
    title: sudo, su ve yetki yukseltme sorunlarini bulmak
    classes: [ortam_farki, parola, windows_yetki]
    triggers: [sudo, sudoers, requiretty, nopasswd, a password is required, no tty present, sorry you must have a tty, elevation, elevated, uac, yonetici olarak, yetki yukselt, highest privileges]
    check_unix: sudo -l -U <kullanici>; sudo -n true; echo $? (parolasiz calisiyor mu); visudo -c; grep -r <kullanici> /etc/sudoers /etc/sudoers.d; grep requiretty /etc/sudoers; su - <kullanici> -c id
    check_windows: whoami /groups | findstr /i "Mandatory"; whoami /priv; Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System | Select-Object EnableLUA,LocalAccountTokenFilterPolicy
    fix_unix: zamanlayicinin calistirdigi komut icin sudoers.d altinda dar bir NOPASSWD kurali yaz (yalniz o komut, tam yol); tty isteyen ayari o kullanici icin kaldir (Defaults:<kullanici> !requiretty); visudo -c ile dogrula
    fix_windows: yukseltme gereken isi yonetici haklarina sahip servis hesabiyla ve en yuksek ayricaliklarla calistir; uzak yonetimde yerel hesaplar icin LocalAccountTokenFilterPolicy'nin etkisini bil
    caution: ALL=(ALL) NOPASSWD ALL gibi genis kural yazma; UAC'yi kapatma
  systemd_birim_inceleme:
    title: systemd servis ve timer birimlerinin neden baslamadigini ya da calismadigini bulmak
    classes: [host, ortam_farki, zaman, yama]
    triggers: [systemd, systemctl, unit file, birim dosyasi, timer, oncalendar, execstart, daemon-reload, status=203, status=217, 203/exec, 217/user, linger, journalctl]
    check_unix: systemctl status <birim> --no-pager -l; systemctl cat <birim>; systemctl show <birim> -p ExecMainStatus,ExecMainCode,Result,NRestarts,User,WorkingDirectory,Environment; journalctl -u <birim> -b --no-pager | tail -50; systemctl list-timers --all --no-pager; systemd-analyze calendar '<OnCalendar ifadesi>'; systemd-analyze verify <birim dosyasi>; loginctl show-user <kullanici> -p Linger
    check_windows: (uygulanmaz)
    fix_unix: 203/EXEC calistirilacak dosya yok ya da calistirilamiyor (tam yol, izin, satir sonu, yorumlayici); 217/USER kullanici yok; 200/CHDIR calisma dizini yok; birim dosyasini degistirdikten sonra systemctl daemon-reload; kacirilan zamanlamayi telafi icin timer'da Persistent=true; kullanici servisleri oturum kapaninca duruyorsa loginctl enable-linger <kullanici>; ortam degiskenlerini Environment= ya da EnvironmentFile= ile ver
    fix_windows: (uygulanmaz)
    caution: birim dosyasini /usr/lib altinda degistirme, systemctl edit ile gecersiz kil; Restart=always ile hatayi gizleme
  performans_onceligi:
    title: Yavaslayan isin darbogazini (CPU, bellek, disk, karsi sistem) ayirmak
    classes: [zaman, kaynak, takili, senkron]
    triggers: [slow, yavas, performance, performans, cpu, load average, yuk ortalamasi, iowait, latency, gecikme, uzun suruyor, takes longer, bottleneck, darbogaz, normalden uzun]
    check_unix: uptime ve nproc (yuk ortalamasi cekirdek sayisina gore); vmstat 5 3 (r, b, si, so, wa); iostat -xz 5 2 (await, %util); pidstat -u -d 5 1; top -b -n1 | head -15; sar -u -r -d (gecmis, sysstat kuruluysa); isin onceki calisma sureleriyle ve veri hacmiyle karsilastir
    check_windows: Get-Counter '\Processor(_Total)\% Processor Time','\Memory\Available MBytes','\PhysicalDisk(_Total)\Avg. Disk sec/Transfer','\System\Processor Queue Length' -SampleInterval 5 -MaxSamples 3; Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 ProcessName,Id,CPU,WS
    fix_unix: darbogazi ayir: CPU (r cekirdek sayisindan buyuk), bellek (si ve so sifirdan buyuk), disk (await ve %util yuksek), ag ya da karsi sistem (surec uyuyor, wa dusuk); ayni saatte calisan agir isleri kaydir ya da kaynakla sinirla; veri hacmi buyuduyse isin sure beklentisini guncelle
    fix_windows: ayni ayrim; antivirus taramasi, yedekleme ve yama pencereleriyle cakismayi kontrol et
    caution: neden bulunmadan isin zaman asimini buyutme ya da sunucuyu yeniden baslatma
  dosya_sistemi_saglik:
    title: Salt okunura donen, G/C hatasi veren ya da inode'u biten dosya sistemini bulmak
    classes: [disk, dosya, host, veritabani]
    triggers: [read-only file system, salt okunur, i/o error, input/output error, dosya sistemi, filesystem, fsck, remount, inode, xfs, ext4, stale file handle, structure needs cleaning]
    check_unix: mount | grep -w ro; findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS <yol>; dmesg -T | grep -i -E 'i/o error|ext4|xfs|remount|blk_update' | tail -20; df -i <yol>; test -w <yol> && echo yazilabilir; lsblk -f; multipath -ll (SAN ise)
    check_windows: Get-Volume | Select-Object DriveLetter,HealthStatus,OperationalStatus,SizeRemaining; Get-PhysicalDisk | Select-Object FriendlyName,HealthStatus,OperationalStatus; Get-WinEvent -FilterHashtable @{LogName='System';ProviderName='disk','Ntfs','volmgr'} -MaxEvents 20; fsutil dirty query C:
    fix_unix: dosya sistemi hata yuzunden salt okunura donduyse alttaki depolama sorununu sistem ve depolama ekibiyle coz, sonra planli bir pencerede denetim (fsck ya da xfs_repair) ve yeniden baglama; inode bittiyse cok sayida kucuk dosya ureten dizini bulup temizle ve donusum kur
    fix_windows: birim kirli ya da sagliksizsa depolama ekibiyle planli chkdsk; olay gunlugundeki disk hatalarini donanim ekibine ilet
    caution: bagli ve kullanilan dosya sisteminde fsck calistirma; salt okunura donen diski nedenini bulmadan yeniden yazilir baglama
  kerberos_ve_alan_kimligi:
    title: Kerberos bileti, keytab ve alan (Active Directory) kimlik dogrulamasini sinamak
    classes: [parola, windows_yetki, aktarim, veritabani]
    triggers: [kerberos, kinit, klist, keytab, spn, kdc, gssapi, krb5, clock skew, preauthentication failed, active directory, secure channel, guven kanali, ldap bind]
    check_unix: klist (bilet var mi, suresi); klist -kt <keytab> (anahtar surumleri); grep -E 'default_realm|kdc' /etc/krb5.conf; KDC ile saat farki (5 dakikadan fazlaysa reddedilir); KRB5_TRACE=/dev/stderr kinit -kt <keytab> <principal> ile ayrintili deneme
    check_windows: klist; klist tgt; nltest /dsgetdc:<alan>; nltest /sc_verify:<alan>; setspn -L <hesap>; Test-ComputerSecureChannel; w32tm /query /status
    fix_unix: bilet suresi dolan uzun islerde bileti isin basinda keytab ile al ya da yenileme kur; parola degistiyse keytab'i yeniden uret (anahtar surumu eslesmeli); saat farkini zaman esitlemesiyle gider
    fix_windows: makine hesabinin guven kanali bozuksa alan yoneticisiyle onar; yinelenen ya da eksik SPN'i alan yoneticisine duzelttir
    caution: keytab dosyasini herkesin okuyabilecegi izinle birakma; parolayi betige yazarak bilet alma
  kume_ve_yuksek_erisilebilirlik:
    title: Kumede kaynagin hangi dugumde oldugunu ve gecisin nedenini bulmak
    classes: [host, senkron, veritabani, port_cakismasi]
    triggers: [cluster, kume gecisi, failover, pacemaker, corosync, fencing, stonith, split brain, bolunmus beyin, virtual ip, sanal ip, failover cluster, wsfc, quorum]
    check_unix: pcs status --full ya da crm_mon -1; corosync-quorumtool -s; ip -4 addr show | grep <sanal ip>; journalctl -u pacemaker -u corosync --since -2h --no-pager | tail -50; uygulama surecinin yalniz etkin dugumde calistigini her dugumde ps ile dogrula
    check_windows: Get-ClusterNode; Get-ClusterGroup | Select-Object Name,OwnerNode,State; Get-ClusterResource | Where-Object State -ne 'Online'; Get-ClusterQuorum; Get-WinEvent -LogName 'Microsoft-Windows-FailoverClustering/Operational' -MaxEvents 30
    fix_unix: gecisin nedenini gunlukten bul (kaynak hatasi mi, dugum kaybi mi); neden giderildikten sonra kaynagin hata sayacini temizle (pcs resource cleanup <kaynak>); zamanlayici bilesenlerinin yeni etkin dugumde dogru sirayla acildigini ve sanal adin oraya tasindigini, agent'larin sanal ada baglandigini dogrula
    fix_windows: grubu saglikli dugume tasi ve bagimli kaynaklarin (disk, ad, servis) sirayla acildigini izle
    caution: iki dugumde ayni anda ayni servisi elle baslatma, veri bozulur; cit (fencing) mekanizmasini kapatma
  konteyner_ve_kubernetes:
    title: Pod, Job ve konteynerin neden baslamadigini ya da oldugunu bulmak
    classes: [takili, sinyal, kaynak, ortam_farki, zaman]
    triggers: [kubernetes, kubectl, pod, cronjob, container, konteyner, docker, crashloopbackoff, imagepullbackoff, oomkilled, evicted, backofflimit, namespace, helm]
    check_unix: kubectl get cronjob,job,pod -n <ad alani> -o wide; kubectl describe pod <pod> -n <ad alani> (Events, Last State, Reason, Exit Code); kubectl logs <pod> -n <ad alani> --previous --tail=100; kubectl get events -n <ad alani> --sort-by=.lastTimestamp | tail -20; kubectl top pod -n <ad alani>; docker ps -a --filter status=exited | head; docker logs --tail 100 <konteyner>; docker inspect <konteyner> --format '{{.State.ExitCode}} {{.State.OOMKilled}}'
    check_windows: ayni kubectl ve docker komutlari; kubectl config current-context ile dogru kumeye baktigini dogrula
    fix_unix: OOMKilled ise bellek sinirini isin gercek ihtiyacina gore ayarla; ImagePullBackOff ise imaj adi, etiketi ve cekme gizli anahtarini duzelt; CrashLoopBackOff ise onceki konteynerin gunlugundeki ilk hatayi coz; Pending ise kaynak istegi, dugum secici ve kota; CronJob kaciriyorsa startingDeadlineSeconds, concurrencyPolicy ve suspend alanlarina bak; tek seferlik deneme icin kubectl create job --from=cronjob/<ad> <deneme-adi>
    fix_windows: ayni
    caution: sorunlu pod'u gunlugunu almadan silme; sinirlari tumden kaldirarak cozme
  http_ve_servis_sinama:
    title: HTTP ve REST cagrilarini sinamak, durum kodunu ve vekil ayarini okumak
    classes: [aktarim, senkron, sertifika, parola, host]
    triggers: [http, rest api, curl, 401, 403, 407, 502, 503, 504, proxy, vekil sunucu, bearer, unauthorized, forbidden, bad gateway, gateway timeout, service unavailable, web service, web servisi, endpoint]
    check_unix: curl -sS -o /dev/null -w '%{http_code} %{time_connect} %{time_total}\n' <adres>; curl -v <adres> 2>&1 | head -40 (TLS, yonlendirme, basliklar); env | grep -i -E 'http_proxy|https_proxy|no_proxy'; jetonun bitis zamani ve iki taraf arasindaki saat farki
    check_windows: Invoke-WebRequest <adres> -UseBasicParsing -Method Head | Select-Object StatusCode; curl.exe -v <adres>; netsh winhttp show proxy; Test-NetConnection <host> -Port 443
    fix_unix: 401 kimlik yok ya da suresi dolmus (yeniden oturum ac, jetonu yenile); 403 kimlik var yetki yok (rol ya da izin); 407 vekil kimlik istiyor; 502 ve 504 aradaki gecit ya da yuk dengeleyici arka uca ulasamiyor (arka ucu ve zaman asimini kontrol et); 503 servis kapali ya da asiri yuklu (kisa aralikla sinirli sayida yeniden deneme); ic adresler icin no_proxy tanimla
    fix_windows: ayni; servis hesabinin vekil ayari kullanici oturumundan farklidir, sistem duzeyinde netsh winhttp ile ayarla
    caution: sertifika dogrulamasini kapatarak kalici cozum uretme; jetonlari gunluge ya da is ciktisina yazdirma
  veritabani_baglanti_hatalari:
    title: Veritabani baglanti hatalarini (Oracle TNS, SQL Server oturum, baglanti siniri) ayirt etmek
    classes: [veritabani, parola, kilit, aktarim]
    triggers: [ora-12154, ora-12541, ora-12514, ora-01017, ora-28000, ora-28001, tnsping, tnsnames, listener, dinleyici, login failed, 18456, sqlstate, odbc, jdbc, connection pool, baglanti havuzu, too many connections, max_connections]
    check_unix: tnsping <takma ad>; echo $ORACLE_HOME $TNS_ADMIN; grep -A6 <takma ad> $TNS_ADMIN/tnsnames.ora; lsnrctl status (veritabani sunucusunda); psql 'host=<host> dbname=<db> user=<kullanici>' -c 'select 1'; psql -c 'show max_connections' ve pg_stat_activity'deki oturum sayisi
    check_windows: Test-NetConnection <host> -Port 1521 (ya da 1433); sqlcmd -S <sunucu> -E -Q "select @@servername"; Get-OdbcDsn; 32 bit DSN'ler icin C:\Windows\SysWOW64\odbcad32.exe; SQL Server hata gunlugunde 18456 olayinin State degeri
    fix_unix: ORA-12154 takma ad cozulmuyor (TNS_ADMIN, tnsnames.ora); ORA-12541 dinleyici yok ya da port yanlis; ORA-12514 servis adi dinleyicide kayitli degil; ORA-01017 kullanici ya da parola yanlis; ORA-28000 hesap kilitli; ORA-28001 parola suresi dolmus; hesap ve parola islemleri DBA ile; baglanti sayisi doluyorsa havuz ayarini ve kapanmayan oturumlari bul
    fix_windows: 18456'da State degeri nedeni soyler (2 ve 5 kullanici yok, 7 hesap devre disi, 8 parola yanlis, 18 parola degismeli); 32 bit uygulama 32 bit DSN ister; Windows kimlik dogrulamasinda servis hesabinin yetkisini ve SPN'i kontrol et
    caution: parolayi baglanti dizesinde acik birakma; kilitli hesabi, onu yanlis parolayla deneyen isi bulmadan actirma, yine kilitlenir
  windows_oturum_ve_etkilesim:
    title: Windows'ta oturum 0, arayuz acan program ve kullanici profili sorunlarini bulmak
    classes: [takili, ortam_farki, windows_yetki]
    triggers: [session 0, oturum 0, interactive, etkilesimli, grafik arayuz, pencere aciyor, masaustu, excel, com automation, user profile, kullanici profili, temporary profile, gecici profil, hkcu, logged on, oturum acikken]
    check_unix: (uygulanmaz)
    check_windows: query session; Get-Process -Id <pid> | Select-Object Id,SessionId,MainWindowTitle,Responding; Get-CimInstance Win32_Process -Filter "ProcessId=<pid>" | Select-Object ProcessId,SessionId,CommandLine; Get-CimInstance Win32_UserProfile | Select-Object LocalPath,Loaded,Special; Get-WinEvent -FilterHashtable @{LogName='Application';ProviderName='Microsoft-Windows-User Profiles Service'} -MaxEvents 10
    fix_unix: (uygulanmaz)
    fix_windows: servisler ve zamanlayici isleri oturum 0'da calisir, pencere acan ya da onay isteyen program orada sonsuza kadar bekler; programi sessiz kipte (/quiet, /S, -NonInteractive, -batch) calistir; Office otomasyonu sunucuda desteklenmez, dosyayi kitaplikla isle; kullanici ayari (HKCU, eslenmis surucu, yazici) gerekiyorsa profili yukleyen calistirma kipini kullan ve gecici profil hatasini gider
    caution: servisi masaustuyle etkilesime izin vererek calistirmaya calisma; isin calismasi icin bir kullanicinin oturumunu acik birakma
  antivirus_ve_uc_nokta_korumasi:
    title: Antivirus ya da uc nokta korumasinin isi yavaslatip engellemedigini bulmak
    classes: [takili, zaman, dosya, yama, windows_yetki]
    triggers: [antivirus, anti-virus, defender, virus taramasi, virus scan, exclusion, quarantine, karantina, endpoint protection, on-access, real-time protection, gercek zamanli koruma]
    check_unix: ps -ef | grep -i -E 'falcon|mdatp|ds_agent|savd|clamd|cylance'; top ile tarayici surecinin CPU ve G/C kullanimi; mdatp health (Defender for Endpoint ise); tarayicinin gunlugunde isin dosyalarina ait kayit
    check_windows: Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled,AntivirusSignatureLastUpdated; Get-MpPreference | Select-Object ExclusionPath,ExclusionProcess,ExclusionExtension; Get-MpThreatDetection | Select-Object -First 10; Get-WinEvent -LogName 'Microsoft-Windows-Windows Defender/Operational' -MaxEvents 30
    fix_unix: tarayici isin calisma dizinini ya da gunluklerini kilitliyor ya da yavaslatiyorsa guvenlik ekibiyle urunun onerdigi dizin ve surecler icin dar istisna tanimlat
    fix_windows: ayni; karantinaya alinan dosyayi guvenlik ekibi dogruladiktan sonra geri yukle; taramanin zamanlanmis saatini toplu is penceresinin disina al
    caution: korumayi tumden kapatma; butun diski istisnaya alma
  eposta_sinama:
    title: Posta sunucusuna erisimi ve iletinin neden gitmedigini sinamak
    classes: [bildirim]
    triggers: [smtp, e-posta, eposta, email, relay, 587, 465, starttls, bounced, teslim edilmedi, mailq, postfix, sendmail]
    check_unix: nc -vz <posta sunucusu> 25; openssl s_client -starttls smtp -connect <sunucu>:587 -crlf </dev/null | head -30; tail -50 /var/log/maillog ya da journalctl -u postfix --no-pager | tail -50; mailq (bekleyen iletiler); dig +short mx <alan>
    check_windows: Test-NetConnection <posta sunucusu> -Port 25; Resolve-DnsName <alan> -Type MX; urunun posta gunlugu
    fix_unix: baglanti yoksa guvenlik duvari ve aktarma (relay) izni; relay access denied ise gonderen hostun posta sunucusunda izin listesine eklenmesi; kimlik dogrulama ya da TLS gerekiyorsa urunun posta ayarina kullanici, port ve TLS kipini gir; sinama iletisi gonder; kuyrukta bekleyenleri neden giderilince yeniden gonder
    fix_windows: ayni; gonderen adresin posta sunucusunca kabul edildigini ve iletinin gereksiz klasorune dusmedigini alicida dogrula
    caution: kritik isler icin bildirimi yalniz e-postaya baglama, ikinci bir kanal kur
  degisiklik_guvenligi:
    title: Son degisikligi bulmak, geri almak ve degisikligi guvenle yapmak
    classes: [degisiklik, yama, veritabani, plan]
    triggers: [rollback, geri al, geri donus, degisiklikten sonra, after the change, after deploy, dagitimdan sonra, change window, degisiklik penceresi, config change, ayar degisikligi, onceki surum, previous version, dun calisiyordu, worked yesterday]
    check_unix: ls -lt <yapilandirma dizini> | head; find <dizin> -newermt '<tarih saat>' -type f | head -30; git -C <dizin> log --since=<tarih> --stat (surum denetimindeyse); diff <yedek> <guncel>; rpm -qa --last | head; last -n 20; zamanlayicida is taniminin surum gecmisi
    check_windows: Get-ChildItem <dizin> -Recurse | Where-Object LastWriteTime -gt (Get-Date).AddDays(-2) | Sort-Object LastWriteTime -Descending | Select-Object -First 30 FullName,LastWriteTime; Compare-Object (Get-Content <yedek>) (Get-Content <guncel>); Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10
    fix_unix: her degisiklikten once dosyanin ya da tanimin tarihli kopyasini al; sorun degisiklikle basladiysa once degisikligi geri al, sonra nedenini test ortaminda ara; geri alma adimini degisiklik kaydina yaz
    fix_windows: ayni; kayit defteri icin reg export, servis ayari icin sc qc ciktisini sakla
    caution: ayni anda birden fazla seyi degistirme, hangisinin duzelttigi anlasilmaz; yedeksiz ve kayitsiz degisiklik yapma
  kanit_ve_eskalasyon:
    title: Mudahaleden once kaniti toplamak ve sorunu dogru ekibe dogru bilgiyle iletmek
    classes: [host, veritabani, senkron, yama, takili, kaybolan]
    triggers: [escalate, eskalasyon, support case, destek kaydi, vendor, uretici destegi, root cause, kok neden, postmortem, olay sonrasi, evidence, kanit, before restart, yeniden baslatmadan once]
    check_unix: yeniden baslatmadan once durumu olay kaydina al: ps -ef, df -h, free -m, ss -tnp, dmesg -T | tail -50 ciktisi ve urun gunluklerinin son bolumu; ilk hatanin zaman damgasi; etkilenen isler ve hostlar
    check_windows: Get-Process, Get-Service, Get-Volume ciktisi ve son iki saatin System ile Application hata olaylari olay kaydina; ilk hatanin zamani; etkilenen isler ve hostlar
    fix_unix: kendi alaninda cozemiyorsan ilgili ekibe (veritabani, ag, depolama, guvenlik, uretici) su bilgilerle ilet: ne oldu, ne zaman basladi, etki (hangi isler, hangi teslim saati), yapilan kontroller ve sonuclari, denenen ve geri alinan adimlar, ekli kanit; beklerken ardil isleri tut ve is sahiplerine durum bildir
    fix_windows: ayni
    caution: kaniti toplamadan yeniden baslatma; baska ekibin sistemine (veritabani, ag cihazi) kendi basina mudahale etme
  etki_ve_ardil_yonetimi:
    title: Dusen isin ardillarini ve teslim saatine etkisini yonetmek
    classes: [setok, sessiz, dosya, disk, kilit, sinyal, parola, host]
    triggers: [downstream, ardil isler, successor, bagimli isler, dependent jobs, critical path, kritik yol, bos rapor, eksik veri, sla ihlali, etkilenen isler, teslim saati]
    check_unix: zamanlayicida dusen isin ardillarini ve bekledikleri kosullari listele; hangilerinin basladigini, hangilerinin bekledigini ayir; kritik zincirlerin bitis saatine kalan sureyi hesapla; dusen isin urettigi verinin (dosya, tablo) yarim kalip kalmadigina bak
    check_windows: zamanlayicida dusen isin ardillarini ve bekledikleri kosullari listele; hangilerinin basladigini, hangilerinin bekledigini ayir; kritik zincirlerin bitis saatine kalan sureyi hesapla; dusen isin urettigi verinin (dosya, tablo) yarim kalip kalmadigina bak
    fix_unix: yanlis ya da yarim veriyle calisacak ardillari tut; kok nedeni duzelt; yarim ciktiyi temizleyip isi yeniden calistir; basarili bitince ardillari serbest birak ve zinciri izle; teslim saati riski varsa is sahiplerine tahmini bitis saatiyle haber ver
    fix_windows: yanlis ya da yarim veriyle calisacak ardillari tut; kok nedeni duzelt; yarim ciktiyi temizleyip isi yeniden calistir; basarili bitince ardillari serbest birak ve zinciri izle; teslim saati riski varsa is sahiplerine tahmini bitis saatiyle haber ver
    caution: dusen isi basarili sayip ardillari baslatma; yarim veriyi temizlemeden yeniden calistirma
  yeniden_calistirilabilirlik:
    title: Isin yeniden calistirilmaya dayanikli olup olmadigini ve yarim ciktisini kontrol etmek
    classes: [mukerrer, sessiz, sinyal, disk, kilit, zaman]
    triggers: [idempotent, yeniden calistirilabilir, restartable, checkpoint, kontrol noktasi, yarim kalan, partial output, duplicate rows, mukerrer kayit, cift kayit, kaldigi yerden, ust uste bindi, overlap]
    check_unix: hedef tabloda ya da dizinde bu calismaya ait kayit var mi (calisma kimligi, tarih); gecici ve yarim dosyalar (ls -la <cikti dizini>); isin kontrol noktasi ya da durum dosyasi; ayni isin baska bir kopyasi calisiyor mu (pgrep -af <betik>)
    check_windows: Get-ChildItem <cikti dizini> | Sort-Object LastWriteTime -Descending | Select-Object -First 20; Get-CimInstance Win32_Process | Where-Object CommandLine -like '*<betik>*' | Select-Object ProcessId,CreationDate,CommandLine
    fix_unix: yeniden calistirmadan once yarim ciktiyi temizle ya da isi ayni anahtar icin once sil sonra yukle bicimine getir; uzun islerde kontrol noktasindan surdur; ust uste binmeyi kilit dosyasi (flock -n) ya da zamanlayicinin kaynak mekanizmasiyla engelle
    fix_windows: ayni; ust uste binmeyi zamanlayicinin yeni kopya baslatma ayariyla ya da adlandirilmis kilitle engelle
    caution: ne yazdigini bilmeden yeniden calistirma; mukerrer kaydi silmeden once kapsami is sahibiyle dogrula
  gunluk_ayiklama:
    title: Buyuk gunlukte ilk hatayi, en sik iletiyi ve basarili calismayla farki bulmak
    classes: [sessiz, kaybolan, takili, host]
    triggers: [grep, awk, select-string, ilk hata, first error, zaman damgasi, timestamp, buyuk gunluk, large log, en sik, most frequent, farki karsilastir, compare output]
    check_unix: grep -n -i -E 'error|fail|fatal|exception|denied|refused|timeout' <gunluk> | head -20 (ilk hatalar); grep -c <desen> <gunluk>; sort <gunluk> | uniq -c | sort -rn | head (en sik iletiler); zgrep ile sikistirilmis gunlukler; diff <dunku basarili cikti> <bugunku cikti>
    check_windows: Select-String -Path <gunluk> -Pattern 'error|fail|fatal|exception|denied|timeout' | Select-Object -First 20 LineNumber,Line; Get-Content <gunluk> -Tail 200; (Select-String -Path <gunluk> -Pattern <desen>).Count; Compare-Object (Get-Content <dun>) (Get-Content <bugun>)
    fix_unix: (teshis yetenegi) ilk hatayi bulunca ilgili yetenege gec; basarili calismanin ciktisiyla farki karsilastirmak cogu zaman en hizli yoldur
    fix_windows: (teshis yetenegi) ayni
    caution: yalniz son satira bakma; buyuk gunlugu sunucuda duzenleyiciyle acma
  gizli_bilgi_yonetimi:
    title: Parola ve anahtarlarin nerede durdugunu bulmak ve donusunu eksiksiz yapmak
    classes: [parola, sertifika, aktarim]
    triggers: [secret, vault, kasa, credential, kimlik bilgisi, api key, parola donusu, password rotation, rotated, anahtar donusu, plain text, acik metin, hard-coded, betikte parola]
    check_unix: gizli bilginin nerede durdugunu bul: grep -r -l -i -E 'password|passwd|secret|token' <betik dizini> | head (yalniz dosya adlari); ls -l <kimlik dosyasi> (izin 600 mu); ps -ef ciktisinda komut satirinda parola gorunuyor mu; kasadaki kaydin son degisim tarihi ile zamanlayicidaki kaydin tarihi
    check_windows: Select-String -Path <betik dizini>\* -Pattern 'password|secret|token' -List | Select-Object Path; cmdkey /list; icacls <kimlik dosyasi>
    fix_unix: parola donusunde butun kullanim yerlerini (zamanlayicinin parola kaydi, servis hesabi, baglanti profili, betik, kasadaki kayit) ayni degisiklikte guncelle; betikten acik parolayi cikar, kasadan ya da zamanlayicinin gizli degiskeninden oku; donusten sonra bir test isiyle dogrula
    fix_windows: ayni; servis hesabinin parolasi degistiyse servislerde ve zamanlanmis gorevlerde de guncelle
    caution: parolayi komut satirinda, is ciktisinda, e-postada ya da destek kaydinda acik yazma
  bulut_kimlik_ve_erisim:
    title: Bulut kimligini, izinlerini ve sinirlamalarini (AWS, Azure, GCP) sinamak
    classes: [aktarim, parola, kaynak]
    triggers: [aws, s3, azure, gcp, gcs, blob, iam rol, accessdenied, expiredtoken, throttling, slowdown, 429, rate limit, instance profile, managed identity, service principal, bucket]
    check_unix: aws sts get-caller-identity; aws configure list; aws s3 ls s3://<kova>/<onek> | head -5; az account show; gcloud auth list; hata iletisindeki hata kodu (AccessDenied, ExpiredToken, SlowDown, 429) ve istek kimligi
    check_windows: ayni CLI komutlari; $env:AWS_PROFILE ve benzeri ortam degiskenleri; (Get-Date).ToUniversalTime() (saat farki imzayi bozar)
    fix_unix: AccessDenied ise kimligin rolunde eksik izni (kaynak ve eylem bazinda) bulut yoneticisine tanimlat; ExpiredToken ise gecici kimligi yenile ya da makine kimligi kullan; 429 ve SlowDown icin ustel beklemeli, sinirli sayida yeniden deneme ve eszamanlilik siniri
    fix_windows: ayni
    caution: kalici erisim anahtarini betige ya da is tanimina yazma; kimlige tam yetki vererek cozme
  ag_derin_teshis:
    title: Ara sira kopan baglantiyi (bosta kalma zaman asimi, RST, MTU) bulmak
    classes: [host, aktarim, senkron, zaman]
    triggers: [connection reset, reset by peer, broken pipe, idle timeout, bosta kalma, keepalive, canli tutma, tcpdump, wireshark, mtu, intermittent, ara sira kopuyor, session timeout, 10054, 10053, 10060, econnreset]
    check_unix: ss -tin dst <host> (yeniden iletim); sysctl net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes; tcpdump -nn -i any host <host> and port <port> -c 200 (yetkiyle; RST'yi kim gonderiyor); ping -M do -s 1472 <host> (MTU); mtr -rwc 20 <host>; kopmalar duzenli bir bosta kalma suresinden sonra mi oluyor
    check_windows: Get-NetTCPSetting | Select-Object SettingName,KeepAlive*; netsh interface tcp show global; Test-NetConnection <host> -Port <port> -InformationLevel Detailed; ping -f -l 1472 <host>; kopmalarin saat duzeni
    fix_unix: baglanti duzenli bir bosta kalma suresinden sonra kopuyorsa aradaki guvenlik duvari ya da yuk dengeleyici oturumu dusuruyordur: canli tutma araligini o sureden kisa yap ya da ag ekibinden o akis icin sureyi uzatmasini iste; RST'yi gonderen tarafin gunlugune bak; MTU uyusmazligini yol uzerinde duzelttir
    fix_windows: ayni
    caution: yeniden denemeyi sinirsiz yapip kopmayi gizleme
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
