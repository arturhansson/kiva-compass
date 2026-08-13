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

    def test_biography_does_not_create_theme_points(self):
        result = score_loan({"use": "to buy food", "description": "She completed her education."}, self.config)
        self.assertEqual(result["score"], 0)

    def test_keyword_does_not_match_word_fragment(self):
        config = {"themes": [{"label": "Brunn", "icon": "💧", "points": 3, "keywords": ["well"]}]}
        self.assertEqual(score_loan({"use": "to improve financial well-being"}, config)["score"], 0)
        self.assertEqual(score_loan({"use": "to dig a well"}, config)["score"], 3)

    def test_bicycle_rule_excludes_motorbikes(self):
        config = {"themes": [
            {"label": "Cykel", "icon": "🚲", "points": 18, "keywords": ["bicycle", "bicycles", "bike", "bikes"]},
        ]}
        self.assertEqual(score_loan({"use": "to repair bikes"}, config)["score"], 18)
        self.assertEqual(score_loan({"use": "to sell motorbike spare parts"}, config)["score"], 0)
        self.assertEqual(score_loan({"use": "to sell motor bike spare parts"}, config)["score"], 0)

    def test_normalizes_wrapped_list(self):
        self.assertEqual(normalize_loans({"loans": [{"id": 1}]}), [{"id": 1}])

    def test_stars(self):
        self.assertEqual(stars(5, 10), "★☆☆☆☆")
        self.assertEqual(stars(10, 99), "★★★☆☆")
        self.assertEqual(stars(20, 99), "★★★★★")
        self.assertEqual(stars(-50, 10), "☆☆☆☆☆")

    def test_negative_rule(self):
        config = {"themes": [
            {"label": "Undvik butik", "icon": "⛔", "points": -50, "keywords": ["retail"]},
            {"label": "Undvik kläder", "icon": "⛔", "points": -50, "keywords": ["clothing"]},
        ]}
        result = score_loan({"sector": "Retail clothing"}, config)
        self.assertEqual(result["score"], -50)

    def test_strongest_climate_penalty_applies_once(self):
        config = {"themes": [
            {"label": "Jordbruk", "icon": "🌱", "points": 2, "keywords": ["agriculture"]},
            {"label": "Mejeri", "icon": "🌡️", "points": -6, "keywords": ["dairy"]},
            {"label": "Kor", "icon": "🌡️", "points": -10, "keywords": ["dairy cows"]},
        ]}
        result = score_loan({"sector": "Agriculture", "use": "to purchase dairy cows"}, config)
        self.assertEqual(result["score"], -8)

    def test_human_bonus_cannot_hide_negative_climate_score(self):
        config = {
            "priorities": {"climate_first": True, "climate_labels": []},
            "themes": [
                {"label": "Klimatrisk: mejeri", "icon": "🌡️", "points": -6, "keywords": ["dairy"]},
            ],
            "attributes": [
                {"field": "woman_owned", "equals": True, "label": "Kvinnors egenmakt", "icon": "♀", "points": 6},
            ],
        }
        result = score_loan({"use": "dairy products", "attributes": {"woman_owned": True}}, config)
        self.assertEqual(result["climate_score"], -6)
        self.assertEqual(result["human_score"], 6)
        self.assertEqual(result["score"], -6)

    def test_us_penalty_keeps_positive_matches(self):
        config = {
            "themes": [{"label": "Cykel", "icon": "🚲", "points": 18, "keywords": ["bicycle"]}],
            "attributes": [{"field": "country", "equals": "United States", "label": "USA", "icon": "🇺🇸", "points": -3}],
        }
        result = score_loan({"country": "United States", "use": "bicycle repair"}, config)
        self.assertEqual(result["score"], 15)

    def test_new_country_bonus(self):
        config = {
            "themes": [],
            "new_country_bonus": {"label": "NYTT LAND", "icon": "🆕🌍", "points": 10, "countries": ["Nepal"]},
        }
        self.assertEqual(score_loan({"country": "Nepal"}, config)["score"], 10)
        self.assertEqual(score_loan({"country": "Kenya"}, config)["score"], 0)

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
