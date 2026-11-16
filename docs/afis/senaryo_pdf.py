"""Reads every scenario under bench/saha/ and writes docs/afis/schedops-bench-senaryolar.html.

Usage (from the repo root):  python docs/afis/senaryo_pdf.py
Then render with headless Chrome:
  chrome --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf=docs/schedops-bench-senaryolar.pdf
         file:///.../docs/afis/schedops-bench-senaryolar.html
Validation status comes from the newest rows of results/saha/dogrula-*/ozet.jsonl for each scenario.
"""
import collections
import glob
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SETS = [
    ("dev", "Geliştirme (dev)", "Harness'i yazan elle yazdı; harness bu kümeye bakılarak ayarlandı."),
    ("test", "Gizli test (test)", "Ayrı bir ajan, harness kodunu ve kartları görmeden yazdı."),
    ("zor-dev", "Zor geliştirme (zor-dev)", "Kalabalık site, yanıltıcı bilet, birbirini ortaya çıkaran arızalar."),
    ("zor-test", "Zor gizli test (zor-test)", "Zor yapıda, ayrı yazılmış küme."),
    ("katalog-dev", "Katalog geliştirme (katalog-dev)", "Arıza kataloğundan (vardiya/saha/katalog.py) tohumla üretilmiş."),
    ("katalog-test", "Katalog test (katalog-test)", "Katalogdan üretilmiş; yalnızca testte çıkan arızalar da var."),
]
FAM = {"ariza": "arıza", "tanim": "tanım", "yonetim": "yönetim"}
TUR = {"aft": "AFT (dosya aktarımı)", "os": "EXC (komut/betik)", "db": "DBJ (veritabanı)", "karma": "karma"}
LIM = 160


def esc(s):
    return html.escape(str(s))


def cut(v, n=LIM):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def kv(d, skip=()):
    return "; ".join(f"{k}={cut(v)}" for k, v in d.items() if k not in skip)


def render(c):
    """One readable line for a check or a harm check."""
    if not isinstance(c, dict) or not c:
        return cut(c)
    name = next(iter(c))
    v = c[name]
    if name == "degil":
        return "DEĞİL: " + render(v)
    if not isinstance(v, dict):
        return f"{name}: {cut(v)}"
    if name == "is":
        s = f"iş {v.get('folder')}/{v.get('job')}: durum {v.get('durum')}"
        extra = kv(v, ("folder", "job", "durum"))
        return s + (f" ({extra})" if extra else "")
    if name == "dosya":
        host = v.get("host", "")
        s = f"dosya {host}:{v.get('yol')}"
        extra = kv(v, ("host", "yol"))
        return s + (f" → {extra}" if extra else "")
    if name == "sql":
        return f"sql {cut(v.get('sorgu'))} → " + kv(v, ("sorgu",))
    if name == "sh":
        return f"kabuk {v.get('host')}: {cut(v.get('cmd'))} → " + kv(v, ("host", "cmd"))
    if name == "iz":
        return f"eylem izi: {v.get('arac')} /{v.get('regex')}/" + (" " + kv(v, ("arac", "regex")) if len(v) > 2 else "")
    return f"{name}: " + kv(v)


def load_sets():
    out = {}
    for key, _, _ in SETS:
        sc = []
        for f in sorted(glob.glob(str(ROOT / "bench" / "saha" / key / "*.json"))):
            j = json.load(open(f, encoding="utf-8"))
            for s in (j if isinstance(j, list) else [j]):
                s["_dosya"] = pathlib.Path(f).name
                sc.append(s)
        out[key] = sc
    return out


def validation(sets):
    """newest bos and referans row per scenario over all dogrula-* runs"""
    rows = {}
    for f in glob.glob(str(ROOT / "results" / "saha" / "dogrula-*" / "ozet.jsonl")):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("kol") not in ("bos", "referans"):
                continue
            k = (r["senaryo"], r["kol"])
            if k not in rows or r.get("zaman", "") > rows[k].get("zaman", ""):
                rows[k] = r
    status = {}
    for key, scs in sets.items():
        res = {"gecti": [], "kaldi": [], "yok": []}
        for s in scs:
            b, r = rows.get((s["id"], "bos")), rows.get((s["id"], "referans"))
            if not b or not r:
                res["yok"].append(s["id"])
            elif b["hukum"] not in ("dogru", "zararli", "kurulamadi") and r["hukum"] == "dogru":
                res["gecti"].append(s["id"])
            else:
                res["kaldi"].append((s["id"], b["hukum"], r["hukum"]))
        status[key] = res
    return status


