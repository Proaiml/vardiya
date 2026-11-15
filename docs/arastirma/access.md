# Control-M için otomatik agent erişimi

Bu sayfa, bir AI ops agent'ının Control-M/Server, Unix agent, Windows agent ve EM/API'ye nasıl erişmesi gerektiğini özetler. Kaynaklar `controlm_actions.json` içindeki `source` alanlarında. BMC dokümanlarının çoğu (documents.bmc.com, docs.bmc.com) otomatik istemcilere 403 döndürdü; bu yüzden birçok ifade arama sonucu özetine dayanıyor ve dosyada "doğrulanamadı" ile işaretli.

## Genel ilke

- Agent, GUI'yi değil CLI ve REST arayüzlerini kullanmalı. Katalogdaki 68 eylemin 64'ü CLI veya REST ile çalışıyor; GUI'ye bağlı olanlar: `ctmpsm` etkileşimli menü, `ctmagcfg`, `ctmwincfg`, Windows servis yönetimi (`services.msc`).
- Her erişim kanalı için ayrı, en az yetkili bir hesap kullanılmalı. Okuma ve yazma yetkileri ayrı hesaplara verilmeli.
- Yazma eylemleri (hold, rerun, kill, delete, setToOk, ctmvar set/delete, ctmudlst, ctmkeytool, ctm_agstat -UPDATE) insan onayı kapısından geçmeli. Bu, agent'ın yapısal bir kuralı olmalı.
- Parolalar komut satırında görünmemeli. Katalogdaki `ctm config user:password::adminUpdate`, `ctmpwd` ve `ctmsetown` komutları parolayı argüman olarak alıyor; tercihen gizli kasa (vault) veya secret kullanılmalı.

## (a) Control-M/Server host'u

