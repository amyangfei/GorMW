# coding: utf-8

import binascii
import unittest

from gor.base import Gor, decode_chunked
from gor.callback import SimpleCallbackContainer


class TestCommon(unittest.TestCase):

    def setUp(self):
        self.gor = Gor(SimpleCallbackContainer())

    def tearDown(self):
        pass

    def test_parse_message(self):
        payload = binascii.hexlify(b'1 2 3\nGET / HTTP/1.1\r\n\r\n')
        message = self.gor.parse_message(payload)
        expected = {
            "type": "1",
            "id": "2",
            "meta": ["1", "2", "3"],
            "http": b"GET / HTTP/1.1\r\n\r\n",
        }
        for k, v in expected.items():
            self.assertEqual(getattr(message, k, None), v)

    def test_http_method(self):
        payload = b'GET /test HTTP/1.1\r\n\r\n'
        method = self.gor.http_method(payload)
        self.assertEqual(method, 'GET')

    def test_http_path(self):
        payload = b"GET /test HTTP/1.1\r\n\r\n"
        path = self.gor.http_path(payload)
        self.assertEqual(path, "/test")

        unicode_path = "/emoji/😊".encode('utf-8')
        new_payload = self.gor.set_http_path(payload, unicode_path)
        self.assertEqual(new_payload, b"GET /emoji/\xf0\x9f\x98\x8a HTTP/1.1\r\n\r\n")

        new_payload = self.gor.set_http_path(payload, b"/new/test")
        self.assertEqual(new_payload, b"GET /new/test HTTP/1.1\r\n\r\n")

    def test_http_path_param(self):
        payload = b'GET / HTTP/1.1\r\n\r\n'
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
            self.assertEqual(new_payload, (expected % ua).encode())

        expected = b'GET / HTTP/1.1\r\nX-Test: test\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.set_http_header(payload, 'X-Test', 'test')
        self.assertEqual(new_payload, expected)

        expected = b'GET / HTTP/1.1\r\nX-Test2: test2\r\nX-Test: test\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.set_http_header(new_payload, 'X-Test2', 'test2')
        self.assertEqual(new_payload, expected)

    def test_delete_http_header(self):
        payload = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.delete_http_header(payload, 'User-Agent')
        self.assertEqual(new_payload, b'GET / HTTP/1.1\r\nContent-Length: 5\r\n\r\nhello')
        new_payload = self.gor.delete_http_header(new_payload, 'not-exists-header')
        self.assertEqual(new_payload, b'GET / HTTP/1.1\r\nContent-Length: 5\r\n\r\nhello')

    def test_http_body(self):
        payload = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        body = self.gor.http_body(payload)
        self.assertEqual(body, b'hello')

        gzip_payload = b'HTTP/1.1 200 OK\r\nServer: nginx/1.23.1\r\nDate: Sun, 11 Sep 2022 15:28:34 GMT\r\nContent-Type: application/json\r\nTransfer-Encoding: chunked\r\nConnection: keep-alive\r\nVary: Accept-Encoding\r\nContent-Encoding: gzip\r\n\r\n5d\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x04\x03\xabVJ\xceOIU\xb2R2T\xd2QP\xcaM-.NL\x07r\x15\x942Rsr\xf2Ab)\xa9%\x89\x999 \xa1\x97\xbb[\x9em\xda\xfc\xb8\xa1\xf1\xe5\xd4\xfd\xcf6\xce\x7f\xdc\xd0\x94\x9a\x9b\x9f\x95i\xa5\xf0a\xfe\x8c. O\xa9\x16\x00Z)\xad4N\x00\x00\x00\r\n0'
        body = self.gor.http_body(gzip_payload)
        self.assertEqual(body, b'5d\r\n\x1f\x8b\x08\x00\x00\x00\x00\x00\x04\x03\xabVJ\xceOIU\xb2R2T\xd2QP\xcaM-.NL\x07r\x15\x942Rsr\xf2Ab)\xa9%\x89\x999 \xa1\x97\xbb[\x9em\xda\xfc\xb8\xa1\xf1\xe5\xd4\xfd\xcf6\xce\x7f\xdc\xd0\x94\x9a\x9b\x9f\x95i\xa5\xf0a\xfe\x8c. O\xa9\x16\x00Z)\xad4N\x00\x00\x00\r\n0')

        invalid_payload = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\nhello'
        body = self.gor.http_body(invalid_payload)
        self.assertEqual(body, b'')

    def test_set_http_body(self):
        payload = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 5\r\n\r\nhello'
        new_payload = self.gor.set_http_body(payload, b'hello, world!')
        expected = b'GET / HTTP/1.1\r\nUser-Agent: Python\r\nContent-Length: 13\r\n\r\nhello, world!'
        self.assertEqual(new_payload, expected)

    def test_http_cookie(self):
        payload = b'GET / HTTP/1.1\r\nCookie: a=b; test=zxc; test2=a=b\r\n\r\n'
        cookie = self.gor.http_cookie(payload, 'test')
        self.assertEqual(cookie, 'zxc')
        cookie = self.gor.http_cookie(payload, 'test2')
        self.assertEqual(cookie, 'a=b')
        cookie = self.gor.http_cookie(payload, 'nope')
        self.assertIsNone(cookie)

    def test_set_http_cookie(self):
        payload = b'GET / HTTP/1.1\r\nCookie: a=b; test=zxc\r\n\r\n'
        new_payload = self.gor.set_http_cookie(payload, 'test', '111')
        self.assertEqual(new_payload, b'GET / HTTP/1.1\r\nCookie: a=b; test=111\r\n\r\n')
        new_payload = self.gor.set_http_cookie(payload, 'new', 'one%3d%3d--test')
        self.assertEqual(new_payload, b'GET / HTTP/1.1\r\nCookie: a=b; test=zxc; new=one%3d%3d--test\r\n\r\n')

    def test_delete_http_cookie(self):
        payload = b'GET / HTTP/1.1\r\nCookie: a=b; test=zxc\r\n\r\n'
        new_payload = self.gor.delete_http_cookie(payload, 'test')
        self.assertEqual(new_payload, b'GET / HTTP/1.1\r\nCookie: a=b\r\n\r\n')

    def test_decompress_gzip_body(self):
        gzip_body_hex = '485454502f312e3120323030204f4b0d0a5365727665723a206e67696e782f312e32332e310d0a446174653a204d6f6e2c2031322053657020323032322030313a30383a343120474d540d0a436f6e74656e742d547970653a206170706c69636174696f6e2f6a736f6e0d0a5472616e736665722d456e636f64696e673a206368756e6b65640d0a436f6e6e656374696f6e3a206b6565702d616c6976650d0a566172793a204163636570742d456e636f64696e670d0a436f6e74656e742d456e636f64696e673a20677a69700d0a0d0a35640d0a1f8b0800000000000403ab564ace4f4955b2523254d25150ca4d2d2e4e4c0772159432527372f2416229a92589993920a197bb5b9e6ddafcb8a1f1e5d4fdcf36ce7fdcd0949a9b9f9569a5f061fe8c2e204fa916005a29ad344e0000000d0a300d0a0d0a'
        gzip_payload = bytes.fromhex(gzip_body_hex)
        body = self.gor.decompress_gzip_body(gzip_payload)
        self.assertEqual(body.decode(), '{"code":"1", "message": "hello", "detail": "黄河、长江。emoji: 😊。"}')

    def test_decode_chunked(self):
        data = b'4\r\nWiki\r\n6\r\npedia \r\nE\r\nin \r\n\r\nchunks.\r\n0\r\n\r\n'
        decoded = decode_chunked(data)
        self.assertEqual(decoded, b"Wikipedia in \r\n\r\nchunks.")

