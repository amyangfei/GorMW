# coding: utf-8

import binascii
import unittest

from gor.base import Gor


class TestCommon(unittest.TestCase):

    def setUp(self):
        self.gor = Gor()

    def tearDown(self):
        pass

    def test_parse_message(self):
        payload = binascii.hexlify(b'1 2 3\nGET / HTTP/1.1\r\n\r\n')
        message = self.gor.parse_message(payload)
        expected = {
            "type": "1",
            "id": "2",
            "meta": ["1", "2", "3"],
            "http": "GET / HTTP/1.1\r\n\r\n",
        }
        for k, v in expected.items():
            self.assertEqual(getattr(message, k, None), v)

    def test_http_method(self):
        payload = 'GET /test HTTP/1.1\r\n\r\n'
        method = self.gor.http_method(payload)
        self.assertEqual(method, 'GET')

    def test_http_path(self):
        payload = "GET /test HTTP/1.1\r\n\r\n"
        path = self.gor.http_path(payload)
        self.assertEqual(path, "/test")

        new_payload = self.gor.set_http_path(payload, "/")
        self.assertEqual(new_payload, "GET / HTTP/1.1\r\n\r\n")

        new_payload = self.gor.set_http_path(payload, "/new/test")
        self.assertEqual(new_payload, "GET /new/test HTTP/1.1\r\n\r\n")

    def test_http_path_param(self):
        payload = 'GET / HTTP/1.1\r\n\r\n'
        self.assertIsNone(self.gor.http_path_param(payload, 'test'))

        payload = self.gor.set_http_path_param(payload, 'test', '123')
        self.assertEqual(self.gor.http_path(payload), '/?test=123')
        self.assertIn('123', self.gor.http_path_param(payload, 'test'))

        payload = self.gor.set_http_path_param(payload, 'qwer', 'ty')
        self.assertEqual(self.gor.http_path(payload), '/?test=123&qwer=ty')
        self.assertIn('ty', self.gor.http_path_param(payload, 'qwer'))

    def test_http_headers(self):
        payload = b'GET / HTTP/1.1\r\nHost: localhost:3000\r\nUser-Agent: Python\r\nContent-Length:5\r\n\r\nhello'
        expected = {
            'Host': 'localhost:3000',
            'User-Agent': 'Python',
            'Content-Length': '5',
        }
        headers = self.gor.http_headers(payload)
        for k, v in expected.items():
            self.assertEqual(headers.get(k), v)

    def test_http_header(self):
        payload = b'GET / HTTP/1.1\r\nHost: localhost:3000\r\nUser-Agent: Python\r\nContent-Length:5\r\n\r\nhello'
        expected = {
            'Host': 'localhost:3000',
            'User-Agent': 'Python',
            'Content-Length': '5',
        }
        for name, value in expected.items():
            header = self.gor.http_header(payload, name)
            self.assertIsNotNone(header)
            self.assertEqual(header['value'], value)

    def test_set_http_header(self):
        payload = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        uas = ['', '1', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_0)']
        expected = 'GET / HTTP/1.1\r\nUser-Agent: %s\r\nContent-Length: 5\r\n\r\nhello'
        for ua in uas:
            new_payload = self.gor.set_http_header(payload, 'User-Agent', ua)
            self.assertEqual(new_payload, expected % ua)

        expected = 'GET / HTTP/1.1\r\nX-Test: test\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.set_http_header(payload, 'X-Test', 'test')
        self.assertEqual(new_payload, expected)

        expected = 'GET / HTTP/1.1\r\nX-Test2: test2\r\nX-Test: test\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.set_http_header(new_payload, 'X-Test2', 'test2')
        self.assertEqual(new_payload, expected)

    def test_delete_http_header(self):
        payload = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.delete_http_header(payload, 'User-Agent')
        self.assertEqual(new_payload, 'GET / HTTP/1.1\r\nContent-Length: 5\r\n\r\nhello')
        new_payload = self.gor.delete_http_header(new_payload, 'not-exists-header')
        self.assertEqual(new_payload, 'GET / HTTP/1.1\r\nContent-Length: 5\r\n\r\nhello')

    def test_http_body(self):
        payload = 'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        body = self.gor.http_body(payload)
        self.assertEqual(body, 'hello')

        invalid_payload = 'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\nhello'
        body = self.gor.http_body(invalid_payload)
        self.assertEqual(body, '')

    def test_set_http_body(self):
        payload = 'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.set_http_body(payload, 'hello, world!')
        expected = 'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 13\r\n\r\nhello, world!'
        self.assertEqual(new_payload, expected)

    def test_http_cookie(self):
        payload = 'GET / HTTP/1.1\r\nCookie: a=b; test=zxc; test2=a=b\r\n\r\n'
        cookie = self.gor.http_cookie(payload, 'test')
        self.assertEqual(cookie, 'zxc')
        cookie = self.gor.http_cookie(payload, 'test2')
        self.assertEqual(cookie, 'a=b')
        cookie = self.gor.http_cookie(payload, 'nope')
        self.assertIsNone(cookie)

    def test_set_http_cookie(self):
        payload = b'GET / HTTP/1.1\r\nCookie: a=b; test=zxc\r\n\r\n'
        new_payload = self.gor.set_http_cookie(payload, 'test', '111')
        self.assertEqual(new_payload, 'GET / HTTP/1.1\r\nCookie: a=b; test=111\r\n\r\n')
        new_payload = self.gor.set_http_cookie(payload, 'new', 'one%3d%3d--test')
        self.assertEqual(new_payload, 'GET / HTTP/1.1\r\nCookie: a=b; test=zxc; new=one%3d%3d--test\r\n\r\n')

    def test_delete_http_cookie(self):
        payload = b'GET / HTTP/1.1\r\nCookie: a=b; test=zxc\r\n\r\n'
        new_payload = self.gor.delete_http_cookie(payload, 'test')
        self.assertEqual(new_payload, 'GET / HTTP/1.1\r\nCookie: a=b\r\n\r\n')
