"""Descarga pausada que comprueba robots.txt y usa un User-Agent identificable."""
from __future__ import annotations
import time,urllib.request,urllib.parse,urllib.robotparser,urllib.error
UA='Tarea2-Python-Victor/2026 (academic OCR-ASR project; https://github.com/victorroman1998/Python_2)'
_robots={};_ultima=0.
def solicitar(url,method='GET',headers=None,timeout=120):
    global _ultima
    parts=urllib.parse.urlsplit(url);origin=parts.scheme+'://'+parts.netloc
    if origin not in _robots:
        rp=urllib.robotparser.RobotFileParser()
        try:
            req=urllib.request.Request(origin+'/robots.txt',headers={'User-Agent':UA})
            with urllib.request.urlopen(req,timeout=45) as r:rp.parse(r.read().decode('utf-8-sig').splitlines())
        except urllib.error.HTTPError as e:
            if e.code in [404,410]:rp.parse([])
            else:raise
        _robots[origin]=rp;_ultima=time.monotonic()
    if not _robots[origin].can_fetch(UA,url):raise PermissionError('robots.txt no permite esta descarga: '+url)
    time.sleep(max(0.,1.3-(time.monotonic()-_ultima)))
    req=urllib.request.Request(url,headers={'User-Agent':UA,**(headers or {})},method=method)
    response=urllib.request.urlopen(req,timeout=timeout);_ultima=time.monotonic();return response

def descargar(url,destino):
    with solicitar(url) as r:
        with destino.open('wb') as f:
            while data:=r.read(1024*1024):f.write(data)
