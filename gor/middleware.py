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

    async def _process(self):
        line = await self.q.get()
        try:
            msg = self.parse_message(line)
            if msg:
                self.emit(msg)
        finally:
            self.q.task_done()

    async def _worker(self):
        while True:
            await self._process()

    async def _run(self):
        for _ in range(self.concurrency):
            self.io_loop.create_task(self._worker())

        while True:
            try:
                line = sys.stdin.readline()
            except KeyboardInterrupt:
                await self.q.join()
                self.io_loop.stop()
                break
            if not line:
                await self.q.join()
                self.io_loop.stop()
                break
            await self.q.put(line)

    def run(self):
        self.io_loop = asyncio.get_event_loop()
        self.io_loop.create_task(self._run())
        try:
            self.io_loop.run_forever()
        except Exception:
            logging.error("exception in run_sync", exc_info=True)
