"""Skill layer: declarative runbooks. A skill is data, never code.

A skill may only use kernel verbs, cannot raise its own authority, and cannot
skip the policy check. Parsing is a strict YAML subset so no dependency is needed.
"""
import pathlib
import re
from dataclasses import dataclass, field

PLAN_STEPS = {"hold_downstream", "free_downstream", "run_cleanup", "rerun", "set_to_ok", "escalate"}


def _scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return int(v) if v.lstrip("-").isdigit() else v


def parse_yaml(text):
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        indent, line = len(raw) - len(raw.lstrip()), raw.strip()
        while stack[-1][0] >= indent:
            stack.pop()
        key, _, val = line.partition(":")
        if val.strip() == "":
            child = {}
            stack[-1][1][key.strip()] = child
            stack.append((indent, child))
        else:
            stack[-1][1][key.strip()] = _scalar(val)
    return root


def _literal(tok, facts):
    if tok in facts:
        return facts[tok]
    return {"true": True, "false": False}.get(tok, _scalar(tok))


def holds(expr, facts):
    """Tiny safe evaluator: `fact op value` clauses joined by ` and `. No eval()."""
    for clause in expr.split(" and "):
        parts = clause.split(None, 2)
        if len(parts) != 3 or parts[1] not in OPS or parts[0] not in facts:
            return False
        try:
            if not OPS[parts[1]](facts[parts[0]], _literal(parts[2].strip(), facts)):
                return False
        except (TypeError, re.error):
            return False
    return True


def _matches(value, pattern):
    # a pattern comes from a skill file: keep both sides short so a bad one cannot stall the desk
    return len(str(pattern)) <= 200 and len(str(value)) <= 500 and re.fullmatch(str(pattern), str(value)) is not None


OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, ">": lambda a, b: a > b,
       ">=": lambda a, b: a >= b, "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
       "matches": _matches, "startswith": lambda a, b: str(a).startswith(str(b)),
       "endswith": lambda a, b: str(a).endswith(str(b))}


@dataclass
class Skill:
    name: str
    description: str
    trigger: str
    authority: int
    allowed_actions: list
    diagnose: dict
    plans: dict
    postconditions: dict
    evidence: list
    body: str = ""
    errors: list = field(default_factory=list)


