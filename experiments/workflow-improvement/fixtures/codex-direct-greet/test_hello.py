import unittest

from hello import greet


class GreetTest(unittest.TestCase):
    def test_greet_returns_expected_message(self):
        self.assertEqual(greet("Codex"), "Hello, Codex!")


if __name__ == "__main__":
    unittest.main()
