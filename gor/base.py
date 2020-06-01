# coding: utf-8

import re
import sys
import binascii
import datetime
import traceback
PY3 = sys.version_info >= (3,)
try:
    from urllib.parse import quote_plus, urlparse, parse_qs
except ImportError:
    from urlparse import urlparse, parse_qs
    from urllib import quote_plus


def gor_hex_data(data):
    if PY3:
        data = b''.join(
            map(lambda x: binascii.hexlify(x)
                if isinstance(x, bytes) else binascii.hexlify(x.encode()),
                [data.raw_meta, '\n', data.http])) + b'\n'
        return data.decode('utf-8')
    else:
        return ''.join(map(lambda x: binascii.hexlify(x),
                           [data.raw_meta, '\n', data.http])) + '\n'


class GorMessage(object):

    def __init__(self, _id, _type, meta, raw_meta, http):
        self.id = _id
        self.type = _type
        self.meta = meta
        self.raw_meta = raw_meta
        self.http = http


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

    def emit(self, msg):
        chan_prefix_map = {
            '1': 'request',
            '2': 'response',
            '3': 'replay',
        }
        chan_prefix = chan_prefix_map[msg.type]
        resp = msg
        for chan_id in ['message', chan_prefix, chan_prefix + '#' + msg.id]:
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
            payload = binascii.unhexlify(line.strip())
            if PY3:
                payload = payload.decode()
            meta_pos = payload.index('\n')
            meta = payload[:meta_pos]
            meta_arr = meta.split(' ')
            p_type, p_id = meta_arr[0], meta_arr[1]
            raw = payload[meta_pos+1:]
            return GorMessage(p_id, p_type, meta_arr, meta, raw)
        except Exception as e:
            self.stderr.write('Error while parsing incoming request: "%s" %s' % (line, e))
            traceback.print_exc(file=sys.stderr)

    def http_method(self, payload):
        pend = payload.index(' ')
        return payload[:pend]

    def http_path(self, payload):
        pstart = payload.index(' ') + 1
        pend = payload.index(' ', pstart)
        return payload[pstart:pend]

    def set_http_path(self, payload, new_path):
        pstart = payload.index(' ') + 1
        pend = payload.index(' ', pstart)
        return payload[:pstart] + new_path + payload[pend:]

    def http_path_param(self, payload, name):
        path_qs = self.http_path(payload)
        query_dict = parse_qs(urlparse(path_qs).query)
        return query_dict.get(name)

    def set_http_path_param(self, payload, name, value):
        path_qs = self.http_path(payload)
        new_path = re.sub(name + '=([^&$]+)',
                          name + '=' + quote_plus(value),
                          path_qs)
        if new_path == path_qs:
            if '?' not in new_path:
                new_path += '?'
            else:
                new_path += '&'
            new_path += name + '=' + quote_plus(value)
        return self.set_http_path(payload, new_path)

    def http_status(self, payload):
        '''
        HTTP response have status code in same position as `path` for requests
        '''
        return self.http_path(payload)

    def set_http_status(self, payload, new_status):
        return self.set_http_path(payload, new_status)

    def http_header(self, payload, name):
        current_line = 0
        idx = 0
        header = {
            'start': -1,
            'end': -1,
            'value_start': -1,
        }
        if PY3 and isinstance(payload, bytes):
            payload = payload.decode()
        while idx < len(payload):
            c = payload[idx]
            if c == '\n':
                current_line += 1
                idx += 1
                header['end'] = idx

                if current_line > 0 and header['start'] > 0 and header['value_start'] > 0:
                    if payload[header['start']:header['value_start']-1].lower() == name.lower():
                        header['value'] = payload[header['value_start']:header['end']].strip()
                        if not PY3:
                            header['value'] = header['value'].encode('utf-8')
                        header['name'] = name.lower()
                        return header

                header['start'] = -1
                header['value_start'] = -1
                continue
            elif c == '\r':
                idx += 1
                continue
            elif c == ':':
                if header['value_start'] == -1:
                    idx += 1
                    header['value_start'] = idx
                    continue
            if header['start'] == -1:
                header['start'] = idx
            idx += 1
        return None

    def set_http_header(self, payload, name, value):
        if PY3 and isinstance(payload, bytes):
            payload = payload.decode()
        header = self.http_header(payload, name)
        if header is None:
            header_start = payload.index('\n') + 1
            return payload[:header_start] + name + ': ' + value + '\r\n' + payload[header_start:]
        else:
            return payload[:header['value_start']] + ' ' + value + '\r\n' + payload[header['end']:]

    def http_body(self, payload):
        if '\r\n\r\n' not in payload:
            return ''
        return payload[payload.index('\r\n\r\n')+4:]

    def set_http_body(self, payload, new_body):
        payload = self.set_http_header(payload, 'Content-Length', str(len(new_body)))
        if '\r\n\r\n' not in payload:
            return payload + '\r\n\r\n' + new_body
        else:
            return payload[:payload.index('\r\n\r\n')+4] + new_body

    def http_cookie(self, payload, name):
        cookie_data = self.http_header(payload, 'Cookie')
        cookies = cookie_data.get('value') or ''
        for item in cookies.split('; '):
            if item.startswith(name + '='):
                return item[item.index('=')+1:]
        return None

    def set_http_cookie(self, payload, name, value):
        cookie_data = self.http_header(payload, 'Cookie')
        cookies = cookie_data.get('value') or ''
        cookies = list(filter(lambda x: not x.startswith(name + '='), cookies.split('; ')))
        cookies.append(name + '=' + value)
        return self.set_http_header(payload, 'Cookie', '; '.join(cookies))
