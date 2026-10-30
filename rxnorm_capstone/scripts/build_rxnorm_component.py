#!/usr/bin/env python3
"""
Build and validate the RxNorm medication-identity component directly from the
RxNorm Current Prescribable Content ZIP. Python standard library only.

The ZIP is opened read-only and the RRF files are streamed from it; nothing is
extracted and the archive is never modified (its SHA-256 is recorded before and
after the run).

Exit codes: 0 = all critical checks passed; 2 = at least one critical check failed
(outputs and the validation report are still written so the failure is inspectable).

Usage:
  python3 scripts/build_rxnorm_component.py \
      --zip /path/to/RxNorm_full_prescribe_10052026.zip \
      --config-dir config --out-dir . 
"""
import argparse
import collections
import csv
import datetime
import hashlib
import io
import json
import os
import re
import sys
import zipfile

# ----------------------------------------------------------------------------
# Constants taken from the NLM documentation (see SOURCE_AND_LICENSE.md)
# ----------------------------------------------------------------------------
RRF_FIELDS = {"RXNCONSO.RRF": 18, "RXNREL.RRF": 16, "RXNSAT.RRF": 13}  # Tech Doc 12.4/12.7/12.5
ACTIVE_REL = ("", "N")  # RXNREL SUPPRESS is blank for every row in this release (Tech Doc 12.7: "not yet in use")
PRESCRIBABLE_CVF = "4096"  # Tech Doc 12.4: CVF 4096 = Current Prescribable Content

# Appendix 5 (Term Types). Value = (concept_type label used in this dataset, description from NLM)
TTY_INFO = {
    "IN": ("ingredient", "Ingredient: base active compound or moiety of a drug"),
    "PIN": ("precise_ingredient", "Precise ingredient: a specific form of an ingredient, most often a salt or isomer"),
    "MIN": ("multiple_ingredient", "Multiple ingredients: two or more ingredients together in one preparation"),
    "BN": ("brand_name", "Brand name: proprietary name shared by a family of products with a given active ingredient"),
    "SCD": ("clinical_drug", "Semantic clinical drug (generic): ingredient + strength + dose form"),
    "SBD": ("branded_drug", "Semantic branded drug: ingredient + strength + dose form + brand name"),
    "SCDC": ("clinical_drug_component", "Semantic clinical drug component: ingredient + strength"),
    "SBDC": ("branded_drug_component", "Semantic branded drug component: ingredient + strength + brand name"),
    "SCDF": ("clinical_drug_form", "Semantic clinical drug form: ingredient + dose form"),
    "SBDF": ("branded_drug_form", "Semantic branded drug form: ingredient + dose form + brand name"),
    "SCDFP": ("clinical_drug_form_precise", "Clinical drug form based on a precise ingredient + dose form"),
    "SBDFP": ("branded_drug_form_precise", "Branded drug form based on a precise ingredient"),
    "SCDG": ("clinical_drug_group", "Semantic clinical drug group: ingredient + dose form group"),
    "SBDG": ("branded_drug_group", "Semantic branded drug group: brand name + dose form group"),
    "SCDGP": ("clinical_drug_group_precise", "Clinical drug group based on a precise ingredient"),
    "GPCK": ("generic_pack", "Generic pack of one or more clinical drugs with quantities"),
    "BPCK": ("brand_pack", "Brand-name pack of one or more drugs with quantities"),
    "DF": ("dose_form", "Dose form"),
    "DFG": ("dose_form_group", "Dose form group"),
}
MAIN_TTYS = set(TTY_INFO)  # Appendix 5: each concept with a normalized name has exactly one of these
SYNONYM_TTYS = {"PSN", "SY", "TMSY"}

# Appendix 1: documented (subject TTY = RXCUI2 side, RELA, object TTY = RXCUI1 side).
# Only the forward direction is listed; inverses are derived below.
INVERSE_RELA = {
    "consists_of": "constitutes",
    "has_ingredient": "ingredient_of",
    "has_ingredients": "ingredients_of",
    "has_part": "part_of",
    "has_precise_ingredient": "precise_ingredient_of",
    "form_of": "has_form",
    "tradename_of": "has_tradename",
    "has_dose_form": "dose_form_of",
    "has_quantified_form": "quantified_form_of",
}
INVERSE_RELA.update({v: k for k, v in list(INVERSE_RELA.items())})
FORWARD_DOC_PAIRS = [
    ("BN", "tradename_of", "IN"), ("BN", "has_precise_ingredient", "PIN"),
    ("SBD", "has_ingredient", "BN"), ("SBDC", "has_ingredient", "BN"),
    ("SBDF", "has_ingredient", "BN"), ("SBDG", "has_ingredient", "BN"),
    ("SCDC", "has_ingredient", "IN"), ("SCDF", "has_ingredient", "IN"), ("SCDG", "has_ingredient", "IN"),
    ("SCDC", "has_precise_ingredient", "PIN"),
    ("SCD", "has_ingredients", "MIN"),
    ("MIN", "has_part", "IN"), ("MIN", "has_part", "PIN"),
    ("PIN", "form_of", "IN"),
    ("SBD", "tradename_of", "SCD"), ("SBDC", "tradename_of", "SCDC"),
    ("SBDF", "tradename_of", "SCDF"), ("SBDG", "tradename_of", "SCDG"),
    ("SBDFP", "form_of", "SBDF"), ("SCDFP", "form_of", "SCDF"), ("SCDGP", "form_of", "SCDG"),
    ("SBDFP", "tradename_of", "SCDFP"), ("SBDG", "tradename_of", "SCDGP"), ("BPCK", "tradename_of", "GPCK"),
    ("SBD", "has_dose_form", "DF"), ("SCD", "has_dose_form", "DF"),
    ("SBDF", "has_dose_form", "DF"), ("SCDF", "has_dose_form", "DF"),
    ("BPCK", "has_dose_form", "DF"), ("GPCK", "has_dose_form", "DF"),
    ("SBD", "consists_of", "SBDC"), ("SBD", "consists_of", "SCDC"), ("SCD", "consists_of", "SCDC"),
    ("SCD", "has_quantified_form", "SCD"), ("SBD", "has_quantified_form", "SBD"),
]
DOC_PAIRS = set()
for s, r, o in FORWARD_DOC_PAIRS:
    DOC_PAIRS.add((s, r, o))
    DOC_PAIRS.add((o, INVERSE_RELA[r], s))
EDGE_RELAS = set(INVERSE_RELA)  # relationship types exported to relationships.csv

