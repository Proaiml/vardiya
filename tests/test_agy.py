"""The Antigravity CLI gateway without the CLI: long prompts go in parts, a failed turn is retried, and a stuck
conversation is replaced by a fresh one that carries the transcript."""
import json
import types
import unittest
import urllib.error
from unittest import mock

from vardiya import gateway


class Cli:
    """Stands in for `agy`: records each call and answers from a script of statuses."""
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def __call__(self, cmd, **kw):
        prompt = next(a for a in cmd if a.startswith("-p="))[3:]
        conv = cmd[cmd.index("--conversation") + 1] if "--conversation" in cmd else None
        self.calls.append({"prompt": prompt, "conversation": conv})
        status, error = self.script.pop(0) if self.script else ("SUCCESS", None)
        out = {"status": status, "conversation_id": conv or f"c{len(self.calls)}", "response": '{"ok": true}', "error": error,
               "usage": {"total_tokens": 10}}
        return types.SimpleNamespace(stdout=json.dumps(out), returncode=0)


def model():
    m = gateway.AgyModel("agy:test")
    return m


class Agy(unittest.TestCase):
    def run_with(self, script, fn):
        cli = Cli(script)
        with mock.patch.object(gateway.subprocess, "run", cli), mock.patch.object(gateway.time, "sleep", lambda s: None):
            return cli, fn()

    def test_long_prompt_goes_in_parts_within_one_conversation(self):
        m = model()
        long = "x" * (m.CHUNK * 2 + 50)
        cli, out = self.run_with([], lambda: m.chat([{"role": "user", "content": long}]))
        self.assertEqual(out, '{"ok": true}')
        self.assertEqual(len(cli.calls), 3)
        self.assertIn("PART 1 of 3", cli.calls[0]["prompt"])
        self.assertIn("the last one", cli.calls[2]["prompt"])
        self.assertIsNone(cli.calls[0]["conversation"])
        self.assertEqual(cli.calls[1]["conversation"], "c1")
        self.assertEqual(cli.calls[2]["conversation"], "c1")

    def test_next_turn_sends_only_the_new_message(self):
        m = model()
        msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "U1"}]
        cli, _ = self.run_with([], lambda: (m.chat(msgs), m.chat(msgs + [{"role": "assistant", "content": "A1"}, {"role": "user", "content": "U2"}])))
        self.assertEqual(len(cli.calls), 2)
        self.assertEqual(cli.calls[1]["conversation"], "c1")
        self.assertTrue(cli.calls[1]["prompt"].startswith("U2"))
        self.assertNotIn("U1", cli.calls[1]["prompt"])

    def test_a_failed_turn_is_retried(self):
        m = model()
        cli, out = self.run_with([("ERROR", "overloaded")], lambda: m.chat([{"role": "user", "content": "U"}]))
        self.assertEqual(out, '{"ok": true}')
        self.assertEqual((len(cli.calls), m.retries), (2, 1))

    def test_a_stuck_conversation_restarts_with_the_transcript(self):
        m = model()
        msgs = [{"role": "user", "content": "U1"}]
        more = msgs + [{"role": "assistant", "content": "A1"}, {"role": "user", "content": "U2"}]
        cli, out = self.run_with([("SUCCESS", None), ("ERROR", "improperly formatted function call")],
                                 lambda: (m.chat(msgs), m.chat(more))[1])
        self.assertEqual(out, '{"ok": true}')
        self.assertEqual(m.restarts, 1)
        self.assertIsNone(cli.calls[-1]["conversation"])
        self.assertIn("U1", cli.calls[-1]["prompt"])
        self.assertIn("U2", cli.calls[-1]["prompt"])

    def test_gives_up_after_the_retries(self):
        m = model()
        with self.assertRaises(urllib.error.URLError):
            self.run_with([("ERROR", "down")] * 6, lambda: m.chat([{"role": "user", "content": "U"}]))

    def test_every_prompt_forbids_native_tool_calls(self):
        m = model()
        cli, _ = self.run_with([], lambda: m.chat([{"role": "user", "content": "U"}]))
        self.assertIn("never emit a function call", cli.calls[0]["prompt"])


if __name__ == "__main__":
    unittest.main()
