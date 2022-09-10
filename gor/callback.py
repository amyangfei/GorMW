# coding: utf-8

import sys
from datetime import datetime
from typing import Callable


class CallbackContainer(object):

    def __init__(self, *args, **kwargs):
        self.ch = None

    def init_container(self):
        raise NotImplementedError

    def ensure_chan(self, chan: str):
        raise NotImplementedError

    def add(self, chan: str, callback: Callable, **kwargs):
        self.ensure_chan(chan)
        self.ch[chan].append({
            'created': datetime.now(),
            'callback': callback,
            'kwargs': kwargs,
         })

    def do_callback(self, gor, chan_id: str, msg) -> str:
        resp = ''
        if self.ch.get(chan_id):
            for channel in self.ch[chan_id]:
                r = channel['callback'](gor, msg, **channel['kwargs'])
                if r:
                    resp = r
        return resp


class MultiProcessCallbackContainer(CallbackContainer):

    def __init__(self, manager, *args, **kwargs):
        super(CallbackContainer, self).__init__(*args, **kwargs)
        self.manager = manager
        self.ch = self.manager.dict()

    def ensure_chan(self, chan: str):
        self.ch.setdefault(chan, self.manager.list())


class SimpleCallbackContainer(CallbackContainer):

    def __init__(self, *args, **kwargs):
        super(CallbackContainer, self).__init__(*args, **kwargs)
        self.ch = {}

    def ensure_chan(self, chan: str):
        self.ch.setdefault(chan, [])
