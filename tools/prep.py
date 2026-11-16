#!/usr/bin/env python3
"""Готовит данные атласа. Запуск: python3 prep.py <папка с исходниками> <папка tools с node_modules> <папка data>"""
import json, sys, os, re, glob, subprocess, csv, hashlib
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import STATES, PEOPLES, POP, WORLD

SRC, TOOLS, OUT = [os.path.abspath(p) for p in sys.argv[1:4]]
STEPS = sys.argv[4:] or ['countries', 'history', 'relief', 'fields']
os.makedirs(OUT + '/hist', exist_ok=True)
TMP = TOOLS + '/tmp'; os.makedirs(TMP, exist_ok=True)

def ms(*args):
    subprocess.run(['npx', 'mapshaper', *args], cwd=TOOLS, check=True, capture_output=True)

def dump(obj, path):
    json.dump(obj, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))

ne = json.load(open(SRC + '/ne.geojson'))
RU = {}
for f in ne['features']:
    p = f['properties']
    for k in ('NAME', 'NAME_LONG', 'SOVEREIGNT', 'ADMIN', 'NAME_EN', 'BRK_NAME', 'FORMAL_EN'):
        if p.get(k) and p.get('NAME_RU'):
            RU.setdefault(p[k], p['NAME_RU'])
SHORT = {'Китайская Народная Республика': 'Китай', 'Демократическая Республика Конго': 'ДР Конго', 'Соединённые Штаты Америки': 'США',
         'Центральноафриканская Республика': 'ЦАР', 'Объединённые Арабские Эмираты': 'ОАЭ', 'Южно-Африканская Республика': 'ЮАР',
         'Корейская Народно-Демократическая Республика': 'Северная Корея', 'Республика Корея': 'Южная Корея',
         'Доминиканская Республика': 'Доминикана', 'Республика Конго': 'Конго', 'Китайская Республика': 'Тайвань'}
for f in ne['features']:
    f['properties']['NAME_RU'] = SHORT.get(f['properties'].get('NAME_RU'), f['properties'].get('NAME_RU'))
RU = {k: SHORT.get(v, v) for k, v in RU.items()}
CONT = {'Africa': 'Африка', 'Asia': 'Азия', 'Europe': 'Европа', 'North America': 'Северная Америка',
        'South America': 'Южная Америка', 'Oceania': 'Океания', 'Antarctica': 'Антарктида',
        'Seven seas (open ocean)': 'Острова океана'}

