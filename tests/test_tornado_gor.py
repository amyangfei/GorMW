# coding: utf-8

import sys
import time
import binascii
import unittest

PY3 = sys.version_info >= (3,)
from tornado import gen, ioloop
from gor.middleware import TornadoGor


def _incr_received(proxy, msg, **kwargs):
    kwargs['passby']['received'] += 1


class TestTornadoGor(unittest.TestCase):

    def setUp(self):
        self.gor = TornadoGor()

    def tearDown(self):
        pass

    def test_init(self):

        passby = {'received': 0}
        self.gor.on('message', _incr_received, passby=passby)
        self.gor.on('request', _incr_received, passby=passby)
        self.gor.on('response', _incr_received, idx='2', passby=passby)
        self.assertEqual(len(self.gor.ch), 3)

        req = self.gor.parse_message(binascii.hexlify(b'1 2 3\nGET / HTTP/1.1\r\n\r\n'))
        resp = self.gor.parse_message(binascii.hexlify(b'2 2 3\nHTTP/1.1 200 OK\r\n\r\n'))
        resp2 = self.gor.parse_message(binascii.hexlify(b'2 3 3\nHTTP/1.1 200 OK\r\n\r\n'))
        self.gor.emit(req)
        self.gor.emit(resp)
        self.gor.emit(resp2)
        self.assertEqual(passby['received'], 5)

    def _proxy_coroutine(self, passby):
        proxy = TornadoGor()
        proxy.on('message', _incr_received, passby=passby)
        proxy.on('request', _incr_received, passby=passby)
        proxy.on('response', _incr_received, idx='2', passby=passby)
        proxy.run()

    def test_run(self):
        old_stdin = sys.stdin
        passby = {'received': 0}
        payload = "\n".join([
            binascii.hexlify(b'1 2 3\nGET / HTTP/1.1\r\n\r\n').decode("utf-8"),
            binascii.hexlify(b'2 2 3\nHTTP/1.1 200 OK\r\n\r\n').decode("utf-8"),
            binascii.hexlify(b'2 3 3\nHTTP/1.1 200 OK\r\n\r\n').decode("utf-8"),
        ])
        if PY3:
            import io
            sys.stdin = io.StringIO(payload)
        else:
            import StringIO
            sys.stdin = StringIO.StringIO(payload)
        self._proxy_coroutine(passby)
        self.assertEqual(passby['received'], 5)
        sys.stdin = old_stdin
