"""cc243 — söluhraði per nýbyggingarverkefni (f.1 gagnalag): mánaðarsölur, 90 d hraði, heildarkaupamerki.

Skilgreiningar = cc237 (D:\\_audit\\cc237_soluhradi\\SKIL_CC237.md §1, s1_grunnur.py/s2_ferlar.py), óbreyttar:
  lykill        = KAUPSAMNINGSDAGUR (UTGDAG) samningsins sem einingataflan valdi (þinglýsingardagur == sala_dags);
                  sala_dags í nybygging_einingar er þinglýsingardagur og er EKKI lykill
  teljari       = fyrsta útganga einingar frá byggjanda: nothaefar (stada seld, ONOTHAEFUR 0) og heildarkaup (cc228 D2′
                  + magnsala) ALLTAF sér
  pakki         = FAERSLUNUMER heildarkaupasamningsins
  óskipt fastnr.= utan mælingar (sala stakrar íbúðar kemst ekki í kaupskrá fyrr en eftir skiptingu) → „ómælanlegt",
                  aldrei 0; verkefni sem er AÐEINS óskipt fær engar mánaðarraðir og hradi_stada 'omaelanlegt'
  nefnari       = óseldar einingar í boði í UPPHAFI mánaðar, regla R1 = min(HMS-nálgun úr fastnúmeraröð, fyrsta
                  söluauglýsing, fyrsti kaupsamningur)
  fullnusta     = q11 (cc227/cc232): miðgildi þroskaðra mánaða T−15…T−4, nothæfir og ónothæfir íbúðasamningar landsins
                  sér; mánaðarraðir bera lægri töluna, bradabirgda = < 90 %
90 d gluggi     = endar á SÍÐASTA ÞROSKAÐA DEGI: síðasti kaupsamningsdagur d þar sem q11-fullnusta dagsins (sömu
                  viðmiðunarmánuðir, leyfð töf = data_through − d) er ≥ 90 % bæði á nothæfum og ónothæfum
hraði           = sölur í glugga / 3 (sölur á mánuði), nothæfar / heildarkaup / samtals
man_i_uppselt   = óseldar við gluggalok / nothæfur hraði — aðeins ef staða 'maelt', ≥ 5 NOTHÆFAR sölur í glugga,
                  ≥ 5 óseldar og ekkert óskipt fastnr. í verkefninu (óseldur lager á óskiptu númeri er óþekktur);
                  heildarkaup eru kekkjótt (einn pakki) og fara ekki í spána
hradi_stada     = 'omaelanlegt' (engin skipt eining, eða skiptar uppseldar en óskipt eftir) | 'uppselt' |
                  'faar_solur' (< 5 sölur samtals í glugga) | 'maelt'
Engir sentinlar: ómælanlegt = NULL + staða.

Hreint fall (engin DB-tenging): reikna_soluhradi(E, K, L) — E = einingatafla smiðsins, K = kaupskrá (lesa_kaupskra),
L = söluauglýsingar á fastnr. eininganna (allir flokkar; fastnum, listed_at, first_seen_at).
"""
from pathlib import Path

import numpy as np
import pandas as pd

KAUPSKRA = Path(r"D:\kaupskra.csv")
IBUD_TEG = {"Fjölbýli", "Einbýli", "Sérbýli"}
SALA_FRA = pd.Timestamp("2021-01-01")
HMS_FRA = 2_500_000            # fastnúmer undir þessu fá enga HMS-nálgun (eldri númer)
HMS_BIL, HMS_MIN, HMS_Q = 2000, 20, 0.05
FULL_MORK = 0.90
GLUGGI_D = 90
MIN_SOLUR = 5
MIN_OSELDAR = 5
STODUR = ("maelt", "faar_solur", "omaelanlegt", "uppselt")


def lesa_kaupskra(slod=KAUPSKRA):
    K = pd.read_csv(slod, sep=";", encoding="latin-1", dtype=str,
                    usecols=["FAERSLUNUMER", "FASTNUM", "UTGDAG", "THINGLYSTDAGS", "ONOTHAEFUR_SAMNINGUR", "TEGUND"])
    return pd.DataFrame(dict(
        faerslunumer=K.FAERSLUNUMER.astype("int64"), fastnum=K.FASTNUM.astype("int64"),
        utg=pd.to_datetime(K.UTGDAG.str[:10]), thgl=pd.to_datetime(K.THINGLYSTDAGS.str[:19]),
        onoth=K.ONOTHAEFUR_SAMNINGUR.astype(int), ibud=K.TEGUND.str.strip().isin(IBUD_TEG)))