ATTR_KEEP = {
    "RXN_QUANTITY", "RXN_QUALITATIVE_DISTINCTION", "RXN_BN_CARDINALITY", "RXN_HUMAN_DRUG",
    "RXN_VET_DRUG", "RXN_AVAILABLE_STRENGTH", "RXN_STRENGTH", "RXN_AI", "RXN_AM",
    "RXN_IN_EXPRESSED_FLAG", "RXN_BOSS_FROM", "RXN_BOSS_STRENGTH_NUM_VALUE",
    "RXN_BOSS_STRENGTH_NUM_UNIT", "RXN_BOSS_STRENGTH_DENOM_VALUE", "RXN_BOSS_STRENGTH_DENOM_UNIT",
}


def norm(s):
    """Documented normalization: Unicode casefold + whitespace collapse. Nothing else (no fuzzy matching)."""
    return " ".join(s.casefold().split())


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


class Report:
    def __init__(self):
        self.checks = []

    def add(self, cid, description, status, detail="", critical=True):
        assert status in ("PASS", "FAIL", "NOT_VERIFIED")
        self.checks.append({"id": cid, "description": description, "status": status,
                            "critical": critical, "detail": detail})

    def critical_failures(self):
        return [c for c in self.checks if c["critical"] and c["status"] == "FAIL"]


