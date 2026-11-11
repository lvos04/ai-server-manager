#!/usr/bin/env python3
"""Dekkingscontrole van het uitvoeringsplan.

Gebruik (vanuit elke map; alle paden zijn relatief aan de map waarin dit script staat):

    python3 dekking.py               dekking + vormcontroles; schrijft DEKKING.tsv
    python3 dekking.py --voortgang   idem, en controleert bovendien VOORTGANG.md
    python3 dekking.py --streng      vormfouten (ontbrekende velden, N5 zonder "Winst:") ook laten tellen voor de exitcode

Leest: ALLE_IDS.txt, STAPPEN_*.md, AGENTEN.md, VALKUILEN.md, POORTEN.md (en met --voortgang VOORTGANG.md).
Schrijft: alleen DEKKING.tsv (kolommen ID, categorie, waar, bestand).

Categorieen per ID uit ALLE_IDS.txt:
    stap      het ID staat in de regel "Werkpakketten en tests" van een stap (### S-...), of een rij van een
              tabel onder een kop "Dekking" noemt voor dit ID een bestaande stap
    nas       geen stap, wel een NAS-onderdeel (### N-...) dat het ID in zijn regel "Rijen" noemt, of een
              Dekking-rij die het ID naar de echte NAS verwijst
    gebouwd   geen stap; een Dekking-rij zegt dat het al gebouwd is
    besluit   geen stap; het ID is een besluit (Dnn) of een Dekking-rij wacht op een besluit
    ONGEDEKT  niets van het bovenstaande (ook: alleen een verwijzing "zie STAPPEN_..." zonder stap)

Exitcode 1 bij een ONGEDEKT ID of een kapotte verwijzing (Vooraf naar een onbekende stap, dubbel stap-ID,
onbekende rol, V-nnn of P-<naam>), en met --voortgang bij een verschil tussen de STAPPEN-bestanden en VOORTGANG.md.
Alleen standaardbibliotheek.
"""

import argparse
import glob
import os
import re
import sys
from collections import OrderedDict, defaultdict

HIER = os.path.dirname(os.path.abspath(__file__))

REPOS = [
    "ai-server-manager", "home-control-hub", "appstore-en-fork", "jelly-leon-platform",
    "zoeken-en-persoonlijke-ai", "media-guard-ultimate", "media-source-optimizer", "my_house",
    "jelly-leon-web", "jelly-leon-clients", "jelly-leon",
]

# ---------------------------------------------------------------------------------------------
# Herkennen van ID's en stap-ID's (met reeksen als "EX15...EX21", "I02-02-05...08", "B10-002 t/m B10-006",
# "I26-26-01, -03", "JLT-68/64/65" en "B03-071, 072, 073").
# ---------------------------------------------------------------------------------------------

ID_RE = re.compile(
    r"(?<![A-Za-z0-9.\-])"
    r"(APP-\d{2}|B\d{2}-\d{3}|D\d{2}|EX\d{2}|I\d{2}-\d{2}-\d{2}|JLT-\d{2}|C1\.3-[A-Z]+-\d{2})"
    r"(?![0-9A-Za-z])"
)
STAP_RE = re.compile(r"(?<![A-Za-z0-9\-])([SN]-[A-Z][A-Z0-9]*-\d+[a-z]?)(?![0-9A-Za-z])")
ID_KERN_RE = re.compile(
    r"(APP-\d{2}|B\d{2}-\d{3}|D\d{2}|EX\d{2}|I\d{2}-\d{2}-\d{2}|JLT-\d{2}|C1\.3-[A-Z]+-\d{2})(?![0-9A-Za-z])"
)
STAP_KERN_RE = re.compile(r"([SN]-[A-Z][A-Z0-9]*-\d+[a-z]?)(?![0-9A-Za-z])")
RANGE_RE = re.compile(r"\s*(?:\.\.\.|…|t/m|tot en met)\s*")
ROL_RE = re.compile(r"(?<![A-Za-z0-9\-])([AR]-[A-Z]+(?:-[A-Z]+)*)(?![A-Za-z0-9])")
V_RE = re.compile(r"(?<![A-Za-z0-9\-])(V-\d{3})(?![0-9])")
P_RE = re.compile(r"(?<![A-Za-z0-9_\-<])(P-[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*)")


