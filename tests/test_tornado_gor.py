# coding: utf-8

import unittest

from gor.middleware import TornadoGor


class TestTornadoGor(unittest.TestCase):

    def setUp(self):
        self.gor = TornadoGor()

    def tearDown(self):
        pass

    def test_init(self):

        def _incr_received(proxy, msg, **kwargs):
            kwargs['passby']['received'] += 1

        passby = {'received': 0}
        self.gor.on('message', _incr_received, passby=passby)
        self.gor.on('request', _incr_received, passby=passby)
        self.gor.on('response', _incr_received, idx='2', passby=passby)
        self.assertEqual(len(self.gor.ch), 3)

        req = self.gor.parse_message('1 2 3\nGET / HTTP/1.1\r\n\r\n'.encode('hex'))
        resp = self.gor.parse_message('2 2 3\nHTTP/1.1 200 OK\r\n\r\n'.encode('hex'))
        resp2 = self.gor.parse_message('2 3 3\nHTTP/1.1 200 OK\r\n\r\n'.encode('hex'))
        self.gor.emit(req)
        self.gor.emit(resp)
        self.gor.emit(resp2)
        self.assertEqual(passby['received'], 5)
