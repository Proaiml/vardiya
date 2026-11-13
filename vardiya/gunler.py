"""Turkish run-day phrases, read by code.

"her ayin son is gunu" does not need a language model. This module turns the common ways of
writing run days into a calendar rule, deterministically, and refuses anything it does not fully
understand: one unknown word and the answer is None, so the phrase goes on to the model or back
to the requester. It was written against the tuning phrases only (sabgen.PHRASES).
"""
import re

FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")
WD_BASES = (("pazartesi", 0), ("cumartesi", 5), ("carsamba", 2), ("persembe", 3), ("sali", 1), ("cuma", 4), ("pazar", 6))
WD_SUFFIX = ("", "leri", "lari", "ler", "lar", "si", "yi", "i", "gunu", "gunleri")
WD_FROM, WD_TO = ("den", "dan", "ten", "tan"), ("ye", "ya", "e", "a")
WORDS = {
    "EVERY": "her", "DAY": "gun gunu gunleri gunlerde gunlerinde gunde gunune gununde",
    "WEEK": "hafta", "WEEK_GEN": "haftanin", "INSIDE": "ici icinde", "END": "sonu sonlari sonunda sonlarinda",
    "END_TO": "sonuna", "LAST": "son", "FIRST": "ilk", "WORK": "is mesai calisma", "MONTH": "ay ayin ayda aylik",
    "START": "basi basinda", "HOL": "tatil tatiller tatillerde tatile tatilde bayram bayramda bayramlarda resmi",
    "HOL_IF": "tatilse", "EXC": "haric", "INC": "dahil", "NEG": "calismasin calismaz", "IF": "gelirse denk degilse rastlarsa",
    "NEXT": "ertesi sonraki takip eden", "PREV": "onceki", "RANGE": "arasi", "SEVEN": "yedi", "TWO": "iki",
    "FILL": "sadece yalnizca yalniz bir kez de da ve ile calissin calisir olsa bile kaysin istisnasiz kapanis "
            "kapanisinda haftada haftalik",
}
TAG = {w: tag for tag, words in WORDS.items() for w in words.split()}
NUM_SUFFIX = {"inde", "unda", "i", "u", "si", "su", "sinde", "sunda", "inci", "nci", "uncu", "ncu", "de", "da"}
TENS, UNITS = {"on": 10, "yirmi": 20, "otuz": 30}, {"bir": 1, "iki": 2, "uc": 3, "dort": 4, "bes": 5, "alti": 6,
                                                    "yedi": 7, "sekiz": 8, "dokuz": 9}
POSSESSIVE = ("sinde", "sunda", "inde", "unda", "si", "su", "i", "u", "")


def fold(text):
    return text.replace("İ", "i").replace("I", "i").lower().translate(FOLD)


def _weekday(tok):
    for base, n in WD_BASES:
        if tok.startswith(base):
            rest = tok[len(base):]
            if rest in WD_SUFFIX:
                return n, "plain"
            if rest in WD_FROM:
                return n, "from"
            if rest in WD_TO:
                return n, "to"
    return None


def _strip(tok, table):
    for suf in POSSESSIVE:
        if suf and tok.endswith(suf) and tok[:-len(suf)] in table:
            return table[tok[:-len(suf)]]
    return table.get(tok)


EXCEPTION = {"haric", "disinda", "disindaki", "disi", "atlayarak", "olmadan", "yok", "degil"}
INTERVAL_STEMS = ("ceyre", "yil", "donem", "periyo", "aralikli", "arada")
COUNT = {"iki", "uc", "dort", "bes", "alti"}
PER = {"haftada", "ayda", "haftalik", "aylik", "haftanin", "ayin", "hafta", "ay", "gunde"}
TIMES = {"kez", "defa", "kere"}
ORDINAL = {"ilk", "son", "birinci", "ikinci", "ucuncu", "dorduncu", "besinci"}
MONTH_WORDS = {"ay", "ayin", "ayda", "aylik", "ayi"}
HOLIDAY_WORDS = set(WORDS["HOL"].split()) | {"tatilse", "tatiller", "bayramlar"}
MONTHLY = ("month_end_workday", "month_day")
WD_SHORT = {"pzt": 0, "pts": 0, "sal": 1, "car": 2, "crs": 2, "prs": 3, "pers": 3, "cum": 4, "cmt": 5, "cts": 5, "paz": 6}
ORDINAL_UNITS = {"birinci": 1, "ikinci": 2, "ucuncu": 3, "dorduncu": 4, "besinci": 5, "altinci": 6, "yedinci": 7,
                 "sekizinci": 8, "dokuzuncu": 9}
