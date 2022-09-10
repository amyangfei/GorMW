# coding: utf-8

import sys
import multiprocessing

from .base import Gor
from .callback import MultiProcessCallbackContainer


EXIT_MSG = ""

class MultiProcessGor(Gor):

    def __init__(self, *args, **kwargs):
        chan_container = MultiProcessCallbackContainer(multiprocessing.Manager())
        super(MultiProcessGor, self).__init__(chan_container, *args, **kwargs)
        self.concurrency = kwargs.get('concurrency', 2)
        self.workers = []
        self.queues = []

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
            msg = self.parse_message(line)
            if msg:
                # messages with the same id must be processed in serializable way
                index = hash(msg.id) % len(self.queues)
                self.queues[index].put(msg)

    def _worker(self, queue):
        while True:
            try:
                msg = queue.get()
            except KeyboardInterrupt:
                break
            try:
                if msg == EXIT_MSG:
                    return
                self.emit(msg)
            finally:
                queue.task_done()

    def _stop(self):
        for queue in self.queues:
            queue.put(EXIT_MSG)
            queue.join()

    def run(self):
        for i in range(self.concurrency):
            queue = multiprocessing.JoinableQueue()
            worker = multiprocessing.Process(target=self._worker, args=(queue,))
            self.queues.append(queue)
            self.workers.append(worker)
        for worker in self.workers:
            worker.start()
        self._stdin_reader()
        for worker in self.workers:
            worker.join()
