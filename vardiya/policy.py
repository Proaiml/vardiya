"""Policy kernel: the single place where safety is enforced.

The model is an untrusted proposal engine. Every action passes through `check`;
anything not explicitly allowed is denied. Keep this file small and reviewable.
"""
from dataclasses import dataclass

from . import intake
from .emulator import NOTOK, OK

# L2 reversible, L3 conditional (pre-flight), L4 high impact (always human approval)
LEVELS = {"hold": 2, "free": 2, "rerun": 3, "run_cleanup": 3, "set_to_ok": 4, "add_event": 4,
          "deploy_job": 3, "delete_job": 3, "close_request": 2, "return_request": 2}
CHANGE_VERBS = ("deploy_job", "delete_job", "close_request", "return_request")
SITE_DEFAULTS = {"max_level": 4, "blast_threshold": 3, "freeze": False, "loop_limit": 2, "approval": "ask"}


@dataclass
class Decision:
    verdict: str  # allow | needs_approval | propose_only | deny
    level: int
    reasons: list


class Policy:
    def __init__(self, site=None, licence=4):
        self.site = {**SITE_DEFAULTS, **(site or {})}
        self.licence, self.count = licence, {}

    def record(self, action, subject):
        self.count[(action, subject)] = self.count.get((action, subject), 0) + 1

    def check_change(self, action, findings=(), ticket=None, definition=None, rollback=False):
        """Definition work. Site decision: the agent applies a definition itself, without human
        approval, but only when it is tied to an open request and every pre-flight check passed."""
        if action not in CHANGE_VERBS:
            return Decision("deny", 0, ["bilinmeyen fiil"])
        level = LEVELS[action]

        def deny(why):
            return Decision("deny", level, [why])

        if ticket is None or ticket.get("status") != "open":
            return deny("acik bir talebe bagli olmayan islem")
        if action in ("deploy_job", "delete_job"):
            asked, _ = intake.parse(ticket["text"])
            if not isinstance(definition, dict) or asked.get("is_adi") != definition.get("name"):
                return deny("tanim, talepte adi gecen isle ayni degil")
            if action == "delete_job" and asked.get("islem") not in ("yeni", "kaldir"):
                return deny("silme yalnizca kaldirma talebinde ya da bu talebin ekledigi isi geri almak icin kullanilir")
            if action == "deploy_job" and asked.get("islem") == "kaldir" and not rollback:
                return deny("kaldirma talebinde tanim yuklenmez")
            errors = [f["msg"] for f in findings if f["severity"] == "error"]
            if errors:
                return Decision("deny", level, errors)
            if self.site["freeze"]:
                return deny("dondurma penceresi acik")
        ceiling = min(self.licence, self.site["max_level"])
        if level > ceiling:
            return Decision("propose_only", level, [f"yetki tavani L{ceiling}, eylem L{level}"])
        return Decision("allow", level, ["talebe bagli; on ucus denetimleri gecti"])

    def check(self, world, action, job=None, event=None, evidence=(), skill=None):
        if action not in LEVELS or action in CHANGE_VERBS:
            return Decision("deny", 0, ["bilinmeyen fiil"])
        level = LEVELS[action]

        def deny(why):
            return Decision("deny", level, [why])

        if action == "add_event":
            job = world.producer.get(event)
            if job is None or world.jobs[job]["status"] != OK:
                return deny("event'in ureticisi basariyla bitmedi; elle eklemek asagi akisi bozuk veriyle tetikler")
        if job not in world.jobs:
            return deny("bilinmeyen is")
        f = world.facts(job)
        if skill is not None and action not in skill.allowed_actions:
            return deny(f"skill bu fiile izinli degil: {action}")
        if not evidence or any(k not in f for k in evidence):
            return deny("kanitsiz oneri: gecerli olgu anahtari gosterilmedi")
        if self.site["freeze"] and level >= 3:
            return deny("dondurma penceresi acik")
        if self.count.get((action, event or job), 0) >= self.site["loop_limit"]:
            return deny("dongu korumasi: ayni eylem bu iste tekrar tekrar denendi")

        if action == "rerun":
            if f["status"] not in (OK, NOTOK):
                return deny("is bitmemis; yeniden calistirilamaz")
            if f["held"]:
                return deny("tutulan is serbest birakilmadan yeniden calistirilamaz")
            if f["idempotency"] == "never":
                return deny("idempotans sinifi: asla otomatik yeniden calismaz")
            if f["idempotency"] == "cleanup_first" and f["target_rows"] > 0:
                return deny(f"hedefte bu gune ait {f['target_rows']} satir var; once temizlik (mukerrer riski)")
        elif action == "run_cleanup":
            if f["status"] != NOTOK or not f["has_cleanup"]:
                return deny("temizlik yalnizca hata almis ve temizligi tanimli iste calisir")
        elif action == "set_to_ok":
            if f["status"] != NOTOK:
                return deny("yalnizca hata almis is basarili sayilabilir")
            if not f["expected_rc"]:
                return deny(f"donus kodu {f['rc']} beklenen hata listesinde degil")
            if f["target_rows"] > 0:
                return deny("hedefte yarim veri var; basarili saymak asagi akisi bozuk veriyle tetikler")

        ceiling = min(self.licence, self.site["max_level"], skill.authority if skill else 4)
        if level > ceiling:
            return Decision("propose_only", level, [f"yetki tavani L{ceiling}, eylem L{level}"])
        if level >= 4:
            return Decision("needs_approval", level, ["yuksek etkili eylem: insan onayi gerekir"])
        if level == 3 and f["critical_downstream"] > self.site["blast_threshold"]:
            return Decision("needs_approval", level,
                            [f"etki alani esigi asildi: {f['critical_downstream']} kritik is"])
        return Decision("allow", level, ["on ucus denetimleri gecti"])
