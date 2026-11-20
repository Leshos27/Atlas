#!/usr/bin/env python3
"""Создаёт текстовые страницы сайта из данных атласа: страны, исторические государства, ресурсы, ветры и течения.
Запуск из корня сайта: python3 tools/pages.py  (адрес сайта — переменная SITE_URL)."""
import json, os, re, sys, glob, html, collections
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import STATES, PEOPLES
SITE = os.environ.get('SITE_URL', 'https://earthatlas.ru').rstrip('/')
os.chdir(ROOT)
E = html.escape

TR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя', ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u', 'f', 'kh', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya']))
def slug(s):
    s = ''.join(TR.get(c, c) for c in s.lower())
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:70]

def nf(x, d=0):
    s = f'{x:,.{d}f}'.replace(',', ' ').replace('.', ',')
    return s
def area(a):
    return f'{nf(a / 1e6, 2)} млн км²' if a >= 1e6 else f'{nf(a / 1e3)} тыс. км²' if a >= 1e4 else f'{nf(a)} км²'
def people(p):
    return f'{nf(p / 1e9, 2)} млрд' if p >= 1e9 else f'{nf(p / 1e6, 1 if p >= 1e7 else 2)} млн' if p >= 1e6 else f'{nf(p / 1e3, 0 if p >= 1e4 else 1)} тыс.' if p >= 1e3 else nf(p)
def mln(m):
    return f'{m} млн' if isinstance(m, str) else f'{nf(m / 1000, 2)} млрд' if m >= 1000 else f'{nf(m, 1 if m < 10 else 0)} млн'
def year(y):
    return f'{-y} г. до н. э.' if y < 0 else f'{y} г.'
def plural(n, one, few, many):
    n = abs(n) % 100
    return many if 11 <= n <= 19 else one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many

CONT_OVERRIDE = {'RUS': 'в Европе и Азии', 'KAZ': 'в Азии и Европе', 'TUR': 'в Азии и Европе'}
CONT_IN = {'Африка': 'в Африке', 'Азия': 'в Азии', 'Европа': 'в Европе', 'Северная Америка': 'в Северной Америке',
           'Южная Америка': 'в Южной Америке', 'Океания': 'в Океании', 'Антарктида': 'в Антарктиде', 'Острова океана': 'на островах в открытом океане'}

pages = []  # (путь, приоритет)

def write(path, title, desc, crumbs, body, kind='article'):
    """path — относительный путь папки, например 'strany/rossiya/'."""
    depth = path.count('/')
    up = '../' * depth
    os.makedirs(path, exist_ok=True)
    nav = ''.join(f'<a href="{up}{href}">{E(t)}</a>' for href, t in
                  (('strany/', 'Страны'), ('istoriya/', 'История'), ('resursy/', 'Ресурсы'), ('vetry-i-techeniya/', 'Ветры и течения')))
    bc = ' <span aria-hidden="true">›</span> '.join([f'<a href="{up}">Атлас мира</a>'] +
                                                     [f'<a href="{up}{h}">{E(t)}</a>' if h is not None else f'<span>{E(t)}</span>' for h, t in crumbs])
    ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement':
          [{'@type': 'ListItem', 'position': 1, 'name': 'Атлас мира', 'item': SITE + '/'}] +
          [{'@type': 'ListItem', 'position': i + 2, 'name': t, **({'item': f'{SITE}/{h}'} if h is not None else {})} for i, (h, t) in enumerate(crumbs)]}
    doc = f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITE}/{path}">
