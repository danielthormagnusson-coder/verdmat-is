"""Inventory all fields HMS returns for a property — to compare against
what Supabase properties already has."""
from curl_cffi import requests
import json, time

# Pick 5 diverse fastnums from the stikkprufa hits + 1 well-known urban property
SAMPLES = [
    (2000044, 'Fiskislóð 77, Rvk — atvinnuhúsnæði (Supabase min)'),
    (2541714, 'Ásavegur 7B, Vestmannaeyjar — íbúð (Supabase max)'),
    (2138438, 'Móberg 1, Húnabyggð — fjárhús (gap hit, sveit)'),
    (2338352, 'Hávegur 1, Fjallabyggð — óbyggð lóð (gap hit, lóð)'),
    (2517176, 'Stakkahlíð 5, Reykjavík — íbúð á hæð (gap hit, blokk)'),
]
API = 'https://hms.is/api/fasteignaskra/fasteign'

print('=== HMS field inventory across 5 diverse samples ===\n')
for nr, label in SAMPLES:
    print(f'--- {nr}: {label} ---')
    r = requests.get(f'{API}/{nr}', impersonate='chrome120', timeout=15)
    d = r.json().get('fasteignData', {})
    print(json.dumps(d, indent=2, ensure_ascii=False))
    print()
    time.sleep(1.5)
