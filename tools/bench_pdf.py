"""Write the whole ops bench (questions, answer keys, harmful actions, sources, the harness's own answer) as a PDF.

    python tools/bench_pdf.py [output.pdf]
"""
import collections
import datetime
import json
import pathlib
import sys
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from vardiya import opsagent, opsbench, opsworld  # noqa: E402
from vardiya.skills import load_incident_classes, load_procedures  # noqa: E402

FONTS = pathlib.Path("C:/Windows/Fonts")
pdfmetrics.registerFont(TTFont("Sans", str(FONTS / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Sans-Bold", str(FONTS / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Sans-Italic", str(FONTS / "ariali.ttf")))
MONO = "Mono" if (FONTS / "consola.ttf").exists() else "Sans"
if MONO == "Mono":
    pdfmetrics.registerFont(TTFont("Mono", str(FONTS / "consola.ttf")))

INK, MUTED, RULE = colors.HexColor("#15181d"), colors.HexColor("#5b616b"), colors.HexColor("#d9d9d3")
VERDICT = {"dogru": ("Doğru", colors.HexColor("#1d8a4e")), "yarim": ("Yarım", colors.HexColor("#b7791f")),
           "yanlis": ("Yanlış", colors.HexColor("#5b616b")), "zararli": ("Zararlı", colors.HexColor("#c2352f"))}
TRACK = {"olay": "Olay", "bilgi": "Bilgi (nasıl yapılır)", "olaysiz": "Olaysız (müdahale gerekmez)"}

S = {
    "title": ParagraphStyle("t", fontName="Sans-Bold", fontSize=22, leading=27, textColor=INK, spaceAfter=6),
    "sub": ParagraphStyle("s", fontName="Sans", fontSize=11, leading=15, textColor=MUTED, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Sans-Bold", fontSize=16, leading=20, textColor=INK, spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Sans-Bold", fontSize=11.5, leading=15, textColor=INK, spaceBefore=4, spaceAfter=3),
    "body": ParagraphStyle("b", fontName="Sans", fontSize=9.5, leading=13.5, textColor=INK, alignment=TA_LEFT),
    "small": ParagraphStyle("sm", fontName="Sans", fontSize=8.5, leading=12, textColor=MUTED),
    "label": ParagraphStyle("l", fontName="Sans-Bold", fontSize=8.5, leading=12, textColor=MUTED),
    "mono": ParagraphStyle("m", fontName=MONO, fontSize=8.3, leading=11.5, textColor=INK),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def esc(x):
    return escape(str(x))


OR = ' <font color="#7a8089">ya da</font> '
BULLET, DASH = "•", "—"
OK, NO = '<font color="#1d8a4e"><b>+</b></font>', '<font color="#c2352f"><b>×</b></font>'


def groups(gs):
    return "<br/>".join(BULLET + " " + OR.join(esc(w) for w in g) for g in gs) or DASH


def table(rows, widths, head=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    style = [("FONT", (0, 0), (-1, -1), "Sans", 8.8), ("TEXTCOLOR", (0, 0), (-1, -1), INK),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        style += [("FONT", (0, 0), (-1, 0), "Sans-Bold", 8.5), ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                  ("LINEBELOW", (0, 0), (-1, 0), 0.8, MUTED)]
    t.setStyle(TableStyle(style))
    return t


def case_block(c, answer, found, verdict, hits):
    v, col = VERDICT[verdict]
    meta = (f"{esc(c['scheduler'])} · {TRACK.get(c['track'], c['track'])} · sınıf: {esc(c['class'])}"
            + (" · <b>birleşik</b>" if c.get("compound") else ""))
    src = c.get("source") or {}
    src_txt = esc(src.get("url") or src.get("note") or src.get("kind") or "—")
    keys = "<br/>".join((OK if h else NO) + " " + OR.join(esc(w) for w in g)
                        for g, h in zip(c["steps"], hits)) if hits else groups(c["steps"])
    steps = answer.get("steps") or []
    ans = esc(answer.get("cause") or "")
    if steps:
        ans += ("<br/>" if ans else "") + "<br/>".join("• " + esc(s[:380] + ("…" if len(s) > 380 else "")) for s in steps)
    found_txt = ", ".join(found.get("classes") or []) or "—"
    if found.get("procedures"):
        found_txt += " · yordam: " + ", ".join(found["procedures"])
    rows = [
        [P("<b>" + esc(c["id"]) + '</b>  <font color="' + col.hexval().replace("0x", "#") + '"><b>' + v + "</b></font>", "h2"), ""],
        [P(meta, "small"), ""],
        [P("SORU", "label"), P(esc(c["prompt"]))],
        [P("CEVAPTA GEÇMESİ GEREKENLER", "label"), P(keys)],
        [P("ZARARLI SAYILANLAR", "label"), P(groups(c.get("harmful", [])))],
        [P("HARNESS'IN BULDUĞU", "label"), P(esc(found_txt), "small")],
        [P("HARNESS'IN CEVABI<br/>(model olmadan)", "label"), P(ans or "<i>Harness bu olay için bir sınıf ya da yordam bulamadı.</i>", "small")],
        [P("KAYNAK", "label"), P(src_txt, "small")],
    ]
    t = Table(rows, colWidths=[42 * mm, 128 * mm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1)),
                           ("LINEABOVE", (0, 0), (-1, 0), 0.8, INK), ("TOPPADDING", (0, 0), (-1, -1), 2),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
    return KeepTogether([t, Spacer(1, 8)])


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sans", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "Vardiya · Zamanlayıcı Ops Bench")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Sayfa {doc.page}")
    canvas.restoreState()


def main(out):
    classes, procs = load_incident_classes(opsbench.SKILLS), load_procedures(opsbench.SKILLS)
    splits = {sp: opsbench.load(sp) for sp in ("dev", "test")}
    results = {}
    for sp, cases in splits.items():
        for c in cases:
            a, f = opsbench.skill_answer(c, classes, procs)
            results[c["id"]] = (a, f) + opsbench.score(c, a)

    story = [P("Zamanlayıcı Ops Bench", "title"),
             P(f"Toplu iş zamanlayıcısı yöneticiliği için gerçek sorunlardan kurulmuş benchmark · "
               f"{datetime.date.today():%d.%m.%Y}", "sub")]
    story.append(P("Nasıl okunur", "h2"))
    story.append(P(
        "Her vaka bir yöneticinin karşılaştığı durumu anlatır. <b>Cevapta geçmesi gerekenler</b>: doğru bir cevabın "
        "her madde için seçeneklerden en az birini içermesi gerekir; hepsi varsa vaka doğru, yarısı varsa yarım sayılır. "
        "<b>Zararlı sayılanlar</b>: cevabın önerdiği adımlarda bunlardan biri geçerse vaka zararlıdır (uyarı ya da "
        "yasak olarak geçmesi sayılmaz). <b>Harness'ın cevabı</b>: modelsiz durumda harness'ın skill'lerinden "
        "bulduğu sınıf ve yordamların metni; model koşunca bu metin modele bağlam olarak verilir. İşaretler bu cevabın "
        "hangi maddeyi karşıladığını gösterir (+ karşıladı, × karşılamadı)."))
    story.append(P("Geliştirme vakaları skill'leri yazarken kullanıldı (BMC topluluğu, Stack Overflow); test vakalarını "
                   "skill'leri görmeyen ayrı ajanlar yazdı (Stack Overflow, Server Fault, Airflow, AutoSys, Slurm, "
                   "Kubernetes, JS7 ve diğerleri). Forum metni kopyalanmadı; vakalar kendi sözcüklerimizle yazıldı ve "
                   "kaynağa bağlantıyla işaret ediyor.", "small"))
    story.append(Spacer(1, 10))

    head = [P("<b>Bölüm</b>", "small"), P("<b>Vaka</b>", "small"), P("<b>Olay / Bilgi / Olaysız</b>", "small"),
            P("<b>Birleşik</b>", "small"), P("<b>Doğru</b>", "small"), P("<b>Yarım</b>", "small"),
            P("<b>Yanlış</b>", "small"), P("<b>Zararlı</b>", "small")]
    rows = [head]
    for sp, cases in splits.items():
        tr = collections.Counter(c["track"] for c in cases)
        v = collections.Counter(results[c["id"]][2] for c in cases)
        rows.append([P("Geliştirme" if sp == "dev" else "Test"), str(len(cases)),
                     f"{tr['olay']} / {tr['bilgi']} / {tr['olaysiz']}", str(sum(1 for c in cases if c.get("compound"))),
                     str(v["dogru"]), str(v["yarim"]), str(v["yanlis"]), str(v["zararli"])])
    story += [P("Özet: harness'ın modelsiz cevapları", "h2"),
              table(rows, [26 * mm, 14 * mm, 34 * mm, 18 * mm, 18 * mm, 18 * mm, 18 * mm, 20 * mm])]
    sch = collections.Counter(c["scheduler"] for cases in splits.values() for c in cases)
    story += [Spacer(1, 6), P("Zamanlayıcılar: " + ", ".join(f"{esc(k)} {n}" for k, n in sch.most_common()), "small")]

    # action track
    story += [PageBreak(), P("Müdahale kolu", "h1"),
              P("Ajan sahaya enjekte edilen arızayı (ya da birbirini etkileyen iki arızayı) araçlarla okur, düzeltir ve "
                "işi yeniden çalıştırır. Her on senaryodan üçü birleşiktir: biri düzeltilince ikincisinin hatası görünür. "
                "Puan: iş OK ve her kök neden giderildi ve zararlı eylem yok = doğru.")]
    plans = opsagent.load_plans()
    rows = [[P("<b>Arıza</b>", "small"), P("<b>Sınıf</b>", "small"), P("<b>Kök neden</b>", "small"),
             P("<b>Harness'ın planı</b>", "small")]]
    for k, f in opsworld.FAULTS.items():
        rows.append([P(esc(k), "mono"), P(esc(f.cls), "small"), P(esc(f.text), "small"),
                     P(esc(" → ".join(plans.get(f.cls, []))), "mono")])
    story += [table(rows, [28 * mm, 22 * mm, 40 * mm, 80 * mm])]
    story += [Spacer(1, 8), P("Birleşik ikililer", "h2"),
              P(", ".join(f"{a} + {b}" for a, b in opsworld.COMPOUND), "mono")]
    for split in ("dev", "test"):
        rws = opsagent.run(split, range(50), out=None, arms=("kod", "saf"))
        story += [Spacer(1, 8), P(f"Sonuç: {'geliştirme' if split == 'dev' else 'test (görülmemiş ifadeler)'}, 50 senaryo", "h2")]
        t = collections.defaultdict(collections.Counter)
        for r in rws:
            t[(r["arm"], "birleşik" if r["compound"] else "tek")][r["verdict"]] += 1
        rows = [[P("<b>Kol</b>", "small"), P("<b>Tür</b>", "small"), P("<b>Doğru</b>", "small"), P("<b>Yarım</b>", "small"),
                 P("<b>Yanlış</b>", "small"), P("<b>Zararlı</b>", "small")]]
        for (arm, kind), c in sorted(t.items()):
            rows.append([{"kod": "harness (kod)", "saf": "saf operatör"}[arm], kind, c["dogru"], c["yarim"], c["yanlis"], c["zararli"]])
        story.append(table(rows, [40 * mm, 22 * mm, 20 * mm, 20 * mm, 20 * mm, 20 * mm]))
    # one worked example of a compound incident
    w = opsworld.OpsWorld(opsworld.scenario(2, "dev", ["cert_expired", "password_rotated"]))
    rounds = opsagent.solve_kod(w, classes, plans)
    story += [Spacer(1, 10), P("Örnek: sertifika bitmiş ve parola değişmiş (birleşik)", "h2")]
    for r in rounds:
        story.append(P("Tur " + str(r["round"]) + ': hata <font name="' + MONO + '">' + esc(r["error"]) + "</font> → sınıf <b>" + esc(r["class"]) + "</b>", "small"))
    story.append(P("<br/>".join(f"{esc(t['verb'])} {esc(t['args'])} → {esc(t.get('result', ''))}"
                                for t in w.trace if t["level"]), "mono"))
    story.append(P(f"Sonuç: <b>{VERDICT[w.verdict()][0]}</b>", "small"))

    for sp, cases in splits.items():
        story += [PageBreak(), P("Geliştirme vakaları" if sp == "dev" else "Test vakaları", "h1")]
        for c in cases:
            a, f, verdict, hits = results[c["id"]]
            story.append(case_block(c, a, f, verdict, hits))

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title="Zamanlayıcı Ops Bench", author="Vardiya")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "zamanlayici-ops-bench.pdf")
    print(main(out))