def _t_hms(K):
    """HMS-skráning nálguð úr fastnúmeraröð (cc237 s1): 5. hundraðsmark fyrsta kaupsamningsdags meðal [f, f+2000)."""
    fyrsti = K.groupby("fastnum").utg.min()
    fy = fyrsti[fyrsti.index >= HMS_FRA]
    idx, vals = fy.index.values, fy.values.astype("datetime64[ns]").astype("int64")

    def f(n):
        if n < HMS_FRA:
            return pd.NaT
        a, b = np.searchsorted(idx, [n, n + HMS_BIL])
        if b - a < HMS_MIN:
            return pd.NaT
        return pd.Timestamp(int(np.quantile(vals[a:b], HMS_Q)), unit="ns").normalize()
    return fyrsti, f


def _samningar(K):
    """Einn hlutur per FAERSLUNUMER (íbúðasamningar): utg, síðasta þinglýsing, ónothæfur."""
    Kc = K[K.ibud].groupby("faerslunumer").agg(utg=("utg", "first"), thgl=("thgl", "max"), onoth=("onoth", "max"))
    Kc["man"] = Kc.utg.dt.to_period("M")
    Kc["tof"] = (Kc.thgl.dt.normalize() - Kc.utg).dt.days
    return Kc


def fullnusta_manadar(Kc, data_through, manudir):
    """q11 per kaupsamningsmánuð T (s1_grunnur.py): (nothæfar, ónothæfar)."""
    hopar = {on: {m: g for m, g in Kc[Kc.onoth == on].groupby("man")} for on in (0, 1)}
    ut = {}
    for T in manudir:
        off = data_through + pd.Timedelta(days=1) - (T + 1).start_time
        r = []
        for on in (0, 1):
            fr = []
            for M in pd.period_range(T - 15, T - 4, freq="M"):
                g = hopar[on].get(M)
                fr.append(float((g.thgl <= (M + 1).start_time + off).mean()) if g is not None and len(g) else np.nan)
            r.append(float(np.nanmedian(fr)))
        ut[T] = tuple(r)
    return ut


def sidasti_throskadi_dagur(Kc, data_through, utg_max):
    """Síðasti kaupsamningsdagur d ≤ utg_max með q11-fullnustu dagsins ≥ FULL_MORK á nothæfum OG ónothæfum.
    Dagsfullnusta = miðgildi yfir M ∈ [T(d)−15, T(d)−4] af hlutfalli samninga í M með töf ≤ data_through − d."""
    hopar = {on: {m: g.tof.values for m, g in Kc[Kc.onoth == on].groupby("man")} for on in (0, 1)}
    d = utg_max
    while True:
        T = d.to_period("M")
        leyft = (data_through - d).days
        f = [float(np.median([(hopar[on][M] <= leyft).mean() for M in pd.period_range(T - 15, T - 4, freq="M")
                              if M in hopar[on]])) for on in (0, 1)]
        if min(f) >= FULL_MORK:
            return d, f
        d -= pd.Timedelta(days=1)


