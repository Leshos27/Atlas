#!/usr/bin/env python3
"""Сообщает Яндексу (и Bing) о страницах сайта по протоколу IndexNow.

Запуск из корня репозитория:  python3 tools/indexnow.py            — все страницы из sitemap.xml
                              python3 tools/indexnow.py strany/indiya/ istoriya/  — только указанные

Ключ лежит в файле <ключ>.txt в корне сайта; он должен открываться по адресу
https://earthatlas.ru/<ключ>.txt, иначе поисковик отклонит запрос.
Запускайте после того, как изменения уже попали на хостинг."""
import json, re, sys, os, urllib.request, urllib.error

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
KEY = '7f80a98a7e36b5b475a38bdb944e4af6'
SITE = os.environ.get('SITE_URL', 'https://earthatlas.ru').rstrip('/')
HOST = re.sub(r'^https?://', '', SITE)
ENDPOINTS = ['https://yandex.com/indexnow', 'https://api.indexnow.org/indexnow']

if sys.argv[1:]:
    urls = [SITE + '/' + a.lstrip('/') for a in sys.argv[1:]]
else:
    urls = re.findall(r'<loc>([^<]+)</loc>', open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read())

body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'{SITE}/{KEY}.txt', 'urlList': urls[:10000]}).encode()
ok = True
for ep in ENDPOINTS:
    req = urllib.request.Request(ep, data=body, headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f'{ep}: {r.status} — отправлено адресов: {len(urls)}')
    except urllib.error.HTTPError as e:
        ok = False
        print(f'{ep}: ошибка {e.code} {e.read().decode(errors="replace")[:300]}')
    except Exception as e:
        ok = False
        print(f'{ep}: не удалось отправить — {e}')
sys.exit(0 if ok else 1)
