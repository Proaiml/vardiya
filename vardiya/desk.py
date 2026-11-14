"""Request desk: template -> checked definition -> deploy -> audit record.

The model never writes a definition. Code parses the template, compiles the job and
runs the checks. The model is asked one narrow thing only: to turn a free-text
"which days" phrase into one of the site's calendars, and its answer is cross-checked
against computed run dates before it is trusted.
"""
import datetime
import pathlib
import re

from . import __version__, checks, gunler, intake
from .ledger import Ledger
from .policy import Policy
from .repo import normalise, run_dates
from .skills import load_request_rules

SKILLS_DIR = pathlib.Path(__file__).resolve().parent.parent / "skills"

HORIZON = 60
MATCH_DAYS = 400  # a rule and a calendar are the same if they agree on every day of this window
COVER_DAYS = 180  # a job's run days must lie within its predecessors' run days over this window
DAYS = ("Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz")
NONE_OF_THESE = "hicbiri"
# strategy = voters joined by "+", optionally "/quorum" (default: all must agree)
STRATEGIES = {"agree2": "name+dates", "single": "name", "rule2": "rule+name", "vote3": "name+dates+rule/2",
              "all3": "name+dates+rule", "rulecheck": "rule+check"}
# How a free-text "which days" phrase becomes a calendar. The model reads; code checks.
#   lex>   phrases written in a fixed pattern are read by code (gunler.parse); on wording by other
#          authors that is about one phrase in five, the rest goes to the model
#   rule   the model fills in a rule form; code finds the calendar that runs on exactly those dates
#   gloss  the model is given the harness's vocabulary notes
#   veto   code compares the model's rule with plain signs in the phrase (gunler.contradicts)
# Measured on phrases written after this was frozen (SAB split ext2): the model's reading alone was
# 76-81% correct with 16-20% wrong calendars; with the veto 91-95% correct and 0-1% wrong.
DEFAULT_STRATEGY = "lex>rule-gloss-veto"
# A strategy name that contains "gloss" also gives the model the harness's vocabulary notes.
STRATEGIES.update({"rule-gloss": "rule", "rulecheck-gloss": "rule+check"})
# Guided reading ("tree") and its combinations with the one-shot rule form and with the lexicon.
STRATEGIES.update({"tree2": "tree+rule", "lex>tree2": "lex>tree+rule"})
# "veto" in a strategy name: the model's rule is checked against surface signs in the phrase
# (gunler.contradicts) before it may become a calendar.
STRATEGIES.update({"rule-gloss-veto": "rule", "tree-veto": "tree", "tree2-gloss-veto": "tree+rule",
                   "any2-gloss-veto": "tree+rule/1", "lex>rule-gloss-veto": "lex>rule"})
# "desc1" in a strategy name: the description is compared with the fields by one open question to the
# model (first version, kept for comparison). Without it: the model reads the description, code compares.
STRATEGIES.update({"lex>rule-gloss-veto-desc1": "lex>rule"})
# "review" in a strategy name (experimental, off by default): after every coded check has passed, the
# model is shown the job with its neighbours and asked an open question: would this definition fail to
# run as intended? A coded check knows only the defects its author thought of; this is the room left
# for the ones nobody coded. A wrong "yes" costs a returned request, never a wrong job.
# "nocaldep" switches the calendar-fit check off, only to measure what the review catches without it.
STRATEGIES.update({"lex>rule-gloss-veto-review": "lex>rule", "lex>rule-gloss-veto-review-nocaldep": "lex>rule",
                   "lex>rule-gloss-veto-nocaldep": "lex>rule"})
REVIEW_FIELDS = {"gunler": "calendar", "saat": "time", "host": "host", "calistiran": "run_as", "bagimlilik": "deps",
                 "komut": "command", "tip": "type"}
CONFLICT_FIELDS = {"gunler": "calendar", "saat": "time", "host": "host", "bagimlilik": "deps"}
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
DAY_WORDS = {"pazartesi": "mon", "sali": "tue", "salı": "tue", "carsamba": "wed", "çarşamba": "wed", "persembe": "thu",
             "perşembe": "thu", "cuma": "fri", "cumartesi": "sat", "pazar": "sun"}