def id_soort(i):
    """Familie van een ID, voor reeksen tussen twee ID's."""
    if i.startswith("C1.3-"):
        return "C1.3-" + i.split("-")[1]
    m = re.match(r"([A-Z]+)", i)
    return m.group(1) if m else i


def splits_laatste(i):
    m = re.match(r"^(.*?)(\d+)([a-z]?)$", i)
    return (m.group(1), m.group(2), m.group(3)) if m else (i, "", "")


def vul_reeks(begin, eind, bekend):
    """Alle ID's van begin tot en met eind. Zelfde voorvoegsel: numeriek; anders: de bekende ID's
    van dezelfde familie die er alfabetisch tussen liggen (de ID's zijn met nullen opgevuld)."""
    pb, nb, _ = splits_laatste(begin)
    pe, ne, _ = splits_laatste(eind)
    if pb == pe and nb and ne:
        a, b = int(nb), int(ne)
        if b < a or b - a > 500:
            return [begin, eind]
        w = len(nb)
        return [pb + str(n).zfill(w) for n in range(a, b + 1)]
    if bekend and id_soort(begin) == id_soort(eind) and begin < eind:
        tussen = sorted(x for x in bekend if id_soort(x) == id_soort(begin) and begin <= x <= eind)
        return tussen or [begin, eind]
    return [begin, eind]


def vul_stapreeks(begin, eind, stappen):
    """Stapreeks: alleen bestaande stappen met hetzelfde voorvoegsel en een nummer ertussen."""
    pb, nb, _ = splits_laatste(begin)
    pe, ne, _ = splits_laatste(eind)
    uit = [begin, eind]
    if pb == pe and nb and ne:
        a, b = int(nb), int(ne)
        for s in stappen:
            ps, ns, _ = splits_laatste(s)
            if ps == pb and ns and a <= int(ns) <= b:
                uit.append(s)
    return uit


def haal_ids(tekst, bekend=None):
    """Alle ID's in de tekst, met reeksen uitgevouwen. Volgorde blijft behouden, zonder dubbelen."""
    uit = []
    for m in ID_RE.finditer(tekst):
        laatste = m.group(1)
        uit.append(laatste)
        pos = m.end()
        while True:
            r = RANGE_RE.match(tekst, pos)
            if r:
                vol = ID_KERN_RE.match(tekst, r.end())
                if vol and id_soort(vol.group(1)) == id_soort(laatste):
                    uit.extend(vul_reeks(laatste, vol.group(1), bekend))
                    laatste, pos = vol.group(1), vol.end()
                    continue
                kort = re.match(r"-?(\d+)(?![0-9A-Za-z])", tekst[r.end():])
                if kort:
                    p, n, _ = splits_laatste(laatste)
                    eind = p + kort.group(1).zfill(len(n))
                    uit.extend(vul_reeks(laatste, eind, bekend))
                    laatste, pos = eind, r.end() + kort.end()
                    continue
            k = re.match(r"\s*,\s*-(\d+)(?![0-9A-Za-z])|/(\d+)(?![0-9A-Za-z])", tekst[pos:])
            if k:
                p, n, _ = splits_laatste(laatste)
                nieuw = p + (k.group(1) or k.group(2)).zfill(len(n))
                uit.append(nieuw)
                laatste, pos = nieuw, pos + k.end()
                continue
            p, n, _ = splits_laatste(laatste)
            if len(n) == 3:
                k = re.match(r"\s*,\s*(\d{3})(?![0-9A-Za-z\-])", tekst[pos:])
                if k:
                    nieuw = p + k.group(1)
                    uit.append(nieuw)
                    laatste, pos = nieuw, pos + k.end()
                    continue
            break
    return list(OrderedDict.fromkeys(uit))


