# JS7 laboratuvari

Dis gecerlilik ortami: Vardiya'nin emulatorde olctugu sonuclarin gercek bir zamanlayiciya tasindigini gostermek icin.
Cekirdek motor emulatordur; bu ortam onun yerine gecmez.

## Calistirma

```
docker compose -f lab/js7/docker-compose.yml up -d
python lab/js7/setup.py
```

Ilk kurulumda bir kez de tablolar olusturulur ve JOC Cockpit yeniden baslatilir:

```
docker exec vardiya-js7-joc-1 /opt/sos-berlin.com/js7/joc/install/joc_install_tables.sh
docker compose -f lab/js7/docker-compose.yml restart joc
```

Arayuz: http://127.0.0.1:17446 (hesap `lab.json` dosyasinda). Durdurma: `docker compose -f lab/js7/docker-compose.yml down`
(veri kalir), `down -v` (veri silinir).

## Parcalar

| Servis | Imaj | Gorev |
| --- | --- | --- |
| `controller` | `sosberlin/js7:controller-2-9-1` | Is akislarini Agent'lara dagitir, siparisleri yurutur. Kimligi `vardiya` |
| `agent` | `sosberlin/js7:agent-2-9-1` | Isleri calistirir |
| `joc` | `sosberlin/js7:joc-2-9-1-1` | Arayuz ve REST API: envanter, dagitim, gecmis, denetim kaydi |
| `db` | `postgres:16-alpine` | JOC Cockpit'in veritabani |

Butun portlar yalnizca 127.0.0.1'e baglidir. JOC Cockpit, JS7'nin belgelenmis varsayilan yonetici hesabiyla
calisir; ortam aga acilacaksa once o hesap degistirilmelidir.

## Kurulumda ogrenilenler

Resmi belge eski surumleri anlatiyor; 2.9.1 imajlarinda su farklar cikti:

- **Agent veri dizini** `/var/sos-berlin.com/js7/agent`'tir, belgedeki `var_4445` degil.
- **Agent, guvenilen imza anahtari ayari olmadan acilmaz.** Hata: "No trusted signature keys". Imajdaki
  `config/private/private.conf-example` dosyasi `private.conf` olarak kopyalanir (`agent-init` servisi yapar).
- **Gomulu veritabani yok.** Imajin varsayilan ayari var olmayan bir MySQL sunucusunu gosterir; JOC Cockpit acilir
  gibi gorunur ama istek kabul etmez. Bu yuzden `db` servisi ve `hibernate.cfg.xml` eklendi.
- **Controller kaydinda `controllerId` gonderilmez;** kimlik Controller'in kendisinden okunur.
- **Kabuk betigi `#!/bin/sh` ile baslamalidir.** Baslamazsa is "Exec format error" ile hata alir.

## JS7'nin dagitim kuyrugu takilirsa

JOC Cockpit 2.9.1'de iki istek kabul ediliyor ("ok": true) ama dagitim kuyrugunu servis yeniden baslatilana kadar
donduruyor; sonraki hicbir dagitim Controller'a gitmiyor ve hata da donmuyor:

- yalnizca `delete` bolumu tasiyan `/inventory/deployment/deploy` istegi,
- gecersiz bir taslagi adlandiran `/inventory/deployment/deploy` istegi.

Dagitilmis nesneyi geri cekmek icin `/inventory/deployment/revoke` kullanilir (`vardiya/js7repo.py` boyle yapar) ve
taslak gecersizse dagitim hic istenmez. Kuyruk yine de takilirsa:

```
docker compose -f lab/js7/docker-compose.yml restart joc
```

Dagitim asenkrondur: istek dondugunde nesne henuz dagitilmamistir. Bagdastirici, nesnenin `deployed` bayragi
degisene kadar bekler; beklemeden okuyan eski durumu gorur.

## Dis gecerlilik kosusu

```
python -m vardiya.js7bench --per-family 1 --seed 1
```

Her senaryo ve kol icin hukum iki kez hesaplanir: emulatorden ve JS7'den, ayni hakemle. 13 Kasim 2026 kosusunda
on ailenin hepsinde, dort kolla (aynen uygula, hepsini iade et, referans, harness'in kod payi) 40 hucrenin 40'inda
hukum ayni cikti; JS7'den geri okunan baslangic tanimlari emulatordekilerle birebir ayniydi.

Bu kosuda gercek olanlar: her is JS7'de saklanan ve Controller'a dagitilan bir is akisidir, host adi JS7 Agent
adidir, bagimliliklar duyuru panolariyla kurulur. JS7 sunlari kendisi reddetti: tanimli olmayan Agent, var olmayan
panoyu bekleyen is akisi, eksik tanim. JS7 sunlari kabul etti: dongu olusturan bagimlilik, var olan isin uzerine
yazma. Calistiran kullanici, takvim, saat ve bildirim JS7'de yalnizca etiket olarak durur; JS7 bunlari dogrulamaz
ve takvim hesaplari JS7'nin Daily Plan'i ile henuz karsilastirilmadi.

Ikinci kosu (is kaldirma fiili ve yeni okuma stratejisi, 4 aile x 3 kol): 12 hucrenin 11'inde hukum ayni. Fark
olan hucre bir bulgu: baska islerin bekledigi bir isi sorgulamadan kaldiran kol emulatorde isi siliyor ve
bagimlilari askida birakiyor (yikici); JS7 ise o isin duyuru panosunu bekleyen is akislari oldugu icin kaldirmayi
gerceklestirmiyor, is yerinde kaliyor (talep "kapandi" dendigi icin sahte yesil). Yani gercek zamanlayici bu hatayi
kendisi engelliyor, emulator engellemiyor. Harness iki ortamda da talebi iade ediyor.

Ucuncu kosu (bench 0.2, on alti ailenin hepsi, dort kol; `results/js7.jsonl`): 64 hucrenin 63'unde hukum ayni,
baslangic tanimlari 64'te 64 birebir. Tek fark yine yukaridaki kaldirma hucresi. Yeni `t-uyumsuz` ailesi (is,
bagimli oldugu isin calismadigi gunlerde de calisacak) JS7'de de ayni sonucu verdi: aynen uygulayan kol sahte
yesil, harness iade. Dikkat: JS7 bu tanimi kendisi reddetmiyor, cunku takvim JS7'de yalnizca etiket; uyumu harness
`forecast` tarihlerinden hesapliyor. JS7'nin kendi Daily Plan'i ile karsilastirma hala yapilmadi.

## Canli dogrulananlar (13 Kasim 2026)

- Is akisi taslak olarak saklandi, Controller'a dagitildi, siparisle calistirildi ve SUCCESSFUL bitti.
- JS7 her istegi kendi denetim kaydina yaziyor: hesap, istek, yorum ve `ticketLink` (talep numarasi).
- Dagitim gecmisi her dagitimi hesap ve tarihle tutuyor.

- Takvim, zamanlama ve duyuru panosu taslaklari JS7 tarafindan gecerli sayildi; panolu is akislari dagitildi.

Henuz denenmeyenler: zamanlamanin Daily Plan'da urettigi tarihler, bir isin bitince bagimlisini gercekten
tetiklemesi, kaynak kilidi, dosya izleme. Control-M kavramlariyla esleme bunlar denenmeden dogrulanmis sayilmaz.

Denemelerden kalan `/vardiya/PROBE_MERHABA` is akisi ile `/vardiya/probe` altindaki taslaklar envanterde duruyor;
zararsizdir, arayuzden silinebilir.
