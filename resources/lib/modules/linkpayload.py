# -*- coding: utf-8 -*-
# A netmozi.com loadLinks valaszanak "linkPayload" mezojet fejti vissza.
# Python portja az oldal link-payload.v1.js dekoderenek: a details_links_btn
# gombok href-je "#", a valodi cimet a payload hordozza, a data-link-loader
# div data-token erteke a kulcs. Az unpack() a cimek listajat adja vissza.
# Ugyanezzel a kodolassal jon az oldalak tartalma is (data-content-payload), amit a
# resolveContent() fejt vissza es illeszt a helyere.

import base64, json, re

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

def resolveContent(html):
    """A data-content-payload scriptek visszafejtese es a hozzajuk tartozo data-content-scope
    placeholder csereje a visszafejtett HTML-re, igy az oldal a regi, teljes szerkezetet adja."""
    for _ in range(3):
        if not html or 'data-content-payload' not in html:
            break
        for m in re.finditer(r'<script[^>]*data-content-payload[^>]*data-content-context="([^"]+)"[^>]*>(.*?)</script>', html, re.S):
            payload = json.loads(m.group(2))
            decoded = ''.join(unpack(payload['value'], m.group(1)))
            if not isinstance(decoded, type(html)):
                decoded = decoded.encode('utf-8')  # Python 2: a json unicode-ot ad, az oldal str
            html = re.sub(r'<div[^>]*data-content-scope="%s"[^>]*>.*?</div>' % re.escape(payload['scope']), lambda _: decoded, html, count=1, flags=re.S)
            html = html.replace(m.group(0), '', 1)
    return html
