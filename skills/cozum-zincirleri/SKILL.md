---
name: cozum-zincirleri
description: Dogru cozulmus gelistirme vakalarindan cikarilan yetenek sirasi; her olay sinifi icin once hangi yetenegin, sonra hangisinin denenecegi.
kind: solution_chains
chains:
  aktarim:
    order: [yordam:aktarim_boyut_dogrulama, genel:ortam_degiskenleri, genel:arsiv_ve_aktarim]
    support: 5
  bildirim:
    order: [sinif:bildirim]
    support: 2
  dosya:
    order: [genel:yeniden_baslatma_dogrulama]
    support: 2
  host:
    order: [genel:ag_baglanti, yordam:agent_portlari]
    support: 9
  ortam_farki:
    order: [genel:ortam_degiskenleri, genel:paylasim_ve_baglama, genel:zamanlanmis_gorevler, genel:dosya_izinleri, genel:yeniden_baslatma_dogrulama]
    support: 5
  parola:
    order: [sinif:parola, genel:yeniden_baslatma_dogrulama]
    support: 2
  plan:
    order: [yordam:eksik_siparis]
    support: 6
  saat_dilimi:
    order: [yordam:k8s_cronjob, genel:saat_senkronu]
    support: 2
  senkron:
    order: [genel:port_kullanimi]
    support: 9
  sertifika:
    order: [yordam:ssl_zincir_testi, yordam:jre_guven_deposu, genel:sertifika_inceleme, genel:servis_yonetimi]
    support: 6
  tarih:
    order: [yordam:kosul_ayarlama]
    support: 5
  windows_yetki:
    order: [genel:windows_kullanici_haklari]
    support: 2
  zaman:
    order: [yordam:dongusel_hata_siniri, genel:yeniden_baslatma_dogrulama]
    support: 4
---

# Cozum zincirleri

Kaynak: `kron-a1` ajaninin yardimsiz ve dogru cozdugu gelistirme vakalari (`python -m vardiya.zincir mine`).
Her adim mevcut bir yetenege eslendi; ayni siniftaki dogru cozumlerde en az iki kez ve cozumlerin en az %30'unda gecen yetenekler, cozumdeki ortalama konumlarina gore siralandi. Eslenemeyen adimlar `results/zincir-bosluklar.jsonl` dosyasinda; yeni yetenek adaylaridir.

`genel:` genel sunucu yetenegi, `yordam:` adminlik yordami, `sinif:` olay sinifinin dogrulanmis duzeltmesi.
