import tempfile
import pathlib
import unittest

from vardiya.erisim import Access, Refused

INV = {"app01": {"os": "unix", "address": "app01.ornek.local", "user": "ctmops"},
       "win01": {"os": "windows", "address": "win01.ornek.local"}, "_server": {"address": "ctm-sunucu.ornek.local"}}


class AccessLayer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.audit = pathlib.Path(self.tmp.name) / "denetim.jsonl"
        self.a = Access(INV, audit=self.audit)

    def tearDown(self):
        self.tmp.cleanup()

    def test_unix_goes_over_ssh_windows_over_powershell_remoting(self):
        self.assertEqual(self.a.command("agent_restart", "app01")[:2], ["ssh", "ctmops@app01.ornek.local"])
        win = self.a.command("agent_restart", "win01")
        self.assertEqual(win[0], "pwsh")
        self.assertIn("Invoke-Command -ComputerName win01.ornek.local", win[-1])
        self.assertIn("ctm run job::rerun", " ".join(self.a.command("job_rerun", job_id="ctm:0004x")))

    def test_refusals_are_logged(self):
        with self.assertRaises(Refused):
            self.a.run("job_set_ok", "app01")
        with self.assertRaises(Refused):
            self.a.run("rdp_login", "win01")
        with self.assertRaises(Refused):
            self.a.run("file_delete", "app01", path="/data/x; rm -rf /")
        with self.assertRaises(Refused):  # level 4 without a person's approval
            self.a.run("password_update", "app01", user="batchusr")
        self.assertEqual(len(self.audit.read_text(encoding="utf-8").splitlines()), 4)

    def test_secrets_never_travel_on_the_command_line(self):
        a = Access(INV, audit=self.audit, approvals={"password_update:app01"})
        cmd = " ".join(a.command("password_update", "app01", user="batchusr"))
        self.assertIn("vault-get run_as", cmd)
        self.assertNotRegex(cmd, r"-password [A-Za-z0-9]{6,}")

    def test_dry_run_runs_nothing(self):
        out = self.a.run("host_df", "app01", path="/data")
        self.assertTrue(out["dry_run"])
        self.assertIn("df -h /data", out["command"][-1])


if __name__ == "__main__":
    unittest.main()