def haal_stappen(tekst, stappen=()):
    """Alle stap- en onderdeel-ID's in de tekst; reeksen ("S-P6-14...16", "S-P2-010 t/m S-P2-060",
    "S-P6-01...06, -10...22") worden uitgevouwen tot de bestaande stappen ertussen."""
    uit = []
    for m in STAP_RE.finditer(tekst):
        laatste = m.group(1)
        uit.append(laatste)
        pos = m.end()
        while True:
            r = RANGE_RE.match(tekst, pos)
            if r:
                vol = STAP_KERN_RE.match(tekst, r.end())
                if vol:
                    uit.extend(vul_stapreeks(laatste, vol.group(1), stappen))
                    laatste, pos = vol.group(1), vol.end()
                    continue
                kort = re.match(r"-?(\d+)(?![0-9A-Za-z])", tekst[r.end():])
                if kort:
                    p, n, _ = splits_laatste(laatste)
                    eind = p + kort.group(1).zfill(len(n))
                    uit.extend(vul_stapreeks(laatste, eind, stappen))
                    laatste, pos = eind, r.end() + kort.end()
                    continue
            k = re.match(r"\s*,\s*-(\d+)(?![0-9A-Za-z])", tekst[pos:])
            if k:
                p, n, _ = splits_laatste(laatste)
                nieuw = p + k.group(1).zfill(len(n))
                uit.append(nieuw)
                laatste, pos = nieuw, pos + k.end()
                continue
            break
    return list(OrderedDict.fromkeys(uit))


# ---------------------------------------------------------------------------------------------
# Lezen van de STAPPEN-bestanden
# ---------------------------------------------------------------------------------------------

KOP_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
STAPKOP_RE = re.compile(r"^###\s+([SN]-[A-Z][A-Z0-9]*-\d+[a-z]?)\s*(?:[-–—:]\s*(.*?))?\s*$")
VELD_RE = re.compile(r"^- \*\*([^*]+?)\*\*\s*(.*)$")


class Stap:
    def __init__(self, sid, titel, bestand, regelnr, positie):
        self.id = sid
        self.titel = titel or ""
        self.bestand = bestand
        self.regelnr = regelnr
        self.positie = positie
        self.soort = "stap" if sid.startswith("S-") else "onderdeel"
        self.velden = OrderedDict()   # label zonder dubbele punt -> tekst (met vervolgregels)
        self.kopregel = ""            # de regel "- **Repo:** ... | **Moeilijkheid:** ... | **Zwaar:** ..."

    def veld(self, *namen):
        for n in namen:
            if n in self.velden:
                return self.velden[n]
        return None

    def kopwaarde(self, sleutel):
        m = re.search(r"\*\*" + re.escape(sleutel) + r":\*\*\s*([^|]*)", self.kopregel)
        return m.group(1).strip() if m else None


def normaliseer_label(label):
    label = label.strip()
    if label.endswith(":"):
        label = label[:-1].strip()
    return label


def lees_regels(pad):
    """Regels van een bestand, met per regel de vlag 'in een codeblok'."""
    with open(pad, encoding="utf-8") as fh:
        regels = fh.read().split("\n")
    in_code = False
    uit = []
    for r in regels:
        if r.lstrip().startswith("```"):
            uit.append((r, True))
            in_code = not in_code
            continue
        uit.append((r, in_code))
    return uit


