# coding: utf-8

import io
import sys
import binascii
import unittest
import multiprocessing

from gor.middleware import MultiProcessGor


class Counter(object):
    def __init__(self):
        self.val = multiprocessing.Value('i', 0)

    def increment(self, n=1):
        with self.val.get_lock():
            self.val.value += n

    @property
    def value(self):
        return self.val.value


def _incr_received(proxy, msg, **kwargs):
    kwargs['passby']['received'].increment()


class TestMultiProcessGor(unittest.TestCase):

    def setUp(self):
        self.gor = MultiProcessGor()

    def tearDown(self):
        pass

    def _proxy_coroutine(self, passby):
        proxy = MultiProcessGor()
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
        self.assertEqual(passby['received'].value, 5)
        sys.stdin = old_stdin
