"""The incident loop: observe -> recall -> diagnose -> propose -> police -> act -> verify -> record.

Two invariants: the model never touches the scheduler (it only proposes), and every
proposal goes through the policy kernel, whoever made it.
"""
from .ledger import Ledger
from .policy import Policy
from .skills import holds
from .world import World


class Harness:
    def __init__(self, adapter, skills, site=None, ledger=None, model=None, licence=4, approver=None):
        self.a, self.skills, self.model = adapter, skills, model
        self.ledger = ledger or Ledger()
        self.policy = Policy(site, licence)
        mode = self.policy.site["approval"]
        self.approver = approver or (lambda step: mode == "auto")
        self.steps, self.reports = [], []

    # ---- the only way an action reaches the scheduler ---------------------------
    def propose(self, action, job=None, event=None, evidence=(), skill=None, by="skill"):
        world = World(self.a)
        d = self.policy.check(world, action, job=job, event=event, evidence=evidence, skill=skill)
        step = {"action": action, "job": job, "event": event, "by": by, "level": d.level,
                "verdict": d.verdict, "reasons": d.reasons, "evidence": list(evidence), "executed": False}
        if d.verdict == "needs_approval":
            step["verdict"] = "allow" if self.approver(step) else "propose_only"
            step["reasons"] = d.reasons + ["onaylandi" if step["verdict"] == "allow" else "onay bekliyor"]
        if step["verdict"] == "allow":
            kw = {"event": event} if action == "add_event" else {"job": job}
            step["executed"] = self.a.call(action, **kw)["ok"]
            self.policy.record(action, event or job)
        self.steps.append(step)
        return step

    # ---- guided mode ------------------------------------------------------------
    def _diagnose(self, skill, facts, precedents):
        candidates = [d for d, when in skill.diagnose.items() if holds(when, facts)]
        note = {"candidates": candidates, "model_choice": None, "overruled": False}
        if self.model is not None:
            ctx = ("Facts (computed by the harness, trustworthy):\n"
                   + "\n".join(f"- {k}: {v}" for k, v in facts.items() if k != "refs")
                   + f"\nPrecedents for this error signature: {precedents}")
            options = {d: f"holds when {when}" for d, when in skill.diagnose.items()}
            options["unknown"] = "none of the above; hand over to a human"
            choice, why = self.model.choose("Which diagnosis fits the evidence?", options, ctx)
            note.update(model_choice=choice, why=why)
            if choice in candidates:
                return choice, note
            note["overruled"] = True  # the model's pick contradicts the evidence
        return (candidates[0] if len(candidates) == 1 else None), note

    def _run_plan(self, skill, plan, target, world):
        for step in plan:
            if step == "escalate":
                return "skill insana devretti"
            if step in ("hold_downstream", "free_downstream"):
                want_held = step == "free_downstream"
                for n in World(self.a).downstream(target):
                    j = World(self.a).jobs[n]
                    if j["held"] == want_held and (want_held or j["status"] == "wait"):
                        self.propose(step.split("_")[0], job=n, evidence=["status"], skill=skill)
                continue
            s = self.propose(step, job=target, evidence=skill.evidence, skill=skill)
            if not s["executed"]:
                return f"{step}: {s['verdict']} ({'; '.join(s['reasons'])})"
        return None

    def handle(self, max_incidents=5):
        seen = set()
        for _ in range(max_incidents):
            world = World(self.a)
            target = world.first_fault()
            if target is None or target in seen:
                break
            seen.add(target)
            facts = world.facts(target)
            precedents = self.ledger.lookup(facts["signature"])
            report = {"target": target, "facts": facts, "precedents": precedents, "skill": None,
                      "diagnosis": None, "escalated": None, "verified": False,
                      "blast_radius": world.blast_radius(target), "critical_path": world.critical_path()}
            first = len(self.steps)
            skill = next((s for s in self.skills if holds(s.trigger, facts)), None)
            if skill is None:
                report["escalated"] = "eslesen skill yok"
            else:
                report["skill"] = skill.name
                diagnosis, note = self._diagnose(skill, facts, precedents)
                report.update(diagnosis=diagnosis, diagnosis_note=note)
                if diagnosis is None:
                    report["escalated"] = "teshis kanitla dogrulanamadi"
                else:
                    report["escalated"] = self._run_plan(skill, skill.plans.get(diagnosis, ["escalate"]), target, world)
                    after = World(self.a).facts(target)
                    post = skill.postconditions.get(diagnosis, [])
                    report["verified"] = report["escalated"] is None and all(holds(p, after) for p in post)
                    if report["escalated"] is None and not report["verified"]:
                        report["escalated"] = "dogrulama kosullari saglanmadi"
            report["steps"] = self.steps[first:]
            self.ledger.append({"clock": world.clock, "job": target, "signature": facts["signature"],
                                "diagnosis": report["diagnosis"], "verified": report["verified"],
                                "actions": [[s["action"], s["job"]] for s in report["steps"] if s["executed"]],
                                "model": getattr(self.model, "spec", None), "escalated": report["escalated"]})
            self.reports.append(report)
            if report["escalated"]:
                break
        return self.reports


def render(reports, alerts=()):
    """Operator-facing report in Turkish, every claim tied to an evidence reference."""
    if not reports:
        extra = f" {len(alerts)} uyari incelendi; esik ici." if alerts else ""
        return "Ariza yok. Hicbir eylem alinmadi." + extra
    out = []
    for r in reports:
        f, refs = r["facts"], r["facts"]["refs"]
        cp = r["critical_path"]
        out += [f"== {r['target']} ==",
                f"Durum: {f['status']} rc={f['rc']}  [{refs['rc']}]",
                f"Yeni sysout satirlari: {f['sysout_diff']}  [{refs['sysout_diff']}]",
                f"Hedefte bu gune ait satir: {f['target_rows']} / kaynak {f['source_rows']}  [{refs['target_rows']}]",
                f"Etki alani: {r['blast_radius']['count']} is, kritik: {r['blast_radius']['critical']}  "
                f"[{refs['critical_downstream']}]",
                f"Kritik yol: {' > '.join(cp['path'])}  tahmini bitis t={cp['eta']}  pay={cp['slack']}",
                f"Emsal: {r['precedents']['verified']} dogrulanmis vaka {r['precedents']['diagnoses']}",
                f"Skill: {r['skill']}  Teshis: {r['diagnosis']}"]
        note = r.get("diagnosis_note") or {}
        if note.get("model_choice") is not None or note.get("overruled"):
            out.append(f"Model secimi: {note.get('model_choice')}"
                       + ("  (kanitla celisti, reddedildi)" if note.get("overruled") else ""))
        for s in r["steps"]:
            mark = "UYGULANDI" if s["executed"] else s["verdict"].upper()
            out.append(f"  L{s['level']} {s['action']:<12} {s['job'] or s['event']:<16} {mark}: {'; '.join(s['reasons'])}")
        out.append("Sonuc: " + ("dogrulandi" if r["verified"] else f"insana devredildi ({r['escalated']})"))
    return "\n".join(out)