def reikna_soluhradi(E, K, L):
    """Skilar (S mánaðartafla, H dálkar per verkefni, R skýrsla)."""
    E = E.copy()
    E["sd"] = pd.to_datetime(E.sala_dags)
    data_through = K.thgl.max().normalize()
    utg_max = K.utg.max()

    # ---- útgönguatburður: samningurinn sem einingataflan valdi (þinglýsingardagur == sala_dags)
    Ke = K[K.fastnum.isin(E.fastnum)].assign(thd=lambda x: x.thgl.dt.normalize())
    sel = E.stada.isin(["seld", "heildarkaup", "magnsala"])
    m = E.loc[sel, ["fastnum", "stada", "sd"]].merge(Ke, on="fastnum")
    m = m[(m.thd == m.sd) & ((m.stada != "seld") | (m.onoth == 0)) & ((m.stada != "heildarkaup") | (m.onoth == 1))]
    m = m.sort_values(["fastnum", "utg", "faerslunumer"])
    sala = m.groupby("fastnum").agg(t_sala=("utg", "first"), pakki=("faerslunumer", "first"))
    n_samsv = int(E.loc[sel, "fastnum"].isin(sala.index).sum())
    E = E.merge(sala, left_on="fastnum", right_index=True, how="left")
    E["sala_teg"] = E.stada.map({"seld": "nothaef", "heildarkaup": "heildarkaup", "magnsala": "heildarkaup"})

    # ---- í boði (R1)
    fyrsti, f_hms = _t_hms(K)
    Lt = pd.to_datetime(L[["listed_at", "first_seen_at"]].min(axis=1), utc=True)
    Lt = Lt.dt.tz_convert("Atlantic/Reykjavik").dt.tz_localize(None).dt.normalize()
    E["t_augl"] = E.fastnum.map(Lt.groupby(L.fastnum.values).min())
    E["t_samn"] = E.fastnum.map(fyrsti)
    E["t_hms"] = E.fastnum.map(f_hms)
    E["R1"] = E[["t_hms", "t_augl", "t_samn"]].min(axis=1)
    E["oskipt"] = E.heildareining.astype(bool)

    # ---- fullnusta og gluggi
    Kc = _samningar(K)
    A = E[~E.oskipt]
    fra = min(A.t_sala.min(), max(A.R1.min(), SALA_FRA)).to_period("M")
    MAN = pd.period_range(fra, data_through.to_period("M"), freq="M")
    FM = fullnusta_manadar(Kc, data_through, list(MAN))      # mæld fyrir ALLA mánuði (engin 1,0-forsenda)
    lok, f_lok = sidasti_throskadi_dagur(Kc, data_through, utg_max)
    upph = lok - pd.Timedelta(days=GLUGGI_D - 1)

    # ---- mánaðartafla per verkefni (aðeins skiptar einingar; vigrað: óseld í upphafi mánaðar M ⇔ R1 ≤ 1. dagur M
    #      ∧ (engin sala ∨ sala ≥ 1. dagur M) → +1 við fyrsta mánaðarupphaf ≥ R1, −1 við fyrsta mánaðarupphaf > sölu)
    byrjun = MAN.start_time.values
    nm = len(MAN)
    vids = sorted(A.verkefni_id.unique())
    vi = pd.Series(np.arange(len(vids)), index=vids)
    a_v = A.verkefni_id.map(vi).values
    inn = np.where(A.R1.notna(), np.searchsorted(byrjun, A.R1.values.astype("datetime64[ns]"), side="left"), nm)
    ut_ = np.where(A.t_sala.notna(), np.searchsorted(byrjun, A.t_sala.values.astype("datetime64[ns]"), side="right"), nm)
    ok = inn < ut_
    D = np.zeros((len(vids), nm + 1), dtype=np.int64)
    np.add.at(D, (a_v[ok], inn[ok]), 1)
    np.add.at(D, (a_v[ok], ut_[ok]), -1)
    OS = np.cumsum(D, axis=1)[:, :nm]
    sm = np.where(A.t_sala.notna(), np.searchsorted(byrjun, A.t_sala.values.astype("datetime64[ns]"), side="right") - 1, -1)
    CN, CH = np.zeros((len(vids), nm), dtype=np.int64), np.zeros((len(vids), nm), dtype=np.int64)
    sn = (sm >= 0) & (A.sala_teg.values == "nothaef")
    sh = (sm >= 0) & (A.sala_teg.values == "heildarkaup")
    np.add.at(CN, (a_v[sn], sm[sn]), 1)
    np.add.at(CH, (a_v[sh], sm[sh]), 1)
    # fyrsti mánuður verkefnis = fyrsta sala, eða fyrsta „í boði" (ekki fyrr en SALA_FRA), hvort sem fyrr er
    r1_m = np.where(A.R1.notna(), np.searchsorted(byrjun, np.maximum(A.R1.values.astype("datetime64[ns]"),
                                                                       np.datetime64(SALA_FRA, "ns")), side="right") - 1, nm)
    f0 = pd.Series(np.minimum(np.where(sm >= 0, sm, nm), r1_m)).groupby(a_v).min().reindex(range(len(vids)), fill_value=nm)
    full = np.round(np.array([min(FM[M]) for M in MAN]), 4)   # flaggið les SÖMU (námunduðu) tölu og dálkurinn
    vv, mm = np.nonzero(np.arange(nm)[None, :] >= f0.values[:, None])   # verkefni án sönnunar og sölu fá engar raðir
    S = pd.DataFrame(dict(verkefni_id=np.array(vids, dtype=object)[vv], manudur=MAN.start_time.date[mm],
                          nothaefar=CN[vv, mm], heildarkaup=CH[vv, mm], oseldar_upphafi=OS[vv, mm],
                          fullnusta=full[mm], bradabirgda=full[mm] < FULL_MORK))
    S["uppsafnad_nothaefar"] = S.groupby("verkefni_id").nothaefar.cumsum()
    S["uppsafnad_heildarkaup"] = S.groupby("verkefni_id").heildarkaup.cumsum()

    # ---- per verkefni
    H = []
    for vid, g in E.groupby("verkefni_id"):
        a = g[~g.oskipt]
        n_osk = int(g.oskipt.sum())
        hk = g[g.stada == "heildarkaup"]   # merkið = D2′ eingöngu (= n_heildarkaup); magnsala er nothæfur samningur
        pk = hk.groupby("pakki").n_undireiningar.sum()
        r = dict(verkefni_id=vid,
                 heildarkaup_fyrst=hk.t_sala.min().date() if len(hk) else None,
                 heildarkaup_sidast=hk.t_sala.max().date() if len(hk) else None,
                 heildarkaup_staersti_pakki=int(pk.max()) if len(pk) else None,
                 heildarkaup_n_pakkar=int(len(pk)) if len(pk) else None,
                 hradi_glugga_fra=upph.date(), hradi_glugga_til=lok.date())
        ig = a.t_sala.between(upph, lok)
        n_n = int((ig & (a.sala_teg == "nothaef")).sum())
        n_h = int((ig & (a.sala_teg == "heildarkaup")).sum())
        osl = int((a.t_sala.isna() | (a.t_sala > lok)).sum())
        if len(a) == 0 or (osl == 0 and n_osk > 0):
            stada = "omaelanlegt"
        elif osl == 0:
            stada = "uppselt"
        elif n_n + n_h < MIN_SOLUR:
            stada = "faar_solur"
        else:
            stada = "maelt"
        if stada == "omaelanlegt":
            r.update(hradi_90d_nothaefar=None, hradi_90d_heildarkaup=None, hradi_90d_samtals=None,
                     hradi_oseldar=None, man_i_uppselt=None)
        else:
            hn, hh = n_n * 30 / GLUGGI_D, n_h * 30 / GLUGGI_D
            mu = (round(osl / hn, 1) if stada == "maelt" and n_n >= MIN_SOLUR and osl >= MIN_OSELDAR and n_osk == 0
                  else None)
            r.update(hradi_90d_nothaefar=round(hn, 2), hradi_90d_heildarkaup=round(hh, 2),
                     hradi_90d_samtals=round(hn + hh, 2), hradi_oseldar=osl, man_i_uppselt=mu)
        r["hradi_stada"] = stada
        r["_n_glugga_noth"], r["_n_glugga_heild"], r["_n_oskipt"] = n_n, n_h, n_osk
        H.append(r)
    H = pd.DataFrame(H)
    R = dict(data_through=data_through.date(), utg_max=utg_max.date(), gluggi=(upph.date(), lok.date()),
             fullnusta_lok=tuple(round(x, 4) for x in f_lok), n_sala=int(sel.sum()), n_samsvarar=n_samsv,
             n_rada=len(S), n_verkefni_rada=int(S.verkefni_id.nunique()), E=E)
    return S, H, R


SCOLS = ["verkefni_id", "manudur", "nothaefar", "heildarkaup", "uppsafnad_nothaefar", "uppsafnad_heildarkaup",
         "oseldar_upphafi", "fullnusta", "bradabirgda"]
HCOLS = ["hradi_90d_nothaefar", "hradi_90d_heildarkaup", "hradi_90d_samtals", "hradi_glugga_fra", "hradi_glugga_til",
         "hradi_oseldar", "man_i_uppselt", "hradi_stada", "heildarkaup_fyrst", "heildarkaup_sidast",
         "heildarkaup_staersti_pakki", "heildarkaup_n_pakkar"]