def block(s):
    ids = [esc(s["id"])]
    meta = [f"aile: {FAM.get(s.get('aile'), s.get('aile'))}", f"iş tipi: {TUR.get(s.get('tur'), s.get('tur'))}",
            "bileşik (iki neden)" if s.get("bilesik") else "tek nedenli"]
    if s.get("kaynak"):
        k = s["kaynak"]
        meta.append("kaynak: " + esc(", ".join(k) if isinstance(k, list) else k))
    if s.get("ariza"):
        a = s["ariza"]
        meta.append("arıza: " + esc(", ".join(a) if isinstance(a, list) else a))
    h = f'<div class="sc"><h4><code>{ids[0]}</code> <span>{esc(s.get("baslik", ""))}</span></h4>'
    h += '<p class="meta">' + " · ".join(meta) + "</p>"
    h += f'<p><b>Talep:</b> {esc(s.get("talep", ""))}</p>'
    h += f'<p><b>Gizli kök neden:</b> {esc(s.get("kok_neden", ""))}</p>'
    h += (f'<p class="meta">Kurulum {len(s.get("kurulum", []))} adım · referans çözüm {len(s.get("cozum", []))} adım'
          + (" · karşı kurum sunucuları: " + esc(", ".join(s["dis_sunucu"])) if s.get("dis_sunucu") else "") + "</p>")
    h += "<p class='lbl'>Kontroller (uç durum)</p><ul>" + "".join(f"<li>{esc(cut(render(c), 400))}</li>" for c in s.get("kontroller", [])) + "</ul>"
    if s.get("zarar"):
        h += "<p class='lbl'>Zarar kontrolleri (hiçbiri tutmamalı)</p><ul class='harm'>" + "".join(
            f"<li>{esc(cut(render(c), 400))}</li>" for c in s["zarar"]) + "</ul>"
    return h + "</div>\n"


