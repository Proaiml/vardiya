import contextlib
import io
import unittest

from vardiya.__main__ import main


class Cli(unittest.TestCase):
    def test_every_entry_point_parses(self):
        # a local import inside main() once shadowed a module-level name and broke every command but `ops`
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["talep", "t-yeni-001"]), 0)
        self.assertTrue(out.getvalue().strip())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stop:
                main(["web", "--help"])
        self.assertEqual(stop.exception.code, 0)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["ops", "eylem", "--split", "dev", "--arms", "kod", "--seeds", "2"]), 0)


if __name__ == "__main__":
    unittest.main()
