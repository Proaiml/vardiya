"""First-time setup of the JS7 lab: register the Controller and the Agent with JOC Cockpit.

    python lab/js7/setup.py

Safe to run again: steps that are already done are reported and skipped.
"""
import pathlib
import sys
import time
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from vardiya.js7 import JS7, JS7Error, lab_config  # noqa: E402


def wait_for_login(js, seconds=240):
    last = None
    for _ in range(seconds // 3):
        try:
            return js.login()
        except (JS7Error, urllib.error.URLError, ConnectionError, OSError) as e:
            last = e
            time.sleep(3)
    raise SystemExit(f"JOC Cockpit {seconds} saniyede hazir olmadi: {last}")


def step(title, fn):
    try:
        out = fn()
        print(f"[tamam] {title}")
        return out
    except JS7Error as e:
        print(f"[atlandi] {title}: {e}")
        return None


def main():
    cfg = lab_config()
    js = JS7(cfg["url"], cfg["account"], cfg["password"])
    who = wait_for_login(js)
    print(f"[tamam] JOC Cockpit'e giris: hesap={who.get('account')}")
    cid = cfg["controller_id"]
    # Yeni kayitta controllerId gonderilmez; kimlik Controller'in kendisinden (RUN_JS_ID) okunur.
    step("Controller kaydi", lambda: js.post("/controller/register", {
        "controllers": [{"url": cfg["controller_url"], "role": "STANDALONE", "title": "Vardiya lab"}],
        "auditLog": {"comment": "vardiya lab kurulumu"}}))
    step("Agent kaydi", lambda: js.post("/agents/inventory/store", {
        "controllerId": cid,
        "agents": [{"agentId": cfg["agent_id"], "agentName": cfg["agent_name"], "url": cfg["agent_url"],
                    "title": "Vardiya lab agent"}],
        "auditLog": {"comment": "vardiya lab kurulumu"}}))
    time.sleep(3)
    step("Agent dagitimi", lambda: js.post("/agents/inventory/deploy", {
        "controllerId": cid, "agentIds": [cfg["agent_id"]], "auditLog": {"comment": "vardiya lab kurulumu"}}))
    js.logout()


if __name__ == "__main__":
    main()
