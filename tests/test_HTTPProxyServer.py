import unittest
import HTTPProxyServer as sut


class UtilTests(unittest.TestCase):

    def test_readline(self):
        text = 'GET test.com HTTP/1.1\r\nsome headers\r\n'
        expected = 'GET test.com HTTP/1.1\r\n'
        # result = sut.readline()

    def test_parse_request_line_good(self):
        requestline = b'GET test.com HTTP/1.1\r\n'
        method, path = sut.parse_request_line(requestline)
        self.assertEqual(method, 'GET')
        self.assertEqual(path, 'test.com')

    def test_parse_request_line_bad(self):
        requestline = b'GET test.co m HTTP/1.1\r\n'
        try:
            sut.parse_request_line(requestline)
        except sut.InvalidRequest:
            self.assertTrue(True)


class ErrorTests(unittest.TestCase):

    def test_InvalidRequest(self):
        try:
            raise sut.InvalidRequest('Cannot parse request line')
        except sut.InvalidRequest:
            self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