ORDINAL_TENS = {"onuncu": 10, "yirminci": 20, "otuzuncu": 30}


def _numbers(toks):
    """Day numbers written as digits or as words: 10, onuncu, on bes, yirmi besinci."""
    out, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t.isdigit():
            out.append(int(t))
        elif t in ORDINAL_TENS:
            out.append(ORDINAL_TENS[t])
        elif t in TENS:
            unit = None
            if i + 1 < len(toks):
                unit = ORDINAL_UNITS.get(toks[i + 1]) or _strip(toks[i + 1], UNITS)
            out.append(TENS[t] + (unit or 0))
            i += 1 if unit else 0
        i += 1
    return [n for n in out if 1 <= n <= 31]


def _interval(toks):
    for a, b in zip(toks, toks[1:] + [""]):
        if a.startswith(INTERVAL_STEMS) and not (a == "yilin" and b == "her"):  # "yilin her gunu" is every day
            return True
        if (a in COUNT and b in PER) or (a in PER and b in COUNT):
            return True
    return any(a in COUNT and b in TIMES for a, b in zip(toks, toks[1:]))


def contradicts(phrase, rule):
    """Why `rule` cannot be what `phrase` asks for, judged from plain surface signs, or None.

    This does not read the phrase: the model does that. It only checks the model's reading against
    signs code can see without understanding the sentence: a weekday name, an exception word, an
    "every N weeks" word, a month word, a day number. A veto is always safe (the request goes back);
    silence is not approval."""
    toks = re.findall(r"\d+|[a-z]+", fold(phrase))
    kind = rule["type"]
    days = {d[0] for d in map(_weekday, toks) if d} | {WD_SHORT[t] for t in toks if t in WD_SHORT}
    nums = _numbers(toks)
    has_month = bool(MONTH_WORDS & set(toks))
    is_day = lambda t: bool(_weekday(t)) or t in WD_SHORT

    if _interval(toks):
        return "ifade aralikli bir duzen anlatiyor (iki haftada bir, uc ayda bir, ceyrek, yil); kural bunu karsilamaz"
    if EXCEPTION & set(toks) and not HOLIDAY_WORDS & set(toks):
        return "ifadede tatil disinda bir istisna var (haric, disinda, degil); kural istisna tasiyamaz"
    if days:
        if has_month or any(a in ORDINAL and is_day(b) for a, b in zip(toks, toks[1:])):
            return "ifade ayin belirli bir haftasindaki gunu anlatiyor (ilk pazartesi, son cuma); kural bunu karsilamaz"
        if kind in MONTHLY:
            return "ifadede gun adi var ama kural aylik"
        if kind == "daily" and "dahil" not in toks:
            return "ifadede gun adi var ama kural her gun"
        if kind == "weekly" and not days <= set(rule["days"]):
            return "ifadede adi gecen gunlerin hepsi kuralda yok"
        if kind == "workdays" and days not in ({0, 4}, {0, 1, 2, 3, 4}):
            return "ifade pazartesiden cumaya butun gunleri saymiyor ama kural is gunleri"
    weekend = any(a == "hafta" and b.startswith("son") for a, b in zip(toks, toks[1:]))
    if weekend and not days and kind == "weekly" and set(rule["days"]) != {5, 6}:
        return "ifade hafta sonundan soz ediyor ama kural cumartesi ve pazari birlikte icermiyor"
    if has_month and kind not in MONTHLY:
        return "ifade aydan soz ediyor ama kural aylik degil"
    if nums and nums != [7]:
        if kind != "month_day":
            return "ifadede gun numarasi var ama kural onu kullanmiyor"
        if set(nums) != {rule["day"]}:
            return "kuraldaki gun numarasi ifadedekiyle ayni degil"
    if kind == "month_end_workday" and "ilk" in toks and "son" not in toks:
        return "ifade ayin basini anlatiyor, kural ayin sonunu"
    if kind == "month_day" and rule["day"] == 1 and "son" in toks and "ilk" not in toks and not nums:
        return "ifade ayin sonunu anlatiyor, kural ayin basini"
    return None


