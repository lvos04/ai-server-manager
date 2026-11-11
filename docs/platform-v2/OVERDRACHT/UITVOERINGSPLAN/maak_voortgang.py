#!/usr/bin/env python3
"""Zet de staptabellen in VOORTGANG.md gelijk met de STAPPEN-bestanden, zonder iets te verliezen.

Gebruik (vanuit elke map; standaard werkt het op VOORTGANG.md naast dit script):

    python3 maak_voortgang.py                      VOORTGANG.md bijwerken (alleen als er iets verandert)
    python3 maak_voortgang.py --droog              niets schrijven; laat zien wat er zou veranderen
    python3 maak_voortgang.py --bestand /tmp/V.md  op een kopie werken (om te testen)

Wat het doet:
- Leest alle STAPPEN_*.md naast dit script (met de lezer uit dekking.py) en maakt per stapbestand een tabel met
  ALLE stappen (### S-...) in de volgorde van het bestand, en per stapbestand met NAS-onderdelen (### N-...) een
  tabel met die onderdelen.
- BEHOUDT ongewijzigd: alles boven de eerste staptabel ("Lopend", "Wacht op de gebruiker", "Topmodel-inzet", "Half
  werk", ...), alles na de laatste staptabel ("Gates", "Fase-afsluitingen", ...), en per stap wat de regisseur invult:
  de kolommen klaar, commit, CI-run, datum, opmerking (bij NAS-onderdelen ook bewijs) en elke kolom die het script
  niet kent. Tekst en andere tabellen die de regisseur in een fasedeel heeft gezet, blijven in dat fasedeel staan.
- Deelstappen van een gesplitste stap (AGENTEN.md 6.7: oorspronkelijk ID met een letter, bv. S-P5-12a) blijven
  staan, direct onder de oorspronkelijke stap.
- Een rij waarvan de stap niet meer in een stapbestand staat: is er iets ingevuld of afgevinkt, dan blijft hij staan
  in het deel "Rijen zonder stap in de stapbestanden"; is hij leeg, dan vervalt hij. Beide worden gemeld.
- Bestaan "Gates" en "Fase-afsluitingen" nog niet, dan zet het script er een leeg sjabloon onder.

Schrijft alleen het VOORTGANG-bestand (en alleen als de inhoud verandert). Alleen standaardbibliotheek.
"""

import sys

sys.dont_write_bytecode = True  # geen __pycache__ in de planmap

import argparse
import os
import re
import tempfile
from collections import OrderedDict

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import dekking as dk  # noqa: E402  (zelfde map; leest de STAPPEN-bestanden op dezelfde manier)

# ---------------------------------------------------------------------------------------------
# Kolommen
# ---------------------------------------------------------------------------------------------

FASE_KOLOMMEN = [
    ("klaar", "klaar"),
    ("stap", "stap-ID"),
    ("titel", "titel"),
    ("baan", "baan (repo)"),
    ("vooraf", "vooraf (ingekort; de stap is leidend)"),
    ("zwaar", "zwaar"),
    ("moeilijkheid", "moeilijkheid"),
    ("niveau", "niveau (afwijkingen)"),
    ("reviewers", "verplichte reviewers"),
    ("commit", "commit"),
    ("ci", "CI-run"),
    ("datum", "datum"),
    ("opmerking", "opmerking"),
]
NAS_KOLOMMEN = [
    ("klaar", "klaar"),
    ("stap", "stap-ID"),
    ("titel", "titel"),
    ("bewijs", "bewijs"),
    ("datum", "datum"),
    ("opmerking", "opmerking"),
]
# Kolommen die het script uit de stapbestanden maakt; alle andere vult de regisseur in en blijven behouden.
GEMAAKT = {"stap", "titel", "baan", "vooraf", "zwaar", "moeilijkheid", "niveau", "reviewers"}

