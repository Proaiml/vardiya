---
name: talep-standartlari
description: Is tanimlarinda ad, komut yolu ve bildirim adresi icin kurum standartlari.
kind: request_rules
rules:
  ad_bicimi:
    require: name matches std_name_regex
    message: is adi kurum standardina uymuyor (buyuk harf, rakam ve alt cizgi; 4-30 karakter)
  ad_oneki:
    require: name startswith folder_prefix
    message: is adi klasorun onekiyle baslamali
  komut_tam_yol:
    require: command startswith /
    message: komut tam yolla yazilmali
  bildirim_adresi:
    require: notify endswith std_notify_suffix
    message: bildirim adresi kurum alan adinda olmali
---

# Talep standartlari

Bu skill, bir is tanimlama ya da degisiklik talebinin kurum standartlarina uyup uymadigini denetler.
Kurallar veridir: her biri bir kosul (`require`) ve kosul saglanmadiginda talep sahibine donecek gerekcedir
(`message`). Kosul saglanmazsa talep iade edilir.

## Kural yazmak

```
kural_adi:
  require: <olgu> <islec> <deger>
  message: <talep sahibinin okuyacagi gerekce>
  when: <istege bagli: kuralin gecerli oldugu durum>
  severity: error | warning
```

Islecler: `==`, `!=`, `>`, `>=`, `<`, `<=`, `matches` (duzenli ifadenin tamami), `startswith`, `endswith`.
Kosullar ` and ` ile birlestirilir.

Kullanilabilen olgular: `name`, `folder`, `type`, `host`, `run_as`, `command`, `calendar`, `time`, `notify`,
`description`, `dep_count`, `hour`, `minute`, `is_new`, `folder_prefix`, `std_name_regex`, `std_notify_suffix`.

## Skill'in yapamayacaklari

- Yalnizca iade gerekcesi ekleyebilir. Cekirdegin reddettigi bir talebi (var olan is, olmayan host, dongu,
  eksik alan) kabul ettiremez.
- Kod calistiramaz ve dis baglanti tasiyamaz.
- Listede olmayan bir olguya ya da islece basvuran skill yuklenmez.

## Ornek: kurumunuza ozel bir kural

Yeni bir klasor acip kendi `SKILL.md` dosyanizi yazin:

```
---
name: gece-penceresi
description: Komut isleri gece penceresinde baslar.
kind: request_rules
rules:
  gece_penceresi:
    when: type == komut
    require: hour < 6
    message: komut isleri 00:00 ile 06:00 arasinda baslamali
---
```
