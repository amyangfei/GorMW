# coding: utf-8

import sys
import logging
import asyncio

from .base import Gor
from .callback import SimpleCallbackContainer


class AsyncioGor(Gor):

    def __init__(self, *args, **kwargs):
        chan_container = SimpleCallbackContainer()
        super(AsyncioGor, self).__init__(chan_container, *args, **kwargs)
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

        stdin_reader_task = self.io_loop.create_task(self._stdin_reader())
        self.tasks.append(stdin_reader_task)

    def _stop(self):
        for t in self.tasks:
            t.cancel()
        self.io_loop.stop()

    def _set_event_loop(self):
        if sys.version_info.major == 3 and sys.version_info.minor < 10:
            # less than 3.10.0
            self.io_loop = asyncio.get_event_loop()
        else:
            # equal or greater than 3.10.0
            try:
                self.io_loop = asyncio.get_running_loop()
            except RuntimeError:
                self.io_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.io_loop)

    def run(self):
        self._set_event_loop()
        self.io_loop.create_task(self._run())
        try:
            self.io_loop.run_forever()
        except Exception:
            logging.error("exception in run_sync", exc_info=True)