# Domain vocabulary the harness owns. It explains words; it does not contain any request.
GLOSSARY = (
    "Turkish vocabulary: 'is gunu' / 'iş günü' / 'mesai günü' / 'çalışma günü' = working day (Monday-Friday, not a "
    "public holiday); 'hafta içi' = Monday to Friday; 'hafta sonu' = Saturday and Sunday; 'her' = every; "
    "'ay sonu' / 'ayın son' = end / last of the month; 'ay başı' / 'ayın ilk' = start / first of the month; "
    "'hariç' = except; 'dahil' = included; 'tatil' = holiday. Weekdays: pazartesi = mon, salı = tue, "
    "çarşamba = wed, perşembe = thu, cuma = fri, cumartesi = sat, pazar = sun.")
RULE_FORM = (
    "Translate the requested run days into ONE JSON object, exactly one of these forms:\n"
    '{"type": "daily"}  - every day, weekends and public holidays included\n'
    '{"type": "workdays"}  - Monday to Friday, except public holidays\n'
    '{"type": "weekly", "days": ["mon", "sat"]}  - the same weekdays every week (mon tue wed thu fri sat sun), '
    "holidays included\n"
    '{"type": "month_end_workday"}  - the last working day of each month\n'
    '{"type": "month_start_workday"}  - the first working day of each month\n'
    '{"type": "month_day", "day": 15, "shift": "next"}  - a fixed day of each month; shift says what happens when '
    'that day is not a working day: "next" = next working day, "prev" = previous working day, "none" = run anyway\n'
    '{"type": "other"}  - anything these forms cannot express exactly (first Monday of the month, every two weeks, '
    "quarterly, yearly, weekdays with an exception, ...)\n"
    "Use \"other\" whenever the request does not fit a form exactly. Do not approximate.")


def parse_rule(obj):
    """Strictly validate the model's rule form. Anything unexpected is treated as no answer."""
    if not isinstance(obj, dict):
        return None
    kind = obj.get("type")
    if kind in ("daily", "workdays", "month_end_workday"):
        return {"type": kind}
    if kind == "month_start_workday":
        return {"type": "month_day", "day": 1, "shift": "next"}
    if kind == "weekly":
        days = obj.get("days")
        if isinstance(days, list) and days and all(isinstance(d, str) for d in days):
            days = [DAY_WORDS.get(d.strip().lower(), d.strip().lower()[:3]) for d in days]  # monday, Mon, pazartesi
            if all(d in WEEKDAYS for d in days):
                return {"type": "weekly", "days": sorted({WEEKDAYS.index(d) for d in days})}
    if kind == "month_day":
        day, shift = obj.get("day"), obj.get("shift", "none")
        if isinstance(day, int) and not isinstance(day, bool) and 1 <= day <= 31 and shift in ("none", "next", "prev"):
            return {"type": "month_day", "day": day, "shift": shift}
    return None


def date_labels(names):
    """Neutral labels for the cross-check question, so the model cannot just repeat a name."""
    return {chr(65 + i): n for i, n in enumerate(sorted(names, reverse=True))}


def _pretty(iso):
    return f"{iso} {DAYS[datetime.date.fromisoformat(iso).weekday()]}"


