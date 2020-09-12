# coding: utf-8

import sys
import multiprocessing

from .base import Gor


EXIT_MSG = ""

class MultiProcessGor(Gor):

    def __init__(self, *args, **kwargs):
        super(MultiProcessGor, self).__init__(*args, **kwargs)
        self.q = multiprocessing.JoinableQueue()
        self.concurrency = kwargs.get('concurrency', 2)
        self.workers = []

    def _stdin_reader(self):
        while True:
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                self._stop()
                break
            if not line:
                self._stop()
                break
            self.q.put(line)

    def _worker(self):
        while True:
            line = self.q.get()
            try:
                if line == EXIT_MSG:
                    return
                msg = self.parse_message(line)
                if msg:
                    self.emit(msg)
            finally:
                self.q.task_done()

    def _stop(self):
        for _ in range(len(self.workers)):
            self.q.put(EXIT_MSG)
        self.q.join()

    def run(self):
        for i in range(self.concurrency):
            worker = multiprocessing.Process(target=self._worker)
            self.workers.append(worker)
        for worker in self.workers:
            worker.start()
        self._stdin_reader()
