# cc357 (WP (ak), GO Danna 20.11): psycopg2 úr GLOBAL-Python inn í logbirting-venvið — og EKKERT annað.
#
# Hvers vegna: 20.11 05:40 UTC lokaði Smart App Control á libssl-3-x64-*.dll í psycopg2_binary.libs í
# D:\verdmat-is\logbirting\.venv (psycopg2-binary 2.9.13) -> verdmat-daily-logbirting rc 4. Global-tvíundin
# (notendasafn %APPDATA%\Python\Python314\site-packages, psycopg2-binary 2.9.12) er sú sem 02:30-verkin hlaða.
#
# Hvers vegna ekki einfaldari leið:
#   * C:\Python314\python.exe í stað venv: global vantar pdfplumber (og supabase) -> þyrfti pip install.
#   * include-system-site-packages = true + fjarlægja psycopg2-binary úr venv: site.py setur notendasafnið
#     FRAMAR en site-packages venvsins, svo requests/pypdfium2/... kæmu líka úr global (blandað umhverfi).
# Þessi skrá breytir engu í venv né global: hún hleðst aðeins þar sem PYTHONPATH vísar á þessa möppu
# (cc193_keyra_verk.ps1 setur það AÐEINS fyrir -Verk logbirting) og erfist í undirferli (keyra_dagleg.py ->
# python -m lb_scraper). Leitari á sys.meta_path svarar AÐEINS efsta nafninu `psycopg2`; undireiningar
# (psycopg2._psycopg, psycopg2.extras) fylgja __path__ pakkans og delvewheel-plástur global-pakkans bætir
# global psycopg2_binary.libs við DLL-leitina. Ekkert er hlaðið fyrr en psycopg2 er flutt inn (letilega).
# Finnist psycopg2 ekki í global fellur innflutningur á venv-útgáfuna eins og áður (engin ný villa).
import importlib.machinery
import os
import site
import sys

try:
    _SLOD = os.environ.get('CC357_PSYCOPG2_SLOD') or site.getusersitepackages()
except Exception:  # pragma: no cover — sitecustomize má aldrei fella ræsingu
    _SLOD = ''


class _Psycopg2UrGlobal:
    @classmethod
    def find_spec(cls, name, path=None, target=None):
        if name != 'psycopg2' or not _SLOD or not os.path.isdir(os.path.join(_SLOD, 'psycopg2')):
            return None
        return importlib.machinery.PathFinder.find_spec(name, [_SLOD])


if not any(getattr(f, '__name__', '') == '_Psycopg2UrGlobal' for f in sys.meta_path):
    sys.meta_path.insert(0, _Psycopg2UrGlobal)