VAGUE = {"gerektiginde", "gerekirse", "gerektikce", "bazen", "ara", "sira", "civari", "civarinda",
         "dogru", "yaklasik", "yogun", "belli", "bazi", "birkac", "arasira", "mumkunse", "tercihen"}
SOME = {"bir", "iki", "uc", "birkac", "bazi", "belli"}
ALL_WORDS = {"her", "tum", "butun", "hergun", "surekli", "istisnasiz", "hepsi", "tamami", "tumu", "yedi", "7", "hep"}
SHIFT_WORDS = ("tatil", "bayram", "denk", "gelirse", "geliyorsa", "rastla", "degilse", "kay", "ertesi", "sonraki", "takip",
               "muteakip", "sonrasinda", "devaminda", "revize", "esas", "musait")


def unsupported(phrase, rule):
    """Why the phrase does not carry enough to justify `rule`, or None.

    contradicts() stops a reading the phrase rules out. This stops a reading the phrase does not
    back up: every rule type needs a sign of its own in the words (a working-day word for "last
    working day", the day number for "the 15th", a weekday name for "every Monday"). A vague phrase
    ("ay sonunda", "uygun bir gunde") has no such sign, so the model's guess does not get through."""
    toks = re.findall(r"\d+|[a-z]+", fold(phrase))
    pairs = list(zip(toks, toks[1:]))
    kind = rule["type"]
    if VAGUE & set(toks):
        return "ifade belirsiz (uygun, gerektiginde, civari, ara sira); hangi gunler oldugu yazilmali"
    counted = [i for i, (a, b) in enumerate(pairs) if a in SOME and b.startswith("gun")]
    # "iki gun de" (both days) and "son iki gunu" (the last two days) say which days; "bir gun", "iki gun" do not
    if any(toks[i + 2:i + 3] not in (["de"], ["da"]) and toks[max(i - 1, 0)] not in ("son", "ilk") for i in counted):
        return "ifade kac gun oldugunu soyluyor ama hangi gunler oldugunu soylemiyor"
    workday = any(a in ("is", "mesai", "calisma") and b.startswith("gun") for a, b in pairs) or "isgunu" in toks
    weekdays_inside = any(a == "hafta" and b.startswith("ic") for a, b in pairs)
    weekend = any(a == "hafta" and b.startswith("son") for a, b in pairs)
    named = {d[0] for d in map(_weekday, toks) if d} | {WD_SHORT[t] for t in toks if t in WD_SHORT}
    nums = _numbers(toks)
    starts = lambda *stems: any(t.startswith(stems) for t in toks)
    if kind == "month_end_workday":
        if not (workday and starts("son", "bitis", "kapan")):
            return "kural ayin son is gunu, ama ifade 'son is gunu' demiyor (son takvim gunu mu, son is gunu mu?)"
    elif kind == "month_day" and rule["day"] == 1 and rule.get("shift") == "next" and (workday or not nums):
        if not (workday and (starts("ilk", "bas", "birinci", "acilis") or nums == [1])):
            return "kural ayin ilk is gunu, ama ifade 'ilk is gunu' demiyor (ayin 1'i mi, ilk is gunu mu?)"
    elif kind == "month_day":
        if rule["day"] not in nums:
            return "kuraldaki gun numarasi ifadede yazmiyor"
        shifted = starts(*SHIFT_WORDS) or weekend
        if rule.get("shift", "none") != "none" and not shifted:
            return "kural tatilde kaydirma iceriyor ama ifade bundan soz etmiyor"
    elif kind == "workdays":
        if not (workday or weekdays_inside or {0, 4} <= named):
            return "kural is gunleri, ama ifadede is gunu, hafta ici ya da pazartesi-cuma araligi gecmiyor"
    elif kind == "weekly":
        first_of_week = rule["days"] == [0] and any(a == "haftanin" and b == "ilk" for a, b in pairs)
        last_two = rule["days"] == [5, 6] and any(a == "haftanin" and b == "son" for a, b in pairs)
        if not (named or weekend or first_of_week or last_two):
            return "kural haftanin belirli gunleri, ama ifadede gun adi gecmiyor"
    elif kind == "daily":
        if not (ALL_WORDS & set(toks)):
            return "kural her gun, ama ifadede 'her', 'tum' gibi bir soz gecmiyor"
    return None


def parse(phrase):
    """Calendar rule for a run-day phrase, or None when any part of it is not understood.
    The code's own reading goes through the same two checks as the model's."""
    rule = _parse(phrase)
    if rule is None or contradicts(phrase, rule) or unsupported(phrase, rule):
        return None
    return rule


