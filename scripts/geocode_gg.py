import json, time, sys, re, urllib.parse, urllib.request
KEY = sys.argv[1] if len(sys.argv) > 1 else None
if not KEY: print("usage: python3 geocode_gg.py <KAKAO_REST_KEY>"); sys.exit(1)
def call(path, q):
    url = 'https://dapi.kakao.com/v2/local/search/' + path + '?query=' + urllib.parse.quote(q)
    req = urllib.request.Request(url, headers={'Authorization': 'KakaoAK ' + KEY})
    try:
        with urllib.request.urlopen(req, timeout=10) as r: j = json.load(r)
        d = j.get('documents') or []
        if d and d[0].get('x') and d[0].get('y'): return (float(d[0]['y']), float(d[0]['x']))
    except Exception: pass
    return None
def clean(a):
    for junk in ['일원','일대','일부',' 및',' 외','번지']: a = a.replace(junk, ' ')
    return re.sub(r'\s+', ' ', a).strip()
def dong(a):
    m = re.search(r'^(.*?(?:동|리|읍|면|가))(?:\s|$)', a)
    return m.group(1).strip() if m else a
d = json.load(open('data/gg_zones.json', encoding='utf-8')); zones = d['zones']
done = fail = 0
for i, z in enumerate(zones):
    if z.get('lat'): continue
    full = clean(z.get('addr') or ''); res = src = None
    if full: res = call('address.json', full); src = 'addr'
    if not res and full:
        dl = dong(full)
        if dl and dl != full:
            res = call('address.json', dl); src = 'dong'
            if not res: res = call('keyword.json', dl); src = 'kw'
    if not res and z.get('sigun'): res = call('address.json', z['sigun']); src = 'sigun'
    if res: z['lat'], z['lng'], z['geo'] = round(res[0],6), round(res[1],6), src; done += 1
    else: fail += 1
    if i % 60 == 0: print(f'  {i}/{len(zones)} (ok {done} fail {fail})')
    time.sleep(0.05)
d['meta']['geocoded'] = sum(1 for z in zones if z.get('lat'))
from collections import Counter
d['meta']['geo_src'] = dict(Counter(z.get('geo') for z in zones if z.get('lat')))
json.dump(d, open('data/gg_zones.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'DONE ok={done} fail={fail} coords={d["meta"]["geocoded"]}/{len(zones)} src={d["meta"]["geo_src"]}')
