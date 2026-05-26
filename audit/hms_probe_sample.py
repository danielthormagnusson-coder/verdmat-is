"""Sample 100 fastnums from mid-size gaps in (Supabase ∪ kaupskra) for HMS probe.

Mid-size = 200..1000 wide; large multi-thousand gaps are excluded because we
already know those are admin-empty regions (pilot v3 result)."""
import re
from pathlib import Path

KNOWN_REAL = Path(r'D:\verdmat-is\app\audit\known_real_fastnums.txt')
SUPABASE_DUMP = Path(r'C:\Users\danie\.claude\projects\D--\8276b227-1f92-44f6-a6aa-975df4fdebf0\tool-results\mcp-claude_ai_Supabase-execute_sql-1778849767605.txt')
OUT = Path(r'D:\verdmat-is\app\audit\hms_probe_fastnums.txt')

sb = set(int(m) for m in re.findall(r'(?<![\d])(2\d{6})(?![\d])', SUPABASE_DUMP.read_text(encoding='utf-8')))
known = set(int(x) for x in KNOWN_REAL.read_text(encoding='utf-8').split() if x.strip())
populated = sorted(sb | known)

# Find gaps of 200..1000 within the populated span
gaps = []
for a, b in zip(populated, populated[1:]):
    g = b - a - 1
    if 200 <= g <= 1000:
        gaps.append((g, a, b))
gaps.sort(reverse=True)
print(f'mid-size (200..1000) gaps found: {len(gaps)}')
for g, a, b in gaps[:15]:
    print(f'  gap={g:4d} between {a} and {b}')

# Pick 100 fastnums: from top 10 gaps, take 10 evenly-spaced candidates each
picks = []
for g, a, b in gaps[:10]:
    step = max(1, g // 10)
    for i in range(1, 11):
        candidate = a + i * step
        if candidate < b and candidate not in populated:
            picks.append(candidate)
        if len([p for p in picks if a < p < b]) >= 10:
            break

picks = sorted(set(picks))[:100]
print(f'\npicked {len(picks)} candidate fastnums')
OUT.write_text('\n'.join(str(p) for p in picks), encoding='utf-8')
print(f'wrote {OUT}')
print('first 10:', picks[:10])
print('last 10:', picks[-10:])