def main():
    sets = load_sets()
    st = validation(sets)
    total = sum(len(v) for v in sets.values())
    out = [HEAD]
    out.append(f"""<div class="cover"><div class="meta">VARDİYA · AÇIK KAYNAK HARNESS · AIOPS</div>
<h1>SchedOps-Bench</h1><p class="lead">Batch zamanlayıcı operasyonları için canlı ortam benchmark'ı: senaryo kataloğu</p>
<p>SchedOps-Bench, bir yapay zekâ ajanının bir iş zamanlayıcıyı gerçek sunucular üzerinde yönetmesini ölçer: taleplerden iş tanımlamak, başarısız dosya aktarımı, komut/betik ve veritabanı işlerini teşhis edip düzeltmek ve yeniden çalıştırmak. Her senaryo canlı bir laboratuvarda (gerçek bir zamanlayıcı, iki ajan sunucusu, bir SFTP sunucusu, bir PostgreSQL veritabanı) gerçekten çalışır; hüküm, ajanın raporundan değil sunuculardan okunan son durumdan verilir. Bu belge {total} senaryonun tamamını listeler.</p>
<p>16 Kasım 2026 · github.com/Proaiml/vardiya · Apache License 2.0</p>
<p class="meta">Vardiya, BMC Software ile bağlantılı değildir; "Control-M" BMC'nin ticari markasıdır. Laboratuvardaki zamanlayıcı JS7'dir. Bu belge <code>docs/afis/senaryo_pdf.py</code> ile senaryo dosyalarından üretilir. Parolalar ve anahtarlar yalnızca laboratuvara özgü uydurma değerlerdir.</p></div>""")
    out.append("""<h2 style="margin-top:0">Bir senaryo nasıl okunur</h2>
<p>Senaryo bir veri dosyasıdır (<code>bench/saha/&lt;küme&gt;/*.json</code>). Her bloktaki alanlar:</p>
<ul>
<li><b>Talep:</b> ajanın gördüğü bilet metni. Kök nedeni söylemez.</li>
<li><b>Gizli kök neden:</b> senaryo yazarının notu; ajana gösterilmez.</li>
<li><b>Kurulum:</b> laboratuvarın sahneyi kurmak için yaptığı adımlar (tanım dağıtma, dosya yazma, parola değiştirme, kilit tutan oturum açma, sipariş verme). Arıza gerçekten üretilir.</li>
<li><b>Kontroller:</b> bölüm sonunda sunuculardan okunan uç durum (iş durumu, dosya içeriği ve özeti, SQL sonucu, tanım, çalışma sırası). Hepsi tutarsa hüküm doğrudur.</li>
<li><b>Zarar kontrolleri:</b> hiçbiri tutmamalı; biri tutarsa hüküm zararlıdır (veri kaybı, mükerrer kayıt, dokunulmaması istenen şeyin değişmesi, herkese yazma izni, <code>set to OK</code> ile gizleme). <code>DEĞİL:</code> ile başlayan satır, ifadenin tersinin zarar sayıldığını gösterir.</li>
<li><b>Referans çözüm:</b> senaryonun çözülebildiğini kanıtlayan örnek adımlar; yalnızca doğrulamada kullanılır.</li>
<li><b>Hükümler:</b> doğru, yarım (kontrollerin bir kısmı), yanlış (hiçbiri), sahte yeşil (iş yeşil ya da "tamam" denmiş ama veri hatalı), zararlı.</li>
<li><b>İki yönlü doğrulama:</b> bir senaryo kümeye ancak kimse dokunmadığında doğru (ve katalogda zararlı) çıkmıyor ve referans çözüm uygulandığında doğru çıkıyorsa girer.</li>
</ul>
<p class="meta">Uzun gömülü değerler (betik gövdeleri, anahtarlar) 160 karakterde kısaltılmıştır; tam hâli senaryo dosyasındadır. <code>bench/saha/erken</code> farklı biçimde (erken uyarı için geçmiş serileri) olduğundan bu belgeye girmez.</p>""")
    # summary
    out.append("<h2>Kümelere genel bakış</h2><table><thead><tr><th>Küme</th><th class='n'>Senaryo</th><th>Aile</th><th>İş tipi</th><th class='n'>Bileşik</th><th>Doğrulama</th></tr></thead><tbody>")
    vtxt = {}
    for key, name, _ in SETS:
        scs, r = sets[key], st[key]
        if len(r["gecti"]) == len(scs):
            t = f"doğrulandı ({len(scs)}/{len(scs)} senaryoda iki satır geçti)"
        elif not r["gecti"] and not r["kaldi"]:
            t = "doğrulanmadı (satır yok)"
        else:
            t = f"doğrulama yarım: {len(r['gecti'])} geçti, {len(r['kaldi'])} kaldı, {len(r['yok'])} satırsız"
        vtxt[key] = t
        fam = collections.Counter(FAM.get(s.get("aile"), s.get("aile")) for s in scs)
        tur = collections.Counter(TUR.get(s.get("tur"), s.get("tur")).split(" ")[0] for s in scs)
        comp = sum(1 for s in scs if s.get("bilesik"))
        out.append(f"<tr><td>{esc(name)}</td><td class='n'>{len(scs)}</td><td>{esc(', '.join(f'{k} {v}' for k, v in fam.items()))}</td>"
                   f"<td>{esc(', '.join(f'{k} {v}' for k, v in tur.items()))}</td><td class='n'>{comp} (%{round(100 * comp / len(scs))})</td><td>{esc(t)}</td></tr>")
    out.append(f"<tr><td><b>Toplam</b></td><td class='n'><b>{total}</b></td><td></td><td></td><td></td><td></td></tr></tbody></table>")
    out.append("<p class='meta'>Doğrulama durumu, <code>results/saha/dogrula-*/ozet.jsonl</code> içindeki her senaryo için en yeni \"kimse dokunmadı\" ve \"örnek çözüm\" satırlarından okunur: geçti = kimse dokunmadığında doğru, zararlı ya da kurulamadı değil ve örnek çözümle doğru. Satır yoksa sayılmaz.</p>")
    for key, name, desc in SETS:
        scs, r = sets[key], st[key]
        out.append(f'<h2 class="pb">{esc(name)}: {len(scs)} senaryo</h2><p>{esc(desc)}</p>')
        out.append(f"<p><b>Doğrulama durumu:</b> {esc(vtxt[key])}.</p>")
        if r["kaldi"]:
            out.append("<p class='meta'>Geçmeyen: " + esc("; ".join(f"{i} (kimse dokunmadı: {b}, örnek çözüm: {c})" for i, b, c in r["kaldi"])) + "</p>")
        if r["yok"]:
            out.append("<p class='meta'>Doğrulama satırı olmayan: " + esc(", ".join(r["yok"])) + "</p>")
        for s in scs:
            out.append(block(s))
    out.append("</body></html>")
    dest = ROOT / "docs" / "afis" / "schedops-bench-senaryolar.html"
    dest.write_text("\n".join(out), encoding="utf-8")
    print("yazildi", dest, total, {k: len(v) for k, v in sets.items()})
    for k, v in st.items():
        print(k, len(v["gecti"]), "gecti", len(v["kaldi"]), "kaldi", len(v["yok"]), "yok")


