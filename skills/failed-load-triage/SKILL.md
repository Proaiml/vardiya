---
name: failed-load-triage
description: Yukleme isi Ended Not OK oldugunda mukerrer kayit uretmeden toparlar; beklenen hatayi gercek arizadan ayirir.
trigger: status == ended_not_ok and job_class == load
authority: L4
allowed_actions: [hold, free, run_cleanup, rerun, set_to_ok]
evidence: [status, rc, target_rows, sysout_diff]
diagnose:
  partial_load: target_rows > 0 and expected_rc == false
  expected_failure: expected_rc == true and target_rows == 0
  failed_before_write: target_rows == 0 and expected_rc == false
plans:
  partial_load: [hold_downstream, run_cleanup, rerun, free_downstream]
  expected_failure: [set_to_ok]
  failed_before_write: [rerun]
postconditions:
  partial_load: [status == ended_ok, target_rows == source_rows, dupes == 0]
  expected_failure: [status == ended_ok, target_rows == 0]
  failed_before_write: [status == ended_ok, target_rows == source_rows, dupes == 0]
---

# Yukleme isi hata aldiginda

Bir yukleme isi yarida kaldiginda en pahali hata, temizlik yapmadan yeniden calistirmaktir:
is yesile doner ama hedef tabloda ayni kayitlar iki kez bulunur.

## Bakilacaklar

1. Hedef tabloda bu gune ait satir var mi (`target_rows`)? Varsa yukleme yarim kalmistir.
2. Donus kodu isin beklenen hata listesinde mi (`expected_rc`)? Ornek: kaynak bos, "bugun veri yok".
3. Son basarili calismaya gore sysout'ta hangi satirlar yeni (`sysout_diff`)?

## Dallar

- **partial_load**: asagi akisi beklet, yarim veriyi temizle, yeniden calistir, asagi akisi serbest birak.
- **expected_failure**: gerekceyi kanitla, Set to OK ile zinciri surdur. Insan onayi gerekir.
- **failed_before_write**: hedefe hic yazilmamis; dogrudan yeniden calistir.

Dogrulama kosullari saglanmazsa vaka cozulmus sayilmaz ve insana devredilir.
