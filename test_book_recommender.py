"""Tests for the local book recommendation catalog."""

import unittest

from book_recommender import ground_recommendations, load_books, recommend_candidates


class BookRecommenderTest(unittest.TestCase):
    def test_loads_all_detail_catalog_entries_once(self) -> None:
        books = load_books()

        self.assertEqual(340, len(books))
        self.assertEqual(340, len({book.id for book in books}))
        self.assertEqual("影响力", next(book.title for book in books if book.id == "071"))

    def test_conflict_query_prioritizes_relevant_books(self) -> None:
        candidates = recommend_candidates(
            {
                "purpose": "解决冲突",
                "concerns": "对方比较强硬，希望先降低情绪再进行谈判",
            },
            limit=12,
        )

        titles = {book["title"] for book in candidates}
        self.assertIn("困难对话", titles)
        self.assertTrue(titles & {"关键对话", "谈判力", "原则谈判"})

    def test_grounds_model_recommendations_and_adds_fallback(self) -> None:
        candidates = recommend_candidates({"purpose": "绩效反馈"}, limit=4)
        strategy = {
            "recommended_books": [
                {"id": candidates[0]["id"], "title": "模型改写的书名", "author": "错误作者"},
                {"id": "999", "title": "不存在的书"},
            ]
        }

        grounded = ground_recommendations(strategy, candidates)["recommended_books"]

        self.assertEqual(2, len(grounded))
        self.assertEqual(candidates[0]["title"], grounded[0]["title"])
        self.assertEqual(candidates[0]["author"], grounded[0]["author"])
        self.assertNotEqual("999", grounded[1]["id"])


if __name__ == "__main__":
    unittest.main()