HEAD = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>SchedOps-Bench senaryolar</title>
<style>
@page { size: A4; margin: 17mm 15mm 18mm 15mm; @bottom-center { content: counter(page); font: 9pt "Segoe UI", Arial, sans-serif; color: #4b5563; } }
:root { --ink:#111827; --muted:#4b5563; --line:#cfcfc8; --teal:#0f6b62; --amber:#9a4a06; --soft:#f1f1ea; }
* { box-sizing: border-box; }
body { margin:0; font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif; font-size:9.6pt; line-height:1.4; color:var(--ink); -webkit-print-color-adjust:exact; print-color-adjust:exact; }
h1 { font-size:30pt; line-height:1.1; margin:2mm 0 4mm; letter-spacing:-.02em; }
h2 { font-size:14pt; margin:7mm 0 2.5mm; color:var(--teal); border-bottom:1.5px solid var(--ink); padding-bottom:1mm; break-after:avoid; }
h4 { font-size:10.5pt; margin:0 0 1mm; break-after:avoid; } h4 span { font-weight:600; }
p { margin:0 0 1.8mm; } ul { margin:0 0 2mm; padding-left:5mm; } li { margin-bottom:.6mm; }
.lead { font-size:12.5pt; color:var(--muted); } .meta { font-size:8.6pt; color:var(--muted); }
code { font-family:Consolas,"Courier New",monospace; font-size:8.3pt; }
table { width:100%; border-collapse:collapse; margin:2mm 0 3mm; font-size:8.6pt; }
th, td { border-bottom:1px solid var(--line); padding:1.2mm 1.6mm; text-align:left; vertical-align:top; }
thead th { border-bottom:1.5px solid var(--ink); background:var(--soft); } .n { text-align:right; white-space:nowrap; }
.cover { min-height:225mm; display:flex; flex-direction:column; justify-content:center; break-after:page; }
.pb { break-before:page; }
.sc { border-top:1px solid var(--line); padding:2.2mm 0 1.4mm; break-inside:auto; }
.sc h4, .sc > p.meta:first-of-type { break-after:avoid; }
.sc ul { font-size:8.4pt; font-family:Consolas,"Courier New",monospace; list-style:square; margin-bottom:1.2mm; }
.sc li { break-inside:avoid; word-break:break-word; }
.lbl { font-size:8.2pt; text-transform:uppercase; letter-spacing:.05em; color:var(--teal); font-weight:700; margin:1.2mm 0 .6mm; break-after:avoid; }
.harm + .lbl, .lbl + .harm { } .harm { color:#7a3a05; }
</style></head><body>"""

if __name__ == "__main__":
    main()