class Desk:
    def __init__(self, adapter, model=None, site=None, ledger=None, licence=4, agent="vardiya",
                 strategy=DEFAULT_STRATEGY, rules=None):
        self.a, self.model, self.strategy = adapter, model, strategy
        self.rules = load_request_rules(SKILLS_DIR) if rules is None else list(rules)
        self.vetoes = []
        self.policy = Policy(site, licence)
        self.ledger = ledger or Ledger()
        self.agent = f"{agent}/{__version__}" + (f" + {model.spec}" if model is not None else " (model bagli degil)")
        self.steps = []

    # ---- the only way an action reaches the repository ----------------------------
    def _act(self, action, kw, ticket, findings=(), definition=None):
        """`definition` is what the policy judges; for deploy_job it is the one being deployed."""
        d = self.policy.check_change(action, findings, ticket=ticket, definition=definition or kw.get("definition"))
        step = {"action": action, "level": d.level, "verdict": d.verdict, "reasons": d.reasons, "executed": False}
        if d.verdict == "allow":
            step["executed"] = self.a.call(action, **kw)["ok"]
        self.steps.append(step)
        return step

    # ---- the one thing the model is asked: which calendar a free-text phrase means ----
    # Three independent ways to ask; a strategy names which are used and how many must agree.
    def _vote_name(self, phrase, env, names, ctx):
        options = {n: env["calendars"][n] for n in names}
        options[NONE_OF_THESE] = "none of these fits; ask the requester"
        choice, _ = self.model.choose("Which calendar matches the requested run days?", options, ctx)
        return choice if choice in names else None

    def _vote_dates(self, phrase, env, names, ctx):
        labels, options = date_labels(names), {}
        for label, n in labels.items():
            dates = self.a.call("forecast", calendar=n, days=HORIZON) or []
            options[label] = ("runs on: " + ", ".join(_pretty(x) for x in dates[:8])) if dates else "no run in this period"
        options["X"] = "none of these fits"
        choice, _ = self.model.choose(f"Which list of run dates (next {HORIZON} days) matches the requested run days?",
                                      options, ctx)
        return labels.get(choice)

    def _vote_rule(self, phrase, env, names, ctx):
        """The model fills in a rule form; code finds the calendar that produces exactly those dates."""
        form = RULE_FORM + ("\n\n" + GLOSSARY if "gloss" in self.strategy else "")
        rule = parse_rule(self.model.ask_json([
            {"role": "system", "content": "You are a careful batch operations analyst."},
            {"role": "user", "content": ctx + "\n\n" + form}]))
        return self._accept(phrase, rule, env, names)

    def _accept(self, phrase, rule, env, names):
        """A rule the model read from the phrase becomes a calendar only if code finds no surface sign
        in the phrase that contradicts it (strategies with "veto") and one calendar runs on its dates."""
        if rule is None:
            return None
        if "veto" in self.strategy:
            why = gunler.contradicts(phrase, rule) or gunler.unsupported(phrase, rule)
            if why:
                self.vetoes.append({"rule": rule, "why": why})
                return None
        return self._calendar_for(rule, env, names)

    def _vote_tree(self, phrase, env, names, ctx):
        return self._accept(phrase, self._tree_rule(ctx), env, names)

    def _tree_rule(self, ctx):
        """Guided reading: the harness walks the model through narrow questions, one decision each,
        and builds the rule from the answers. The model still does all of the reading."""
        ctx = ctx + "\n" + GLOSSARY
        ask = lambda question, options: self.model.choose(question, options, ctx)[0]
        system = {"role": "system", "content": "You are a careful batch operations analyst."}
        kind = ask("According to the requester, how often should the job run?", {
            "every_day": "every single day, Saturdays, Sundays and public holidays included",
            "working_days": "every working day: Monday to Friday, but not on public holidays",
            "weekdays": "only on certain named weekdays, every week (only Mondays; Saturday and Sunday; Tuesday and Thursday)",
            "monthly": "once a month",
            "other": "anything else: every two weeks, quarterly, yearly, twice a month, or a pattern with an exception "
                     "such as 'weekdays except Wednesday'"})
        rule = None
        if kind == "every_day":
            rule = {"type": "daily"}
        elif kind == "working_days":
            rule = {"type": "workdays"}
        elif kind == "weekdays":
            out = self.model.ask_json([system, {"role": "user", "content": (
                ctx + '\n\nWhich weekdays does the requester name? Reply with JSON: {"days": ["mon", "tue", "wed", "thu", '
                '"fri", "sat", "sun"] (only the named ones), "every_week": true or false (false if it is every '
                'second week, or only a certain week of the month such as the first Monday)}')}])
            if isinstance(out, dict) and out.get("every_week") is True:
                rule = parse_rule({"type": "weekly", "days": out.get("days")})
        elif kind == "monthly":
            which = ask("Which day of the month does the requester mean?", {
                "last_working_day": "the last working day of the month",
                "first_working_day": "the first working day of the month",
                "fixed_day": "a fixed day number, such as the 10th or the 15th",
                "weekday_position": "a weekday position, such as the first Monday or the last Friday of the month",
                "other": "something else, or not clear"})
            if which == "last_working_day":
                rule = {"type": "month_end_workday"}
            elif which == "first_working_day":
                rule = {"type": "month_day", "day": 1, "shift": "next"}
            elif which == "fixed_day":
                out = self.model.ask_json([system, {"role": "user", "content": (
                    ctx + '\n\nReply with JSON: {"day": <day number 1-31>, "shift": "next" | "prev" | "none"}. '
                    'shift says what the requester wants when that day is a weekend or public holiday: "next" = move to '
                    'the next working day, "prev" = move to the previous working day, "none" = run on that day anyway or '
                    'nothing is said about it.')}])
                rule = parse_rule({"type": "month_day", **out}) if isinstance(out, dict) else None
        return rule

    def _calendar_for(self, rule, env, names):
        """The one calendar that runs on exactly the rule's dates, or None."""
        today = datetime.date.fromisoformat(env["today"])
        want = [d.isoformat() for d in run_dates(rule, env["holidays"], today, MATCH_DAYS)]
        same = [n for n in names if self.a.call("forecast", calendar=n, days=MATCH_DAYS) == want]
        return same[0] if len(same) == 1 else None

    def _confirm(self, phrase, env, calendar, ctx):
        """Verification gate: show the dates the chosen calendar really produces and ask yes or no."""
        dates = self.a.call("forecast", calendar=calendar, days=HORIZON) or []
        shown = ", ".join(_pretty(x) for x in dates[:10]) or "no run in this period"
        out = self.model.ask_json([
            {"role": "system", "content": "You are a careful batch operations analyst."},
            {"role": "user", "content": (
                f"{ctx}\n{GLOSSARY}\n\nA calendar was chosen for this request. In the next {HORIZON} days it runs on:\n{shown}\n"
                "(Pzt=Mon Sal=Tue Car=Wed Per=Thu Cum=Fri Cmt=Sat Paz=Sun)\n\n"
                "Check the request word by word against these dates: the weekdays, the day of the month, and any "
                "exception it mentions. Is this exactly what the requester asked for, no more and no less?\n"
                'Reply with JSON: {"mismatch": "<what differs, or none>", "answer": "yes" or "no"}')}])
        return isinstance(out, dict) and str(out.get("answer", "")).strip().lower() == "yes"

    def _conflict_by_reading(self, definition, env, jobs, text):
        """The model reads the description; code compares what it read with the form.

        The model is shown only the description, never the form values, and reports what the
        description states: a start time, a server, predecessor jobs, run days. Code keeps only what
        it can find in the description itself, then compares each item with the field. Asking the
        model "does this contradict the form?" worked worse: it argued its way to "no"."""
        out = self.model.ask_json([
            {"role": "system", "content": "You are a careful batch operations analyst."},
            {"role": "user", "content": (
                f"A team wrote this free-text description for a batch job:\n\"{text}\"\n\n"
                "Report only what the description itself states. Reply with ONE JSON object:\n"
                '{"start_time": "<clock time the job starts at, as HH:MM, or empty if not stated>",\n'
                ' "server": "<name of the server it runs on, or empty if not stated>",\n'
                ' "starts_after": [<names of the jobs it starts after, or an empty list>],\n'
                ' "run_days": <one of the run-day forms below>,\n'
                ' "run_days_quote": "<the exact words of the description that state the run days, or empty>"}\n\n'
                "Run-day forms:\n" + RULE_FORM.split("\n", 1)[1]
                + '\n{"type": "not_stated"}  - the description says nothing about which days the job runs\n\n' + GLOSSARY)}])
        if not isinstance(out, dict):
            return None
        times = {f"{int(m.group(1)):02d}:{m.group(2)}": m.group(0)
                 for m in re.finditer(r"(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)", text)}
        mentioned = lambda word: re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, re.I) is not None

        stated = re.fullmatch(r"\s*([01]?\d|2[0-3])[:.]([0-5]\d)\s*", str(out.get("start_time") or ""))
        if stated:
            stated = f"{int(stated.group(1)):02d}:{stated.group(2)}"
            if stated in times and stated != definition["time"]:
                return "saat", times[stated]
        server = str(out.get("server") or "").strip()
        match = next((h for h in env["hosts"] if h.lower() == server.lower()), None)
        if match and mentioned(match) and match != definition["host"]:
            return "host", match
        after = out.get("starts_after") if isinstance(out.get("starts_after"), list) else []
        for name in after:
            if isinstance(name, str) and name in jobs and mentioned(name) and name not in definition["deps"]:
                return "bagimlilik", name

        rule = parse_rule(out.get("run_days"))
        quote = str(out.get("run_days_quote") or "").strip().strip(".;, ")
        if len(quote) < 4 or gunler.fold(quote) not in gunler.fold(text):
            return None  # nothing stated about run days, or no such words in the description
        if rule is None and isinstance(out.get("run_days"), dict) and out["run_days"].get("type") == "other":
            # The description does state run days, but the model could not put them into a form in one
            # go ("hem hafta ici hem hafta sonlari"). Walk it through the narrow questions once.
            rule = self._tree_rule(f"A job description states its run days in these words: \"{quote}\".")
        if rule is None or gunler.contradicts(quote, rule) or gunler.unsupported(quote, rule):
            return None  # not readable, or the quoted words do not carry the reading ("gun sonu" is not "every day")
        today = datetime.date.fromisoformat(env["today"])
        days = [d.isoformat() for d in run_dates(rule, env["holidays"], today, MATCH_DAYS)]
        if days != self.a.call("forecast", calendar=definition["calendar"], days=MATCH_DAYS):
            return "gunler", quote
        return None

    def _second_look(self, definition, env, jobs):
        """An open question, asked last: with its neighbours in view, would this job fail to run as
        intended? Returns (field, what the model saw) or None.

        The harness brings the context (who the job waits for, who waits for it, and the coming run
        dates of each); the model looks for what no coded check names. Code holds the answer to the
        little it can verify: a real field, and a job that really is a neighbour."""
        name = definition["name"]
        near = {n: jobs[n] for n in definition["deps"] if n in jobs and n != name}
        waiting = {n: j for n, j in jobs.items() if name in j["deps"] and n != name}
        dates = lambda cal: ", ".join(_pretty(x) for x in (self.a.call("forecast", calendar=cal, days=21) or [])[:10])
        line = lambda j: (f"{j['name']}: runs on calendar {j['calendar']} ({env['calendars'].get(j['calendar'], '')}), "
                          f"starts {j['time']}, host {j['host']}, type {j['type']}\n    next run dates: {dates(j['calendar'])}")
        out = self.model.ask_json([
            {"role": "system", "content": "You are an experienced batch scheduler administrator reviewing a job definition."},
            {"role": "user", "content": (
                "A job waits until every job it depends on has finished on the same day. All field values below have "
                "already passed the format and reference checks.\n\nJob about to be deployed:\n  " + line(definition)
                + f"\n  command {definition['command']}, run as {definition['run_as']}\n\n"
                "Jobs it depends on:\n  " + ("\n  ".join(line(j) for j in near.values()) or "none")
                + "\n\nJobs that depend on it:\n  " + ("\n  ".join(line(j) for j in waiting.values()) or "none")
                + "\n\nIs there a concrete reason this job, or a job that depends on it, would not run as intended "
                "on some of its run dates? Only report a problem you can point to in the values above; a job that "
                "simply starts later than planned is not a problem.\n"
                'Reply with ONE JSON object: {"problem": "<one sentence, or none>", "field": "<gunler | saat | host | '
                'calistiran | bagimlilik | komut | tip | none>", "other_job": "<name of the other job involved, or empty>"}')}])
        if not isinstance(out, dict):
            return None
        problem, field = str(out.get("problem") or "").strip(), str(out.get("field") or "").strip().lower()
        other = str(out.get("other_job") or "").strip()
        if len(problem) < 12 or problem.lower().strip(". ") in ("none", "yok") or field not in REVIEW_FIELDS:
            return None
        if other and other not in near and other not in waiting:
            return None  # points at a job that is not a neighbour: not something it could have seen above
        return field, problem

    def _description_conflict(self, definition, env, jobs=None):
        """Does the free-text description say something different from the fields? Only a reader can
        tell, so the model judges. Code then holds it to its evidence: the words it quotes must really
        be in the description and must name a real field, otherwise the claim is dropped."""
        text = str(definition.get("description") or "")
        if self.model is None or "nodesc" in self.strategy or len(text) < 8:
            return None
        if "desc1" not in self.strategy:
            return self._conflict_by_reading(definition, env, jobs or {}, text)
        cal = definition["calendar"]
        fields = (f"- gunler (run days): {cal} = {env['calendars'].get(cal, '')}\n"
                  f"- saat (start time): {definition['time']}\n"
                  f"- host (server): {definition['host']}\n"
                  f"- bagimlilik (starts after these jobs end): {', '.join(definition['deps']) or 'none'}")
        out = self.model.ask_json([
            {"role": "system", "content": "You are a careful batch operations analyst."},
            {"role": "user", "content": (
                "A team filled in a job request form. The form fields are:\n" + fields + "\n\n"
                f"They also wrote this free-text description:\n\"{text}\"\n\n{GLOSSARY}\n\n"
                "Does the description state a run-day pattern, a start time, a server or a predecessor job that is "
                "DIFFERENT from the form field? A description that does not mention one of these, or that agrees with "
                "the field, is not a contradiction.\n"
                'Reply with JSON: {"contradiction": true or false, "field": "gunler" | "saat" | "host" | "bagimlilik" '
                '| "none", "quote": "<the exact words copied from the description that contradict the field, or empty>"}')}])
        if not isinstance(out, dict) or out.get("contradiction") is not True or out.get("field") not in CONFLICT_FIELDS:
            return None
        quote = str(out.get("quote") or "").strip().strip(".;, ")
        if len(quote) < 4 or gunler.fold(quote) not in gunler.fold(text):
            return None  # an unsupported claim: no such words in the description
        return out["field"], quote

    def _resolve_calendar(self, phrase, env):
        spec = STRATEGIES.get(self.strategy, self.strategy)
        note = {"field": "gunler", "given": phrase, "chosen": None, "strategy": self.strategy, "votes": {}}
        if spec.startswith("lex>"):
            # Code reads the phrase first. If it understands every word, that is the answer, with or
            # without a model; only what code cannot read is left for the model.
            spec = STRATEGIES.get(spec[4:], spec[4:])
            rule = gunler.parse(phrase)
            if rule is not None:
                note["votes"]["lex"] = note["chosen"] = self._calendar_for(rule, env, sorted(env["calendars"]))
                note["rule"] = rule
                return note["chosen"], note
        voters, _, quorum = spec.partition("/")
        voters = voters.split("+")
        confirm = "check" in voters
        voters = [v for v in voters if v != "check"]
        quorum = int(quorum) if quorum else len(voters)
        if self.model is None:
            return None, note
        names = sorted(env["calendars"])
        ctx = (f"A job request states the run days in the requester's own words: \"{phrase}\".\n"
               f"Today is {_pretty(env['today'])}. Site holidays: {', '.join(env['holidays']) or 'none'}.")
        tally = {}
        for i, voter in enumerate(voters):
            vote = getattr(self, "_vote_" + voter)(phrase, env, names, ctx)
            note["votes"][voter] = vote
            if vote:
                tally[vote] = tally.get(vote, 0) + 1
            best = max(tally.values(), default=0)
            if best >= quorum or best + (len(voters) - i - 1) < quorum:
                break  # decided, or no calendar can still reach the quorum
        winners = [n for n, c in tally.items() if c >= quorum]
        if len(winners) == 1:
            note["chosen"] = winners[0]
            if confirm:
                note["confirmed"] = self._confirm(phrase, env, winners[0], ctx)
                if not note["confirmed"]:
                    note["chosen"] = None
        return note["chosen"], note

    # ---- flow -----------------------------------------------------------------
    def handle(self, talep_no=None):
        ticket = self.a.call("get_request", talep_no=talep_no)
        report = {"talep_no": ticket and ticket["talep_no"], "outcome": "none", "reasons": [], "definition": None,
                  "before": None, "findings": [], "notes": [], "forecast": [], "agent": self.agent, "steps": self.steps}
        if ticket is None or ticket["status"] != "open":
            report["reasons"] = ["acik talep yok"]
            return report
        env = self.a.call("list_env")
        jobs = {j["name"]: j for j in self.a.call("list_defs")}

        values, errors = intake.parse(ticket["text"])
        if errors:
            return self._return(report, ticket, errors)
        if values["islem"] == "kaldir":
            return self._remove(report, ticket, values, jobs)
        asked = intake.to_definition(values)
        if "calendar" in asked and asked["calendar"] not in env["calendars"]:
            chosen, note = self._resolve_calendar(asked["calendar"], env)
            report["notes"].append(note)
            if chosen is None:
                why = (f"gunler alani okundu ({note['rule']}) ama ortamda bu gunlerde calisan bir takvim yok"
                       if note.get("rule") else f"gunler alani bir takvime cevrilemedi: '{asked['calendar']}'")
                return self._return(report, ticket, [
                    why + ". Takvim adini yazin ya da yeni takvim isteyin. Gecerli takvimler: "
                    + "; ".join(f"{n} ({d})" for n, d in env["calendars"].items())])
            asked["calendar"] = chosen

        is_new = values["islem"] == "yeni"
        before = jobs.get(asked.get("name"))
        if not is_new and before and asked.get("folder") != before["folder"]:
            return self._return(report, ticket, [f"{asked['name']} isi {asked.get('folder')} klasorunde degil, "
                                                 f"{before['folder']} klasorunde; talepteki klasor duzeltilmeli"])
        definition = normalise(asked if is_new else {**(before or {}), **asked})
        runs = None if "nocaldep" in self.strategy else {
            c: set(self.a.call("forecast", calendar=c, days=COVER_DAYS) or []) for c in env["calendars"]}
        findings = checks.check(env, jobs, definition, is_new, self.rules, runs)
        report.update(definition=definition, before=before, findings=findings)
        errors = [f["msg"] for f in findings if f["severity"] == "error"]
        if errors:
            return self._return(report, ticket, errors)

        conflict = self._description_conflict(definition, env, jobs) if is_new else None
        if conflict:
            report["notes"].append({"field": conflict[0], "quote": conflict[1], "by": "model"})
            return self._return(report, ticket, [
                f"aciklama ile {conflict[0]} alani celisiyor: aciklamada \"{conflict[1]}\" yaziyor, "
                f"{conflict[0]} alaninda {definition[CONFLICT_FIELDS[conflict[0]]]}. Hangisi dogru?"])

        if self.model is not None and "review" in self.strategy:
            doubt = self._second_look(definition, env, jobs)
            if doubt:
                report["notes"].append({"field": doubt[0], "review": doubt[1], "by": "model"})
                return self._return(report, ticket, [
                    f"tanim denetimlerden gecti, ama son bakista {doubt[0]} alaninda bir sorun goruldu: {doubt[1]} "
                    "Dogruysa duzeltin; degilse talebi bu notla yeniden gonderin."])

        step = self._act("deploy_job", {"definition": definition}, ticket, findings)
        if not step["executed"]:
            report.update(outcome="proposed", reasons=step["reasons"])
            return report
        if self.a.call("get_def", job=definition["name"]) != definition:  # read back; undo if it did not land as compiled
            if before:
                self._act("deploy_job", {"definition": before}, ticket)
            else:
                self._act("delete_job", {"job": definition["name"]}, ticket, definition=definition)
            return self._return(report, ticket, ["tanim yuklendi ama okunan deger derlenenle ayni degil; geri alindi"])

        report["forecast"] = (self.a.call("forecast", calendar=definition["calendar"], days=HORIZON) or [])[:5]
        record = {"talep_no": ticket["talep_no"], "kapatan": self.agent, "talep_eden": values["talep_eden"],
                  "islem": values["islem"], "istenen": ticket["text"], "uygulanan": definition, "onceki": before,
                  "uyarilar": [f["msg"] for f in findings if f["severity"] == "warning"],
                  "cozumlemeler": report["notes"], "sonraki_calismalar": report["forecast"],
                  "gecerlilik": "bir sonraki siparisten itibaren; plana alinmis calisma eski tanimla calisir"}
        closed = self._act("close_request", {"talep_no": ticket["talep_no"], "record": record}, ticket)
        report.update(outcome="closed" if closed["executed"] else "applied_not_closed", record=record)
        self._remember(values, definition, verified=closed["executed"])
        return report

    def _remove(self, report, ticket, values, jobs):
        name, before = values["is_adi"], jobs.get(values["is_adi"])
        if before and values["klasor"] != before["folder"]:
            return self._return(report, ticket, [f"{name} isi {values['klasor']} klasorunde degil, "
                                                 f"{before['folder']} klasorunde; talepteki klasor duzeltilmeli"])
        findings = checks.check_removal(jobs, name)
        report.update(before=before, findings=findings)
        errors = [f["msg"] for f in findings if f["severity"] == "error"]
        if errors:
            return self._return(report, ticket, errors)
        step = self._act("delete_job", {"job": name}, ticket, findings, definition=before)
        if not step["executed"]:
            report.update(outcome="proposed", reasons=step["reasons"])
            return report
        if self.a.call("get_def", job=name) is not None:
            return self._return(report, ticket, ["is kaldirilamadi; tanim yerinde duruyor"])
        record = {"talep_no": ticket["talep_no"], "kapatan": self.agent, "talep_eden": values["talep_eden"],
                  "islem": "kaldir", "istenen": ticket["text"], "uygulanan": None, "onceki": before,
                  "gecerlilik": "bir sonraki siparisten itibaren; plana alinmis calisma yine calisir"}
        closed = self._act("close_request", {"talep_no": ticket["talep_no"], "record": record}, ticket)
        report.update(outcome="closed" if closed["executed"] else "applied_not_closed", record=record)
        self._remember(values, before, verified=closed["executed"])
        return report

    def _return(self, report, ticket, reasons):
        step = self._act("return_request", {"talep_no": ticket["talep_no"], "reason": "; ".join(reasons)}, ticket)
        report.update(outcome="returned" if step["executed"] else "proposed", reasons=reasons)
        values, _ = intake.parse(ticket["text"])
        self._remember(values, report["definition"] or {}, verified=False, reasons=reasons)
        return report

    def _remember(self, values, definition, verified, reasons=()):
        self.ledger.append({"signature": f"talep:{values.get('klasor')}:{values.get('islem')}", "verified": verified,
                            "diagnosis": values.get("islem"), "job": definition.get("name"),
                            "talep_no": values.get("talep_no"), "agent": self.agent, "returned_for": list(reasons)})


