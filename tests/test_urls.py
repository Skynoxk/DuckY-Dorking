import unittest
from urllib.parse import urlencode

from skyScrape import decode_duckduckgo_href


class DuckDuckGoDecodeTests(unittest.TestCase):
    def test_redirect_preserves_target_percent_encoding(self):
        target = 'https://example.com/a%2Fb?q=one%26two&literal=%252F'
        for prefix in ('/l/?', '//duckduckgo.com/l/?',
                       'https://duckduckgo.com/l/?'):
            with self.subTest(prefix=prefix):
                href = prefix + urlencode({'uddg': target})
                self.assertEqual(decode_duckduckgo_href(href), target)

    def test_direct_url_is_unchanged(self):
        target = 'https://example.com/a%2Fb?q=one%26two'
        self.assertEqual(decode_duckduckgo_href(target), target)

    def test_empty_href_is_ignored(self):
        self.assertIsNone(decode_duckduckgo_href(''))


if __name__ == '__main__':
    unittest.main()
