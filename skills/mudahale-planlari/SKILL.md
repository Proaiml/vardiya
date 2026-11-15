---
name: mudahale-planlari
description: Her ariza sinifi icin kanit toplama ve duzeltme adimlari, harness'in fiilleriyle; tutmazsa harness kaniti yeniden okur.
kind: remediation_plans
plans:
  host:
    steps: [agent_status host={host}, syslog host={host} grep=agent, agent_restart host={host}, agent_status host={host}]
  sertifika:
    steps: [cert_info host={host}, syslog host={host} grep=ssl, cert_renew host={host}, agent_restart host={host}, agent_status host={host}]
  parola:
    steps: [run_as_check host={host} user={run_as}, password_update host={host} user={run_as}, run_as_check host={host} user={run_as}]
  disk:
    steps: [host_df host={host}, list_files host={host} path=/data, file_delete host={host} path=@old_logs, host_df host={host}]
  sinyal:
    steps: [syslog host={host} grep=out of memory, host_mem host={host}, job_definition job={job}, list_hosts, job_update job={job} field=host value=@bigger_host]
  kaynak:
    steps: [resource_status resource={resource}, resource_release resource={resource} holder=@dead_holders]
  ortam_farki:
    steps: [job_definition job={job}, job_update job={job} field=cmd value=@full_path]
  takili:
    steps: [job_status job={pred}, job_set_notok job={pred}, job_rerun job={pred}]
  setok:
    steps: [job_status job={pred}, job_rerun job={pred}]
  dosya:
    steps: [notify to=owner text=beklenen dosya gelmedi; kaynak sistemin sahibine haber verildi, wait minutes=30]
  windows_yetki:
    steps: [run_as_check host={host} user={run_as}, grant_right host={host} user={run_as} right=replace_token]
  veritabani:
    steps: [service_status host={db_host}, syslog host={db_host} grep=postgres, list_files host={db_host} path=/ctm, file_move host={db_host} path=@corrupt to=/tmp/yedek/replorigin_checkpoint, service_restart host={db_host} service=db]
  kilit:
    steps: [job_definition job={job}, job_update job={job} field=resource_guard value=DEFTER]
---

# Mudahale planlari

Her plan bir ariza sinifinin genellestirilmis cozumudur: once kanit okunur, sonra en dar etkili duzeltme uygulanir,
sonra etkisi dogrulanir. Harness plani uyguladiktan sonra isi yeniden calistirir; is yine duserse yeni hata satirini
ve sunucu gunlugunu okuyup sinifi yeniden belirler. Birlesik olaylarda boylece ikinci neden de bulunur.

| Yazim | Anlami |
| --- | --- |
| `fiil anahtar=deger` | harness'in bir fiili ve argumanlari |
| `{host}`, `{job}`, `{run_as}`, `{pred}`, `{resource}`, `{db_host}` | olaydaki isin tanimindan gelir |
| `@old_logs`, `@bigger_host`, `@dead_holders`, `@full_path`, `@corrupt` | onceki okumalardan harness'in sectigi degerler |

Bu planlarda hic gecmeyen fiiller: isi zorla basarili saymak, SSL'i kapatmak, havuz sinirini buyutmek, veri dosyasi
silmek. Plan bir sinifin cozumunu bilmiyorsa harness insan onayi ister, tahmin etmez.

Erisim: Unix sunuculara SSH, Windows sunuculara WinRM/PowerShell Remoting ya da OpenSSH; hepsi yalnizca izin verilen
komutlari calistiran sabit bir sarmalayicidan. Uzak masaustu (RDP) bir otomasyon arayuzu degildir, kullanilmaz.
