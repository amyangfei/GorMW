# coding: utf-8

import sys
import logging
import asyncio

from .base import Gor


class AsyncioGor(Gor):

    def __init__(self, *args, **kwargs):
        super(AsyncioGor, self).__init__(*args, **kwargs)
        self.q = asyncio.Queue()
        self.concurrency = kwargs.get('concurrency', 2)
        self.tasks = []

    async def _worker(self):
        while True:
            line = await self.q.get()
            try:
                msg = self.parse_message(line)
                if msg:
                    self.emit(msg)
            finally:
                self.q.task_done()

    async def _stdin_reader(self):
        while True:
            try:
                await asyncio.sleep(0)
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                await self.q.join()
                self._stop()
                break
            if not line:
                await self.q.join()
                self._stop()
                break
            await self.q.put(line)

    async def _run(self):
        for _ in range(self.concurrency):
            t = self.io_loop.create_task(self._worker())
            self.tasks.append(t)

        self.io_loop.create_task(self._stdin_reader())

    def _stop(self):
        for t in self.tasks:
            t.cancel()
        self.io_loop.stop()

    def run(self):
        self.io_loop = asyncio.get_event_loop()
        self.io_loop.create_task(self._run())
        try:
            self.io_loop.run_forever()
        except Exception:
            logging.error("exception in run_sync", exc_info=True)