if 'countries' in STEPS:
    ms(SRC + '/ne.geojson', '-each', 'a=Math.round(this.area/1e6)', '-simplify', '45%', 'keep-shapes',
       '-o', TMP + '/ne.json', 'precision=0.001', 'format=geojson')
    d = json.load(open(TMP + '/ne.json'))
    for i, f in enumerate(d['features']):
        p = f['properties']
        f['id'] = i + 1
        f['properties'] = {
            'n': p.get('NAME_RU') or p['NAME'], 'en': p['NAME'], 'a': p['a'], 'pop': int(p.get('POP_EST') or 0),
            'py': p.get('POP_YEAR'), 'gdp': p.get('GDP_MD'), 'cont': CONT.get(p.get('CONTINENT'), ''),
            'c': int(p.get('MAPCOLOR7') or 1), 'lx': p.get('LABEL_X'), 'ly': p.get('LABEL_Y'),
            'sov': RU.get(p.get('SOVEREIGNT'), '') if p.get('SOVEREIGNT') != p.get('ADMIN') else '',
            'iso': p.get('ADM0_A3')}
    dump(d, OUT + '/countries.json')
    print('countries', len(d['features']), os.path.getsize(OUT + '/countries.json') // 1024, 'KB')

NONSTATE = re.compile(r'hunter|gatherer|forag|culture|farmer|pastoral|nomad|tribe|peoples|complex|focus|fisher|'
                      r'ficher|shellfish|aborigin|chiefdom', re.I)
STATEKW = re.compile(r'empire|kingdom|khanate|caliphate|sultanate|republic|duchy|emirate|dynasty|shogun|viceroyalty|'
                     r'principalit|confedera|horde|states?$|tsardom|imamate|county|bishopric|colony|union|league|'
                     r'\(|company|territory|protectorate|dominion', re.I)

if 'history' in STEPS:
    wb = {}
    for r in csv.DictReader(open(SRC + '/pop.csv')):
        wb[(r['Country Name'], int(r['Year']))] = float(r['Value']) / 1e6
    ALIAS = {'Russia': 'Russian Federation', 'Iran': 'Iran, Islamic Rep.', 'Egypt': 'Egypt, Arab Rep.',
             'Zaire': 'Congo, Dem. Rep.', 'Turkey': 'Turkiye', 'Venezuela': 'Venezuela, RB', 'Syria': 'Syrian Arab Republic',
             'Yemen': 'Yemen, Rep.', 'Vietnam': 'Viet Nam', 'South Korea': 'Korea, Rep.', 'Korea, Republic of': 'Korea, Rep.',
             "Korea, Democratic People's Republic of": "Korea, Dem. People's Rep.", 'Laos': 'Lao PDR',
             'Tanzania, United Republic of': 'Tanzania', 'Slovakia': 'Slovak Republic', 'Kyrgyzstan': 'Kyrgyz Republic',
             'Ivory Coast': "Cote d'Ivoire", 'Gambia, The': 'Gambia, The', 'Congo': 'Congo, Rep.', 'Burma': 'Myanmar',
             'Czechoslovakia': None}
    years = []
    for f in sorted(glob.glob(SRC + '/hb/geojson/world_*.geojson')):
        m = re.search(r'world_(bc)?(\d+)', f)
        y = int(m.group(2)) * (-1 if m.group(1) else 1)
        if y < -4000 or y in (1492, 1878):
            continue
        t = f'{TMP}/h{y}.json'
        ms(f, '-filter', 'NAME!=null && NAME!=""', '-dissolve2', 'NAME', 'copy-fields=BORDERPRECISION',
           '-each', 'a=Math.round(this.area/1e6), cx=+(this.innerX||0).toFixed(2), cy=+(this.innerY||0).toFixed(2)',
           '-simplify', '22%', 'keep-shapes', '-o', t, 'precision=0.01', 'format=geojson')
        d = json.load(open(t))
        out = []
        for i, ft in enumerate(d['features']):
            p = ft['properties']; en = p['NAME'].strip()
            if not ft.get('geometry'):
                continue
            if en == 'White Russia' and p['a'] > 5e6:
                ru, st = 'СССР', 1
            elif en in STATES:
                ru, st = STATES[en], 1
            elif en in PEOPLES:
                ru, st = PEOPLES[en], 0
            elif en in RU:
                ru, st = RU[en], 1
            else:
                ru = en
                x0, y0 = p['cx'], p['cy']
                tribal = (110 < x0 < 155 and -45 < y0 < -9) or (x0 < -50 and y0 > 25 and y < 1880) or y < 1500
                st = 0 if NONSTATE.search(en) else 1 if STATEKW.search(en) else 0 if tribal else 1
            pop = None
            if en in POP and y in POP[en]:
                pop = POP[en][y]
            elif y >= 1960 and st:
                v = wb.get((ALIAS.get(en, en), y))
                if v:
                    pop = round(v, 1 if v >= 10 else 2)
            col = int(hashlib.md5(en.encode()).hexdigest(), 16) % 9
            ft['id'] = i + 1
            ft['properties'] = {'n': ru, 'en': en, 'a': p['a'], 's': st, 'c': col, 'x': p['cx'], 'y': p['cy']}
            if pop is not None:
                ft['properties']['pop'] = pop
            out.append(ft)
        d['features'] = out
        dump(d, f'{OUT}/hist/{y}.json')
        ns = sum(1 for x in out if x['properties']['s'])
        years.append({'y': y, 'world': WORLD.get(y), 'states': ns, 'all': len(out)})
        print(y, len(out), 'states', ns, os.path.getsize(f'{OUT}/hist/{y}.json') // 1024, 'KB')
    dump(years, OUT + '/years.json')

if 'relief' in STEPS:
    Image.MAX_IMAGE_PIXELS = None
    im = np.asarray(Image.open(SRC + '/HYP_50M_SR_W.tif').convert('RGB'))
    H, W = im.shape[:2]
    N = 3072 * 2
    ML = 85.0511287798
    yy = (np.arange(N) + 0.5) / N
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * yy))))
    rows = np.clip(((90 - lat) / 180 * H).astype(int), 0, H - 1)
    cols = np.clip(((np.arange(N) + 0.5) / N * W).astype(int), 0, W - 1)
    merc = im[rows][:, cols]
    h = N // 2
    for r in range(2):
        for c in range(2):
            Image.fromarray(merc[r * h:(r + 1) * h, c * h:(c + 1) * h]).save(f'{OUT}/relief_{r}{c}.jpg', quality=82, optimize=True)
            print('relief', r, c, os.path.getsize(f'{OUT}/relief_{r}{c}.jpg') // 1024, 'KB')
    # Тёмная подложка для режимов ветров и течений: суша/вода по цвету океана исходника
    Image.fromarray(merc[::6, ::6]).save(TMP + '/small.png')

if 'fields' in STEPS:
    w = json.load(open(SRC + '/wind.json'))
    u = np.array(w[0]['data'], dtype=float).reshape(181, 360)
    v = np.array(w[1]['data'], dtype=float).reshape(181, 360)
    q = lambda a, s: np.clip(np.round(a / s), -127, 127).astype(np.int8)
    dump({'u': q(u, 0.4).ravel().tolist(), 'v': q(v, 0.4).ravel().tolist()}, OUT + '/wind.json')
    o = json.load(open(SRC + '/oscar.json'))
    def grid(rec):
        a = np.array([np.nan if x is None else x for x in rec['data']], dtype=float).reshape(481, 1080)
        a = np.roll(a, 60, axis=1)          # долгота 20° -> 0°
        return a[::2, ::2]                  # 0.667°, 241 x 540
    cu, cv = grid(o[0]), grid(o[1])
    def qc(a):
        b = np.clip(np.round(a / 0.02), -127, 127)
        b[np.isnan(a)] = -128
        return b.astype(np.int8)
    dump({'u': qc(cu).ravel().tolist(), 'v': qc(cv).ravel().tolist()}, OUT + '/currents.json')
    print('wind', os.path.getsize(OUT + '/wind.json'), 'currents', os.path.getsize(OUT + '/currents.json'),
          'max wind', float(np.hypot(u, v).max()), 'max cur', float(np.nanmax(np.hypot(cu, cv))))

if 'hydro' in STEPS:
    from rivers import RIVERS
    ms(SRC + '/ne_50m_rivers_lake_centerlines.geojson', '-simplify', '60%', '-o', TMP + '/riv.json', 'precision=0.001', 'format=geojson')
    ms(SRC + '/ne_50m_lakes.geojson', '-each', 'a=Math.round(this.area/1e6), cx=+(this.innerX||0).toFixed(2), cy=+(this.innerY||0).toFixed(2)',
       '-simplify', '50%', 'keep-shapes', '-o', TMP + '/lak.json', 'precision=0.001', 'format=geojson')
    out = []
    for f in json.load(open(TMP + '/riv.json'))['features']:
        p = f['properties']; en = p.get('name')
        if not f.get('geometry'):
            continue
        lake = p['featurecla'] == 'Lake Centerline'
        out.append({'type': 'Feature', 'geometry': f['geometry'],
                    'properties': {'k': 'r', 'n': '' if lake else RIVERS.get(en, en or ''), 'r': p['scalerank'], 'lc': 1 if lake else 0}})
    for f in json.load(open(TMP + '/lak.json'))['features']:
        p = f['properties']
        if not f.get('geometry'):
            continue
        out.append({'type': 'Feature', 'geometry': f['geometry'],
                    'properties': {'k': 'l', 'n': p.get('name_ru') or p.get('name') or '', 'r': p['scalerank'], 'a': p['a'], 'x': p['cx'], 'y': p['cy']}})
    for i, f in enumerate(out):
        f['id'] = i + 1
    dump({'type': 'FeatureCollection', 'features': out}, OUT + '/water.json')
    print('water', len(out), os.path.getsize(OUT + '/water.json') // 1024, 'KB', 'untranslated rivers:',
          sorted({f['properties']['n'] for f in out if f['properties']['k'] == 'r' and re.search('[A-Za-z]', f['properties']['n'])})[:200])

if 'cities' in STEPS:
    ms(SRC + '/ne_50m_populated_places.geojson', '-join', SRC + '/ne.geojson', 'fields=NAME_RU,ADM0_A3', 'prefix=J_', '-o', TMP + '/cit.json', 'format=geojson')
    out = []
    for f in json.load(open(TMP + '/cit.json'))['features']:
        p = f['properties']
        if p['FEATURECLA'] in ('Scientific station', 'Historic place'):
            continue
        country = SHORT.get(p.get('J_NAME_RU'), p.get('J_NAME_RU')) or RU.get(p.get('ADM0NAME'), '')
        cap = 1 if p['FEATURECLA'].startswith('Admin-0 capital') and (not p.get('J_ADM0_A3') or p.get('J_ADM0_A3') == p.get('ADM0_A3')) else 0
        out.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(p['LONGITUDE'], 3), round(p['LATITUDE'], 3)]},
                    'properties': {'n': {'Нур-Султан': 'Астана'}.get(p.get('NAME_RU'), p.get('NAME_RU') or p['NAME']), 'c': country, 'pop': int(p.get('POP_MAX') or 0), 'cap': cap, 'r': p['SCALERANK']}})
    out.sort(key=lambda f: (-f['properties']['cap'], -f['properties']['pop']))
    for i, f in enumerate(out):
        f['id'] = i + 1
    dump({'type': 'FeatureCollection', 'features': out}, OUT + '/cities.json')
    print('cities', len(out), os.path.getsize(OUT + '/cities.json') // 1024, 'KB', 'caps', sum(f['properties']['cap'] for f in out),
          [(f['properties']['n'], f['properties']['c']) for f in out if f['properties']['n'] in ('Донецк', 'Мариуполь', 'Херсон', 'Севастополь', 'Киев', 'Москва', 'Луганск')])