<link rel="icon" href="{up}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{up}site.css">
<meta property="og:type" content="{kind}">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="Атлас мира">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{SITE}/{path}">
<meta property="og:image" content="{SITE}/og.jpg">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head>
<body>
<header class="top"><div class="wrap"><a class="brand" href="{up}">Атлас мира</a><nav>{nav}</nav></div></header>
<main class="wrap">
<p class="crumbs">{bc}</p>
{body}
</main>
<footer class="wrap foot"><a href="{up}">Открыть карту</a><a href="{up}about.html">Об атласе и источниках</a><a href="{up}privacy.html">Персональные данные</a></footer>
</body>
</html>
'''
    open(path + 'index.html', 'w').write(doc)
    pages.append(path)

def maplink(up, params, text='Показать на карте'):
    q = '&'.join(f'{k}={v}' for k, v in params.items())
    return f'<a class="btn" href="{up}?{q}">{E(text)} →</a>'

# ---------- данные ----------
countries = json.load(open('data/countries.json'))['features']
cities = json.load(open('data/cities.json'))['features']
water = json.load(open('data/water.json'))['features']
content = json.load(open('data/content.json'))
geoms = [shape(f['geometry']).buffer(0) for f in countries]
tree = STRtree(geoms)

used = set()
def uniq(s):
    base = s; i = 2
    while s in used:
        s = f'{base}-{i}'; i += 1
    used.add(s); return s

cslug = {}
for f in countries:
    cslug[f['properties']['iso']] = uniq(slug(f['properties']['n']))

def country_of(lon, lat, offshore=1.5):
    pt = Point(lon, lat)
    for i in tree.query(pt):
        if geoms[i].contains(pt):
            return int(i)
    i = tree.nearest(pt)
    return int(i) if geoms[i].distance(pt) <= offshore else None

# ресурсы по странам
res_by_c = collections.defaultdict(list)
site_country = {}
for r in content['resources']:
    for s in r['s']:
        i = country_of(s[0], s[1])
        site_country[(r['id'], s[2])] = i
        if i is not None:
            res_by_c[i].append((r, s))

# реки по странам
rivers_by_c = collections.defaultdict(dict)
for f in water:
    p = f['properties']
    if p['k'] != 'r' or not p['n'] or p['r'] > 5 or re.search('[A-Za-z]', p['n']):
        continue
    g = shape(f['geometry'])
    name = p['n'].split(' (')[0]
    for i in tree.query(g):
        if geoms[i].intersects(g) and geoms[i].intersection(g).length > 0.6:
            rivers_by_c[int(i)][name] = min(p['r'], rivers_by_c[int(i)].get(name, 9))

# соседи
neigh = collections.defaultdict(set)
for i, g in enumerate(geoms):
    gb = g.buffer(0.03)
    for j in tree.query(gb):
        j = int(j)
        if j != i and gb.intersects(geoms[j]):
            neigh[i].add(j)

sovereign = [i for i, f in enumerate(countries) if not f['properties']['sov']]
rank_a = {i: k + 1 for k, i in enumerate(sorted(sovereign, key=lambda i: -countries[i]['properties']['a']))}
rank_p = {i: k + 1 for k, i in enumerate(sorted(sovereign, key=lambda i: -countries[i]['properties']['pop']))}

cities_by_c = collections.defaultdict(list)
for f in cities:
    cities_by_c[f['properties']['c']].append(f['properties'])

# ---------- общий стиль ----------
open('site.css', 'w').write('''@font-face { font-family: "Golos Text"; font-weight: 400; font-display: swap; src: url(fonts/golos-text-cyrillic-400-normal.woff2) format("woff2"); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: "Golos Text"; font-weight: 400; font-display: swap; src: url(fonts/golos-text-latin-400-normal.woff2) format("woff2"); unicode-range: U+0000-00FF, U+2000-206F; }
@font-face { font-family: "Golos Text"; font-weight: 600; font-display: swap; src: url(fonts/golos-text-cyrillic-600-normal.woff2) format("woff2"); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: "Golos Text"; font-weight: 600; font-display: swap; src: url(fonts/golos-text-latin-600-normal.woff2) format("woff2"); unicode-range: U+0000-00FF, U+2000-206F; }
@font-face { font-family: "Playfair Display"; font-weight: 700; font-display: swap; src: url(fonts/playfair-display-cyrillic-700-normal.woff2) format("woff2"); unicode-range: U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116; }
@font-face { font-family: "Playfair Display"; font-weight: 700; font-display: swap; src: url(fonts/playfair-display-latin-700-normal.woff2) format("woff2"); unicode-range: U+0000-00FF, U+2000-206F; }
/* Текстовые страницы: узкая колонка чтения, шапка-навигация по разделам атласа */
:root { --bg: #f4f7f9; --card: #ffffff; --ink: #14263a; --muted: #5a6b7c; --line: #cdd7e0; --accent: #c2500f; --accent-ink: #ffffff; --soft: #e8eef3; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #0b131c; --card: #111b27; --ink: #e7eef5; --muted: #93a4b6; --line: #2b3b4d; --accent: #f08a3c; --accent-ink: #1a1206; --soft: #1a2838; color-scheme: dark; } }
:root[data-theme="dark"] { --bg: #0b131c; --card: #111b27; --ink: #e7eef5; --muted: #93a4b6; --line: #2b3b4d; --accent: #f08a3c; --accent-ink: #1a1206; --soft: #1a2838; color-scheme: dark; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.6 "Golos Text", "Segoe UI", system-ui, sans-serif; }
.wrap { max-width: 860px; margin: 0 auto; padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.top { background: var(--card); border-bottom: 1px solid var(--line); }
.top .wrap { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 20px; padding-block: 12px; }
.brand { font: 700 20px/1.2 "Playfair Display", Georgia, serif; color: var(--ink); text-decoration: none; }
nav { display: flex; flex-wrap: wrap; gap: 4px 16px; }
nav a { color: var(--muted); text-decoration: none; font-weight: 600; font-size: 15px; }
nav a:hover { color: var(--accent); }
main { padding-block: 20px 48px; }
.crumbs { font-size: 13.5px; color: var(--muted); margin: 0 0 6px; }
.crumbs a { color: var(--muted); }
h1 { font: 700 32px/1.2 "Playfair Display", Georgia, serif; margin: 6px 0 10px; text-wrap: balance; }
h2 { font-size: 20px; margin: 30px 0 10px; text-wrap: balance; }
p { margin: 0 0 12px; max-width: 68ch; }
a { color: var(--accent); }
.lead { font-size: 18px; }
.btn { display: inline-block; background: var(--accent); color: var(--accent-ink); text-decoration: none; font-weight: 600; padding: 10px 16px; border-radius: 8px; margin: 6px 0 4px; }
.facts { display: grid; grid-template-columns: minmax(0, 220px) minmax(0, 1fr); gap: 0; margin: 14px 0; background: var(--card); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }
.facts dt, .facts dd { margin: 0; padding: 9px 14px; border-bottom: 1px solid var(--line); }
.facts dt { color: var(--muted); }
.facts dd { font-weight: 600; font-variant-numeric: tabular-nums; min-width: 0; }
.facts dt:nth-last-of-type(1), .facts dd:last-child { border-bottom: 0; }
@media (max-width: 560px) { .facts { grid-template-columns: 1fr; } .facts dt { border-bottom: 0; padding-bottom: 0; font-size: 13px; } }
.cols { columns: 3 220px; column-gap: 28px; padding: 0; margin: 0 0 12px; list-style: none; }
.cols li { break-inside: avoid; padding: 3px 0; }
.cols .num { color: var(--muted); font-size: 14px; font-variant-numeric: tabular-nums; }
ul.plain { padding-left: 20px; } ul.plain li { margin-bottom: 6px; }
.tbl { overflow-x: auto; margin: 10px 0 16px; }
table { border-collapse: collapse; width: 100%; font-size: 15px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 12px 7px 0; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--muted); font-weight: 600; font-size: 13.5px; }
.note { color: var(--muted); font-size: 14px; }
.foot { display: flex; flex-wrap: wrap; gap: 6px 20px; padding-block: 20px 40px; border-top: 1px solid var(--line); font-size: 14px; }
.foot a { color: var(--muted); }
''')

# ---------- страны ----------
cont_groups = collections.defaultdict(list)
pages_json = {'countries': {}, 'states': {}, 'resources': {}}
for i, f in enumerate(countries):
    p = f['properties']; s = cslug[p['iso']]
    pages_json['countries'][p['iso']] = f'strany/{s}/'
    cont_groups[p['cont'] or 'Острова океана'].append((p['n'], s, p['pop']))
    up = '../../'
    dens = p['pop'] / p['a'] if p['pop'] and p['a'] else 0
    caps = [c for c in cities_by_c.get(p['n'], []) if c['cap']]
    big = sorted(cities_by_c.get(p['n'], []), key=lambda c: -c['pop'])[:6]
    facts = [('Площадь', '≈ ' + area(p['a']) + (f' · {rank_a[i]}-е место в мире' if i in rank_a else ''))]
    if p['pop']:
        facts.append((f'Население ({p["py"]})' if p.get('py') else 'Население', people(p['pop']) + (f' · {rank_p[i]}-е место в мире' if i in rank_p else '')))
    if dens:
        facts.append(('Плотность населения', f'{nf(dens, 1 if dens < 10 else 0)} чел./км²'))
    if p.get('gdp'):
        g = p['gdp']; facts.append(('ВВП', f'{nf(g / 1e6, 2)} трлн долл.' if g >= 1e6 else f'{nf(g / 1e3, 1 if g < 1e4 else 0)} млрд долл.'))
        if p['pop']:
            facts.append(('ВВП на душу населения', f'≈ {nf(g * 1e6 / p["pop"] / 1000, 1)} тыс. долл.' if g * 1e6 / p['pop'] >= 1000 else f'≈ {nf(g * 1e6 / p["pop"])} долл.'))
    if p['cont']:
        facts.append(('Часть света', {'RUS': 'Европа и Азия', 'KAZ': 'Азия и Европа', 'TUR': 'Азия и Европа'}.get(p['iso'], p['cont'])))
    if caps:
        facts.append(('Столица', ', '.join(c['n'] for c in caps[:2])))
    if p['sov']:
        facts.append(('Под управлением', p['sov']))
    nb = sorted(neigh[i], key=lambda j: countries[j]['properties']['n'])
    if nb:
        facts.append(('Соседи по суше', ', '.join(f'<a href="../{cslug[countries[j]["properties"]["iso"]]}/">{E(countries[j]["properties"]["n"])}</a>' for j in nb)))
    dl = ''.join(f'<dt>{E(k)}</dt><dd>{v if k == "Соседи по суше" else E(v)}</dd>' for k, v in facts)
    lead = f'<b>{E(p["n"])}</b> — '
    lead += (f'территория под управлением государства «{E(p["sov"])}»' if p['sov'] else 'государство') + f' {CONT_OVERRIDE.get(p["iso"], CONT_IN.get(p["cont"], ""))}.'
    lead += f' Площадь — около {area(p["a"])}'
    lead += f', население — {people(p["pop"])} человек' + (f' по данным на {p["py"]} год' if p.get('py') else '') + '.' if p['pop'] else '.'
    if i in rank_a and i in rank_p and p['pop']:
        lead += f' По площади страна занимает {rank_a[i]}-е место в мире, по численности населения — {rank_p[i]}-е.'
    body = f'<h1>{E(p["n"])}</h1>\n<p class="lead">{lead}</p>\n{maplink(up, {"mode": "today", "country": p["iso"]})}\n<dl class="facts">{dl}</dl>'
    if big:
        body += '<h2>Крупнейшие города</h2><ul class="cols">' + ''.join(
            f'<li>{E(c["n"])}{" (столица)" if c["cap"] else ""} <span class="num">{people(c["pop"])}</span></li>' for c in big) + '</ul>'
        body += '<p class="note">Население городов указано для агломераций.</p>'
    rv = sorted(rivers_by_c[i].items(), key=lambda kv: (kv[1], kv[0]))[:12]
    if rv:
        body += '<h2>Крупные реки</h2><p>' + ', '.join(E(n) for n, _ in rv) + '.</p>'
    if res_by_c[i]:
        body += '<h2>Ресурсы и отрасли</h2><ul class="plain">'
        for r, s_ in sorted(res_by_c[i], key=lambda t: -t[1][3]):
            nm = re.sub(r', ' + re.escape(p['n']) + r'(?= —|$)', '', s_[2])
            body += f'<li><a href="{up}resursy/{slug(r["n"])}/">{E(r["n"])}</a>: {E(nm)}</li>'
        body += '</ul>'
    body += '<p class="note">Площадь посчитана по контуру страны на карте атласа и может немного отличаться от официальной. Население — оценка Natural Earth.</p>'
    title = f'{p["n"]}: площадь, население, столица, карта — Атлас мира'
    desc = f'{p["n"]} на интерактивной карте: площадь ≈ {area(p["a"])}' + (f', население {people(p["pop"])}' if p['pop'] else '') + (f', столица — {caps[0]["n"]}' if caps else '') + '. Соседи, крупные города, реки и ресурсы.'
    write(f'strany/{s}/', title, desc, [('strany/', 'Страны'), (None, p['n'])], body)

body = '<h1>Страны мира</h1><p class="lead">Площадь, население, столицы, соседи, реки и ресурсы всех стран и зависимых территорий мира. Выберите страну, чтобы открыть её справку и показать на карте.</p>'
order = ['Европа', 'Азия', 'Африка', 'Северная Америка', 'Южная Америка', 'Океания', 'Антарктида', 'Острова океана']
for c in order:
    if c not in cont_groups:
        continue
    lst = sorted(cont_groups[c])
    body += f'<h2>{E(c)} <span class="note">· {len(lst)}</span></h2><ul class="cols">' + ''.join(
        f'<li><a href="{s}/">{E(n)}</a> <span class="num">{people(pp) if pp else ""}</span></li>' for n, s, pp in lst) + '</ul>'
write('strany/', 'Страны мира: площадь, население и столицы — Атлас мира',
      'Справочник всех стран мира: площадь, население, столицы, соседи, реки и ресурсы с интерактивной картой.', [(None, 'Страны')], body, 'website')

# ---------- исторические государства ----------
hist = {}
for f in glob.glob('data/hist/*.json'):
    y = int(os.path.basename(f)[:-5])
    for x in json.load(open(f))['features']:
        q = x['properties']
        if q['s']:
            hist.setdefault(q['en'], []).append((y, q['a'], q['x'], q['y'], q.get('pop')))
cards = collections.OrderedDict()
for en, card in content['states'].items():
    cards.setdefault(tuple(card), []).append(en)
hlist = []
for card, ens in cards.items():
    occ = sorted([(y, a, x, yy, pop, en) for en in ens for (y, a, x, yy, pop) in hist.get(en, [])])
    if not occ:
        continue
    ru = STATES.get(ens[0], ens[0])
    s = uniq(slug(ru)); path = f'istoriya/{s}/'
    for en in ens:
        pages_json['states'][en] = path
    best = max(occ, key=lambda t: t[1])
    years_, cap, rulers, about = card
    up = '../../'
    rows = ''.join(f'<tr><td>{E(year(y))}</td><td>{E(STATES.get(en, en))}</td><td>≈ {area(a)}</td><td>{("≈ " + mln(pop)) if pop is not None else "—"}</td></tr>' for y, a, x, yy, pop, en in occ)
    facts = [('Годы существования', years_), ('Столица', cap), ('Известные правители', rulers), ('Наибольшая площадь на карте атласа', f'≈ {area(best[1])} ({year(best[0])})')]
    body = (f'<h1>{E(ru)}</h1><p class="lead">{E(about)}</p>'
            + maplink(up, {'mode': 'history', 'year': best[0], 'state': best[5].replace(' ', '%20')}, f'Показать на карте ({year(best[0])})')
            + '<dl class="facts">' + ''.join(f'<dt>{E(k)}</dt><dd>{E(v)}</dd>' for k, v in facts) + '</dl>'
            + f'<h2>На исторической карте</h2><p>Государство есть на {len(occ)} {plural(len(occ), "срезе", "срезах", "срезах")} времени атласа. Площадь посчитана по контуру на карте и приблизительна, особенно для древних эпох.</p>'
            + f'<div class="tbl"><table><thead><tr><th>Год</th><th>Название на карте</th><th>Площадь</th><th>Население</th></tr></thead><tbody>{rows}</tbody></table></div>')
    title = f'{ru}: годы, столица, правители, карта — Атлас мира'
    desc = f'{ru} ({years_}): столица — {cap}; правители: {rulers}. Границы на исторической карте мира.'
    write(path, title, desc[:300], [('istoriya/', 'История'), (None, ru)], body)
    hlist.append((occ[0][0], ru, s, years_))
hlist.sort()
body = ('<h1>История государств</h1><p class="lead">Справки о государствах прошлого — от первых цивилизаций Месопотамии и Египта до империй XX века: годы существования, столицы, правители и границы на исторической карте.</p>'
        + maplink('../', {'mode': 'history'}, 'Открыть историческую карту')
        + '<div class="tbl"><table><thead><tr><th>Государство</th><th>Годы существования</th></tr></thead><tbody>'
        + ''.join(f'<tr><td><a href="{s}/">{E(ru)}</a></td><td>{E(ys)}</td></tr>' for _, ru, s, ys in hlist) + '</tbody></table></div>')
write('istoriya/', 'История государств мира на карте — Атлас мира',
      'Государства прошлого на исторической карте мира: Древний Египет, Римская империя, Монгольская империя, Российская империя и другие — годы, столицы, правители.', [(None, 'История')], body, 'website')

# ---------- ресурсы ----------
RES_TEXT = {
 'oil': 'Нефть — главное топливо транспорта и сырьё для химической промышленности: из неё делают бензин, дизельное и авиационное топливо, пластмассы, смазки. Крупнейшие запасы сосредоточены на Ближнем Востоке, в Венесуэле, Канаде и России.',
 'gas': 'Природный газ в основном состоит из метана. Его сжигают на электростанциях и в котельных, используют для отопления домов и производства удобрений. Газ доставляют по трубопроводам или в сжиженном виде на танкерах.',
 'coal': 'Уголь — древнейшее промышленное топливо. Энергетический уголь сжигают на электростанциях, коксующийся нужен для выплавки чугуна и стали. Крупнейший производитель и потребитель угля — Китай.',
 'uranium': 'Уран — топливо атомных электростанций. Его добывают в шахтах, карьерах и методом подземного выщелачивания, затем обогащают и превращают в тепловыделяющие элементы реакторов.',
 'iron': 'Железная руда — основа металлургии: из неё выплавляют чугун и сталь для строительства, машин и транспорта. Крупнейшие экспортёры — Австралия и Бразилия.',
 'copper': 'Медь хорошо проводит электричество и тепло, поэтому из неё делают провода, кабели, электродвигатели и трубы. Спрос на медь растёт вместе с электромобилями и возобновляемой энергетикой.',
 'bauxite': 'Бокситы — главная руда алюминия. Из них получают глинозём, а затем электролизом — лёгкий и прочный металл для самолётов, автомобилей, упаковки и строительства.',
 'nickel': 'Никель добавляют в нержавеющую сталь и жаропрочные сплавы, а в последние годы — в аккумуляторы электромобилей.',
 'gold': 'Золото служит резервом центральных банков, сырьём для ювелирных украшений и электроники. За всю историю человечество добыло около двухсот тысяч тонн золота.',
 'diamonds': 'Алмазы образуются глубоко в мантии и выносятся к поверхности в кимберлитовых трубках. Крупные прозрачные камни идут на бриллианты, остальные — на режущий и шлифовальный инструмент.',
 'lithium': 'Литий — самый лёгкий металл и основа литий-ионных аккумуляторов для телефонов, ноутбуков и электромобилей. Его добывают из горных пород и из рассолов солёных озёр.',
 'ree': 'Редкоземельные металлы — группа из 17 элементов. Без них не обходятся мощные постоянные магниты в электродвигателях и ветрогенераторах, экраны, лазеры и электроника.',
 'wheat': 'Пшеница — одна из главных продовольственных культур мира: из неё делают муку, хлеб и макароны. Крупнейшие районы выращивания — степи и прерии умеренного пояса.',
 'rice': 'Рис кормит больше половины человечества. Его выращивают в основном на затопляемых полях в тёплых и влажных районах Южной и Восточной Азии.',
 'coffee': 'Кофейное дерево растёт в тропиках, лучше всего — на возвышенностях. Родина кофе — Эфиопия, а крупнейший производитель — Бразилия.',
 'cotton': 'Хлопок — главное растительное волокно для тканей. Ему нужны тепло, солнце и много воды, поэтому хлопковые районы часто зависят от орошения.',
}
body = '<h1>Ресурсы мира: где что добывают и выращивают</h1><p class="lead">Главные районы добычи полезных ископаемых и выращивания сельскохозяйственных культур на карте мира.</p>' + maplink('../', {'mode': 'resources'}, 'Открыть карту ресурсов')
groups = collections.OrderedDict()
for r in content['resources']:
    groups.setdefault(r['g'], []).append(r)
for g, lst in groups.items():
    body += f'<h2>{E(g)}</h2><ul class="plain">' + ''.join(f'<li><a href="{slug(r["n"])}/">{E(r["n"])}</a> — {len(r["s"])} {plural(len(r["s"]), "район", "района", "районов")}</li>' for r in lst) + '</ul>'
write('resursy/', 'Ресурсы мира на карте: нефть, газ, металлы, урожай — Атлас мира',
      'Где в мире добывают нефть, газ, уголь, уран, железную руду, медь, золото, алмазы, литий и где выращивают пшеницу, рис, кофе и хлопок.', [(None, 'Ресурсы')], body, 'website')
for r in content['resources']:
    s = slug(r['n']); pages_json['resources'][r['id']] = f'resursy/{s}/'
    up = '../../'
    rows = ''
    for site in sorted(r['s'], key=lambda t: -t[3]):
        i = site_country.get((r['id'], site[2]))
        cn = f'<a href="{up}strany/{cslug[countries[i]["properties"]["iso"]]}/">{E(countries[i]["properties"]["n"])}</a>' if i is not None else '—'
        rows += f'<tr><td>{E(site[2])}</td><td>{cn}</td><td>{"крупнейший" if site[3] == 3 else "крупный" if site[3] == 2 else "заметный"}</td></tr>'
    body = (f'<h1>{E(r["n"])}: где добывают и производят</h1><p class="lead">{E(RES_TEXT.get(r["id"], ""))}</p>'
            + maplink(up, {'mode': 'resources', 'res': r['id']})
            + f'<h2>Основные районы на карте</h2><div class="tbl"><table><thead><tr><th>Район</th><th>Страна</th><th>Значение</th></tr></thead><tbody>{rows}</tbody></table></div>'
            + '<p class="note">Районы нанесены на карту схематично: кружок обозначает район, а не точные границы месторождения.</p>')
    write(f'resursy/{s}/', f'{r["n"]}: где добывают в мире, карта — Атлас мира',
          f'{r["n"]} на карте мира: крупнейшие районы добычи и производства по странам.', [('resursy/', 'Ресурсы'), (None, r['n'])], body)

# ---------- ветры и течения ----------
cur_warm = sorted({c[2] for c in content['currents'] if c[3] == 'w'})
cur_cold = sorted({c[2] for c in content['currents'] if c[3] == 'c'})
body = f'''<h1>Ветры и океанские течения</h1>
<p class="lead">Воздух и вода переносят тепло от экватора к полюсам. Из-за этого возникают постоянные ветры и течения, которые определяют климат целых континентов.</p>
{maplink('../', {'mode': 'fields', 'field': 'wind'}, 'Карта ветров')} {maplink('../', {'mode': 'fields', 'field': 'cur'}, 'Карта течений')}
<h2>Как устроены главные ветры</h2>
<p>У экватора воздух сильно нагревается и поднимается вверх. Здесь лежит экваториальная штилевая зона — пояс слабых ветров и частых ливней. Поднявшийся воздух растекается к северу и югу и опускается примерно на 30-х широтах, где тоже мало ветра. Моряки называли эти районы «конскими широтами».</p>
<p>От 30-х широт к экватору дуют <b>пассаты</b> — самые постоянные ветры на Земле. Из-за вращения Земли они отклоняются: в Северном полушарии дуют с северо-востока, в Южном — с юго-востока. На пассатах парусные корабли пересекали океаны.</p>
<p>В умеренных широтах господствует <b>западный перенос</b>: ветры дуют с запада на восток и приносят циклоны с дождями. В Южном полушарии их почти не тормозит суша, поэтому там дуют сильные «ревущие сороковые» и «неистовые пятидесятые». У полюсов холодный воздух растекается в стороны — это полярные восточные ветры.</p>
<p><b>Муссоны</b> меняют направление по сезонам. Зимой суша остывает сильнее океана, и ветер дует с материка — сухой зимний муссон. Летом суша нагревается, и ветер с океана приносит дожди. Сильнее всего муссоны выражены в Южной и Восточной Азии.</p>
<h2>Как устроены океанские течения</h2>
<p>Поверхностные течения разгоняются постоянными ветрами. Пассаты гонят воду на запад вдоль экватора, западные ветры — на восток в умеренных широтах. Берега материков замыкают эти потоки в огромные круговороты: в Северном полушарии вода в них движется по часовой стрелке, в Южном — против.</p>
<p><b>Тёплые течения</b> несут воду от экватора к полюсам и смягчают климат. Благодаря Гольфстриму и Северо-Атлантическому течению в Норвегии и на Кольском полуострове не замерзают порты за Полярным кругом. <b>Холодные течения</b> идут от полюсов к экватору. Вдоль их берегов мало дождей, поэтому там лежат прибрежные пустыни — Атакама у Перуанского течения и Намиб у Бенгельского.</p>
<p>Самое мощное течение Земли — <b>Течение Западных Ветров</b>: оно непрерывным кольцом огибает Антарктиду.</p>
<h2>Тёплые течения на карте</h2><ul class="cols">{''.join(f'<li>{E(n)}</li>' for n in cur_warm)}</ul>
<h2>Холодные течения на карте</h2><ul class="cols">{''.join(f'<li>{E(n)}</li>' for n in cur_cold)}</ul>
<p class="note">На карте атласа показан снимок ветров и течений за 31 января 2014 года: зима Северного полушария.</p>'''
write('vetry-i-techeniya/', 'Ветры и океанские течения на карте мира: пассаты, муссоны, Гольфстрим — Атлас мира',
      'Как устроены пассаты, западные ветры, муссоны и океанские течения. Тёплые и холодные течения на интерактивной карте и глобусе.', [(None, 'Ветры и течения')], body)

json.dump(pages_json, open('data/pages.json', 'w'), ensure_ascii=False, separators=(',', ':'))
open('tools/pages.txt', 'w').write('\n'.join(sorted(pages)) + '\n')
print('страниц:', len(pages), '· стран:', len(pages_json['countries']), '· государств:', len(hlist), '· ресурсов:', len(pages_json['resources']))