def lees_stapbestand(pad, positie_start=0):
    """Geeft (stappen, dekkingsrijen, overige_blokken) van een STAPPEN-bestand.
    dekkingsrijen: lijst van (cellen, kop) uit tabellen onder een kop met het woord "Dekking".
    overige_blokken: (kop, regelnr, velden) van koppen die geen stap zijn maar wel velden hebben (bv. F.1)."""
    naam = os.path.basename(pad)
    regels = lees_regels(pad)
    stappen = []
    dekking = []
    blokken = []
    huidig = None
    blok = None
    laatste_veld = None
    dekking_niveau = None
    dekking_kop = ""
    pos = positie_start
    for nr, (r, in_code) in enumerate(regels, 1):
        kop = KOP_RE.match(r) if not in_code else None
        if kop:
            niveau = len(kop.group(1))
            tekst = kop.group(2)
            if dekking_niveau is not None and niveau <= dekking_niveau:
                dekking_niveau = None
            sk = STAPKOP_RE.match(r)
            if sk:
                pos += 1
                huidig = Stap(sk.group(1), sk.group(2), naam, nr, pos)
                stappen.append(huidig)
                blok = None
                laatste_veld = None
                continue
            if niveau <= 3:
                huidig = None
                laatste_veld = None
                blok = {"kop": tekst, "regelnr": nr, "velden": OrderedDict(), "bestand": naam}
                blokken.append(blok)
            if re.search(r"\bDekking\b", tekst) and dekking_niveau is None:
                dekking_niveau = niveau
                dekking_kop = tekst
            continue
        doel = huidig.velden if huidig is not None else (blok["velden"] if blok is not None else None)
        v = VELD_RE.match(r) if not in_code else None
        if v and doel is not None:
            label = normaliseer_label(v.group(1))
            waarde = v.group(2)
            if huidig is not None and label == "Repo" and not huidig.kopregel:
                huidig.kopregel = r
            if label not in doel:
                doel[label] = waarde
                laatste_veld = label
            else:
                laatste_veld = None
            continue
        if doel is not None and laatste_veld is not None and r.strip() and not r.startswith("|"):
            if r.startswith("- **"):
                laatste_veld = None
            else:
                doel[laatste_veld] += "\n" + r
        elif not r.strip():
            pass
        if dekking_niveau is not None and r.lstrip().startswith("|") and not in_code:
            cellen = [c.strip() for c in r.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cellen if c):
                continue
            dekking.append((cellen, dekking_kop, naam, nr))
    blokken = [b for b in blokken if b["velden"]]
    return stappen, dekking, blokken


def stapbestanden():
    return sorted(glob.glob(os.path.join(HIER, "STAPPEN_*.md")))


def lees_alles():
    alle_stappen = []
    alle_dekking = []
    alle_blokken = []
    pos = 0
    for pad in stapbestanden():
        s, d, b = lees_stapbestand(pad, pos)
        pos += len(s)
        alle_stappen.extend(s)
        alle_dekking.extend(d)
        alle_blokken.extend(b)
    return alle_stappen, alle_dekking, alle_blokken


def lees_alle_ids():
    pad = os.path.join(HIER, "ALLE_IDS.txt")
    with open(pad, encoding="utf-8") as fh:
        return [r.strip() for r in fh if r.strip()]


def kopnamen(pad, patroon):
    if not os.path.exists(pad):
        return None
    namen = set()
    for r, in_code in lees_regels(pad):
        if in_code:
            continue
        m = re.match(patroon, r)
        if m:
            namen.add(m.group(1))
    return namen


def is_tabelkop_dekking(cellen):
    eerste = cellen[0].strip("`* ").lower() if cellen else ""
    return eerste in ("id", "id-reeks", "nr", "id-reeks of onderwerp")


# ---------------------------------------------------------------------------------------------
# Hulpfuncties die ook maak_voortgang.py gebruikt
# ---------------------------------------------------------------------------------------------

N5_RE = re.compile(r"(?<![\w\-])N5(?![\w\-])")


def heeft_n5(niveau):
    """True als de regel "Niveau" een inzet op N5 noemt (niet: "N5-review ... in S-...", "geen N5")."""
    if not niveau:
        return False
    for m in N5_RE.finditer(niveau):
        voor = niveau[max(0, m.start() - 14):m.start()].lower()
        if re.search(r"(geen|niet|nooit|zonder|dan)\s+(op\s+)?$", voor):
            continue
        return True
    return False


def rollen(tekst):
    return list(OrderedDict.fromkeys(ROL_RE.findall(tekst or "")))


# ---------------------------------------------------------------------------------------------
# Hoofdprogramma
# ---------------------------------------------------------------------------------------------

NAS_RE = re.compile(r"N-P6-\d+|echte NAS|\bNAS\b|echte hardware|echt(e)? account|echte omgeving|DEEL B", re.I)
BESLUIT_RE = re.compile(r"\bBG-\d+|\bBLOK-\d+|besluit|\bZ-\d+|\bT-\d+|wacht op", re.I)
GEBOUWD_RE = re.compile(r"al gebouwd|gebouwd in P\d|reeds gebouwd|is gebouwd|al gedaan|al klaar", re.I)
VERWIJS_RE = re.compile(r"zie STAPPEN_|niet in dit bestand|niet in P\d|hoort (in|bij) P\d|andere fase", re.I)