def render(report):
    """Requester- and auditor-facing summary in Turkish."""
    out = [f"== Talep {report['talep_no']} ==", f"Sonuc: {report['outcome']}", f"Ajan: {report['agent']}"]
    for n in report["notes"]:
        if "votes" not in n:  # what the model read in the description, or its second look
            out.append(f"Model notu ({n.get('field')}): {n.get('quote') or n.get('review')}")
            continue
        votes = ", ".join(f"{k}: {v}" for k, v in n["votes"].items()) or "model bagli degil"
        out.append(f"Gunler ifadesi: '{n['given']}' -> oylar ({n['strategy']}): {votes}; kabul edilen: {n['chosen']}")
    if report["outcome"] in ("returned", "proposed", "none"):
        out += ["Gerekce:"] + [f"  - {r}" for r in report["reasons"]]
        return "\n".join(out)
    d, b = report["definition"], report["before"] or {}
    if d is None:
        out += [f"Kaldirilan is: {b.get('name')} ({b.get('folder')})",
                "Denetim kaydi: kapatan, talep numarasi, istenen ve kaldirilan tanim talebe yazildi."]
        return "\n".join(out)
    for k, v in d.items():
        if b and b.get(k) != v:
            out.append(f"  {k}: {b.get(k)} -> {v}")
        elif not b:
            out.append(f"  {k}: {v}")
    out += [f"Uyari: {f['msg']}" for f in report["findings"] if f["severity"] == "warning"]
    out.append("Sonraki calismalar: " + ", ".join(_pretty(x) for x in report["forecast"]))
    out.append("Denetim kaydi: kapatan, talep numarasi ve istenen tanim talebe yazildi.")
    return "\n".join(out)
