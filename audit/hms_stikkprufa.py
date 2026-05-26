"""HMS 100-fastnum stikkprufa.

Reads hms_probe_fastnums.txt (100 fastnums sampled from mid-size gaps in
Supabase ∪ kaupskra) and queries each one through hms.is/api/fasteignaskra/fasteign/{nr}
via curl_cffi (Chrome120 TLS impersonation to bypass Cloudflare WAF).

Status codes:
  200 = real property (extract heimilisfang, sveitarfelag, notkun)
  500 = does not exist (admin-empty fastnum slot)
  other = anomaly (log + skip)

Output:
  hms_stikkprufa_results.json — full per-fastnum results + summary
"""
import json, time
from pathlib import Path
from collections import Counter
from curl_cffi import requests

API = "https://hms.is/api/fasteignaskra/fasteign"
DELAY = 1.0
LIST_FILE = Path(r'D:\verdmat-is\app\audit\hms_probe_fastnums.txt')
OUT_FILE = Path(r'D:\verdmat-is\app\audit\hms_stikkprufa_results.json')

fastnums = [int(x) for x in LIST_FILE.read_text(encoding='utf-8').split() if x.strip()]
print(f'Loaded {len(fastnums)} fastnums for stikkprufa')

results = []
status_counts = Counter()

for i, nr in enumerate(fastnums, 1):
    url = f"{API}/{nr}"
    try:
        r = requests.get(url, impersonate="chrome120", timeout=15)
        sc = r.status_code
        status_counts[sc] += 1
        entry = {'fastnum': nr, 'status': sc}
        if sc == 200:
            try:
                d = r.json().get('fasteignData', {}) or {}
                entry.update({
                    'stadfang': d.get('stadfang_birting'),
                    'postnumer': d.get('postnumer'),
                    'sveitarfelag': d.get('sveitarfelag_nafn'),
                    'notkun': d.get('notkun_texti'),
                    'notkun_kodi': d.get('notkun_kodi'),
                    'einflm': d.get('einflm'),
                    'fasteignamat': d.get('fasteignamat'),
                    'byggingarar_str': d.get('byggingarar') if 'byggingarar' in d else None,
                })
            except Exception as e:
                entry['parse_error'] = str(e)
        elif sc == 500:
            pass  # confirmed-empty
        else:
            entry['body_head'] = r.text[:200]
        results.append(entry)
        mark = '*' if sc == 200 else ('.' if sc == 500 else '?')
        if sc == 200:
            print(f'  [{i:3d}/{len(fastnums)}] {nr} -> {sc} {mark} {entry.get("stadfang","?")} / {entry.get("sveitarfelag","?")} ({entry.get("notkun","?")})')
        else:
            print(f'  [{i:3d}/{len(fastnums)}] {nr} -> {sc} {mark}')
    except Exception as e:
        status_counts['error'] += 1
        results.append({'fastnum': nr, 'status': 'error', 'exc': f'{type(e).__name__}: {e}'})
        print(f'  [{i:3d}/{len(fastnums)}] {nr} -> ERR {type(e).__name__}')
    time.sleep(DELAY)

summary = {
    'total': len(fastnums),
    'status_counts': dict(status_counts),
    'hit_rate_pct': round(100 * status_counts[200] / len(fastnums), 1),
}
print('\n=== Summary ===')
print(json.dumps(summary, indent=2, ensure_ascii=False))

# Bucket-distribute the 200s
by_bucket = Counter()
for e in results:
    if e.get('status') == 200:
        by_bucket[(e['fastnum'] // 100_000) * 100_000] += 1
if by_bucket:
    print('\nReal-property hits by 100K bucket:')
    for k in sorted(by_bucket):
        print(f'  {k:>9,} - {k+99_999:>9,}: {by_bucket[k]}')

OUT_FILE.write_text(json.dumps({'summary': summary, 'results': results}, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'\nWrote {OUT_FILE}')

# Show sample of real properties found
print('\nSample of real properties found in gaps (first 10):')
hits = [e for e in results if e.get('status') == 200]
for h in hits[:10]:
    print(f"  {h['fastnum']}: {h.get('stadfang','?')} ({h.get('postnumer','?')}) - {h.get('notkun','?')} - {h.get('sveitarfelag','?')}")