- Erişim: SSH, `ctm` (veya BMC'nin kurduğu) sunucu kullanıcısı ile. Komutlar: `ctmpsm`, `ctm_agstat`, `ctmcontb`, `ctmudly`, `ctmudlst`, `ctmvar`, `ecaqrtab`, `ctmloadset`, `ctm_diag_comm`, `ctmkeytool`, `ctmipc`.
- Öneri: SSH anahtarıyla, parolasız giriş. Anahtar yalnızca sabit bir komut sarmalayıcısına (forced command) bağlanmalı; ham shell açılmamalı. Sarmalayıcı, katalogdaki `id` listesine göre izin vermeli.
- `ctmpsm` etkileşimli menüdür; agent bunu kullanmamalı. Yalnızca `-UPDATEAJF` gibi komut satırı kullanımı tercih edilmeli ve tam sözdizimi önce doğrulanmalı (doğrulanamadı).
- Kaynak: `ctm_agstat`, `ctmcontb`, `ctmudlst`, `ctmvar` sayfaları (documents.bmc.com 9.0.21/9.0.22, arama özetleri).

## (b) Unix agent host'ları

- Erişim: SSH. Hedef kullanıcı mümkünse agent kullanıcısı olmalı. `start-ag` ve `shut-ag` root veya agent sahibi kullanıcı ister (`-u <Agent_User>` seçeneği var).
- `ag_diag_comm` yönetici olmayan kullanıcıda eksik rapor üretiyor; tanı için yetkili hesap gerekir.
- Önerilen sıra: önce `ag_diag_comm` ve `ctm_agstat -LIST` (salt okunur), sonra gerekirse `start-ag`. `shut-ag -p all` yalnızca insan onayıyla.
- Kaynak: `Agent_Utilities` ve `Agent_Troubleshooting_Utilities` (arama özeti).

## (c) Windows agent host'ları

Karşılaştırma (genel bilgi; Microsoft dokümanları bu çalışmada kaynak olarak açılmadı, bu nedenle bu tablo doğrulanmış kaynaklı değildir):

| Kriter | SSH (OpenSSH Server) | WinRM / PowerShell Remoting | RDP |
|---|---|---|---|
| Tür | Komut satırı | Komut satırı, PowerShell nesneleri | Grafik masaüstü |
| Otomasyon uygunluğu | İyi (Windows'ta OpenSSH sunucusu kurulabilir) | En iyi (yapılandırılmış çıktı, oturum, yetki) | Uygun değil (ekran okuma, tıklama, kırılgan) |
| Control-M için | `ag_diag_comm` ve `ctmpwd` komut satırından çalıştırılabilir (yönetici hesabı gerekir) | `Restart-Service`, `Get-Service`, log okuma için uygun | Yalnızca acil durum için insan operatör |
| Kimlik | Anahtar veya parola | Kerberos (domain) tercih edilir | Parola ve oturum |
| Denetim | Oturum logu | PowerShell transcript ve olay günlüğü | Ekran kaydı dışında iz zayıf |

- Sonuç: Windows agent için hedef, PowerShell Remoting (WinRM) veya OpenSSH. RDP otomasyon için önerilmez; agent'ın yapamadığı işler (ör. `ctmwincfg`, `services.msc`) GUI'ye bağlı olduğu için insan operatöre devredilmeli.
- `ag_diag_comm` ve `ctmpwd` Windows'ta yönetici oturumu gerektiriyor.
- Kaynak: Control-M tarafı için `ctmwincfg`, `ctmpwd`, `services.msc` (`Agent_Utilities`, `Agent_Configuration_Utilities`, arama özeti). Protokol karşılaştırması: genel bilgi, kaynak doğrulanmadı.

## (d) EM ve Automation API

- Erişim: REST, `https://<host>:8443/automation-api`. CLI (`ctm`) aynı API'yi sarar.
- Oturum: `POST /session/login` ile token alınır, `POST /session/logout` ile kapatılır. Varsayılan token ömrü 30 dakika (Session service sayfası, arama özeti). BMC, 9.0.21 sonrası için Authentication Service ile API token oluşturulmasını öneriyor; uzun süreli agent için bu daha uygun görünüyor (doğrulanamadı: servis hesabı kılavuzu bulunamadı).
- Başlık tutarsızlığı: bazı örnekler `Authorization: Bearer`, bazıları `x-api-key` kullanıyor. Sürüme göre doğrulanmalı.
- Güvenlik notu: resmi örnek `curl -k` ile TLS doğrulamasını kapatıyor (kendinden imzalı sertifika için). Üretimde CA sertifikası eklenmeli. Aynı örnekte `$username` değişkeni tanımlı değil; bu bir örnek hatası.
- Kaynak: `calling_automation_api_using_curl.sh` (github.com/controlm/automation-api-quickstart); Session service sayfası (arama özeti).

## En az yetki (least privilege)

- Roller ve kullanıcılar Control-M'de Configuration alanındaki Roles ve Access Control sekmelerinde tanımlanıyor. Her API işlemi bir erişim kategorisine bağlı: iş durumunu okuma Monitoring görünümü izni, iş eylemleri (hold, rerun vb.) action izni, rol ve kullanıcı yönetimi Admin Management izni ister (arama özeti, `Automation_API_Authorizations`).
- Örnek kurulum: `ctm config authorization:role::add`, `authorization:user::add`, `authorization:ldap:role::add` (official quickstart `authorization.sh`).
- Önerilen rol ayrımı:
  1. `agent-readonly`: yalnızca Monitoring görünümü (jobs:status, job output/log, agent ping, config okuma). Otomatik teşhis bu rolle çalışmalı.
  2. `agent-remediate`: readonly + job action (hold, free, rerun, kill). Yalnızca onaylı akışlarda kullanılmalı.
  3. Admin Management, kullanıcı parolası ve rol değişiklikleri: agent'a verilmemeli.
- Salt okunur bir API rolünün SaaS sürümünde varlığı doğrulanamadı; Viewer rolü 9.0.21 EM sayfasında geçiyor.
- Sunucu tarafı CLI (ctmcontb, ctmvar, ctmudlst, ctmkeytool) için ayrı bir OS hesabı kullanılmalı; bu hesap yalnızca ilgili dizinlere ve komutlara erişmeli.

## Denetim izi (audit trail)

- Control-M tarafındaki API işlem denetim kaydı için kaynak bulunamadı; arama sonuçlarında denetim logu kapsamı yoktu (doğrulanamadı). Control-M Administration/Security dokümanı veya BMC desteğiyle teyit edilmeli.
- Agent tarafında önerilen yapı (genel uygulama, Control-M dokümanı değil):
  - Her çağrıda: zaman, kullanıcı/token kimliği, olay ID'si, katalog `id`, tam komut (parolalar maskelenmiş), çıkış kodu, dönen durum.
  - Yazma eylemlerinde önce ve sonra durum anlık görüntüsü (`ctm run jobs:status::get` çıktısı).
  - Log, agent'ın yazamayacağı ayrı bir yere (WORM veya merkezi log) gönderilmeli.
- Oturum token'ı loglara yazılmamalı; `session/login` gövdesi maskelenmeli.

## RDP hakkında

- RDP bir grafik protokoldür; otomasyon için genellikle uygun değildir: ekran görüntüsü tabanlı kontrol kırılgandır, yapılandırılmış çıktı vermez, denetim izi zayıftır.
- Control-M için kapsanan işlemlerin çoğu CLI veya REST ile yapılabildiği için RDP gerekmemeli.
- RDP yalnızca yedek, insan operatörün yaptığı acil durum erişimi olarak tutulmalı; agent RDP oturumu açmamalı.

## Açık noktalar

1. Control-M API işlem denetim logu kapsamı (hangi olay, hangi alanlar).
2. Salt okunur API rolünün mevcut sürümdeki karşılığı.
3. Servis hesabı ve Authentication Service token'ının kurulumu (sürüme göre).
4. `ctmipc -msgid MFO`, `ctmagcfg`/`ctmwincfg` bayrakları, `ctm config server:agent::ping` çıktı biçimi.
5. Windows agent için WinRM/OpenSSH'nin Control-M resmi destek durumu.
