# coding: utf-8

import sys
import datetime
import traceback

def gor_hex_data(data):
    return ''.join(map(lambda x: x.encode('hex'), [data['raw_meta'], '\n', data['http']])) + '\n'


class Gor(object):

    def __init__(self, stderr=None):
        self.stderr = stderr or sys.stderr
        self.ch = {}

    def run(self):
        raise NotImplementedError

    def on(self, chan, callback, idx=None, **kwargs):
        if idx is not None:
            chan = chan + '#' + idx

        self.ch.setdefault(chan, [])
        self.ch[chan].append({
            'created': datetime.datetime.now(),
            'callback': callback,
            'kwargs': kwargs,
        })
        return self

    def emit(self, msg, raw):
        chan_prefix_map = {
            '1': 'request',
            '2': 'response',
            '3': 'replay',
        }
        chan_prefix = chan_prefix_map[msg['type']]
        resp = msg
        for chan_id in ['message', chan_prefix, chan_prefix + '#' + msg['id']]:
            if self.ch.get(chan_id):
                for channel in self.ch[chan_id]:
                    r = channel['callback'](self, msg, **channel['kwargs'])
                    if r:
                        resp = r
        if resp:
            sys.stdout.write(gor_hex_data(resp))
            sys.stdout.flush()

    def parse_message(self, line):
        try:
            payload = line.strip().decode('hex')
            meta_pos = payload.index('\n')
            meta = payload[:meta_pos]
            meta_arr = meta.split(' ')
            p_type, p_id = meta_arr[0], meta_arr[1]
            raw = payload[meta_pos+1:]
            return {
                'type': p_type,
                'id': p_id,
                'raw_meta': meta,
                'meta': meta_arr,
                'http': raw,
            }
        except Exception as e:
            self.stderr.write('Error while parsing incoming request: %s %s' % (line, e))
            traceback.print_exc(file=sys.stderr)

    def http_path(self, payload):
        pstart = payload.index(' ') + 1
        pend = payload.index(' ', pstart)
        return payload[pstart:pend]

    def set_http_path(self, payload, new_path):
        pstart = payload.index(' ') + 1
        pend = payload.index(' ', pstart)
        return payload[:pstart] + new_path + payload[pend:]
