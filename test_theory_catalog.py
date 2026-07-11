"""Tests for structured theory retrieval and grounding."""

import unittest

from theory_catalog import ground_theory_applications, recommend_theories


class TheoryCatalogTest(unittest.TestCase):
    def test_includes_core_and_contextual_theories(self) -> None:
        cards = recommend_theories(
            {
                "target": "直属领导",
                "purpose": "争取资源",
                "concerns": "需要审批，对方担心项目风险",
            }
        )
        ids = {card["id"] for card in cards}

        self.assertTrue(
            {
                "equity_theory",
                "interest_based_negotiation",
                "big_five",
                "abc_model",
                "metacognition",
                "cialdini",
            }.issubset(ids)
        )
        self.assertIn("power_dependence", ids)
        self.assertIn("framing_effect", ids)

    def test_grounds_theory_metadata_and_rejects_unknown_ids(self) -> None:
        cards = recommend_theories({"purpose": "绩效反馈"})
        strategy = {
            "theory_applications": [
                {
                    "theory_id": "equity_theory",
                    "theory_name": "模型改写的名称",
                    "evidence": "工作量分配",
                    "inference": "可能存在公平顾虑",
                    "action": "询问对方对分配依据的看法",
                    "script_link": "用于开场话术",
                    "boundary": "模型改写的边界",
                },
                {"theory_id": "invented_theory", "theory_name": "不存在的理论"},
            ]
        }

        grounded = ground_theory_applications(strategy, cards)["theory_applications"]

        self.assertEqual(1, len(grounded))
        self.assertEqual("公平理论", grounded[0]["theory_name"])
        self.assertEqual(["工作量分配"], grounded[0]["evidence"])
        self.assertIn("不能在缺少事实时断言", grounded[0]["boundary"])


if __name__ == "__main__":
    unittest.main()
