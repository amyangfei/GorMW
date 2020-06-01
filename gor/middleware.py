# coding: utf-8

import sys
import logging

from .base import Gor

from tornado import gen, ioloop, queues


import contextlib
from tornado.stack_context import StackContext

@contextlib.contextmanager
def die_on_error():
    try:
        yield
    except Exception:
        logging.error("exception in asynchronous operation", exc_info=True)
        sys.exit(1)


class TornadoGor(Gor):

    def __init__(self, *args, **kwargs):
        super(TornadoGor, self).__init__(*args, **kwargs)
        self.q = queues.Queue()
        self.concurrency = kwargs.get('concurrency', 2)

    @gen.coroutine
    def _process(self):
        line = yield self.q.get()
        try:
            msg = self.parse_message(line)
            if msg:
                self.emit(msg)
        finally:
            self.q.task_done()

    @gen.coroutine
    def _worker(self):
        while True:
            yield self._process()

    @gen.coroutine
    def _run(self):
        for _ in range(self.concurrency):
            self._worker()

        while True:
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                yield self.q.join()
                break
            if not line:
                yield self.q.join()
                break
            self.q.put(line)
            yield

    def run(self):
        with StackContext(die_on_error):
            self.io_loop = ioloop.IOLoop.current()
            self.io_loop.run_sync(self._run)
