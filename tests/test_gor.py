# coding: utf-8

import unittest

from gor.base import Gor


class TestCommon(unittest.TestCase):

    def setUp(self):
        self.gor = Gor()

    def tearDown(self):
        pass

    def test_parse_message(self):
        payload = "1 2 3\nGET / HTTP/1.1\r\n\r\n".encode("hex")
        message = self.gor.parse_message(payload)
        expected = {
            "type": "1",
            "id": "2",
            "meta": ["1", "2", "3"],
            "http": "GET / HTTP/1.1\r\n\r\n",
        }
        for k, v in expected.items():
            self.assertEqual(message.get(k), v)

    def test_http_path(self):
        payload = "GET /test HTTP/1.1\r\n\r\n"
        path = self.gor.http_path(payload)
        self.assertEqual(path, "/test")

        new_payload = self.gor.set_http_path(payload, "/new/test")
        self.assertEqual(new_payload, "GET /new/test HTTP/1.1\r\n\r\n")
