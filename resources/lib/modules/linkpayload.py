# -*- coding: utf-8 -*-
# A netmozi.com loadLinks valaszanak "linkPayload" mezojet fejti vissza.
# Python portja az oldal link-payload.v1.js dekoderenek: a details_links_btn
# gombok href-je "#", a valodi cimet a payload hordozza, a data-link-loader
# div data-token erteke a kulcs. Az unpack() a cimek listajat adja vissza.

import base64, json

M = 0xFFFFFFFF

def _seed(value):
    state = 2166136261
    for ch in value:
        state ^= ord(ch)
        state = (state + (state << 1) + (state << 4) + (state << 7) + (state << 8) + (state << 24)) & M
    return state

def _generator(state):
    s = [state]
    def nxt():
        x = (s[0] ^ (s[0] << 13)) & M
        x ^= x >> 17
        x = (x ^ (x << 5)) & M
        s[0] = x
        return x
    return nxt

def unpack(value, token):
    order = _generator(_seed(token + '|' + value['n'] + '|order') or 1)
    encoded = ''
    for r in value['r']:
        position = (r ^ order()) & M
        encoded += value['p'][position % 3][position // 3]
    raw = bytearray(base64.b64decode(encoded))
    nxt = _generator(_seed(token + '|' + value['n']) or 1)
    plain = bytearray(b ^ (nxt() & 255) for b in raw)
    if ('%08x' % _seed(''.join(chr(b) for b in plain)))[-8:] != value['h']:
        raise ValueError('linkPayload hash mismatch')
    return json.loads(bytes(plain).decode('utf-8'))