def kort(t, n=140):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[: n - 3] + "..."


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dekkingscontrole van het uitvoeringsplan (schrijft DEKKING.tsv).")
    ap.add_argument("--voortgang", action="store_true", help="controleer ook VOORTGANG.md tegen de STAPPEN-bestanden")
    ap.add_argument("--streng", action="store_true", help="vormfouten tellen ook voor de exitcode")
    args = ap.parse_args(argv)

    fout = False
    alle_ids = lees_alle_ids()
    bekend = set(alle_ids)
    stappen, dekking, blokken = lees_alles()
    bestanden = [os.path.basename(p) for p in stapbestanden()]

    stap_ids = [s.id for s in stappen]
    per_id = defaultdict(list)
    for s in stappen:
        per_id[s.id].append(s)
    bestaand = set(stap_ids)
    alleen_s = [s for s in stappen if s.soort == "stap"]
    s_ids = set(s.id for s in alleen_s)

    # 1. ID's uit "Werkpakketten en tests" (stappen) en "Rijen" (NAS-onderdelen)
    werk = defaultdict(list)      # ID -> [stap-ID's] via Werkpakketten
    nasrij = defaultdict(list)    # ID -> [onderdeel-ID's] via Rijen
    bestand_van = defaultdict(set)
    for s in stappen:
        if s.soort == "stap":
            for i in haal_ids(s.veld("Werkpakketten en tests") or "", bekend):
                werk[i].append(s.id)
                bestand_van[i].add(s.bestand)
        else:
            for i in haal_ids(s.veld("Rijen") or "", bekend):
                nasrij[i].append(s.id)
                bestand_van[i].add(s.bestand)

    # 2. Dekking-tabellen
    dek_stap = defaultdict(list)
    dek_reden = defaultdict(list)
    for cellen, kop, bestand, nr in dekking:
        if not cellen or is_tabelkop_dekking(cellen):
            continue
        ids = haal_ids(cellen[0], bekend)
        if not ids:
            continue
        rest = " | ".join(cellen[1:])
        refs = [x for x in haal_stappen(rest, stap_ids) if x in s_ids]
        for i in ids:
            bestand_van[i].add(bestand)
            if refs:
                dek_stap[i].extend(refs)
            else:
                dek_reden[i].append((rest, bestand))

    # 3. Categorie per ID
    rijen = []
    telling = OrderedDict((k, 0) for k in ("stap", "gebouwd", "nas", "besluit", "ONGEDEKT"))
    ongedekt = []
    for i in alle_ids:
        stapset = list(OrderedDict.fromkeys(werk.get(i, []) + dek_stap.get(i, [])))
        stapset.sort(key=lambda x: per_id[x][0].positie if x in per_id else 10**9)
        if stapset:
            cat, waar = "stap", ", ".join(stapset)
        elif i in nasrij and re.fullmatch(r"D\d{2}", i):
            cat, waar = "besluit", ("gegeven of besluit van de gebruiker; vastleggen in NAS-onderdeel "
                                    + ", ".join(OrderedDict.fromkeys(nasrij[i])))
        elif i in nasrij:
            cat, waar = "nas", ("geen bouwstap; alleen NAS-onderdeel "
                                + ", ".join(OrderedDict.fromkeys(nasrij[i])) + " (regel Rijen)")
        else:
            redenen = dek_reden.get(i, [])
            echte = [(t, b) for t, b in redenen if not VERWIJS_RE.search(t) or GEBOUWD_RE.search(t)]
            cat, waar = "ONGEDEKT", "geen stap, geen NAS-onderdeel, geen Dekking-rij"
            if re.fullmatch(r"D\d{2}", i) and redenen:
                cat, waar = "besluit", kort(redenen[0][0])
            elif echte:
                t = echte[0][0]
                if GEBOUWD_RE.search(t):
                    cat = "gebouwd"
                elif NAS_RE.search(t):
                    cat = "nas"
                elif BESLUIT_RE.search(t):
                    cat = "besluit"
                else:
                    cat = "ONGEDEKT"
                waar = kort(t)
                if cat == "ONGEDEKT":
                    waar = "Dekking-rij zonder stap en zonder herkenbare reden: " + kort(t)
            elif redenen:
                waar = "alleen een verwijzing naar een ander bestand: " + kort(redenen[0][0])
        if cat == "ONGEDEKT":
            ongedekt.append((i, waar))
        telling[cat] += 1
        rijen.append((i, cat, waar, ", ".join(sorted(bestand_van.get(i, [])))))

    uitpad = os.path.join(HIER, "DEKKING.tsv")
    with open(uitpad, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("ID\tcategorie\twaar\tbestand\n")
        for r in rijen:
            fh.write("\t".join(x.replace("\t", " ").replace("\n", " ") for x in r) + "\n")

    print("== Dekking (DEKKING.tsv geschreven)")
    print("Stapbestanden: %s" % ", ".join(bestanden))
    print("Stappen (### S-): %d; NAS-onderdelen (### N-): %d" % (len(alleen_s), len(stappen) - len(alleen_s)))
    print("ID's in ALLE_IDS.txt: %d" % len(alle_ids))
    for k, v in telling.items():
        print("  %-9s %d" % (k, v))
    print()
    print("== ONGEDEKTE ID's (%d)" % len(ongedekt))
    for i, w in ongedekt:
        print("  %s  - %s" % (i, w))
    if ongedekt:
        fout = True

    # Werkpakketten (Bnn-nnn) zonder bouwstap: ter controle (kan terecht zijn als ze in P0/P1 al gebouwd zijn)
    alleen_nas = [r[0] for r in rijen if r[1] == "nas" and re.fullmatch(r"B\d{2}-\d{3}", r[0])]
    print()
    print("== Ter controle: werkpakketten (Bnn-nnn) zonder bouwstap, alleen in een NAS-onderdeel: %d" % len(alleen_nas))
    if alleen_nas:
        print("  " + ", ".join(alleen_nas))
        print("  (terecht als het werkpakket in P0/P1 al gebouwd is; anders ontbreekt er een bouwstap)")

    # ID's buiten ALLE_IDS (contractpunten): alleen ter informatie
    extra = set()
    for i in list(werk) + list(dek_stap) + list(dek_reden):
        if i not in bekend:
            extra.add(i)
    extra_zonder = sorted(i for i in extra if not werk.get(i) and not dek_stap.get(i))
    print()
    print("== Ter informatie: ID's buiten ALLE_IDS.txt (contractpunten C1.3-...): %d gezien, %d zonder stap"
          % (len(extra), len(extra_zonder)))
    if extra_zonder:
        print("  zonder stap (reden in de Dekking-tabel): " + ", ".join(extra_zonder))
    vreemd = sorted(i for i in extra if not i.startswith("C1.3-"))
    if vreemd:
        print("  LET OP, ID-vorm van ALLE_IDS maar niet in ALLE_IDS.txt (tikfout of reeks?): " + ", ".join(vreemd))

    # ID's in meer dan een bouwstap
    print()
    meer = [(i, werk[i]) for i in alle_ids if len(set(werk.get(i, []))) > 1]
    print("== ID's in de regel 'Werkpakketten en tests' van meer dan een stap (mag; ter controle): %d" % len(meer))
    for i, st in meer:
        print("  %s: %s" % (i, ", ".join(OrderedDict.fromkeys(st))))

    # Dubbele stap-ID's
    print()
    dubbel = [(sid, lst) for sid, lst in per_id.items() if len(lst) > 1]
    print("== Dubbele stap-ID's: %d" % len(dubbel))
    for sid, lst in dubbel:
        print("  %s: %s" % (sid, "; ".join("%s regel %d" % (s.bestand, s.regelnr) for s in lst)))
    if dubbel:
        fout = True

    # Vooraf naar niet-bestaande stappen
    print()
    kapot_vooraf = []
    for s in alleen_s:
        vooraf = s.veld("Vooraf") or ""
        for ref in haal_stappen(vooraf, stap_ids):
            if ref not in bestaand:
                kapot_vooraf.append((s, ref))
    print("== 'Vooraf' verwijst naar een stap die niet bestaat: %d" % len(kapot_vooraf))
    for s, ref in kapot_vooraf:
        print("  %s (%s): %s" % (s.id, s.bestand, ref))
    if kapot_vooraf:
        fout = True

    # Vormcontroles per stap
    vormfout = False
    print()
    ontbreekt = []
    for s in alleen_s:
        mis = [v for v in ("Agents", "Al gedaan?", "Niveau") if s.veld(v) is None]
        if mis:
            ontbreekt.append((s, mis))
    print("== Stappen zonder regel 'Agents', 'Al gedaan?' of 'Niveau': %d" % len(ontbreekt))
    for s, mis in ontbreekt:
        print("  %s (%s): mist %s" % (s.id, s.bestand, ", ".join(mis)))
    vormfout |= bool(ontbreekt)

    print()
    zonder_m = [s for s in alleen_s if "Moeilijkheid" not in s.kopregel]
    print("== Stappen zonder 'Moeilijkheid' in de kopregel (- **Repo:** ...): %d" % len(zonder_m))
    for s in zonder_m:
        print("  %s (%s)%s" % (s.id, s.bestand, "" if s.kopregel else " - geen kopregel met **Repo:**"))
    vormfout |= bool(zonder_m)

    print()
    n5_zonder = [s for s in alleen_s if heeft_n5(s.veld("Niveau")) and "Winst:" not in (s.veld("Niveau") or "")]
    print("== 'Niveau' met N5 zonder de tekst 'Winst:': %d" % len(n5_zonder))
    for s in n5_zonder:
        print("  %s (%s): %s" % (s.id, s.bestand, kort(s.veld("Niveau"), 160)))
    vormfout |= bool(n5_zonder)

    print()
    print("== Stappen met N5 in 'Niveau' (richtlijn: hooguit ongeveer 1 op 8; escalaties niet meegeteld)")
    tot_n5 = tot = 0
    for b in bestanden:
        st = [s for s in alleen_s if s.bestand == b]
        n5 = [s for s in st if heeft_n5(s.veld("Niveau"))]
        tot_n5 += len(n5)
        tot += len(st)
        pct = (100.0 * len(n5) / len(st)) if st else 0.0
        print("  %-24s %3d van %3d (%4.1f%%)%s" % (b, len(n5), len(st), pct, "  BOVEN 1 op 8" if len(st) and len(n5) * 8 > len(st) else ""))
    print("  %-24s %3d van %3d (%4.1f%%)" % ("totaal", tot_n5, tot, (100.0 * tot_n5 / tot) if tot else 0.0))

    # Rollen, valkuilen en poorten
    print()
    prompts = kopnamen(os.path.join(HIER, "AGENTEN.md"), r"^###\s+([AR]-[A-Z]+(?:-[A-Z]+)*)\s*$")
    if prompts is None:
        print("== AGENTEN.md ontbreekt: rolcontrole niet mogelijk")
        fout = True
    else:
        onbekend = defaultdict(list)
        for s in stappen:
            for rol in rollen(s.veld("Agents")):
                if rol not in prompts:
                    onbekend[rol].append(s.id)
        for b in blokken:
            for rol in rollen(b["velden"].get("Agents")):
                if rol not in prompts:
                    onbekend[rol].append(b["bestand"] + "#" + b["kop"])
        print("== Rolnamen in 'Agents' zonder prompt in AGENTEN.md (bekend: %s): %d"
              % (", ".join(sorted(prompts)), len(onbekend)))
        for rol, waar in sorted(onbekend.items()):
            print("  %s: %s" % (rol, ", ".join(waar[:12]) + (" ..." if len(waar) > 12 else "")))
        if onbekend:
            fout = True

    def verwijzingen(regex):
        gevonden = defaultdict(list)
        for pad in stapbestanden():
            naam = os.path.basename(pad)
            for nr, (r, _c) in enumerate(lees_regels(pad), 1):
                for m in regex.finditer(r):
                    gevonden[m.group(1)].append("%s:%d" % (naam, nr))
        return gevonden

    print()
    vk = kopnamen(os.path.join(HIER, "VALKUILEN.md"), r"^#{2,4}\s+(V-\d{3})\b")
    if vk is None:
        print("== VALKUILEN.md ontbreekt: controle van V-nnn niet mogelijk")
        fout = True
    else:
        mis = {k: v for k, v in verwijzingen(V_RE).items() if k not in vk}
        print("== V-nnn-verwijzingen die niet in VALKUILEN.md staan (daar %d valkuilen): %d" % (len(vk), len(mis)))
        for k, v in sorted(mis.items()):
            print("  %s: %s" % (k, ", ".join(v[:8]) + (" ..." if len(v) > 8 else "")))
        if mis:
            fout = True

    print()
    pk = kopnamen(os.path.join(HIER, "POORTEN.md"), r"^#{2,4}\s+(P-[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*)\s*$")
    if pk is None:
        print("== POORTEN.md ontbreekt: controle van P-<naam> niet mogelijk")
        fout = True
    else:
        mis = {k: v for k, v in verwijzingen(P_RE).items() if k not in pk}
        print("== P-<naam>-verwijzingen die niet in POORTEN.md staan (daar: %s): %d" % (", ".join(sorted(pk)), len(mis)))
        for k, v in sorted(mis.items()):
            print("  %s: %s" % (k, ", ".join(v[:8]) + (" ..." if len(v) > 8 else "")))
        if mis:
            fout = True

    # VOORTGANG.md
    if args.voortgang:
        print()
        vpad = os.path.join(HIER, "VOORTGANG.md")
        if not os.path.exists(vpad):
            print("== VOORTGANG.md ontbreekt")
            fout = True
        else:
            in_v = defaultdict(int)
            kolom2 = None
            for r, in_code in lees_regels(vpad):
                if in_code or not r.lstrip().startswith("|"):
                    kolom2 = None if not r.lstrip().startswith("|") else kolom2
                    continue
                cellen = [c.strip() for c in r.strip().strip("|").split("|")]
                if len(cellen) < 2:
                    continue
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cellen if c):
                    continue
                if not re.fullmatch(r"\[[ xX~-]?\]", cellen[0]):
                    kolom2 = cellen[1].strip("`* ").lower()
                    continue
                if kolom2 != "stap-id":
                    continue
                sid = cellen[1].strip("`* ")
                in_v[sid] += 1
            niet_in_v = [s for s in stap_ids if in_v.get(s, 0) == 0]
            vaker = [(s, n) for s, n in in_v.items() if n > 1]
            deel = [s for s in in_v if s not in bestaand and re.sub(r"[a-z]$", "", s) in bestaand]
            vreemd_v = [s for s in in_v if s not in bestaand and s not in deel]
            print("== VOORTGANG.md: %d stap-rijen; %d stappen/onderdelen in de STAPPEN-bestanden" % (sum(in_v.values()), len(set(stap_ids))))
            print("  ontbreken in VOORTGANG.md (%d): %s" % (len(niet_in_v), ", ".join(niet_in_v)))
            print("  meer dan een keer in VOORTGANG.md (%d): %s" % (len(vaker), ", ".join("%s (%dx)" % x for x in vaker)))
            print("  in VOORTGANG.md maar niet in de STAPPEN-bestanden (%d): %s" % (len(vreemd_v), ", ".join(vreemd_v)))
            print("  deelstappen van een gesplitste stap (toegestaan, AGENTEN 6.7) (%d): %s" % (len(deel), ", ".join(deel)))
            if niet_in_v or vaker or vreemd_v:
                fout = True

    print()
    if args.streng and vormfout:
        fout = True
    print("UITKOMST: %s" % ("FOUT (exitcode 1)" if fout else "in orde (exitcode 0)")
          + ("" if args.streng else "; vormfouten tellen alleen met --streng"))
    return 1 if fout else 0


if __name__ == "__main__":
    sys.exit(main())
