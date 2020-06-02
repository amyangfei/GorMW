# coding: utf-8

import io
import sys
import binascii
import unittest
import threading

from gor.middleware import AsyncioGor


class Counter(object):
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            self.value += 1

    def count(self):
        with self._lock:
            return self.value


def _incr_received(proxy, msg, **kwargs):
    kwargs['passby']['received'].increment()


class TestAsyncioGor(unittest.TestCase):

    def setUp(self):
        self.gor = AsyncioGor()

    def tearDown(self):
        pass

    def test_init(self):

        passby = {'received': Counter()}
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
        self.assertEqual(passby['received'].count(), 5)

    def _proxy_coroutine(self, passby):
        proxy = AsyncioGor()
        proxy.on('message', _incr_received, passby=passby)
        proxy.on('request', _incr_received, passby=passby)
        proxy.on('response', _incr_received, idx='2', passby=passby)
        proxy.run()

    def test_run(self):
        old_stdin = sys.stdin
        passby = {'received': Counter()}
        payload = "\n".join([
            binascii.hexlify(b'1 2 3\nGET / HTTP/1.1\r\n\r\n').decode("utf-8"),
            binascii.hexlify(b'2 2 3\nHTTP/1.1 200 OK\r\n\r\n').decode("utf-8"),
            binascii.hexlify(b'2 3 3\nHTTP/1.1 200 OK\r\n\r\n').decode("utf-8"),
        ])
        sys.stdin = io.StringIO(payload)
        self._proxy_coroutine(passby)
        self.assertEqual(passby['received'].count(), 5)
        sys.stdin = old_stdin
