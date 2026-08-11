import unittest

from kiva_compass import normalize_loans, score_loan, stars
from fetch_kiva import _normalize


class CompassTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "themes": [{"label": "Vatten", "icon": "💧", "points": 6, "keywords": ["water"]}],
            "attributes": [{"field": "woman_owned", "equals": True, "label": "Egenmakt", "icon": "♀", "points": 3}],
        }

    def test_scores_text_and_attribute(self):
        result = score_loan({"use": "Clean water pump", "attributes": {"woman_owned": True}}, self.config)
        self.assertEqual(result["score"], 9)
        self.assertEqual(len(result["matches"]), 2)

    def test_theme_only_scores_once(self):
        result = score_loan({"use": "Water tank and water pump"}, self.config)
        self.assertEqual(result["score"], 6)

    def test_normalizes_wrapped_list(self):
        self.assertEqual(normalize_loans({"loans": [{"id": 1}]}), [{"id": 1}])

    def test_stars(self):
        self.assertEqual(stars(5, 10), "★★☆☆☆")

    def test_normalizes_live_loan(self):
        loan = _normalize({
            "id": 42, "name": "Amina", "gender": "FEMALE", "tags": ["Refugees and IDPs"],
            "geocode": {"country": {"name": "Kenya"}}, "activity": {"name": "Bicycles"},
            "sector": {"name": "Services"}, "loanFundraisingInfo": {"fundedAmount": "25"},
        })
        self.assertEqual(loan["country"], "Kenya")
        self.assertTrue(loan["attributes"]["woman_owned"])
        self.assertTrue(loan["attributes"]["refugee"])
        self.assertEqual(loan["url"], "https://www.kiva.org/lend/42")


if __name__ == "__main__":
    unittest.main()