KLAAR_RE = re.compile(r"^\[[ xX~-]?\]$")
FASEKOP_RE = re.compile(r"^##\s+(.*?)\s*\((STAPPEN_[A-Za-z0-9_]+\.md)\b[^)]*\)\s*$")
H2_RE = re.compile(r"^##\s+(?!#)")
REVIEWER_RE = re.compile(r"(?<![A-Za-z0-9\-])(R-[A-Z]+(?:-[A-Z]+)*)(?![A-Za-z0-9])")
VASTE_REVIEWVOLGORDE = ["R-TECH", "R-VEILIG", "R-HARDE-EIS", "R-MANIFEST", "R-ONTWERP", "R-EERLIJK"]

INTRO_FASE = ('De volgorde binnen een baan en wat tegelijk mag staat in "Volgorde en banen" van {bestand}; deze tabel '
              'volgt de volgorde van het bestand.')
INTRO_KOLOMMEN = ("Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in; de andere kolommen maakt "
                  "maak_voortgang.py uit het stapbestand (ingekort; de stap is leidend).")
INTRO_NAS = [
    "Deze onderdelen voert de regisseur niet zelf uit: de gebruiker doet ze op de echte NAS met het draaiboek uit {bestand}.",
    "Afvinken alleen met het bewijs dat het onderdeel noemt.",
]
INTRO_WEES = ("Deze rijen staan in geen enkel stapbestand meer, maar er was iets ingevuld of afgevinkt. Niet weggooien: "
              "zoek uit of de stap is hernoemd of verplaatst, zet de gegevens dan met de hand in de goede rij en haal "
              "de rij hier pas daarna weg.")
WEES_KOP = "## Rijen zonder stap in de stapbestanden (behouden; nakijken)"
# Regels die het script zelf schrijft: die tellen bij het inlezen niet als tekst van de regisseur.
GEGENEREERD_BEGIN = [
    "De volgorde binnen een baan en wat tegelijk mag staat in",
    "Kolommen klaar, commit, CI-run, datum en opmerking vult de regisseur in",
    "Deze onderdelen voert de regisseur niet zelf uit",
    "Afvinken alleen met het bewijs dat het onderdeel noemt",
    "Deze rijen staan in geen enkel stapbestand meer",
]

STANDAARD_STAART = """## Gates

Per gate een regel; de eisen staan in het deel "Gates" en in de fase-afsluiting van het stapbestand. Afvinken alleen met het
rapport van A-GATE in de ketenmap.

| klaar | gate | stapbestand | rapport A-GATE | datum |
|---|---|---|---|---|
{gates}
## Fase-afsluitingen

| fase | dekking.py --voortgang schoon | A-GATE | Excel bijgewerkt (commit) | STATUS.md bijgewerkt | gemeld aan de gebruiker |
|---|---|---|---|---|---|
{fasen}"""


def kolomsleutel(naam):
    n = naam.strip().strip("*`").strip().lower()
    if n in ("klaar", "[ ]", "[x]", "", "af"):
        return "klaar"
    for sleutel, begin in (("stap", "stap"), ("titel", "titel"), ("baan", "baan"), ("baan", "repo"),
                           ("vooraf", "vooraf"), ("zwaar", "zwaar"), ("moeilijkheid", "moeilijkheid"),
                           ("niveau", "niveau"), ("commit", "commit"), ("ci", "ci"), ("datum", "datum"),
                           ("opmerking", "opmerking"), ("bewijs", "bewijs")):
        if n.startswith(begin):
            return sleutel
    if "reviewer" in n:
        return "reviewers"
    return "x:" + naam.strip()


