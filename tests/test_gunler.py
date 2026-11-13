import datetime
import unittest

from vardiya import gunler, sabgen
from vardiya.repo import run_dates

TODAY = datetime.date(2026, 11, 13)


def calendar_of(phrase):
    """(understood, calendar): the calendar whose dates equal the parsed rule's, if any."""
    rule = gunler.parse(phrase)
    if rule is None:
        return False, None
    dates = lambda r: run_dates(r, sabgen.HOLIDAYS, TODAY, 400)
    same = [n for n, (r, _) in sabgen.CALENDARS.items() if dates(r) == dates(rule)]
    return True, same[0] if len(same) == 1 else None


class Lexicon(unittest.TestCase):
    def test_tuning_phrases_are_all_read_correctly(self):
        for cal, phrases in sabgen.PHRASES.items():
            for p in phrases:
                self.assertEqual(calendar_of(p), (True, cal), p)

    def test_it_never_picks_a_wrong_calendar_on_either_phrase_set(self):
        # Precision is the contract; recall may be lower on phrases it was not written against.
        for bank, traps in ((sabgen.PHRASES, sabgen.NO_CALENDAR), (sabgen.PHRASES_TEST, sabgen.NO_CALENDAR_TEST)):
            for cal, phrases in bank.items():
                for p in phrases:
                    understood, got = calendar_of(p)
                    if understood:
                        self.assertEqual(got, cal, p)
            for p in traps:
                self.assertIsNone(calendar_of(p)[1], p)

    def test_one_unknown_word_means_no_answer(self):
        for p in ("her gün ama yağmurlu günlerde değil", "hafta içi her gün, çarşamba hariç", "cuma hariç her gün",
                  "iki haftada bir cuma", "her ayın ilk pazartesi günü", "her ayın son cuma günü", "arada bir",
                  "salıdan", "", "pazartesi 09:00"):
            self.assertIsNone(gunler.parse(p), p)

    def test_rules(self):
        self.assertEqual(gunler.parse("Salı ve Perşembe"), {"type": "weekly", "days": [1, 3]})
        self.assertEqual(gunler.parse("salıdan perşembeye"), {"type": "weekly", "days": [1, 2, 3]})
        self.assertEqual(gunler.parse("pazartesiden cumaya"), {"type": "weekly", "days": [0, 1, 2, 3, 4]})
        self.assertEqual(gunler.parse("pazartesiden cumaya, tatiller hariç"), {"type": "workdays"})
        self.assertEqual(gunler.parse("her ayın 10'unda"), {"type": "month_day", "day": 10, "shift": "none"})
        self.assertEqual(gunler.parse("ayın yirmi beşi"), {"type": "month_day", "day": 25, "shift": "none"})
        self.assertEqual(gunler.parse("HER GÜN"), {"type": "daily"})
        self.assertIsNone(gunler.parse("her ayın 32'sinde"))


class ConsistencyGate(unittest.TestCase):
    """contradicts() never reads a phrase; it only vetoes a reading that plain signs in the phrase rule out."""
    RULES = {n: r for n, (r, _) in sabgen.CALENDARS.items()}

    @staticmethod
    def gate(phrase, rule):
        return gunler.contradicts(phrase, rule) or gunler.unsupported(phrase, rule)

    def test_a_correct_reading_is_left_alone(self):
        for split in ("dev", "test", "ext"):
            phrases, _ = sabgen.phrase_sets(split)
            for cal, items in phrases.items():
                for p in items:
                    self.assertIsNone(gunler.contradicts(p, self.RULES[cal]), (split, p))
        for split in ("dev", "test"):  # the support check costs nothing on the author's own phrases
            phrases, _ = sabgen.phrase_sets(split)
            for cal, items in phrases.items():
                for p in items:
                    self.assertIsNone(gunler.unsupported(p, self.RULES[cal]), (split, p))

    def test_no_site_calendar_fits_a_phrase_that_has_none(self):
        for split in ("dev", "test", "ext", "ext2"):
            _, traps = sabgen.phrase_sets(split)
            for p in traps:
                for cal, rule in self.RULES.items():
                    self.assertIsNotNone(self.gate(p, rule), (split, p, cal))

    def test_other_authors_phrases_cost_a_few_correct_readings(self):
        # the price of both checks on wording by other authors: a handful of safe returns
        for split, most in (("ext", 3), ("ext2", 2)):
            phrases, _ = sabgen.phrase_sets(split)
            lost = [p for cal, items in phrases.items() for p in items if self.gate(p, self.RULES[cal])]
            self.assertLessEqual(len(lost), most, lost)

    def test_a_reading_needs_a_sign_of_its_own_in_the_phrase(self):
        u = gunler.unsupported
        last, first = {"type": "month_end_workday"}, {"type": "month_day", "day": 1, "shift": "next"}
        self.assertIsNotNone(u("ay sonunda", last))                 # last calendar day or last working day?
        self.assertIsNone(u("ayın son iş günü", last))
        self.assertIsNotNone(u("ay başında", first))
        self.assertIsNone(u("her ayın 1. iş günü", first))
        self.assertIsNotNone(u("ayın ortasında", {"type": "month_day", "day": 15, "shift": "next"}))
        self.assertIsNotNone(u("ayın 15'inde", {"type": "month_day", "day": 15, "shift": "next"}))  # nobody said "shift"
        self.assertIsNone(u("ayın 15'inde", {"type": "month_day", "day": 15, "shift": "none"}))
        self.assertIsNotNone(u("yoğun olmayan günlerde", {"type": "workdays"}))
        self.assertIsNotNone(u("uygun bir günde", {"type": "workdays"}))
        self.assertIsNotNone(u("hafta sonu bir gün", {"type": "weekly", "days": [5, 6]}))
        self.assertIsNone(u("hafta sonu iki gün de", {"type": "weekly", "days": [5, 6]}))
        self.assertIsNone(u("haftanın son iki günü", {"type": "weekly", "days": [5, 6]}))
        self.assertIsNotNone(u("gerektiğinde", {"type": "daily"}))
        self.assertIsNone(u("yılın her günü için uygun", {"type": "daily"}))

    def test_signs(self):
        c = gunler.contradicts
        self.assertIn("aralikli", c("iki haftada bir cuma", {"type": "weekly", "days": [4]}))
        self.assertIn("istisna", c("çarşamba hariç hafta içi", {"type": "workdays"}))
        self.assertIn("haftasindaki", c("her ayın ilk pazartesi günü", {"type": "weekly", "days": [0]}))
        self.assertIn("is gunleri", c("salı ve perşembe", {"type": "workdays"}))
        self.assertIn("aylik degil", c("her ayın son iş günü", {"type": "daily"}))
        self.assertIn("ayni degil", c("her ayın 10'unda", {"type": "month_day", "day": 15, "shift": "next"}))
        self.assertIn("kullanmiyor", c("ayın onuncu günü", {"type": "month_end_workday"}))
        self.assertIsNone(c("pazartesiden cumaya, resmi tatiller hariç", {"type": "workdays"}))
        self.assertIsNone(c("Pzt-Cum, tatiller hariç", {"type": "workdays"}))
        self.assertIsNone(c("yılın her günü", {"type": "daily"}))
        self.assertIsNone(c("bambaşka bir cümle", {"type": "daily"}))  # silence is not approval, only no veto


if __name__ == "__main__":
    unittest.main()