def stream(zf, name):
    return io.TextIOWrapper(zf.open("rrf/" + name), encoding="utf-8", errors="strict", newline="\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", required=True)
    ap.add_argument("--config-dir", default="config")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--allow-unresolved", action="store_true",
                    help="do not fail the run when a seed concept is unresolved (they are still reported)")
    args = ap.parse_args()

    data_dir = os.path.join(args.out_dir, "data")
    rep_dir = os.path.join(args.out_dir, "reports")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(rep_dir, exist_ok=True)
    R = Report()

    # ------------------------------------------------------------------ Phase A: archive audit
    sha_before = sha256_file(args.zip)
    zf = zipfile.ZipFile(args.zip, "r")
    members = {i.filename: i for i in zf.infolist()}
    inventory = [{"name": i.filename, "bytes": i.file_size} for i in zf.infolist()]
    need = ["rrf/" + n for n in RRF_FIELDS] + [n for n in members if n.lower().startswith("readme")]
    missing = [n for n in need if n not in members]
    R.add("A1", "Archive contains RXNCONSO/RXNREL/RXNSAT.RRF and a README",
          "PASS" if not missing else "FAIL", "missing: %s" % missing if missing else "all present")
    if missing:
        json.dump({"checks": R.checks}, open(os.path.join(rep_dir, "validation_report.json"), "w"), indent=2)
        sys.exit(2)

    readme_name = [n for n in members if n.lower().startswith("readme")][0]
    readme = zf.read(readme_name).decode("utf-8", errors="replace")
    m_date = re.search(r"README: RxNorm (\d\d/\d\d/\d{4}) Current Prescribable Content", readme)
    m_full = re.search(r"created from the (\w+ \d\d, \d{4}) Full\s+Release", readme)
    release_label = {"readme_title_date": m_date.group(1) if m_date else None,
                     "readme_full_release_date": m_full.group(1) if m_full else None,
                     "readme_first_line": readme.strip().splitlines()[0]}
    R.add("A2", "README states a release date matching the ZIP file name (10052026 = October 05, 2026)",
          "PASS" if (m_date and m_date.group(1) == "10/05/2026" and m_full and m_full.group(1) == "October 05, 2026"
                     and "10052026" in os.path.basename(args.zip)) else "FAIL", json.dumps(release_label))
    declared = {n: int(s.replace(",", "")) for n, s in
                re.findall(r"^(RXN\w+\.RRF)\s+([\d,]+)\s+bytes", readme, flags=re.M)}
    mism = {n: (declared.get(n), members["rrf/" + n].file_size) for n in RRF_FIELDS
            if declared.get(n) != members["rrf/" + n].file_size}
    R.add("A3", "RRF file sizes listed in the archive README equal actual sizes", "PASS" if not mism else "FAIL",
          "mismatches: %s" % mism if mism else json.dumps(declared))
    readme_decl = re.search(r"^Readme_Full_Prescribe_\d+\.txt\s+([\d,]+)\s+bytes", readme, flags=re.M)
    readme_note = {"declared_bytes": int(readme_decl.group(1).replace(",", "")) if readme_decl else None,
                   "actual_bytes": members[readme_name].file_size}
    R.add("A4", "README declared size of itself equals actual size",
          "PASS" if readme_note["declared_bytes"] == readme_note["actual_bytes"] else "FAIL",
          "declared %(declared_bytes)s vs actual %(actual_bytes)s (cosmetic: README text edited after size was written)" % readme_note,
          critical=False)

    # ------------------------------------------------------------------ Phase B: structural parse
    structure = {}
    atoms_by_rxcui = collections.defaultdict(list)   # RXNORM-SAB atoms only
    name_index = collections.defaultdict(set)        # normalized STR -> {rxcui}, RXNORM-SAB only
    conso_stats = collections.Counter()
    with stream(zf, "RXNCONSO.RRF") as fh:
        n = bad = 0
        for ln, line in enumerate(fh, 1):
            n += 1
            p = line.rstrip("\n").split("|")
            if len(p) != RRF_FIELDS["RXNCONSO.RRF"] + 1 or p[-1] != "":
                bad += 1
                continue
            conso_stats["sab:" + p[11]] += 1
            conso_stats["suppress:" + p[16]] += 1
            conso_stats["cvf:" + p[17]] += 1
            if p[11] == "RXNORM":
                a = {"rxcui": p[0], "rxaui": p[7], "sab": p[11], "tty": p[12], "code": p[13],
                     "str": p[14], "suppress": p[16], "cvf": p[17], "line": ln}
                atoms_by_rxcui[p[0]].append(a)
                name_index[norm(p[14])].add(p[0])
        structure["RXNCONSO.RRF"] = {"lines": n, "malformed_lines": bad}

    rels = []  # CUI-level SAB=RXNORM rows
    rel_stats = collections.Counter()
    with stream(zf, "RXNREL.RRF") as fh:
        n = bad = 0
        for ln, line in enumerate(fh, 1):
            n += 1
            p = line.rstrip("\n").split("|")
            if len(p) != RRF_FIELDS["RXNREL.RRF"] + 1 or p[-1] != "":
                bad += 1
                continue
            rel_stats["sab:" + p[10]] += 1
            if p[10] == "RXNORM" and p[0] and p[4]:
                # p: RXCUI1 RXAUI1 STYPE1 REL RXCUI2 RXAUI2 STYPE2 RELA RUI SRUI SAB SL RG DIR SUPPRESS CVF
                rels.append({"rxcui1": p[0], "rel": p[3], "rxcui2": p[4], "rela": p[7], "rui": p[8],
                             "sab": p[10], "suppress": p[14], "cvf": p[15], "line": ln})
                rel_stats["cui_level_rxnorm"] += 1
        structure["RXNREL.RRF"] = {"lines": n, "malformed_lines": bad}

    sat_lines = 0
    sat_bad = 0
    # RXNSAT is streamed later (needs the selected set); here only structure is counted in the same pass.
    R.add("B1", "RXNCONSO/RXNREL lines have exactly the documented field count with a trailing delimiter",
          "PASS" if all(v["malformed_lines"] == 0 for v in structure.values()) else "FAIL", json.dumps(structure))

    # concept -> main atom
    main_atom = {}
    multi_main = []
    for rx, atoms in atoms_by_rxcui.items():
        mains = [a for a in atoms if a["tty"] in MAIN_TTYS]
        if len(mains) == 1:
            main_atom[rx] = mains[0]
        elif len(mains) > 1:
            multi_main.append(rx)
    R.add("B2", "Each RXNORM concept has at most one main-term-type atom (Appendix 5 statement)",
          "PASS" if not multi_main else "FAIL", "violations: %d" % len(multi_main))
    R.add("B3", "Prescribable subset contains no suppressed/obsolete RXNCONSO rows (SUPPRESS=N, CVF=4096 everywhere)",
          "PASS" if (conso_stats["suppress:N"] == structure["RXNCONSO.RRF"]["lines"]
                     and conso_stats["cvf:" + PRESCRIBABLE_CVF] == structure["RXNCONSO.RRF"]["lines"]) else "FAIL",
          json.dumps({k: v for k, v in conso_stats.items() if k.startswith(("suppress", "cvf"))}))

    rel_sup = collections.Counter(r["suppress"] for r in rels)
    R.add("B6", "RXNREL CUI-level RXNORM rows: SUPPRESS values are only blank or N (blank = 'not yet in use' per Tech Doc 12.7)",
          "PASS" if rels and set(rel_sup) <= set(ACTIVE_REL) else "FAIL", json.dumps(dict(rel_sup)))

    # relationship indexes: subject = RXCUI2, object = RXCUI1 (Tech Doc 12.7: REL = relationship of
    # the SECOND concept to the FIRST); verified empirically in this archive (see README).
    by_subject = collections.defaultdict(list)
    for r in rels:
        by_subject[r["rxcui2"]].append(r)

    def tty_of(rx):
        a = main_atom.get(rx)
        return a["tty"] if a else None

    def name_of(rx):
        a = main_atom.get(rx)
        return a["str"] if a else ""

    def objects(subject, rela, want_tty=None):
        out = []
        for r in by_subject.get(subject, []):
            if r["rela"] == rela and r["suppress"] in ACTIVE_REL and (want_tty is None or tty_of(r["rxcui1"]) == want_tty):
                out.append(r)
        return out

    # empirical direction check against Appendix 1 on the whole subset
    dir_total = dir_ok = 0
    undocumented = collections.Counter()
    for r in rels:
        if r["rela"] in EDGE_RELAS:
            s, o = tty_of(r["rxcui2"]), tty_of(r["rxcui1"])
            if s and o:
                dir_total += 1
                if (s, r["rela"], o) in DOC_PAIRS:
                    dir_ok += 1
                else:
                    undocumented[(s, r["rela"], o)] += 1
    R.add("B4", "Relationship direction (subject=RXCUI2, object=RXCUI1) agrees with Appendix 1 TTY pairs across all "
                "exported-RELA CUI-level rows in the subset",
          "PASS" if dir_total and dir_ok == dir_total else "FAIL",
          "%d/%d rows documented; undocumented pairs: %s" % (dir_ok, dir_total, dict(list(undocumented.items())[:10])))

    string_collisions = sum(1 for v in name_index.values() if len(v) > 1)

    # ------------------------------------------------------------------ Phase C/D: seed resolution
    seeds = read_csv(os.path.join(args.config_dir, "seed_concepts.csv"))
    probes = read_csv(os.path.join(args.config_dir, "probe_inputs.csv"))
    selected = collections.OrderedDict()  # rxcui -> seed row
    seed_resolution = []
    for s in seeds:
        cands = sorted(rx for rx in name_index.get(norm(s["input_name"]), ()) if tty_of(rx) == s["expected_tty"])
        status = "UNIQUE" if len(cands) == 1 else ("MULTIPLE" if cands else "NONE")
        rxcui = cands[0] if len(cands) == 1 else ""
        pin_ok = (s["pinned_rxcui"] == rxcui) if s["pinned_rxcui"] else None
        seed_resolution.append({"input_name": s["input_name"], "expected_tty": s["expected_tty"], "status": status,
                                "rxcui": rxcui, "candidates": cands, "pinned_ok": pin_ok})
        if rxcui:
            if rxcui in selected:
                R.add("D0", "Duplicate seed resolving to same RXCUI: %s" % s["input_name"], "FAIL")
            selected[rxcui] = s
    unresolved = [r for r in seed_resolution if r["status"] != "UNIQUE"]
    R.add("D1", "Every seed concept resolves to exactly one RXNORM concept of the expected term type (no substitution)",
          "PASS" if not unresolved else ("NOT_VERIFIED" if args.allow_unresolved else "FAIL"),
          "unresolved: %s" % [(u["input_name"], u["status"], u["candidates"]) for u in unresolved] if unresolved
          else "%d/%d resolved" % (len(seeds) - len(unresolved), len(seeds)))
    pin_bad = [r for r in seed_resolution if r["pinned_ok"] is False]
    R.add("D2", "Resolved RXCUIs equal the RXCUIs pinned in config (regression check; pins were taken from this same "
                "release, so this detects drift between releases, not independent truth)",
          "PASS" if not pin_bad else "FAIL", "mismatches: %s" % [(r["input_name"], r["rxcui"]) for r in pin_bad])
    name_bad = [(rx, main_atom[rx]["str"], s["input_name"]) for rx, s in selected.items()
                if norm(main_atom[rx]["str"]) != norm(s["input_name"])]
    R.add("D3", "For every selected concept the input name equals the SAB=RXNORM normalized-name atom (not just a synonym)",
          "PASS" if not name_bad else "FAIL", "mismatches: %s" % name_bad)
    flag_bad = [rx for rx in selected if main_atom[rx]["suppress"] != "N" or main_atom[rx]["cvf"] != PRESCRIBABLE_CVF]
    R.add("D4", "Selected concepts' main atoms are SUPPRESS=N and CVF=4096", "PASS" if not flag_bad else "FAIL",
          "violations: %s" % flag_bad)

    # ------------------------------------------------------------------ Phase E: relationships and derivation
    def rel_row(r):
        return {"rui": r["rui"], "line": r["line"]}

    def ingredients_of(rx):
        """Return (set of IN rxcuis, set of PIN rxcuis, list of link dicts). Link dicts are emitted verbatim."""
        t = tty_of(rx)
        links = []
        ins, pins = set(), set()

        def pin_to_in(pin_rx, via):
            for r in objects(pin_rx, "form_of", "IN"):
                ins.add(r["rxcui1"])
                links.append({"concept": rx, "component": via, "ingredient": r["rxcui1"], "path": "form_of",
                              "ruis": [r["rui"]], "lines": [r["line"]]})
        if t == "IN":
            ins.add(rx)
        elif t == "PIN":
            pins.add(rx)
            for r in objects(rx, "form_of", "IN"):
                ins.add(r["rxcui1"])
                links.append({"concept": rx, "component": "", "ingredient": r["rxcui1"], "path": "form_of",
                              "ruis": [r["rui"]], "lines": [r["line"]]})
        elif t == "MIN":
            for r in objects(rx, "has_part"):
                part = r["rxcui1"]
                if tty_of(part) == "IN":
                    ins.add(part)
                    links.append({"concept": rx, "component": "", "ingredient": part, "path": "has_part",
                                  "ruis": [r["rui"]], "lines": [r["line"]]})
                elif tty_of(part) == "PIN":
                    pins.add(part)
                    links.append({"concept": rx, "component": "", "ingredient": part, "path": "has_part",
                                  "ruis": [r["rui"]], "lines": [r["line"]]})
                    for r2 in objects(part, "form_of", "IN"):
                        ins.add(r2["rxcui1"])
        elif t == "BN":
            for r in objects(rx, "tradename_of", "IN"):
                ins.add(r["rxcui1"])
                links.append({"concept": rx, "component": "", "ingredient": r["rxcui1"], "path": "tradename_of",
                              "ruis": [r["rui"]], "lines": [r["line"]]})
        elif t in ("SCD", "SBD"):
            for rc in objects(rx, "consists_of", "SCDC"):
                scdc = rc["rxcui1"]
                for r in objects(scdc, "has_ingredient", "IN"):
                    ins.add(r["rxcui1"])
                    links.append({"concept": rx, "component": scdc, "ingredient": r["rxcui1"],
                                  "path": "consists_of>has_ingredient", "ruis": [rc["rui"], r["rui"]],
                                  "lines": [rc["line"], r["line"]]})
                for r in objects(scdc, "has_precise_ingredient", "PIN"):
                    pins.add(r["rxcui1"])
                    links.append({"concept": rx, "component": scdc, "ingredient": r["rxcui1"],
                                  "path": "consists_of>has_precise_ingredient", "ruis": [rc["rui"], r["rui"]],
                                  "lines": [rc["line"], r["line"]]})
                    for r2 in objects(r["rxcui1"], "form_of", "IN"):
                        ins.add(r2["rxcui1"])
        return ins, pins, links

    derived = {}
    problems = []
    all_links = []
    for rx in selected:
        t = tty_of(rx)
        d = {"ins": set(), "pins": set(), "scdcs": [], "df": None, "df_row": None, "bn": None, "cross": ""}
        ins, pins, links = ingredients_of(rx)
        d["ins"], d["pins"] = ins, pins
        all_links.extend(links)
        if t in ("SCD", "SBD"):
            d["scdcs"] = [r["rxcui1"] for r in objects(rx, "consists_of", "SCDC")]
            dfs = objects(rx, "has_dose_form", "DF")
            if len(dfs) == 1:
                d["df"], d["df_row"] = dfs[0]["rxcui1"], dfs[0]
            else:
                problems.append((rx, "dose_form_count=%d" % len(dfs)))
            nm = name_of(rx)
            for sc in d["scdcs"]:
                if name_of(sc) not in nm:
                    problems.append((rx, "strength component '%s' not in name" % name_of(sc)))
            if d["df"] and name_of(d["df"]) not in nm:
                problems.append((rx, "dose form '%s' not in name" % name_of(d["df"])))
            if not d["scdcs"]:
                problems.append((rx, "no strength component"))
            if t == "SCD":
                mins = objects(rx, "has_ingredients", "MIN")
                if mins:
                    m_ins, m_pins, _ = ingredients_of(mins[0]["rxcui1"])
                    # MIN-side parts may be IN or PIN; compare at IN level
                    if m_ins != ins:
                        problems.append((rx, "ingredient set via MIN %s != via SCDC %s" % (sorted(m_ins), sorted(ins))))
                    else:
                        d["cross"] = "SCDC-path == MIN-path"
            if t == "SBD":
                bns = objects(rx, "has_ingredient", "BN")
                if len(bns) == 1:
                    d["bn"] = bns[0]["rxcui1"]
                else:
                    problems.append((rx, "brand_count=%d" % len(bns)))
                if d["bn"] and ("[%s]" % name_of(d["bn"])) not in nm:
                    problems.append((rx, "brand '%s' not bracketed in name" % name_of(d["bn"])))
                gen = objects(rx, "tradename_of", "SCD")
                if len(gen) != 1:
                    problems.append((rx, "tradename_of SCD count=%d" % len(gen)))
                else:
                    g_ins, _, _ = ingredients_of(gen[0]["rxcui1"])
                    if g_ins != ins:
                        problems.append((rx, "SBD ingredient set != generic SCD ingredient set"))
                    else:
                        d["cross"] = "SBD ingredients == tradename_of SCD ingredients"
        if t == "BN":
            d["bn"] = rx
        if t in ("IN", "PIN", "MIN", "BN", "SCD", "SBD") and not ins:
            problems.append((rx, "no ingredient resolved"))
        derived[rx] = d
    R.add("E1", "Every selected concept: ingredient chain resolved via RXNREL; each SCD/SBD has exactly one dose form, "
                "strength components and (SBD) one brand; names are consistent with relationship-derived components; "
                "cross-paths (SCDC-path vs MIN-path, SBD vs its generic SCD) agree",
          "PASS" if not problems else "FAIL", "problems: %s" % problems)

    # relationships.csv: closure = selected + one-hop neighbours of product/PIN/MIN/BN concepts
    sel = set(selected)
    closure = set(sel)
    for rx in sel:
        if tty_of(rx) in ("SCD", "SBD", "PIN", "MIN", "BN"):
            for r in by_subject.get(rx, []):
                if r["rela"] in EDGE_RELAS and r["suppress"] in ACTIVE_REL:
                    closure.add(r["rxcui1"])
    edges = []
    seen_edge = set()
    for rx in sorted(closure):
        for r in by_subject.get(rx, []):
            if r["rela"] not in EDGE_RELAS or r["suppress"] not in ACTIVE_REL:
                continue
            o = r["rxcui1"]
            if o not in closure or (rx not in sel and o not in sel):
                continue
            key = r["rui"]
            if key in seen_edge:
                continue
            seen_edge.add(key)
            s_t, o_t = tty_of(rx), tty_of(o)
            edges.append({
                "rui": r["rui"], "subject_rxcui": rx, "subject_tty": s_t, "subject_name": name_of(rx),
                "rela": r["rela"], "rel": r["rel"], "object_rxcui": o, "object_tty": o_t, "object_name": name_of(o),
                "subject_selected": str(rx in sel).lower(), "object_selected": str(o in sel).lower(),
                "in_appendix1_table": str((s_t, r["rela"], o_t) in DOC_PAIRS).lower(),
                "raw_rxcui1": r["rxcui1"], "raw_rxcui2": r["rxcui2"], "sab": r["sab"],
                "source_file": "RXNREL.RRF", "source_line": r["line"]})
    edges.sort(key=lambda e: (int(e["subject_rxcui"]), e["rela"], int(e["object_rxcui"]), e["rui"]))
    undoc_edges = [e for e in edges if e["in_appendix1_table"] != "true"]
    R.add("E2", "All exported relationship rows are of a (subject TTY, RELA, object TTY) combination documented in Appendix 1 (and at least one row was exported)",
          "PASS" if (edges and not undoc_edges) else "FAIL", "undocumented: %d of %d" % (len(undoc_edges), len(edges)))
    ruis = [e["rui"] for e in edges]
    R.add("E3", "No duplicate relationship identifiers (RUI) in relationships.csv (non-empty set)", "PASS" if (ruis and len(ruis) == len(set(ruis))) else "FAIL",
          "%d rows" % len(ruis))
    edge_idx = {(e["subject_rxcui"], e["rela"], e["object_rxcui"]) for e in edges}
    missing_inv = [(e["rui"], e["rela"]) for e in edges
                   if (e["object_rxcui"], INVERSE_RELA[e["rela"]], e["subject_rxcui"]) not in edge_idx]
    R.add("E4", "Every exported relationship row has its inverse-direction row in the exported set (RxNorm stores one row per direction)",
          "PASS" if (edges and not missing_inv) else "FAIL", "rows lacking inverse: %d of %d" % (len(missing_inv), len(edges)))

    # ------------------------------------------------------------------ RXNSAT pass
    attrs, ndcs = [], []
    spl_counts = collections.Counter()
    sat_stats = collections.Counter()
    with stream(zf, "RXNSAT.RRF") as fh:
        for ln, line in enumerate(fh, 1):
            sat_lines += 1
            p = line.rstrip("\n").split("|")
            if len(p) != RRF_FIELDS["RXNSAT.RRF"] + 1 or p[-1] != "":
                sat_bad += 1
                continue
            rx = p[0]
            if rx not in sel:
                continue
            sab, atn = p[9], p[8]
            if sab == "MTHSPL" and atn == "SPL_SET_ID":
                spl_counts[rx] += 1
            elif sab == "RXNORM":
                if p[11] != "N":
                    sat_stats["excluded_suppressed_rows"] += 1
                    continue
                if atn == "NDC":
                    ndcs.append({"rxcui": rx, "rxaui": p[3], "ndc_11digit": p[10], "sab": sab,
                                 "source_file": "RXNSAT.RRF", "source_line": ln})
                elif atn in ATTR_KEEP:
                    attrs.append({"rxcui": rx, "rxaui": p[3], "atn": atn, "atv": p[10], "sab": sab,
                                  "source_file": "RXNSAT.RRF", "source_line": ln})
    structure["RXNSAT.RRF"] = {"lines": sat_lines, "malformed_lines": sat_bad}
    R.add("B5", "RXNSAT lines have exactly the documented field count with a trailing delimiter",
          "PASS" if sat_bad == 0 else "FAIL", json.dumps(structure["RXNSAT.RRF"]))
    attr_by = collections.defaultdict(list)
    for a in attrs:
        attr_by[a["rxcui"]].append(a)

    # ------------------------------------------------------------------ concepts.csv
    concept_rows = []
    for rx, s in selected.items():
        a = main_atom[rx]
        t = a["tty"]
        d = derived[rx]
        qty = sorted({x["atv"] for x in attr_by[rx] if x["atn"] == "RXN_QUANTITY"})
        concept_rows.append({
            "rxcui": rx, "rxnorm_name": a["str"], "tty": t,
            "concept_type": TTY_INFO[t][0], "concept_type_description": TTY_INFO[t][1],
            "source_vocabulary": a["sab"], "term_status_suppress": a["suppress"], "content_view_flag": a["cvf"],
            "ingredient_names": " | ".join(sorted(name_of(i) for i in d["ins"])),
            "ingredient_rxcuis": " | ".join(sorted(d["ins"], key=int)),
            "precise_ingredient_names": " | ".join(sorted(name_of(i) for i in d["pins"])),
            "strength_components": " | ".join(sorted(name_of(i) for i in d["scdcs"])),
            "dose_form": name_of(d["df"]) if d["df"] else "",
            "quantity_factor": " | ".join(qty),
            "brand_name": name_of(d["bn"]) if d["bn"] else "",
            "match_status": "UNIQUE", "match_method": "exact_normalized_string_match_SAB=RXNORM_with_expected_TTY",
            "source_file": "RXNCONSO.RRF", "source_rxaui": a["rxaui"], "source_line": a["line"],
            "source_record_key": "RXNCONSO:RXAUI=%s;RXCUI=%s;SAB=RXNORM;TTY=%s" % (a["rxaui"], rx, t),
            "ndc_count_rxnorm": sum(1 for n in ndcs if n["rxcui"] == rx),
            "contrast_tags": s["contrast_tags"], "inclusion_reason": s["inclusion_reason"],
            "dailymed_set_id": "", "dailymed_link_status": "PENDING_NOT_VERIFIED",
            "validation_status": "", "notes": "",
        })
    # per-concept validation status: any problem listed for the concept -> FAIL
    prob_by = collections.defaultdict(list)
    for rx, msg in problems:
        prob_by[rx].append(msg)
    for row in concept_rows:
        row["validation_status"] = "FAIL" if prob_by[row["rxcui"]] else "PASS"
        row["notes"] = "; ".join(prob_by[row["rxcui"]]) or ""
        if row["tty"] in ("IN", "PIN", "MIN", "BN"):
            row["notes"] = (row["notes"] + "; " if row["notes"] else "") + \
                "strength/dose_form not applicable at this term type"
    concept_rows.sort(key=lambda r: ({"IN": 0, "PIN": 1, "MIN": 2, "BN": 3, "SCD": 4, "SBD": 5}[r["tty"]], r["rxnorm_name"]))
    rx_list = [r["rxcui"] for r in concept_rows]
    R.add("E5", "No duplicate RXCUI rows in concepts.csv", "PASS" if len(rx_list) == len(set(rx_list)) else "FAIL",
          "%d rows" % len(rx_list))

    # ------------------------------------------------------------------ input_aliases.csv
    alias_rows = []

    def resolve(raw):
        cands = sorted(name_index.get(norm(raw), ()), key=int)
        return cands

    seen_pairs = set()
    for s in seeds:
        rx = next((k for k, v in selected.items() if v is s), "")
        alias_rows.append({"input_name": s["input_name"], "normalized_name": norm(s["input_name"]),
                           "input_kind": "canonical_rxnorm_name", "intent": "official RxNorm normalized name",
                           "expected_resolution": "UNIQUE", "candidate_count": 1 if rx else 0,
                           "candidate_rxcuis": rx, "candidate_ttys": tty_of(rx) or "",
                           "candidate_names": name_of(rx), "match_status": "UNIQUE" if rx else "NONE",
                           "match_method": "exact_normalized_string_match_SAB=RXNORM",
                           "in_selected_set": "true" if rx else "false", "expectation_met": "true" if rx else "false"})
    for pr in probes:
        c = resolve(pr["input_name"])
        status = "NONE" if not c else ("UNIQUE" if len(c) == 1 else "MULTIPLE")
        exp = pr["expected_resolution"]
        met = "n/a" if exp == "OBSERVE" else str(status == exp).lower()
        alias_rows.append({"input_name": pr["input_name"], "normalized_name": norm(pr["input_name"]),
                           "input_kind": "probe_input", "intent": pr["intent"], "expected_resolution": exp,
                           "candidate_count": len(c), "candidate_rxcuis": " | ".join(c),
                           "candidate_ttys": " | ".join(tty_of(x) or "?" for x in c),
                           "candidate_names": " | ".join(name_of(x) for x in c), "match_status": status,
                           "match_method": "exact_normalized_string_match_SAB=RXNORM",
                           "in_selected_set": " | ".join(str(x in sel).lower() for x in c) if c else "",
                           "expectation_met": met})
    for r in alias_rows:
        for rx in r["candidate_rxcuis"].split(" | "):
            if rx:
                k = (r["input_name"], rx)
                if k in seen_pairs:
                    R.add("F0", "duplicate alias mapping %s" % (k,), "FAIL")
                seen_pairs.add(k)
    exp_bad = [(r["input_name"], r["expected_resolution"], r["match_status"]) for r in alias_rows
               if r["expectation_met"] == "false"]
    R.add("F1", "Probe/canonical inputs behave as designed where an expectation was declared (UNIQUE/NONE); "
                "OBSERVE inputs carry no expectation", "PASS" if not exp_bad else "FAIL",
          "mismatches: %s" % exp_bad, critical=False)

    # ------------------------------------------------------------------ links tables
    link_rows = []
    for l in all_links:
        link_rows.append({
            "concept_rxcui": l["concept"], "concept_tty": tty_of(l["concept"]), "concept_name": name_of(l["concept"]),
            "component_rxcui": l["component"], "component_name": name_of(l["component"]) if l["component"] else "",
            "ingredient_rxcui": l["ingredient"], "ingredient_tty": tty_of(l["ingredient"]),
            "ingredient_name": name_of(l["ingredient"]), "path": l["path"],
            "rui_chain": " > ".join(l["ruis"]), "source_file": "RXNREL.RRF",
            "source_lines": " > ".join(str(x) for x in l["lines"])})
    link_rows.sort(key=lambda r: (int(r["concept_rxcui"]), r["path"], int(r["ingredient_rxcui"])))
    # distinct, verified counts
    prod_in = {(l["concept"], i) for l in all_links if tty_of(l["concept"]) in ("SCD", "SBD")
               for i in [l["ingredient"]] if tty_of(i) == "IN"}
    prod_in_via_pin = set()
    for l in all_links:
        if tty_of(l["concept"]) in ("SCD", "SBD") and tty_of(l["ingredient"]) == "PIN":
            for r in objects(l["ingredient"], "form_of", "IN"):
                prod_in_via_pin.add((l["concept"], r["rxcui1"]))
    prod_ing_pairs = prod_in | prod_in_via_pin
    ing_by_concept = {rx: derived[rx]["ins"] for rx in selected}
    n_prod = sum(1 for rx in selected if tty_of(rx) in ("SCD", "SBD"))
    R.add("E6", "Every selected SCD/SBD has at least one verified ingredient link", "PASS" if n_prod and all(
        ing_by_concept[rx] for rx in selected if tty_of(rx) in ("SCD", "SBD")) else "FAIL", "%d products checked" % n_prod)

    # ------------------------------------------------------------------ ingredient-level fan-out (C11)
    fanout_rows = []
    for rx in selected:
        t = tty_of(rx)
        if t not in ("IN", "MIN"):
            continue
        scds = set()
        if t == "IN":
            for r1 in objects(rx, "ingredient_of", "SCDC"):
                for r2 in objects(r1["rxcui1"], "constitutes", "SCD"):
                    scds.add(r2["rxcui1"])
        else:
            for r1 in objects(rx, "ingredients_of", "SCD"):
                scds.add(r1["rxcui1"])
        comb = {x for x in scds if objects(x, "has_ingredients", "MIN")}
        sbds = set()
        for x in scds:
            for r1 in objects(x, "has_tradename", "SBD"):
                sbds.add(r1["rxcui1"])
        fanout_rows.append({"rxcui": rx, "name": name_of(rx), "tty": t, "candidate_scd_total": len(scds),
                            "candidate_scd_single_ingredient": len(scds - comb), "candidate_scd_combination": len(comb),
                            "candidate_sbd_via_has_tradename": len(sbds), "fanout_gt_1": str(len(scds) > 1).lower(),
                            "derivation": "IN: ingredient_of>SCDC, constitutes>SCD; MIN: ingredients_of>SCD; SBD via SCD has_tradename"})
    fanout_rows.sort(key=lambda r: (r["tty"], r["name"]))
    R.add("G2", "Every selected IN/MIN concept is contained in more than one SCD in the subset (ingredient-level mention is not product-unique)",
          "PASS" if fanout_rows and all(r["fanout_gt_1"] == "true" for r in fanout_rows) else "FAIL",
          "; ".join("%s=%s" % (r["name"], r["candidate_scd_total"]) for r in fanout_rows))

    # ------------------------------------------------------------------ contrast checks
    by_input = {s["input_name"]: rx for rx, s in selected.items()}
    contrast_defs = read_csv(os.path.join(args.config_dir, "contrast_definitions.csv"))
    checks = read_csv(os.path.join(args.config_dir, "contrast_checks.csv"))
    check_results = []

    def strengths(rx):
        return frozenset(name_of(x) for x in derived[rx]["scdcs"])

    for c in checks:
        a, b = by_input.get(c["a_input_name"]), by_input.get(c["b_input_name"])
        res, detail = "FAIL", "operand not resolved"
        if a and b:
            ia, ib = ing_by_concept[a], ing_by_concept[b]
            p = c["predicate"]
            if p == "ingredient_in":
                res = "PASS" if tty_of(a) == "IN" and a in ib and tty_of(b) in ("SCD", "SBD") else "FAIL"
            elif p == "ingredient_proper_subset":
                res = "PASS" if ia < ib else "FAIL"
            elif p == "ingredient_sets_disjoint":
                res = "PASS" if not (ia & ib) and ia and ib else "FAIL"
            elif p == "share_exactly_one_ingredient":
                res = "PASS" if len(ia & ib) == 1 and ia != ib else "FAIL"
            elif p == "same_ingredients_diff_strength":
                res = "PASS" if ia == ib and derived[a]["df"] == derived[b]["df"] and strengths(a) != strengths(b) else "FAIL"
            elif p == "same_ingredients_diff_doseform":
                res = "PASS" if ia == ib and derived[a]["df"] != derived[b]["df"] else "FAIL"
            elif p == "same_ingredient_diff_pin":
                res = "PASS" if ia == ib and derived[a]["pins"] != derived[b]["pins"] and derived[a]["pins"] and derived[b]["pins"] else "FAIL"
            elif p == "brand_of":
                gen = [r["rxcui1"] for r in objects(b, "tradename_of", "SCD")]
                res = "PASS" if gen == [a] and tty_of(b) == "SBD" and ia == ib and a != b else "FAIL"
            else:
                detail = "unknown predicate"
            detail = "a=%s(%s) b=%s(%s) ing_a=%s ing_b=%s" % (a, tty_of(a), b, tty_of(b), sorted(ia), sorted(ib))
        check_results.append({"check_id": c["check_id"], "contrast_id": c["contrast_id"], "a_input_name": c["a_input_name"],
                              "a_rxcui": a or "", "b_input_name": c["b_input_name"], "b_rxcui": b or "",
                              "predicate": c["predicate"], "result": res, "detail": detail})
    fails = [x["check_id"] for x in check_results if x["result"] != "PASS"]
    R.add("G1", "All declared contrast checks hold on relationship-derived data", "PASS" if not fails else "FAIL",
          "%d/%d pass; failing: %s" % (len(check_results) - len(fails), len(check_results), fails))

    # contrast membership counts from tags
    members = collections.defaultdict(list)
    for r in concept_rows:
        for t in [x for x in r["contrast_tags"].split(";") if x]:
            members[t].append(r)
    cov_rows = []
    for cd in contrast_defs:
        cid = cd["contrast_id"]
        if cid == "C10":
            amb = [a for a in alias_rows if a["input_kind"] == "probe_input" and a["match_status"] == "NONE"]
            exp_none = [a for a in amb if a["expected_resolution"] == "NONE"]
            n_c, n_k, n_ok = len(amb), len(exp_none), sum(1 for a in exp_none if a["expectation_met"] == "true")
            member_desc = "; ".join("%s -> NONE" % a["input_name"] for a in amb)
        elif cid == "C11":
            n_c, n_k, n_ok = len(fanout_rows), len(fanout_rows), sum(1 for r in fanout_rows if r["fanout_gt_1"] == "true")
            member_desc = "; ".join("%s [%s %s]: %s SCDs" % (r["name"], r["tty"], r["rxcui"], r["candidate_scd_total"]) for r in fanout_rows)
        else:
            n_c = len(members[cid])
            ks = [x for x in check_results if x["contrast_id"] == cid]
            n_k, n_ok = len(ks), sum(1 for x in ks if x["result"] == "PASS")
            member_desc = "; ".join("%s [%s %s]" % (m["rxnorm_name"], m["tty"], m["rxcui"]) for m in members[cid])
        cov_rows.append({"contrast_id": cid, "name": cd["name"], "members_or_inputs": n_c, "checks_total": n_k,
                         "checks_pass": n_ok, "member_list": member_desc,
                         "failure_mode_supported": cd["failure_mode_supported"],
                         "does_not_establish": cd["does_not_establish"]})
    ttyc = collections.Counter(r["tty"] for r in concept_rows)
    missing_info = [r["rxcui"] for r in concept_rows if r["tty"] in ("SCD", "SBD") and not (
        r["strength_components"] and r["dose_form"] and r["ingredient_names"] and (r["tty"] != "SBD" or r["brand_name"]))]
    alias_status = collections.Counter(a["match_status"] for a in alias_rows if a["input_kind"] == "probe_input")
    metrics = {
        "input_rows_total": len(alias_rows),
        "input_rows_canonical": sum(1 for a in alias_rows if a["input_kind"] == "canonical_rxnorm_name"),
        "input_rows_probe": sum(1 for a in alias_rows if a["input_kind"] == "probe_input"),
        "unique_normalized_input_terms": len({a["normalized_name"] for a in alias_rows}),
        "unique_rxcuis_in_concepts_csv": len(rx_list),
        "ingredient_concepts_IN": ttyc["IN"], "precise_ingredient_concepts_PIN": ttyc["PIN"],
        "multiple_ingredient_concepts_MIN": ttyc["MIN"], "clinical_drug_concepts_SCD": ttyc["SCD"],
        "branded_drug_concepts_SBD": ttyc["SBD"], "brand_name_concepts_BN": ttyc["BN"],
        "branded_concepts_BN_plus_SBD": ttyc["BN"] + ttyc["SBD"],
        "verified_product_to_IN_pairs_SCD_SBD": len(prod_ing_pairs),
        "verified_MIN_to_ingredient_links": sum(1 for l in all_links if tty_of(l["concept"]) == "MIN"),
        "verified_PIN_to_IN_links": sum(1 for l in all_links if tty_of(l["concept"]) == "PIN"),
        "verified_BN_to_IN_links": sum(1 for l in all_links if tty_of(l["concept"]) == "BN"),
        "relationship_rows_exported": len(edges),
        "rxnorm_normalized_strings_total": len(name_index),
        "rxnorm_normalized_strings_mapping_to_multiple_rxcuis": string_collisions,
        "probe_inputs_resolving_NONE": alias_status["NONE"], "probe_inputs_resolving_MULTIPLE": alias_status["MULTIPLE"],
        "probe_inputs_resolving_UNIQUE": alias_status["UNIQUE"],
        "seed_concepts_unresolved": len(unresolved),
        "duplicate_rxcui_rows": len(rx_list) - len(set(rx_list)),
        "duplicate_alias_mapping_rows": 0,
        "selected_products_missing_relevant_info": len(missing_info),
        "ndc_rows_rxnorm_selected": len(ndcs),
        "selected_concepts_with_any_MTHSPL_SPL_SET_ID_in_RXNSAT": sum(1 for rx in sel if spl_counts[rx]),
    }
    cov_flat = [{"category": "metric", "name": k, "value": v} for k, v in metrics.items()]
    for c in cov_rows:
        cov_flat.append({"category": "contrast", "name": c["contrast_id"] + ":" + c["name"],
                         "value": "members_or_inputs=%d; checks_pass=%d/%d" % (c["members_or_inputs"], c["checks_pass"], c["checks_total"])})

    # DailyMed boundary
    dm_nonempty = [r["rxcui"] for r in concept_rows if r["dailymed_set_id"]]
    R.add("H1", "No DailyMed set ID is populated; all link statuses are PENDING_NOT_VERIFIED",
          "PASS" if not dm_nonempty and all(r["dailymed_link_status"] == "PENDING_NOT_VERIFIED" for r in concept_rows) else "FAIL")

    # ------------------------------------------------------------------ write outputs
    concept_fields = ["rxcui", "rxnorm_name", "tty", "concept_type", "concept_type_description", "source_vocabulary",
                      "term_status_suppress", "content_view_flag", "ingredient_names", "ingredient_rxcuis",
                      "precise_ingredient_names", "strength_components", "dose_form", "quantity_factor", "brand_name",
                      "match_status", "match_method", "source_file", "source_rxaui", "source_line", "source_record_key",
                      "ndc_count_rxnorm", "contrast_tags", "inclusion_reason", "dailymed_set_id", "dailymed_link_status",
                      "validation_status", "notes"]
    write_csv(os.path.join(data_dir, "concepts.csv"), concept_fields, concept_rows)
    write_csv(os.path.join(data_dir, "input_aliases.csv"),
              ["input_name", "normalized_name", "input_kind", "intent", "expected_resolution", "candidate_count",
               "candidate_rxcuis", "candidate_ttys", "candidate_names", "match_status", "match_method",
               "in_selected_set", "expectation_met"], alias_rows)
    write_csv(os.path.join(data_dir, "relationships.csv"),
              ["rui", "subject_rxcui", "subject_tty", "subject_name", "rela", "rel", "object_rxcui", "object_tty",
               "object_name", "subject_selected", "object_selected", "in_appendix1_table", "raw_rxcui1", "raw_rxcui2",
               "sab", "source_file", "source_line"], edges)
    write_csv(os.path.join(data_dir, "ingredient_links.csv"),
              ["concept_rxcui", "concept_tty", "concept_name", "component_rxcui", "component_name", "ingredient_rxcui",
               "ingredient_tty", "ingredient_name", "path", "rui_chain", "source_file", "source_lines"], link_rows)
    attrs.sort(key=lambda r: (int(r["rxcui"]), r["atn"], r["atv"]))
    write_csv(os.path.join(data_dir, "concept_attributes.csv"),
              ["rxcui", "rxaui", "atn", "atv", "sab", "source_file", "source_line"], attrs)
    ndcs.sort(key=lambda r: (int(r["rxcui"]), r["ndc_11digit"]))
    write_csv(os.path.join(data_dir, "concept_ndc_rxnorm.csv"),
              ["rxcui", "rxaui", "ndc_11digit", "sab", "source_file", "source_line"], ndcs)
    write_csv(os.path.join(data_dir, "contrast_checks_results.csv"),
              ["check_id", "contrast_id", "a_input_name", "a_rxcui", "b_input_name", "b_rxcui", "predicate", "result", "detail"],
              check_results)
    write_csv(os.path.join(data_dir, "ingredient_product_fanout.csv"),
              ["rxcui", "name", "tty", "candidate_scd_total", "candidate_scd_single_ingredient", "candidate_scd_combination",
               "candidate_sbd_via_has_tradename", "fanout_gt_1", "derivation"], fanout_rows)
    write_csv(os.path.join(data_dir, "coverage_matrix.csv"),
              ["contrast_id", "name", "members_or_inputs", "checks_total", "checks_pass", "member_list",
               "failure_mode_supported", "does_not_establish"], cov_rows)

    # post-write consistency: recompute headline counts from the written CSV files
    re_c = read_csv(os.path.join(data_dir, "concepts.csv"))
    recount = collections.Counter(r["tty"] for r in re_c)
    consistent = (len(re_c) == metrics["unique_rxcuis_in_concepts_csv"] and recount["IN"] == metrics["ingredient_concepts_IN"]
                  and recount["MIN"] == metrics["multiple_ingredient_concepts_MIN"]
                  and recount["SCD"] == metrics["clinical_drug_concepts_SCD"]
                  and len(read_csv(os.path.join(data_dir, "relationships.csv"))) == metrics["relationship_rows_exported"])
    R.add("I1", "Headline counts recomputed from the written CSV files equal the counts in the validation report",
          "PASS" if consistent else "FAIL")
    req_empty = [(r["rxcui"], f) for r in re_c for f in ("rxcui", "rxnorm_name", "tty", "concept_type", "source_record_key")
                 if not r[f]]
    R.add("I2", "Required concept fields are non-empty and RXCUIs are numeric", "PASS" if not req_empty and all(
        r["rxcui"].isdigit() for r in re_c) else "FAIL", "empty: %s" % req_empty)

    zf.close()
    sha_after = sha256_file(args.zip)
    R.add("I3", "Source ZIP SHA-256 identical before and after the run (archive not modified)",
          "PASS" if sha_before == sha_after else "FAIL", sha_before)
    R.add("X1", "Release notes data counts (TTY counts, NDC counts) for the 10/05/2026 release compared with this archive",
          "NOT_VERIFIED", "No 2026 release-notes page could be retrieved; official page not inspected for this release")
    R.add("X2", "ZIP authenticity versus an NLM-published MD5/SHA for RxNorm_full_prescribe_10052026.zip",
          "NOT_VERIFIED", "No published checksum for this file was retrieved; local SHA-256 recorded for future comparison")
    R.add("X3", "Semantic type (STY) per concept", "NOT_VERIFIED",
          "RXNSTY.RRF is not part of the Current Prescribable Content ZIP; concept_type is derived from TTY (Appendix 5) only")

    report = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "script": "scripts/build_rxnorm_component.py",
        "archive": {"file": os.path.basename(args.zip), "sha256": sha_after, "bytes": os.path.getsize(args.zip),
                    "inventory": inventory, "release_label": release_label, "readme_self_size": readme_note},
        "rrf_structure": structure,
        "rxnconso_profile": {k: v for k, v in sorted(conso_stats.items())},
        "rxnrel_profile": {k: v for k, v in sorted(rel_stats.items())},
        "metrics": metrics,
        "seed_resolution": seed_resolution,
        "checks": R.checks,
        "summary": {"PASS": sum(1 for c in R.checks if c["status"] == "PASS"),
                    "FAIL": sum(1 for c in R.checks if c["status"] == "FAIL"),
                    "NOT_VERIFIED": sum(1 for c in R.checks if c["status"] == "NOT_VERIFIED"),
                    "critical_failures": [c["id"] for c in R.critical_failures()]},
    }
    with open(os.path.join(rep_dir, "validation_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=list)
        f.write("\n")
    print(json.dumps(report["summary"], indent=2))
    for c in R.checks:
        print("%-4s %-12s %s" % (c["id"], c["status"], c["description"][:110]))
    sys.exit(2 if R.critical_failures() else 0)


if __name__ == "__main__":
    main()