def cellen_van(regel):
    """Cellen van een tabelregel; een geescapete pipe (\\|) splitst niet."""
    binnen = regel.strip()
    if binnen.startswith("|"):
        binnen = binnen[1:]
    if binnen.endswith("|") and not binnen.endswith("\\|"):
        binnen = binnen[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", binnen)]


def is_scheiding(cellen):
    return all(re.fullmatch(r":?-{2,}:?", c) for c in cellen if c) and any(cellen)


def schoon(t):
    t = (t or "").replace("`", "").replace("**", "").replace("|", "/")
    return re.sub(r"\s+", " ", t).strip()


def kort(t, n):
    t = schoon(t)
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def reviewers(agents):
    """Reviewers uit de regel "Agents"; niet: "geen R-TECH", "zonder R-X", "R-TECH vervalt"."""
    gevonden = []
    tekst = agents or ""
    for m in REVIEWER_RE.finditer(tekst):
        voor = tekst[max(0, m.start() - 12):m.start()].lower()
        na = tekst[m.end():m.end() + 12].lower()
        if re.search(r"(geen|zonder)\s+$", voor) or re.match(r"\s*vervalt", na):
            continue
        if m.group(1) not in gevonden:
            gevonden.append(m.group(1))
    gevonden.sort(key=lambda r: (VASTE_REVIEWVOLGORDE.index(r) if r in VASTE_REVIEWVOLGORDE else 99, r))
    return ", ".join(gevonden) if gevonden else "-"


def jaofnee(t):
    m = re.match(r"\s*(ja|nee)\b", (t or "").lower())
    return m.group(1) if m else (kort(t, 20) if t else "ONBEKEND")


def moeilijkheid(t):
    if not t:
        return "ONBEKEND"
    kern = t.split("(")[0].strip()
    return kort(kern or t, 24)


def niveau(t):
    if not t:
        return "ONBEKEND"
    s = schoon(t)
    if re.fullmatch(r"standaard\.?", s, re.I):
        return "standaard"
    uit = kort(s, 70)
    if dk.heeft_n5(t) and "N5" not in uit:
        uit = "[N5] " + kort(s, 64)
    return uit


# ---------------------------------------------------------------------------------------------
# Stapbestanden lezen
# ---------------------------------------------------------------------------------------------

def fasenaam(pad):
    """Naam van de fase uit de H1 van het stapbestand ("# STAPPEN_P2 - Fase P2: ..." -> "Fase P2")."""
    naam = os.path.basename(pad)
    with open(pad, encoding="utf-8") as fh:
        for r in fh:
            if r.startswith("# "):
                m = re.search(r"(Fase\s+[^:(—–]+?)\s*(?::|\(|—|–|$)", r)
                if m:
                    return m.group(1).strip()
                break
    return "Fase " + naam[len("STAPPEN_"):-3].replace("_", " ")


def lees_stappen():
    """[(bestand, fasenaam, [stap, ...])] in de volgorde van de bestanden; stap = (soort, id, dict met cellen)."""
    uit = []
    for pad in dk.stapbestanden():
        stappen, _dek, _blok = dk.lees_stapbestand(pad)
        rijen = []
        for s in stappen:
            if s.soort == "stap":
                cel = {
                    "stap": s.id,
                    "titel": kort(s.titel, 70),
                    "baan": kort(s.kopwaarde("Repo") or "ONBEKEND", 40),
                    "vooraf": kort(s.veld("Vooraf") or "ONBEKEND", 60),
                    "zwaar": jaofnee(s.kopwaarde("Zwaar")),
                    "moeilijkheid": moeilijkheid(s.kopwaarde("Moeilijkheid")),
                    "niveau": niveau(s.veld("Niveau")),
                    "reviewers": reviewers(s.veld("Agents")),
                }
            else:
                cel = {"stap": s.id, "titel": kort(s.titel, 70)}
            rijen.append((s.soort, s.id, cel))
        uit.append((os.path.basename(pad), fasenaam(pad), rijen))
    return uit


# ---------------------------------------------------------------------------------------------
# Bestaande VOORTGANG.md lezen
# ---------------------------------------------------------------------------------------------

class Deel:
    def __init__(self, kop):
        self.kop = kop               # de regel "## ..." (of None voor tekst voor de eerste kop)
        self.regels = []
        self.staptabellen = []       # [(kolomsleutels, kolomnamen, [cellen, ...])]
        self.extra = []              # regels van de regisseur (geen staptabel, geen gegenereerde tekst)


def splits_delen(tekst):
    delen = [Deel(None)]
    in_code = False
    for r in tekst.split("\n"):
        if r.lstrip().startswith("```"):
            in_code = not in_code
        if not in_code and H2_RE.match(r):
            delen.append(Deel(r))
            continue
        delen[-1].regels.append(r)
    return delen


def ontleed_deel(deel):
    """Vult staptabellen en extra. Een staptabel is een tabel met als tweede kolom precies "stap-ID" (zoals in
    dekking.py --voortgang); andere tabellen ("Lopend", "Topmodel-inzet", ...) zijn geen staptabel."""
    regels = deel.regels
    i = 0
    extra = []
    while i < len(regels):
        r = regels[i]
        if r.lstrip().startswith("|"):
            blok = []
            while i < len(regels) and regels[i].lstrip().startswith("|"):
                blok.append(regels[i])
                i += 1
            kop = cellen_van(blok[0])
            if (len(kop) >= 2 and kop[1].strip("`* ").lower() == "stap-id" and len(blok) >= 2
                    and is_scheiding(cellen_van(blok[1]))):
                sleutels = [kolomsleutel(k) for k in kop]
                rijen = []
                for b in blok[2:]:
                    c = cellen_van(b)
                    if is_scheiding(c):
                        continue
                    c = c + [""] * (len(sleutels) - len(c))
                    rijen.append(c)
                deel.staptabellen.append((sleutels, kop, rijen))
            else:
                extra.extend(blok)
            continue
        if any(r.strip().startswith(b) for b in GEGENEREERD_BEGIN):
            i += 1
            continue
        extra.append(r)
        i += 1
    while extra and not extra[0].strip():
        extra.pop(0)
    while extra and not extra[-1].strip():
        extra.pop()
    deel.extra = extra


def deelsleutel(kop):
    """Welk stapbestand hoort bij een deel: ("fase", bestand), ("nas", bestand of None), ("wees", None) of None."""
    if kop is None:
        return None
    if kop.strip() == WEES_KOP:
        return ("wees", None)
    m = re.search(r"(STAPPEN_[A-Za-z0-9_]+\.md)", kop)
    if re.match(r"^##\s+NAS-onderdelen", kop):
        return ("nas", m.group(1) if m else None)
    if m:
        return ("fase", m.group(1))
    return None


def lees_voortgang(tekst):
    delen = splits_delen(tekst)
    for d in delen:
        ontleed_deel(d)
    met_tabel = [i for i, d in enumerate(delen) if d.staptabellen]
    if not met_tabel:
        return tekst, None, [], ""
    eerste, laatste = met_tabel[0], met_tabel[-1]
    # Het stappengebied loopt van de eerste tot en met de laatste deel met een staptabel, plus direct volgende
    # delen die door dit script worden gemaakt (bv. een leeg deel "Rijen zonder stap").
    while laatste + 1 < len(delen) and deelsleutel(delen[laatste + 1].kop) is not None:
        laatste += 1
    kop_tekst = "\n".join(_deeltekst(d) for d in delen[:eerste])
    staart = "\n".join(_deeltekst(d) for d in delen[laatste + 1:])
    return kop_tekst, delen[eerste:laatste + 1], delen, staart


def _deeltekst(d):
    if d.kop is None:
        return "\n".join(d.regels)
    return "\n".join([d.kop] + d.regels)


# ---------------------------------------------------------------------------------------------
# Opbouwen
# ---------------------------------------------------------------------------------------------

def tabelregel(cellen):
    return "| " + " | ".join(c if c else "" for c in cellen) + " |"


def scheiding(n):
    return "|" + "---|" * n


def leeg_ingevuld(rij):
    """True als de regisseur niets heeft ingevuld of afgevinkt in deze rij."""
    for k, v in rij.items():
        if k in GEMAAKT:
            continue
        if k == "klaar":
            if v.strip() not in ("[ ]", "[]", ""):
                return False
            continue
        if v.strip():
            return False
    return True


def bouw(oud_tekst):
    stapdata = lees_stappen()
    kop_tekst, gebied, _alle, staart = lees_voortgang(oud_tekst)
    melding = []

    # Bestaande rijen per stap-ID (alle staptabellen van het gebied) en extra tekst per deel
    oude_rijen = OrderedDict()       # id -> dict(sleutel -> waarde)
    extra_kolommen = OrderedDict()   # ("fase"/"nas", bestand) -> [(sleutel, naam)]
    oude_volgorde = []               # [(deelsleutel, id)]
    extra_tekst = OrderedDict()
    oude_labels = {}
    if gebied:
        for d in gebied:
            ds = deelsleutel(d.kop)
            if ds and ds[0] == "fase":
                m = FASEKOP_RE.match(d.kop)
                if m:
                    oude_labels[ds[1]] = m.group(1).strip()
            if d.extra:
                sleutel = ds if ds else ("kop", d.kop)
                stuk = d.extra if ds else [d.kop, ""] + d.extra   # een onbekend deel houdt zijn kop
                extra_tekst.setdefault(sleutel, []).extend(([""] if sleutel in extra_tekst else []) + stuk)
            for sleutels, namen, rijen in d.staptabellen:
                for s, n in zip(sleutels, namen):
                    if s.startswith("x:"):
                        lijst = extra_kolommen.setdefault(ds, [])
                        if s not in [x[0] for x in lijst]:
                            lijst.append((s, n))
                for c in rijen:
                    rij = OrderedDict((s, v) for s, v in zip(sleutels, c))
                    sid = rij.get("stap", "").strip("`* ")
                    if not sid:
                        continue
                    if sid in oude_rijen:
                        melding.append("LET OP: %s stond meer dan een keer in de oude staptabellen; de ingevulde "
                                       "waarden van de rijen zijn samengevoegd" % sid)
                        for k, v in rij.items():
                            if v.strip() and not oude_rijen[sid].get(k, "").strip() and k not in GEMAAKT:
                                oude_rijen[sid][k] = v
                            elif k == "klaar" and v.strip() not in ("[ ]", "") and oude_rijen[sid].get(k, "[ ]") in ("[ ]", ""):
                                oude_rijen[sid][k] = v
                        continue
                    oude_rijen[sid] = rij
                    oude_volgorde.append((ds, sid))

    alle_ids = set()
    for _b, _f, rijen in stapdata:
        for _soort, sid, _cel in rijen:
            alle_ids.add(sid)

    # Deelstappen (S-P5-12a) bij hun oorspronkelijke stap; wezen apart
    deelstappen = OrderedDict()
    wezen = []
    vervallen = []
    for _ds, sid in oude_volgorde:
        if sid in alle_ids:
            continue
        basis = re.sub(r"[a-z]$", "", sid)
        if basis != sid and basis in alle_ids:
            deelstappen.setdefault(basis, []).append(sid)
        elif not leeg_ingevuld(oude_rijen[sid]):
            wezen.append(sid)
        else:
            vervallen.append(sid)

    def rij_cellen(kolommen, nieuw, oud):
        uit = []
        for s, _n in kolommen:
            if s in GEMAAKT and nieuw is not None:
                uit.append(nieuw.get(s, ""))
            elif oud is not None and s in oud:
                uit.append(oud[s])
            elif s == "klaar":
                uit.append("[ ]")
            else:
                uit.append(nieuw.get(s, "") if nieuw is not None and s in nieuw else "")
        return uit

    def kolommen_voor(basis, ds):
        extra = extra_kolommen.get(ds, [])
        if not extra:
            return basis
        return basis[:-1] + extra + basis[-1:]

    stukken = []
    tellingen = []
    nieuw_ids = []
    behouden_ingevuld = 0
    # 1. Fasetabellen
    for bestand, fnaam, rijen in stapdata:
        s_rijen = [(sid, cel) for soort, sid, cel in rijen if soort == "stap"]
        if not s_rijen:
            continue
        ds = ("fase", bestand)
        label = oude_labels.get(bestand, fnaam)
        kolommen = kolommen_voor(FASE_KOLOMMEN, ds)
        regels = ["## %s (%s; %d stappen)" % (label, bestand, len(s_rijen)), "",
                  INTRO_FASE.format(bestand=bestand), INTRO_KOLOMMEN, "",
                  tabelregel([n for _s, n in kolommen]), scheiding(len(kolommen))]
        for sid, cel in s_rijen:
            oud = oude_rijen.get(sid)
            if oud is None:
                nieuw_ids.append(sid)
            elif not leeg_ingevuld(oud):
                behouden_ingevuld += 1
            regels.append(tabelregel(rij_cellen(kolommen, cel, oud)))
            for deel_id in deelstappen.get(sid, []):
                regels.append(tabelregel(rij_cellen(kolommen, None, oude_rijen[deel_id])))
                if not leeg_ingevuld(oude_rijen[deel_id]):
                    behouden_ingevuld += 1
        if extra_tekst.get(ds):
            regels += [""] + extra_tekst.pop(ds)
        regels.append("")
        stukken.append("\n".join(regels))
        tellingen.append("%s: %d stappen" % (bestand, len(s_rijen)))

    # 2. NAS-onderdelen
    for bestand, fnaam, rijen in stapdata:
        n_rijen = [(sid, cel) for soort, sid, cel in rijen if soort == "onderdeel"]
        if not n_rijen:
            continue
        ds = ("nas", bestand)
        kolommen = kolommen_voor(NAS_KOLOMMEN, ds)
        fase = re.sub(r"^Fase\s+", "", oude_labels.get(bestand, fnaam))
        regels = ["## NAS-onderdelen van %s (%s; %d onderdelen; alleen met de gebruiker op de echte NAS; tot dan NIET "
                  "GEVALIDEERD)" % (fase, bestand, len(n_rijen)), ""]
        regels += [t.format(bestand=bestand) for t in INTRO_NAS]
        regels += ["", tabelregel([n for _s, n in kolommen]), scheiding(len(kolommen))]
        for sid, cel in n_rijen:
            oud = oude_rijen.get(sid)
            if oud is None:
                nieuw_ids.append(sid)
            elif not leeg_ingevuld(oud):
                behouden_ingevuld += 1
            regels.append(tabelregel(rij_cellen(kolommen, cel, oud)))
            for deel_id in deelstappen.get(sid, []):
                regels.append(tabelregel(rij_cellen(kolommen, None, oude_rijen[deel_id])))
        # tekst uit een oud NAS-deel zonder bestandsnaam in de kop hoort hier
        for sleutel in (ds, ("nas", None)):
            if extra_tekst.get(sleutel):
                regels += [""] + extra_tekst.pop(sleutel)
        regels.append("")
        stukken.append("\n".join(regels))
        tellingen.append("%s: %d NAS-onderdelen" % (bestand, len(n_rijen)))

    # 3. Wezen en overgebleven tekst van de regisseur (bv. een fasedeel waarvan het stapbestand weg is)
    rest_tekst = [t for _k, t in extra_tekst.items() if t]
    if wezen or rest_tekst:
        kolommen = list(FASE_KOLOMMEN)
        regels = [WEES_KOP, "", INTRO_WEES, ""]
        if wezen:
            regels += [tabelregel([n for _s, n in kolommen]), scheiding(len(kolommen))]
            for sid in wezen:
                oud = oude_rijen[sid]
                regels.append(tabelregel([oud.get(s, "[ ]" if s == "klaar" else "") for s, _n in kolommen]))
                behouden_ingevuld += 1
                weg = [s for s in oud if s.startswith("x:") and oud[s].strip()]
                if weg:
                    melding.append("LET OP: %s had waarden in kolommen %s; staan nog in de oude kopie" % (sid, weg))
        for t in rest_tekst:
            regels += [""] + t
        regels.append("")
        stukken.append("\n".join(regels))

    gebied_tekst = "\n".join(stukken)

    if not staart.strip():
        gates = "".join("| [ ] | %s | %s |  |  |\n" % (f, b) for b, f, r in stapdata if any(x[0] == "stap" for x in r))
        fasen = "".join("| %s |  |  |  |  |  |\n" % f for b, f, r in stapdata if any(x[0] == "stap" for x in r))
        staart = STANDAARD_STAART.format(gates=gates, fasen=fasen)
        melding.append("Gates en Fase-afsluitingen ontbraken: sjabloon toegevoegd")

    kop_tekst = kop_tekst.rstrip("\n")
    delen = [kop_tekst, "", gebied_tekst.rstrip("\n"), ""]
    if staart.strip():
        delen += [staart.strip("\n"), ""]
    nieuw = "\n".join(delen)
    if not nieuw.endswith("\n"):
        nieuw += "\n"

    melding.insert(0, "Staptabellen: " + "; ".join(tellingen))
    melding.append("Rijen met iets ingevuld of afgevinkt, behouden: %d" % behouden_ingevuld)
    if gebied is not None:
        melding.append("Nieuw in VOORTGANG (stond er nog niet in): %d%s"
                       % (len(nieuw_ids), (" - " + ", ".join(nieuw_ids)) if nieuw_ids else ""))
    else:
        melding.append("Geen bestaande staptabellen gevonden: alle tabellen nieuw gemaakt")
    melding.append("Deelstappen behouden onder hun stap: %d%s"
                   % (sum(len(v) for v in deelstappen.values()),
                      (" - " + ", ".join(x for v in deelstappen.values() for x in v)) if deelstappen else ""))
    if wezen:
        melding.append("LET OP: rijen zonder stap maar met gegevens, behouden in '%s': %s"
                       % (WEES_KOP[3:], ", ".join(wezen)))
    if vervallen:
        melding.append("Vervallen (stap bestaat niet meer en er was niets ingevuld): %s" % ", ".join(vervallen))
    if rest_tekst:
        melding.append("LET OP: tekst uit een fasedeel zonder stapbestand verplaatst naar '%s'" % WEES_KOP[3:])
    return nieuw, melding


def main(argv=None):
    ap = argparse.ArgumentParser(description="Zet de staptabellen in VOORTGANG.md gelijk met de STAPPEN-bestanden.")
    ap.add_argument("--bestand", default=os.path.join(HIER, "VOORTGANG.md"),
                    help="het VOORTGANG-bestand (standaard VOORTGANG.md naast dit script)")
    ap.add_argument("--droog", action="store_true", help="niets schrijven; alleen melden wat er zou veranderen")
    args = ap.parse_args(argv)

    pad = os.path.abspath(args.bestand)
    if os.path.exists(pad):
        with open(pad, encoding="utf-8") as fh:
            oud = fh.read()
        mtime = os.stat(pad).st_mtime_ns
    else:
        oud, mtime = "# VOORTGANG - afvinkgrootboek van de regisseur\n", None

    nieuw, melding = bouw(oud)
    for m in melding:
        print(m)

    if nieuw == oud:
        print("UITKOMST: geen wijziging (%s)" % pad)
        return 0
    if args.droog:
        import difflib
        verschil = list(difflib.unified_diff(oud.split("\n"), nieuw.split("\n"), "oud", "nieuw", lineterm="", n=0))
        print("\n".join(verschil[:400]))
        if len(verschil) > 400:
            print("... (%d regels verschil in totaal)" % len(verschil))
        print("UITKOMST: zou %s wijzigen (--droog: niets geschreven)" % pad)
        return 0
    if mtime is not None and os.stat(pad).st_mtime_ns != mtime:
        print("UITKOMST: FOUT - %s is tijdens het draaien gewijzigd; niets geschreven, draai opnieuw" % pad)
        return 1
    fd, tmp = tempfile.mkstemp(prefix=".voortgang-", dir=os.path.dirname(pad))
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(nieuw)
    if os.path.exists(pad):
        os.chmod(tmp, os.stat(pad).st_mode & 0o777)
    os.replace(tmp, pad)
    print("UITKOMST: %s bijgewerkt" % pad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
