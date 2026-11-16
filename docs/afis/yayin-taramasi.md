# Yayın taraması

16 Kasım 2026. Kapsam: `git ls-files` ile izlenen 243 dosya (tarama sırasında). Hiçbir şey silinmedi ya da değiştirilmedi;
aşağıda dosya, satır ve neden listelenir. "Karar" sütunu sahibine kalan maddeleri gösterir.

## Özet

| Konu | Bulgu | Karar gerekir mi |
| --- | --- | --- |
| Gizli test kümeleri izleniyor | `bench/saha/test/t1-t3.json`, `bench/saha/zor-test/z1-z3.json` depoda; depo açılınca gizli olmaktan çıkar | **Evet** |
| Kanıt dosyaları depoda yok | `results/saha/` altında yalnızca `TABLOLAR.md` izleniyor; README ve afiş `results/saha/dev-flash-low/` gibi dizinlere atıf yapıyor | **Evet** |
| Git geçmişindeki e-posta | 126 commit'in tamamında yazar e-postası kişisel bir Gmail adresi | **Evet** |
| Kişisel ad | "İlhan" belgelerde 13 satırda | Evet |
| Başka proje ve oturum adları | `Desktop\harness` (Nöbetçi), `hub` klasörü, "başka bir oturum" | Evet |
| Forum okuyucusu | `tools/bmc/okuyucu.js`, `tools/bmc/kullanilmis.json` | **Evet** |
| Forum kaynaklı vakalar | `bench/ops/dev.jsonl` vb.: örneklenen 15 vaka özgün Türkçe özet | Bilgi, kaynak adresleri için karar |
| Özel anahtar blokları | 7 senaryo dosyasında OpenSSH özel anahtarı | Evet (laboratuvara özgü olduğu doğrulanmalı) |
| Gerçek kimlik bilgisi, jeton | Bulunmadı | Hayır |
| Kişisel yol | 2 satır | Evet (küçük) |

## 1. Gizli test kümeleri (karar gerekli)

- `bench/saha/test/t1.json`, `t2.json`, `t3.json` ve `bench/saha/zor-test/z1.json`, `z2.json`, `z3.json` izleniyor.
  Raporlar bunları "gizli" olarak anlatıyor; depo herkese açık olunca bu kümeler okunabilir olur ve harness bunlara
  bakılarak ayarlanabilir. Sonraki ölçümler için ayrı, yayımlanmamış bir küme gerekir. `bench/saha/katalog-test/`
  izlenmiyor (iyi).
- Bu tarama sırasında tek bir `git grep` çıktısı bu dosyalardan birkaç satır (parola örnekleri, bir özel anahtar bloğu)
  ekrana getirdi; dosyalar açılmadı, hiçbir senaryo içeriği kullanılmadı. Daha önce gizli olduklarını söyleyen taraf
  bunu bilmeli.

## 2. Kanıt dosyaları depoda değil

`git ls-files results/saha` yalnızca `results/saha/TABLOLAR.md` döndürüyor. `README.md` ve afiş, bölüm dökümlerini
`results/saha/dev-flash-low/aft-parola-degisti__usta.json` gibi yollarla gösteriyor; bu dizinler şu an izlenmeyen
(`??`) durumda. Yayından önce ilgili koşu dizinlerinin eklenmesi ya da README'deki atıfların kaldırılması gerekir
(`dev-flash-low`, `test-flash-low`, `test-gpt-oss`, `test-gpt-oss-b10`, `zor-dev-qwen-t1`, `zor-dev-qwen-t2`,
`zor-test-gpt-oss`, `dev-hydrogen-high`, `dogrula-dev5`). `.gitignore` zaten `results/saha/dogrula-*/` ve
`results/saha/*.log` kalıplarını dışlıyor; README'de adı geçen `dogrula-dev5` bu yüzden eklenmez. Ya o koşu
istisna yapılmalı ya da README'deki "kimse dokunmadı" atıfı `bos` kolunun başka bir koşuya taşınmasıyla düzeltilmeli.

## 3. E-posta adresleri

- Dosyalarda gerçek bir kişisel adres yok. Görülenler: `bench/ops/test.jsonl:104` (`slurm-users@lists.schedmd.com`, herkese
  açık bir posta listesi), `ornekler/*`, `tests/test_erisim.py:21`, `vardiya/bench_req.py:332` (`x@disari.com`),
  `odeme-nobet@ornek.local`: hepsi uydurma ya da herkese açık.
- **Git geçmişi:** 126 commit'in tamamında yazar `İlhan Koçaslan <kocaslanilhan1@gmail.com>`. Depo açılınca bu adres
  görünür. Geçmişi yeniden yazmak ya da GitHub'da e-posta gizleme (noreply adresi) kullanmak sahibin kararı.

## 4. Kişisel ad ve yollar

- Ad: `docs/00-devir-notu.md` 28, 37, 153, 239, 251, 268; `docs/01-saha-arastirmasi-ve-urun-tasarimi.md` 455;
  `docs/02-admin-rolu-ve-talep-akisi.md` 8, 124; `docs/06-is-tipleri-benchmarklar-ve-olay-onceligi.md` 278 (forumun
  "İlhan'ın hesabıyla girilerek" okunduğu yazıyor); `docs/10-ana-is-akisi.md` 72, 86, 110.