def _parse(phrase):
    toks = re.findall(r"\d+|[a-z]+", fold(phrase))
    tags, wd, nums, ranges = [], [], [], []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.isdigit():
            nums.append(int(t))
            if i + 1 < len(toks) and toks[i + 1] in NUM_SUFFIX:
                i += 1
            if i + 1 < len(toks) and TAG.get(toks[i + 1]) == "DAY":  # "15. gunu"
                i += 1
            i += 1
            continue
        if tags and tags[-1] == "MONTH" and toks[i - 1] == "ayin" and (t in TENS or _strip(t, TENS)):  # "ayin on besi"
            value = _strip(t, TENS)
            unit = _strip(toks[i + 1], UNITS) if i + 1 < len(toks) else None
            if t in TENS and unit:
                value, i = value + unit, i + 1
            nums.append(value)
            i += 1
            continue
        day = _weekday(t)
        if day:
            wd.append(day[0])
            if day[1] == "from":
                ranges.append(["from", day[0]])
            elif day[1] == "to" and ranges and ranges[-1][0] == "from":
                ranges[-1] = ["span", ranges[-1][1], day[0]]
            tags.append("WD")
        elif t in TAG:
            tags.append(TAG[t])
        else:
            return None
        i += 1

    has = set(tags)
    seq = " ".join(tags)
    if "RANGE" in has:
        if len(wd) != 2:
            return None
        ranges = [["span", wd[0], wd[1]]]
    if any(r[0] == "from" for r in ranges):
        return None
    if ranges:
        if len(ranges) != 1:
            return None
        _, a, b = ranges[0]
        if a >= b or set(wd) != {a, b}:
            return None
        wd = list(range(a, b + 1))
    if "TWO" in has and "TWO DAY" not in seq:        # "iki gun de" is fine, "iki haftada bir" is not
        return None
    if "SEVEN" in has and "WEEK_GEN SEVEN DAY" not in seq:
        return None
    if "PREV" in has:
        return None
    excluded_holidays = ("HOL" in has or "HOL_IF" in has) and ("EXC" in has or "NEG" in has)
    weekdays_inside = "WEEK INSIDE" in seq
    weekend = "WEEK END" in seq
    work_day = "WORK DAY" in seq
    every_day = "EVERY DAY" in seq or "WEEK_GEN EVERY DAY" in seq or "WEEK_GEN SEVEN DAY" in seq
    shift = ("IF" in has or "HOL_IF" in has or "END_TO" in has)

    if "MONTH" in has:
        if wd or weekdays_inside or "EXC" in has or "NEG" in has or "INC" in has:
            return None
        if not nums:
            if "LAST" in has and work_day and "FIRST" not in has:
                return {"type": "month_end_workday"}
            if "FIRST" in has and work_day and "LAST" not in has:
                return {"type": "month_day", "day": 1, "shift": "next"}
            return None
        if len(nums) != 1 or not 1 <= nums[0] <= 31 or "LAST" in has or "FIRST" in has:
            return None
        if shift:
            return {"type": "month_day", "day": nums[0], "shift": "next"} if "NEXT" in has and work_day else None
        if has & {"HOL", "NEXT", "WORK", "WEEK"}:
            return None
        return {"type": "month_day", "day": nums[0], "shift": "none"}

    if nums or shift or "NEXT" in has or "START" in has or "LAST" in has:
        return None
    if weekdays_inside or (work_day and not wd):
        if wd or "INC" in has or weekend or (("EXC" in has or "NEG" in has) and not excluded_holidays):
            return None
        return {"type": "workdays"}
    if "EXC" in has or "NEG" in has:
        if wd == [0, 1, 2, 3, 4] and excluded_holidays and not weekend:  # "pazartesiden cumaya, tatiller haric"
            return {"type": "workdays"}
        return None
    if every_day:
        if (wd or weekend) and "INC" not in has:
            return None
        return {"type": "daily"}
    if "FIRST" in has and not ("WEEK_GEN FIRST DAY" in seq and wd == [0]):  # "haftanin ilk gunu (pazartesi)"
        return None
    if weekend and not wd:
        return {"type": "weekly", "days": [5, 6]}
    if wd and not weekend and "WORK" not in has:
        return {"type": "weekly", "days": sorted(set(wd))}
    return None
