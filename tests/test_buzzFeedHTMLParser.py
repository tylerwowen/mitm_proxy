import re
from unittest import TestCase

from modifier import BuzzFeedHTMLParser


class TestBuzzFeedHTMLParser(TestCase):

    def test_title_exists_found_true(self):
        parser = BuzzFeedHTMLParser()
        parser.feed('<h1 class="title">some title</h1>')
        self.assertEqual(parser.title, 'some title')

    def test_title_not_exists_found_false(self):
        parser = BuzzFeedHTMLParser()
        parser.feed('<h2 class="title">some title</h2>')
        self.assertFalse(parser.title_found)

    def test_regex(self):
        html = '<h1 class="title" >some title</h1>'
        html_md = re.sub(r'<h1 class="title" >.*</h1>', '<h1 class="title" >CS176B is Great!</h1>', html)
        self.assertEqual('<h1 class="title" >CS176B is Great!</h1>', html_md)