- Yol: `docs/00-devir-notu.md:270` ve `docs/04-ajan-araciyla-olcum.md:19` (`C:\D\projeler\schedularharness`).
  `C:\Users\...` biçiminde yol bulunmadı.
- Hepsi yalnızca ilk adı ve proje klasörünü gösteriyor; gizli bir bilgi değil, ama sahibinin görmek isteyeceği şeyler.

## 5. Başka projeler ve oturumlar

- `docs/00-devir-notu.md:4-5` ve `docs/01-...:382`: eski ad "Nöbetçi" ve aynı adlı NOC izleme projesi (`Desktop\harness`).
- `docs/10-ana-is-akisi.md:68-69`: makine kuralları, `Desktop\harness (Nöbetçi)` deposuna dokunulmaz, başka projelerin
  Docker imajları silinmez.
- `docs/00-devir-notu.md:202`: GPU'da eğitim koşan başka bir oturum, eşgüdüm masaüstündeki `hub` klasörü.
- `tools/isi_bekcisi.py:32`: varsayılan yol `~/Desktop/hub/konuşmlar.txt`; `.gitignore:9` `results/hub-arsiv/`.
- `docs/00-devir-notu.md:166-182, 268`, `docs/03:188-198`, `docs/04`, `docs/05:135`: Antigravity ve `agy` aracı,
  kullanıcıya ait kota. Gizli değil; yayın için fazla kişisel bulunabilir.
- Claude, Anthropic adları `vardiya/gateway.py:18` (API adresi tablosu) ve `.gitignore` (`Claude outputs/`) dışında kodda yok;
  belgelerde model adı olarak geçiyor (claude-sonnet-5-5-low), sorun değil.

## 6. Jeton ve kimlik bilgisi

Gerçek görünen anahtar ya da jeton (`sk-`, `ghp_`, `AKIA`, `xox`, Bearer) **bulunmadı**. Parola benzeri değerlerin hepsi
laboratuvara özgü uydurma değerler: `Mft-2026-Ilk`, `Mft-2026-Kasim`, `Etl-2026-Ilk`, `Rapor-2026-Ilk`, `saha-yonetici`
(`lab/saha/docker-compose.yml:145`), `js7lab` (`lab/js7/docker-compose.yml:80`, `lab/saha/docker-compose.yml:113`),
`Lab-Win-2026` (`lab/saha/windows/docker-compose.yml:19`), `Gizli2026` (`ornekler/talep-aktarim-parola.txt:12`,
`vardiya/sabgen.py:409,411`).

**OpenSSH özel anahtar blokları** (`-----BEGIN OPENSSH PRIVATE KEY-----`) şu dosyalarda: `bench/saha/katalog-dev/`
`k1-03-...json:43,52`, `k1-20-...json:43,207`, `k1-23-...json:43,52`, `k1-26-...json:40,49`; `bench/saha/zor-test/z2.json:579,1128`.
Bunlar senaryo kurulumunun laboratuvarda ürettiği anahtarlar gibi görünüyor ama bu taramada doğrulanamadı; sahibi
bunların yalnızca bu laboratuvarın bir kereliklik anahtarları olduğunu onaylamalı.

## 7. Forum kaynaklı vakalar ve `tools/bmc/`

- `bench/ops/dev.jsonl` (236 vaka), `test.jsonl` (128), `test2.jsonl` (86), `test3.jsonl` (60), `test4.jsonl` (59):
  hepsi UTF-8, alanlar `id, split, track, scheduler, class, prompt, steps, harmful, source`.
- **15 vaka rastgele örneklendi** (5 dosyadan, tohum 7): görülen şey kısa, 1-2 cümlelik
  özgün Türkçe özetler; forum metnini yapıştırma izi yok. Kaynak kayıtlarında tırnak içinde kısa hata iletileri var
  (örneğin `unsupported mode`, `CONTROL-M Configuration Agent Not Available`), bunlar ürün çıktısı, forum cümlesi değil.
  Örneklemde yapıştırma görülmedi; 569 vakanın hepsi okunmadı.
- `source` alanı BMC Community adreslerini ve görüntülenme sayılarını taşıyor (`community.bmc.com/s/article/...`,
  `.../s/question/...`); `docs/06` ve `docs/07` forumun giriş yapılarak okunduğunu söylüyor. Adreslerin ve sayıların
  yayımlanması (ve forumun kullanım koşulları) sahibin kararı.
- `tools/bmc/okuyucu.js`: salt okur forum okuyucusu (40 saniyede bir sayfa, 429'da durur, forum metni diske çıkmaz).
  Giriş yapılmış bir tarayıcı oturumunda çalışacak şekilde yazılmış. Herkese açık depoda durması sahibin kararı.
  `tools/bmc/kullanilmis.json`: forum kayıt kimliklerinin listesi.
- `bench/ops/aday/` `.gitignore` ile dışlı, izlenmiyor.

## 8. Başka notlar

- `results/ops.jsonl` ve benzeri sonuç dosyaları model çıktısı içeriyor; "Desktop Heap" geçişleri (Windows terimi)
  dışında kişisel veri görülmedi.
- `README.md` alt bölümleri eski, noktalamasız yazımla duruyor (ASCII Türkçe); yalnızca biçim.
- `vardiya/__init__.py` sürümü `0.3.0` gösteriyor, son commit iletisi 0.7.0 diyor; yayından önce tutarlı hale getirilmeli.
