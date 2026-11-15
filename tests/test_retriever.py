import unittest

from src.retriever import retrieve_relevant_material


class TestCurriculumRetrieval(unittest.TestCase):

    def test_router_question(self):
        results = retrieve_relevant_material(
            "What is a router?",
            "Computer Networks"
        )

        self.assertTrue(
            any(
                "router" in result["content"].lower()
                for result in results
            )
        )

    def test_primary_key_question(self):
        results = retrieve_relevant_material(
            "What is a primary key?",
            "DBMS"
        )

        self.assertTrue(
            any(
                "primary key" in result["content"].lower()
                for result in results
            )
        )

    def test_empty_question(self):
        results = retrieve_relevant_material(
            "",
            "Computer Networks"
        )

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()