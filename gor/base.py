# coding: utf-8

import re
import sys
import gzip
import binascii
import datetime
import traceback
from urllib.parse import quote_plus, urlparse, parse_qs
from typing import Dict


def gor_hex_data(data):
    data = b''.join(
        map(lambda x: binascii.hexlify(x)
            if isinstance(x, bytes) else binascii.hexlify(x.encode()),
            [data.raw_meta, '\n', data.http])) + b'\n'
    return data.decode('utf-8')


class GorMessage(object):

    def __init__(self, _id, _type, meta, raw_meta, http):
        self.id = _id
        self.type = _type
        self.meta = meta
        self.raw_meta = raw_meta
        self.http = http


class Gor(object):

    def __init__(self, chan_container, *args, **kwargs):
        self.stderr = sys.stderr
        self.chan_container = chan_container

    def run(self):
        raise NotImplementedError

    def on(self, chan, callback, idx=None, **kwargs):
        if idx is not None:
            chan = chan + '#' + idx

        self.chan_container.add(chan, callback, **kwargs)
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
            r = self.chan_container.do_callback(self, chan_id, msg)
            if r:
                resp = r
        if resp:
            sys.stdout.write(gor_hex_data(resp))
            sys.stdout.flush()

    def parse_message(self, line: bytes) -> bytes:
        try:
            payload = binascii.unhexlify(line.strip())
            meta_pos = payload.index(b'\n')
            meta = payload[:meta_pos].decode()
            meta_arr = meta.split(' ')
            p_type, p_id = meta_arr[0], meta_arr[1]
            raw = payload[meta_pos+1:]
            return GorMessage(p_id, p_type, meta_arr, meta, raw)
        except Exception as e:
            self.stderr.write('Error while parsing incoming request: "%s" %s' % (line, e))
            traceback.print_exc(file=sys.stderr)

    def http_method(self, payload: bytes) -> str:
        pend = payload.index(b' ')
        return payload[:pend].decode()

    def http_path(self, payload: bytes) -> str:
        pstart = payload.index(b' ') + 1
        pend = payload.index(b' ', pstart)
        return payload[pstart:pend].decode()

    def set_http_path(self, payload: bytes, new_path: bytes) -> bytes:
        pstart = payload.index(b' ') + 1
        pend = payload.index(b' ', pstart)
        return payload[:pstart] + new_path + payload[pend:]

    def http_path_param(self, payload: bytes, name: str) -> str:
        path_qs = self.http_path(payload)
        query_dict = parse_qs(urlparse(path_qs).query)
        return query_dict.get(name)

    def set_http_path_param(self, payload: bytes, name: str, value: str) -> bytes:
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
        new_path = new_path.encode()
        return self.set_http_path(payload, new_path)

    def http_status(self, payload: bytes) -> str:
        '''
        HTTP response have status code in same position as `path` for requests
        '''
        return self.http_path(payload)

    def set_http_status(self, payload: bytes, new_status: str) -> bytes:
        return self.set_http_path(payload, new_status)

    def http_headers(self, payload: bytes) -> Dict[str, str]:
        """
        Parse the payload and return http headers in a map
        :param payload: the http payload to inspect
        :return: a map mapping from key to value of each http header item
        """
        start_index = payload.index(b"\r\n")
        end_index = payload.index(b"\r\n\r\n")
        if end_index == -1:
            end_index = len(payload)
        headers = {}
        for item in payload[start_index+2:end_index].split(b"\r\n"):
            sep_index = item.index(b":")
            key = item[:sep_index].decode()
            value = item[sep_index+1:].lstrip().decode()
            headers[key] = value
        return headers

    def http_header(self, payload: bytes, name: str) -> Dict[str, str]:
        current_line = 0
        idx = 0
        header = {
            'start': -1,
            'end': -1,
            'value_start': -1,
        }
        name = name.encode()
        while idx < len(payload):
            c = payload[idx]
            if c == ord('\n'):
                current_line += 1
                idx += 1
                header['end'] = idx

                if current_line > 0 and header['start'] > 0 and header['value_start'] > 0:
                    if payload[header['start']:header['value_start']-1].lower() == name.lower():
                        header['value'] = payload[header['value_start']:header['end']].strip().decode()
                        header['name'] = name.lower().decode()
                        return header

                header['start'] = -1
                header['value_start'] = -1
                continue
            elif c == ord('\r'):
                idx += 1
                continue
            elif c == ord(':'):
                if header['value_start'] == -1:
                    idx += 1
                    header['value_start'] = idx
                    continue
            if header['start'] == -1:
                header['start'] = idx
            idx += 1
        return None

    def set_http_header(self, payload: bytes, name: str, value: str) -> bytes:
        header = self.http_header(payload, name)
        if header is None:
            header_start = payload.index(b'\n') + 1
            return payload[:header_start] + name.encode() + b': ' + value.encode() + b'\r\n' + payload[header_start:]
        else:
            return payload[:header['value_start']] + b' ' + value.encode() + b'\r\n' + payload[header['end']:]

    def delete_http_header(self, payload: bytes, name: str) -> bytes:
        header = self.http_header(payload, name)
        if header is None:
            return payload
        else:
            return payload[:header['start']] + payload[header['end']:]

    def http_body(self, payload: bytes) -> bytes:
        if b'\r\n\r\n' not in payload:
            return b''
        return payload[payload.index(b'\r\n\r\n')+4:]

    def set_http_body(self, payload: bytes, new_body: bytes) -> bytes:
        payload = self.set_http_header(payload, 'Content-Length', str(len(new_body)))
        if b'\r\n\r\n' not in payload:
            return payload + b'\r\n\r\n' + new_body
        else:
            return payload[:payload.index(b'\r\n\r\n')+4] + new_body

    def http_cookie(self, payload: bytes, name: str) -> str:
        cookie_data = self.http_header(payload, 'Cookie')
        cookies = cookie_data.get('value') or ''
        for item in cookies.split('; '):
            if item.startswith(name + '='):
                return item[item.index('=')+1:]
        return None

    def set_http_cookie(self, payload: bytes, name: str, value: str) -> bytes:
        cookie_data = self.http_header(payload, 'Cookie')
        cookies = cookie_data.get('value') or ''
        cookies = list(filter(lambda x: not x.startswith(name + '='), cookies.split('; ')))
        cookies.append(name + '=' + value)
        return self.set_http_header(payload, 'Cookie', '; '.join(cookies))

    def delete_http_cookie(self, payload: bytes, name: str) -> bytes:
        cookie_data = self.http_header(payload, 'Cookie')
        cookies = cookie_data.get('value') or ''
        cookies = list(filter(lambda x: not x.startswith(name + '='), cookies.split('; ')))
        return self.set_http_header(payload, 'Cookie', '; '.join(cookies))

    '''
    def decompress_gzip_body(self, payload: bytes) -> str:
        headers = self.http_headers()
        transfer_encoding = headers.get('Transfer-Encoding')
        content_encoding  = headers.get('Content-Encoding')
        body = self.http_body(payload)
        if encoding == 'gzip':
            data = body
            if transfer_encoding.lower() == 'chunked':
                # TODO: chunked data decode
                pass
            body = gzip.decompress(data)
        else:
            body = body.decode('utf-8')
        return body
    '''
