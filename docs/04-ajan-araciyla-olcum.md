# Bir ajan aracını bench'e sokmak

Bazı modellere API ile ulaşılamaz; yalnızca bir aracın içinden kullanılabilirler (örnek: Antigravity içindeki
Gemini 4 Hydrogen). Bu durumda model, bench'in "ham model" koltuğuna komut satırı üzerinden oturtulur: ajan
kabukta komut çalıştırır, köprü her talebi sırayla verir ve yaptıklarını kaydeder.

Ölçülen şey modelin tek başına muhakemesidir: ajan zamanlayıcının ham fiilleriyle baş başadır, harness yoktur.

## Adımlar

1. Oturumu başlat (bu komutu sen çalıştır):

```
python -m vardiya.agentbench start --name hydrogen --label "antigravity:gemini-4-hydrogen-extra" --per-family 2 --seed 1
```

On iki aileden ikişer, toplam 24 talep hazırlanır. Tohum 1 olduğu için aynı talepler diğer kollarla eşleşir.

2. Antigravity'de modeli seç, proje klasörü olarak `C:\D\projeler\schedularharness` açıkken aşağıdaki istemi yapıştır.

3. Ajan "Butun talepler bitti" çıktısını görünce sonucu al:

```
python -m vardiya.agentbench report --name hydrogen
python -m vardiya.agentbench merge --name hydrogen
python -m vardiya sab report
```

`merge`, ajanın satırlarını `results/sab.jsonl` dosyasına ekler; rapor aynı senaryolarda harness ile eşleştirir.

Plasebo koşusu için ayrı bir oturum aç: `--name hydrogen-runbook --mode runbook`. Bu modda her talebin altında
kurum runbook'u da gösterilir.

## Ajana yapıştırılacak istem

```
Bu klasörde bir ölçüm köprüsü var. Bir toplu iş zamanlayıcısının iş tanımlarını yöneten admin olarak
24 talebi sırayla ele alacaksın.

Kurallar:
- Yalnızca şu komutu kullan: python -m vardiya.agentbench ...
- Bu klasördeki hiçbir dosyayı açma, okuma, arama (vardiya/, scenarios/, results/, docs/, tests/ dahil).
  Doğru cevaplar orada duruyor; okursan ölçüm geçersiz olur.
- Bana soru sorma. Karar senin.
- Geçici JSON dosyası gerekirse yalnızca results/agent/tmp/ altına yaz.

Başlamak için:
  python -m vardiya.agentbench show

Bu komut açık talebi ve kullanabileceğin fiilleri gösterir. Her talep için:
1. Gerekli gördüğün kadar oku (list_env, list_defs, get_def, forecast).
2. Karar ver: talebi doğru uygula ve kapat, ya da olduğu gibi uygulanmaması gerekiyorsa gerekçesiyle iade et.
   Başka hiçbir işe dokunma.
3. python -m vardiya.agentbench next   ile sıradaki talebe geç.

Fiil çağırma örnekleri:
  python -m vardiya.agentbench call list_defs
  python -m vardiya.agentbench call get_def --file results/agent/tmp/arg.json      (dosya: {"job": "IS_ADI"})
  python -m vardiya.agentbench call deploy_job --file results/agent/tmp/tanim.json (dosya: {"definition": {...}})
  python -m vardiya.agentbench call return_request --file results/agent/tmp/iade.json (dosya: {"reason": "..."})
  python -m vardiya.agentbench call close_request --file results/agent/tmp/kapat.json
      (dosya: {"record": {"talep_no": "...", "kapatan": "...", "istenen": "..."}})

"Butun talepler bitti" çıktısını görene kadar devam et, sonra dur.
```

## Sınırlar

- Ajan dosya sistemine erişebilir; kaynak kodu ve beklenen sonuçlar aynı klasördedir. İstem okumayı yasaklar ama
  bunu teknik olarak engelleyen bir şey yoktur. Ajanın çalışma kaydında dosya okuması görürsen koşuyu sayma.
- Ajanın kendi iç adımları ve düşünme süresi kaydedilmez; yalnızca köprü üzerinden yaptığı çağrılar kaydedilir.
- Sonuç tek koşudur ve ajan aracının kendi sistem istemi de işin içindedir; aynı modelin API üzerinden vereceği
  sonuçla birebir aynı olması beklenmez.
