"""Local incident ledger: append-only, hash-chained, stays on site.

Only verified episodes count as precedent (an unverified memory poisons the next diagnosis).
"""
import hashlib
import json
import sqlite3


class Ledger:
    def __init__(self, path=":memory:"):
        # The web front end serves requests on several threads; it serialises every use behind one lock.
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS episodes (id INTEGER PRIMARY KEY, signature TEXT,"
                        " verified INTEGER, body TEXT, prev TEXT, hash TEXT)")

    def __del__(self):
        self.db.close()

    def _last(self):
        row = self.db.execute("SELECT hash FROM episodes ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else "genesis"

    def append(self, rec):
        body, prev = json.dumps(rec, sort_keys=True, ensure_ascii=False), self._last()
        h = hashlib.sha256((prev + body).encode()).hexdigest()
        self.db.execute("INSERT INTO episodes (signature, verified, body, prev, hash) VALUES (?,?,?,?,?)",
                        (rec.get("signature"), int(bool(rec.get("verified"))), body, prev, h))
        self.db.commit()
        return h

    def lookup(self, signature):
        rows = self.db.execute("SELECT verified, body FROM episodes WHERE signature=?", (signature,)).fetchall()
        out = {"seen": len(rows), "verified": 0, "diagnoses": {}, "last_actions": []}
        for verified, body in rows:
            if verified:
                rec = json.loads(body)
                out["verified"] += 1
                out["diagnoses"][rec["diagnosis"]] = out["diagnoses"].get(rec["diagnosis"], 0) + 1
                out["last_actions"] = rec.get("actions", [])
        return out

    def verify_chain(self):
        prev = "genesis"
        for body, p, h in self.db.execute("SELECT body, prev, hash FROM episodes ORDER BY id"):
            if p != prev or hashlib.sha256((prev + body).encode()).hexdigest() != h:
                return False
            prev = h
        return True