def load_skill(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    m = parse_yaml(front)
    s = Skill(m["name"], m.get("description", ""), m["trigger"], int(str(m["authority"]).lstrip("L")),
              m.get("allowed_actions", []), m.get("diagnose", {}), m.get("plans", {}),
              m.get("postconditions", {}), m.get("evidence", []), body.strip())
    # static safety gate: a skill can only name kernel plan steps it declared as allowed
    for diag, steps in s.plans.items():
        for step in steps:
            if step not in PLAN_STEPS:
                s.errors.append(f"{diag}: bilinmeyen adim {step}")
            base = {"hold_downstream": "hold", "free_downstream": "free"}.get(step, step)
            if step != "escalate" and base not in s.allowed_actions:
                s.errors.append(f"{diag}: {step} izinli eylemlerde yok")
        if diag not in s.diagnose:
            s.errors.append(f"plan '{diag}' icin teshis kosulu yok")
    if "http://" in text or "https://" in text:
        s.errors.append("skill dis baglanti tasiyamaz")
    return s


def _kind(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return parse_yaml(text.split("---", 2)[1]).get("kind", "incident")


def load_skills(directory):
    """Incident skills (runbooks). Request-rule skills in the same folder are loaded separately."""
    skills = [load_skill(p) for p in sorted(pathlib.Path(directory).glob("*/SKILL.md")) if _kind(p) == "incident"]
    bad = [f"{s.name}: {e}" for s in skills for e in s.errors]
    if bad:
        raise ValueError("gecersiz skill: " + "; ".join(bad))
    return skills


# ---- request-rule skills ---------------------------------------------------------
# A site's own standards for job definitions, as data. A rule can only add a reason to return a
# request; nothing in a skill can make the desk accept what the kernel checks refuse.
RULE_FACTS = ("name", "folder", "type", "host", "run_as", "command", "calendar", "time", "notify", "description",
              "dep_count", "hour", "minute", "is_new", "folder_prefix", "std_name_regex", "std_notify_suffix")


@dataclass
class Rule:
    skill: str
    id: str
    require: str
    message: str
    when: str = ""
    severity: str = "error"


def load_rule_skill(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    m = parse_yaml(text.split("---", 2)[1])
    rules, errors = [], []
    if "http://" in text or "https://" in text:
        errors.append("skill dis baglanti tasiyamaz")
    for rid, body in (m.get("rules") or {}).items():
        if not isinstance(body, dict) or not body.get("require") or not body.get("message"):
            errors.append(f"{rid}: require ve message zorunlu")
            continue
        if set(body) - {"require", "message", "when", "severity"}:
            errors.append(f"{rid}: bilinmeyen alan {sorted(set(body) - {'require', 'message', 'when', 'severity'})}")
        if body.get("severity", "error") not in ("error", "warning"):
            errors.append(f"{rid}: severity error ya da warning olmali")
        for expr in (str(body["require"]), str(body.get("when", ""))):
            for clause in filter(None, expr.split(" and ")):
                parts = clause.split(None, 2)
                if len(parts) != 3 or parts[1] not in OPS:
                    errors.append(f"{rid}: kosul okunamadi: {clause}")
                elif parts[0] not in RULE_FACTS:
                    errors.append(f"{rid}: bilinmeyen olgu {parts[0]}")
        rules.append(Rule(m.get("name", "?"), rid, str(body["require"]), str(body["message"]),
                          str(body.get("when", "")), body.get("severity", "error")))
    if errors:
        raise ValueError(f"gecersiz skill {m.get('name', path)}: " + "; ".join(errors))
    return rules


# ---- incident-class skills -------------------------------------------------------
# The evidence queries a class may ask for. The queries themselves live in cozumle.py; a class only names them.
EVIDENCE = {"shared_attr", "named_in_error", "recent_change", "host_change", "pred_failed", "pred_setok",
            "crossed_new_day", "slowing", "precedent", "external_source"}
HARMFUL_ACTIONS = {"rerun", "set_ok", "run_now"}  # run_now: start ignoring conditions, resources and time


def load_incident_classes(directory):
    """Failure classes from `kind: incident_classes` skills: {class: {title, signs, cause, fix, harmful, evidence}}.
    A class with no signs, no fix, or an unknown evidence query or action is refused, not half-loaded."""
    out = {}
    for path in sorted(pathlib.Path(directory).glob("*/SKILL.md")):
        if _kind(path) != "incident_classes":
            continue
        m = parse_yaml(path.read_text(encoding="utf-8").split("---", 2)[1])
        for name, c in (m.get("classes") or {}).items():
            if not isinstance(c, dict):
                continue
            signs = [str(s).lower() for s in (c.get("signs") if isinstance(c.get("signs"), list) else [c.get("signs")])
                     if s]
            evidence = c.get("evidence") if isinstance(c.get("evidence"), list) else [c.get("evidence")]
            harmful = c.get("harmful") if isinstance(c.get("harmful"), list) else ([c["harmful"]] if c.get("harmful") else [])
            if not signs or not c.get("fix") or not set(evidence) <= EVIDENCE or not set(harmful) <= HARMFUL_ACTIONS:
                continue
            # fix_airflow, fix_cron, ...: the same class, fixed in that product's own words
            fix_by = {key[4:]: str(v) for key, v in c.items() if key.startswith("fix_") and v}
            out[name] = {"title": c.get("title", name), "signs": signs, "cause": str(c.get("cause", "")),
                         "fix": str(c["fix"]), "fix_by": fix_by, "harmful": harmful, "evidence": evidence,
                         "skill": m.get("name")}
    return out


def load_procedures(directory):
    """Admin procedures from `kind: admin_procedures` skills: {name: {title, triggers, steps, caution}}.
    A procedure with fewer than two triggers or no steps is refused."""
    out = {}
    for path in sorted(pathlib.Path(directory).glob("*/SKILL.md")):
        if _kind(path) != "admin_procedures":
            continue
        m = parse_yaml(path.read_text(encoding="utf-8").split("---", 2)[1])
        for name, p in (m.get("procedures") or {}).items():
            if not isinstance(p, dict):
                continue
            triggers = [str(t).lower() for t in (p.get("triggers") if isinstance(p.get("triggers"), list) else []) if t]
            if len(triggers) < 2 or not p.get("steps"):
                continue
            needs = [str(x).lower() for x in (p.get("needs") if isinstance(p.get("needs"), list) else []) if x]
            out[name] = {"title": str(p.get("title", name)), "triggers": triggers, "steps": str(p["steps"]),
                         "caution": str(p.get("caution", "")), "needs": needs, "skill": m.get("name")}
    return out


def _stem(word):
    """A rough Turkish/English stem: long words lose their last two letters (saati -> saa, kilitli -> kilit)."""
    return word[:max(4, len(word) - 2)] if len(word) >= 5 else word


def soft_in(phrase, text):
    """The phrase occurs in the text, exactly or word by word with suffixes ('baslama saati' in
    'baslama ve bitis saatlerini'). Every word of the phrase must start some word of the text."""
    p, t = fold(phrase), fold(text)
    if p in t:
        return True
    words = re.findall(r"[a-z0-9_.%$-]+", t)
    parts = re.findall(r"[a-z0-9_.%$-]+", p)
    return bool(parts) and all(len(w) >= 3 and any(x.startswith(_stem(w)) for x in words) for w in parts)


def match_procedures(procedures, text, need=2, limit=2):
    """The procedures whose triggers occur in the text, best first; a procedure needs `need` hits."""
    # a procedure with `needs` belongs to one product: it is considered only when the text names that product
    scored = sorted(((sum(soft_in(t, text) for t in p["triggers"]), name) for name, p in procedures.items()
                     if not p.get("needs") or any(soft_in(n, text) for n in p["needs"])), reverse=True)
    return [name for hits, name in scored if hits >= need][:limit]


def load_general_skills(directory):
    """Product-independent server skills from `kind: general_skills` skills:
    {name: {title, classes, triggers, check: {unix, windows}, fix: {unix, windows}, caution}}.
    A skill with fewer than two triggers or no read-only check is refused."""
    out = {}
    for path in sorted(pathlib.Path(directory).glob("*/SKILL.md")):
        if _kind(path) != "general_skills":
            continue
        m = parse_yaml(path.read_text(encoding="utf-8").split("---", 2)[1])
        for name, g in (m.get("skills") or {}).items():
            if not isinstance(g, dict):
                continue
            triggers = [str(t).lower() for t in (g.get("triggers") if isinstance(g.get("triggers"), list) else []) if t]
            check = {o: str(g.get(f"check_{o}", "")) for o in ("unix", "windows")}
            if len(triggers) < 2 or not any(v and not v.startswith("(uygulanmaz") for v in check.values()):
                continue
            classes = g.get("classes") if isinstance(g.get("classes"), list) else []
            out[name] = {"title": str(g.get("title", name)), "classes": [str(c) for c in classes],
                         "triggers": triggers, "check": check,
                         "fix": {o: str(g.get(f"fix_{o}", "")) for o in ("unix", "windows")},
                         "caution": str(g.get("caution", "")), "skill": m.get("name")}
    return out


def load_chains(directory):
    """Solution chains from `kind: solution_chains` skills: {incident class: {"order": [ref, ...], "support": n}}.
    A ref is genel:<name>, yordam:<name> or sinif:<name>."""
    out = {}
    for path in sorted(pathlib.Path(directory).glob("*/SKILL.md")):
        if _kind(path) != "solution_chains":
            continue
        m = parse_yaml(path.read_text(encoding="utf-8").split("---", 2)[1])
        for cls, c in (m.get("chains") or {}).items():
            order = c.get("order") if isinstance(c, dict) and isinstance(c.get("order"), list) else []
            order = [str(r) for r in order if re.fullmatch(r"(genel|yordam|sinif):[a-z0-9_]+", str(r))]
            if order:
                out[cls] = {"order": order, "support": int(c.get("support") or 0)}
    return out


WINDOWS_WORDS = ("windows", "powershell", ".bat", ".ps1", ".cmd", "registry", "kayit defteri", "winrm", "secpol",
                 "event viewer", "c:\\", "net use", "unc", "iis", "mssql", "sqlcmd", "logon as", "log on as")
UNIX_WORDS = ("linux", "unix", "aix", "solaris", "hp-ux", "rhel", "ubuntu", "bash", "ksh", "/etc/", "/var/",
              "systemd", "systemctl", "cron", "ulimit", "chmod", "chown", "ssh", "nfs", "kubernetes", "slurm")


def host_os(text):
    """'windows', 'unix' or None (both) from the words of the text."""
    low = fold(text)
    w, u = sum(x in low for x in WINDOWS_WORDS), sum(x in low for x in UNIX_WORDS)
    return "windows" if w > u else "unix" if u > w else None


def match_general(general, text, found_classes=(), limit=3):
    """General skills for a case: those bound to the matched incident classes (first class first), then those
    whose own triggers occur in the text (two hits). The bound ones rank by their trigger hits in the text."""
    hits = {name: sum(soft_in(t, text) for t in g["triggers"]) for name, g in general.items()}
    out = []
    for c in found_classes:
        bound = sorted((n for n, g in general.items() if c in g["classes"]), key=lambda n: -hits[n])
        out += [n for n in bound[:2] if n not in out]
    out += [n for n, h in sorted(hits.items(), key=lambda x: -x[1]) if h >= 2 and n not in out]
    return out[:limit]


_FOLD =str.maketrans("çğıöşüÇĞİÖŞÜâîû", "cgiosuCGIOSUaiu")


def fold(text):
    """Lower case without Turkish diacritics, so 'yeniden başlat' and 'yeniden baslat' compare equal."""
    return str(text or "").translate(_FOLD).lower()


def load_request_rules(directory):
    out = []
    for p in sorted(pathlib.Path(directory).glob("*/SKILL.md")):
        if _kind(p) == "request_rules":
            out += load_rule_skill(p)
    return out
