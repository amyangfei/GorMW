# coding: utf-8

import os, sys

from .base import Gor

from tornado import gen, ioloop, queues


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
                self.emit(msg, line)
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
                try:
                    sys.exit(0)
                except SystemExit:
                    os._exit(0)
            self.q.put(line)
            yield

    def run(self):
        self.io_loop = ioloop.IOLoop.current()
        self.io_loop.run_sync(self._run)
