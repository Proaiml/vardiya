"""The agent loop on the live lab: a model, the tools, a ticket, and (for the harnessed arm) Usta around it.

Arms:
    yalin   the model with the handbook and the tools, nothing else
    kart    the same plus the skill cards pasted into its prompt (placebo: knowledge without the harness)
    usta    the same model inside the harness: triage pack, matched skill cards, pre-flight checks before a deploy,
            a guard on destructive actions, loop detection and a finish gate that verifies with its own probes

The protocol is one JSON object per turn, so any text model can drive it (local, API, or a CLI such as agy).
"""
import json
import time
import urllib.error

from .araclar import EL_KITABI

ROL = """Sen bir bankanin batch operasyon ekibinde Control-M yoneticisisin. Sana bir talep ya da ariza bildirimi gelir;
isi ucundan sonuna kadar kendin yaparsin: incelersin, duzeltirsin ya da tanimlarsin, calistirirsin ve sonucu
dogrularsin. Kimseye soru soramazsin. Varsayim yerine ortama bak. Veriyi bozan ya da geri alinamayan bir is yapma.

Her turda YALNIZCA bir JSON nesnesi yaz: {"dusunce": "<kisa gerekce>", "arac": "...", ...}. Baska metin yazma.
Is bittiginde {"arac": "bitir", "rapor": "..."} ile kapat."""

MAX_ADIM = 40
MAX_SANIYE = 1200


def baglam_siniri(model):
    """Characters of conversation a model can take. Local Ollama models have a fixed window (VARDIYA_NUM_CTX tokens)
    and silently drop the START of an overlong prompt, which is the system prompt and the handbook; for them the
    conversation is kept under the window (about 2.8 characters per token, room left for the answer). Hosted models
    get the whole conversation as before."""
    if not str(getattr(model, "spec", "")).startswith("ollama:"):
        return None
    import os
    return int(int(os.environ.get("VARDIYA_NUM_CTX", 16384)) * 2.8) - 6000


def sikistir(messages, sinir, son=6, ilk_satir=4):
    """Context discipline, the same for every arm: the system prompt, the ticket (with whatever came with it) and the
    last `son` messages stay whole; older tool results shrink to their first lines. If that is still too long the
    kept tail shrinks too, down to the last two messages."""
    if not sinir or sum(len(m["content"]) for m in messages) <= sinir:
        return messages

    def kisa(m, n):
        if m["role"] != "user" or len(m["content"]) < 400:
            return m
        lines = m["content"].splitlines()
        return {**m, "content": "\n".join(lines[:n]) + f"\n... (eski arac ciktisi kisaltildi; {len(lines) - n} satir)"}
    for keep in range(son, 1, -2):
        head, mid, tail = messages[:2], messages[2:-keep] if len(messages) > keep + 2 else [], messages[max(2, len(messages) - keep):]
        out = head + [kisa(m, ilk_satir) for m in mid] + tail
        if sum(len(m["content"]) for m in out) <= sinir:
            return out
    return head + [kisa(m, 2) for m in mid] + [kisa(m, 30) for m in tail]


def kos(model, araclar, talep, usta=None, ek_baglam="", max_adim=MAX_ADIM, max_saniye=MAX_SANIYE, gunluk=None):
    """Run one episode. Returns {"rapor", "adim", "saniye", "bitis", "cagri", "mesajlar"}."""
    t0 = time.time()
    system = ROL + "\n\n" + EL_KITABI + (("\n\n" + ek_baglam) if ek_baglam else "")
    ilk = "## Talep\n" + talep
    if max_adim < MAX_ADIM:          # a crisis budget is told up front, to every arm alike
        ilk += f"\n\nBu is acil: en cok {max_adim} adimin var (bitir adimi dahil). Adimlarini buna gore sec."
    if usta is not None:
        system += "\n\n" + usta.KURALLAR
        ilk += "\n\n" + usta.baslangic(talep)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": ilk + "\n\nIlk adimini JSON olarak yaz."}]
    rapor, bitis, bozuk = "", "adim_siniri", 0
    sinir = baglam_siniri(model)
    for adim in range(1, max_adim + 1):
        if time.time() - t0 > max_saniye:
            bitis = "sure_siniri"
            break
        try:
            eylem = model.ask_json(sikistir(messages, sinir))
        except (urllib.error.URLError, OSError, ValueError) as e:
            bitis = f"model_hatasi: {str(e)[:120]}"
            break
        if not isinstance(eylem, dict) or "arac" not in eylem:
            bozuk += 1
            if bozuk >= 4:
                bitis = "gecersiz_cikti"
                break
            messages += [{"role": "assistant", "content": json.dumps(eylem, ensure_ascii=False) if eylem else "{}"},
                         {"role": "user", "content": 'Gecersiz cikti. Tek bir JSON nesnesi yaz; "arac" alani ctm, sh ya da bitir olmali.'}]
            continue
        messages.append({"role": "assistant", "content": json.dumps(eylem, ensure_ascii=False)})
        if gunluk:
            gunluk(adim, eylem)
        if eylem["arac"] == "bitir":
            rapor = str(eylem.get("rapor", ""))
            # on the last step there is nothing left to send back to: the gate cannot ask for more work
            ret = usta.bitis(rapor, eylem) if usta is not None and adim < max_adim else None
            if ret is None:
                bitis = "bitir"
                break
            messages.append({"role": "user", "content": ret})
            continue
        ret = usta.once(eylem) if usta is not None else None
        if ret is not None:
            araclar._kayit(eylem["arac"], {k: v for k, v in eylem.items() if k not in ("arac", "dusunce")}, ret, 1, False)
            sonuc = ret
        else:
            sonuc = araclar.cagir({k: v for k, v in eylem.items() if k != "dusunce"})
            if usta is not None:
                sonuc = usta.sonra(eylem, sonuc)
        kalan = max_adim - adim
        messages.append({"role": "user", "content": "SONUC:\n" + sonuc + (f"\n\n(kalan adim: {kalan})" if kalan <= 8 else "")})
    return {"rapor": rapor, "adim": adim, "saniye": round(time.time() - t0, 1), "bitis": bitis,
            "cagri": getattr(model, "calls", None), "mesajlar": messages,
            **({"baglam": {"sinir_karakter": sinir, **getattr(model, "baglam", {})}} if sinir else {})}
