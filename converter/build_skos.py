"""Build SKOS concept schemes for CV1 (Actions), CV2 (Purpose Constraints) and
CV3 (Other Constraints) from the SubGroup 2 "Actions and Purposes" Google Sheet.

Usage (from this directory):
  uv run --no-project --with openpyxl --with rdflib python build_skos.py               # download, else bundled copy
  uv run --no-project --with openpyxl --with rdflib python build_skos.py --xlsx F.xlsx # use a specific .xlsx

Writes cv1-actions.ttl, cv2-purposes.ttl, cv3-constraints.ttl and cdif-access-vocab.ttl
(all three combined) to ../config/.

The sheet is downloaded first; if that fails, the bundled copy "Actions and Purposes.xlsx"
next to this script is used instead (and refreshed whenever a download succeeds).
Downloading: if the sheet is shared as "Anyone with the link can view" no login is needed.
Otherwise set GOOGLE_ACCESS_TOKEN to an OAuth token with Drive read access, e.g.
  GOOGLE_ACCESS_TOKEN=$(gcloud auth print-access-token \
      --scopes=https://www.googleapis.com/auth/drive.readonly) uv run --no-project ... build_skos.py
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import openpyxl
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, SKOS, XSD

HERE = Path(__file__).resolve().parent
BUNDLED_XLSX = HERE / "Actions and Purposes.xlsx"
SHEET_ID = "1TxeIVLdYr6nXj07AyGzbhHPQdDWfxtO8TvlhPGKRsW0"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

BASE = "https://odrl.codata.org/"
CV1 = Namespace(BASE + "cv1/")
CV2 = Namespace(BASE + "cv2/")
CV3 = Namespace(BASE + "cv3/")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
CC = Namespace("http://creativecommons.org/ns#")
DPV = Namespace("https://w3id.org/dpv#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
DATE = Literal("2026-11-04", datatype=XSD.date)

# ODRL common-vocabulary terms that actually live in the Creative Commons namespace.
CC_TERMS = {"derivativeworks": "DerivativeWorks", "distribution": "Distribution", "reproduction": "Reproduction"}

# ODRL terms that exist in the ODRL 2.2 vocabulary but are not flagged "ODRL Common?" in the sheet.
EXTRA_ODRL = {"Modify": "modify", "secondaryUse": "secondaryUse", "Share": "share", "extractWord": "extractWord"}


def clean(v):
    return re.sub(r"\s+", " ", str(v)).strip() if v is not None else ""


def camel(label, upper):
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", label) if p]
    if upper:
        return "".join(p[0].upper() + p[1:] for p in parts)
    head = parts[0].lower() if parts[0].isupper() else parts[0][0].lower() + parts[0][1:]  # "AI" -> "ai"
    return head + "".join(p[0].upper() + p[1:] for p in parts[1:])


def rows(ws, first, ncols):
    for r in ws.iter_rows(min_row=first, max_col=ncols):
        yield [clean(c.value) for c in r], r[0].row


def new_graph():
    g = Graph()
    for p, ns in [("skos", SKOS), ("dct", DCTERMS), ("owl", OWL), ("odrl", ODRL), ("cc", CC),
                  ("dpv", DPV), ("obo", OBO), ("cv1", CV1), ("cv2", CV2), ("cv3", CV3)]:
        g.bind(p, ns)
    return g


def scheme(g, ns, title, description, source):
    s = URIRef(str(ns).rstrip("/"))
    g.add((s, RDF.type, SKOS.ConceptScheme))
    g.add((s, DCTERMS.title, Literal(title, lang="en")))
    g.add((s, DCTERMS.description, Literal(description, lang="en")))
    g.add((s, DCTERMS.source, URIRef(source)))
    g.add((s, DCTERMS.created, DATE))
    return s


def concept(g, s, uri, label, top=True):
    g.add((uri, RDF.type, SKOS.Concept))
    g.add((uri, SKOS.prefLabel, Literal(label, lang="en")))
    g.add((uri, SKOS.inScheme, s))
    if top:
        g.add((uri, SKOS.topConceptOf, s))
        g.add((s, SKOS.hasTopConcept, uri))


def collection(g, uri, label, members):
    g.add((uri, RDF.type, SKOS.Collection))
    g.add((uri, SKOS.prefLabel, Literal(label, lang="en")))
    for m in members:
        g.add((uri, SKOS.member, m))


# --------------------------------------------------------------------------- CV1
def build_cv1(ws, extra_duties):
    g = new_graph()
    s = scheme(g, CV1, "CDIF Actions (CV1)",
               "Actions that can be permitted, prohibited or required (duties) in CDIF access "
               "policies. Re-uses the ODRL Common Vocabulary where possible.",
               "https://www.w3.org/TR/odrl-vocab/#actionsCommon")
    by_label, deprecated, rule_types = {}, [], {"Duty": [], "Prohibition": [], "Permission": []}
    odrl_common, cdif_ext = [], []

    for (label, common, src, note), _ in rows(ws, 5, 4):
        if not label:
            continue
        uri = CV1[camel(label, upper=False)]
        concept(g, s, uri, label)
        by_label[label.lower()] = uri

        if common.startswith("Yes") and "#term-" in src:
            term = src.split("#term-")[1]
            target = CC[CC_TERMS[term.lower()]] if term.lower() in CC_TERMS else ODRL[term[0].lower() + term[1:]]
            g.add((uri, SKOS.exactMatch, target))
            g.add((uri, DCTERMS.source, URIRef(src)))
            odrl_common.append(uri)
        else:
            cdif_ext.append(uri)
            if label in EXTRA_ODRL:
                g.add((uri, SKOS.exactMatch, ODRL[EXTRA_ODRL[label]]))
                g.add((uri, SKOS.editorialNote, Literal(
                    "Mapping to ODRL added during SKOS conversion; not stated in source sheet.", lang="en")))

        if note:
            g.add((uri, SKOS.scopeNote, Literal(note, lang="en")))
            m = re.match(r"(?i)deprecated(?: by (\S+))?", note)
            if m:
                deprecated.append((uri, m.group(1)))
            # notes such as "Duty", "Duty/Prohibition (...)", "Permission with ..." name the ODRL rule type
            head = re.split(r"[(,]| e\.g\.| with | at | during ", note)[0]
            for rt in rule_types:
                if re.search(rf"\b{rt}\b", head):
                    rule_types[rt].append(uri)
            if "deprecated" in note.lower() and not m:   # e.g. "Deprecated, ..." on Ad-hoc sharing
                deprecated.append((uri, None))

    # duty actions named in CV3's "ASSOCIATED DUTY ACTION" column that CV1 does not list yet
    for name, origin in extra_duties:
        if name.lower() in by_label:
            continue
        uri = CV1[camel(name, upper=False)]
        concept(g, s, uri, name)
        by_label[name.lower()] = uri
        cdif_ext.append(uri)
        rule_types["Duty"].append(uri)
        g.add((uri, SKOS.editorialNote, Literal(
            f"Added from the CV3 sheet, where it is the associated duty action of '{origin}'.", lang="en")))

    # deprecations; point replacements at the CDIF concept for the replacing ODRL action
    for uri, by in deprecated:
        g.add((uri, OWL.deprecated, Literal(True)))
        if by:
            repl = by_label.get(by.rstrip("/").split("/")[-1].lower())
            g.add((uri, DCTERMS.isReplacedBy, repl if repl else URIRef(by)))

    collection(g, CV1["collection/odrlCommon"], "Actions from the ODRL Common Vocabulary", odrl_common)
    collection(g, CV1["collection/cdifExtension"], "CDIF-specific actions", cdif_ext)
    for rt, members in rule_types.items():
        collection(g, CV1[f"collection/{rt.lower()}Actions"],
                   f"Actions typically used in an ODRL {rt}", members)
    return g


# --------------------------------------------------------------------------- CV2
def build_cv2(ws):
    g = new_graph()
    s = scheme(g, CV2, "CDIF Purpose Constraints (CV2)",
               "Purposes used as constraints on CDIF actions, re-using Data Privacy Vocabulary (DPV) "
               "purpose concepts.", "https://w3id.org/dpv/modules/purposes")
    data = [(r, n) for r, n in rows(ws, 5, 5) if r[0]]
    by_label = {}
    for (label, _src, _parent, iri, note), _ in data:
        uri = CV2[camel(label, upper=True)]
        by_label[label.lower().replace(" ", "").replace("-", "")] = uri
        concept(g, s, uri, label, top=False)
        local = iri.split("#")[-1] if "#" in iri else camel(label, upper=True)
        g.add((uri, SKOS.exactMatch, DPV[local]))
        if note:
            g.add((uri, SKOS.definition, Literal(note, lang="en")))

    for (label, _src, parent, _iri, _note), _ in data:
        uri = by_label[label.lower().replace(" ", "").replace("-", "")]
        if parent == "Root":
            g.add((uri, SKOS.topConceptOf, s))
            g.add((s, SKOS.hasTopConcept, uri))
            continue
        if not parent:
            parent = "Purpose"
            g.add((uri, SKOS.editorialNote, Literal(
                "Parent not given in source sheet; set to Purpose following the DPV hierarchy.", lang="en")))
        for p in parent.split(";"):
            key = p.split("#")[-1].strip().lower().replace(" ", "").replace("-", "")
            g.add((uri, SKOS.broader, by_label[key]))
            g.add((by_label[key], SKOS.narrower, uri))
    return g


# --------------------------------------------------------------------------- CV3
def build_cv3(ws, cv1):
    g = new_graph()
    s = scheme(g, CV3, "CDIF Other Constraints (CV3)",
               "Other constraints describing the scope of applicability of a CDIF access policy "
               "(environment, legal, usage context, person, identity, role, financial, ...).",
               "https://www.w3.org/TR/odrl-vocab/#actionsCommon")
    cv1_labels = {str(o).lower(): sub for sub, o in cv1.subject_objects(SKOS.prefLabel)}
    last = None
    for (label, src, alt, note, duty, refinement), _ in rows(ws, 5, 6):
        if src.startswith("DUO:"):   # DUO-based rows are not part of CV3 (group decision 2026-11-04)
            last = None
            continue
        if label:
            last = CV3[camel(label, upper=True)]
            concept(g, s, last, label)
            if note:
                g.add((last, SKOS.scopeNote, Literal(note, lang="en")))
            if alt:
                g.add((last, SKOS.editorialNote, Literal(f"DPV/ODRL alternative: {alt}", lang="en")))
            if refinement:
                g.add((last, SKOS.editorialNote, Literal(f"Refinement: {refinement}", lang="en")))
        # associated duty action (may continue on a row with an empty label, e.g. row 19)
        if duty and duty.lower() != "x" and last is not None:
            target = cv1_labels.get(duty.lower())
            if target:
                g.add((last, SKOS.related, target))
            g.add((last, SKOS.note, Literal(f"Associated duty action: {duty}", lang="en")))
    return g


def cv3_duty_actions(ws):
    """(action name, constraint label) for single-term entries in CV3's duty-action column."""
    out, origin = [], None
    for (label, _src, _alt, _note, duty, _ref), _ in rows(ws, 5, 6):
        origin = label or origin
        if re.fullmatch(r"[A-Z][A-Za-z]+", duty):
            out.append((duty, origin))
    return out


def download_sheet(sheet_id, dest):
    """Download the Google Sheet as .xlsx: Drive API with a token, else the public export link."""
    token = os.environ.get("GOOGLE_ACCESS_TOKEN")
    if token:
        url = f"https://www.googleapis.com/drive/v3/files/{sheet_id}/export?mimeType={XLSX_MIME}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    else:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        hint = ("check that the token has Drive read access to the sheet" if token else
                "the sheet is not public: share it as 'Anyone with the link can view', "
                "set GOOGLE_ACCESS_TOKEN, or pass --xlsx with a downloaded copy")
        raise RuntimeError(f"HTTP {e.code}: {hint}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"network error: {e.reason}") from e
    if not data.startswith(b"PK"):   # .xlsx is a zip; Google returns an HTML login page otherwise
        raise RuntimeError("response is not an .xlsx file (login page?)")
    dest.write_bytes(data)
    print(f"Downloaded sheet {sheet_id} ({len(data) // 1024} KB)")
    return dest


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--xlsx", type=Path, help="local .xlsx copy (skips the download)")
    ap.add_argument("--sheet-id", default=SHEET_ID, help="Google Sheet ID to download")
    ap.add_argument("--out", type=Path, default=HERE.parent / "config", help="output directory (default: ../config)")
    ap.add_argument("--no-download", action="store_true", help="use the bundled .xlsx without downloading")
    args = ap.parse_args()

    if args.xlsx:
        xlsx = args.xlsx
    elif args.no_download:
        xlsx = BUNDLED_XLSX
    else:
        try:
            xlsx = download_sheet(args.sheet_id, Path(tempfile.mkdtemp()) / "actions-and-purposes.xlsx")
            BUNDLED_XLSX.write_bytes(xlsx.read_bytes())   # keep the bundled copy current
        except RuntimeError as e:
            if not BUNDLED_XLSX.exists():
                sys.exit(f"Download failed ({e}) and no bundled copy at {BUNDLED_XLSX}.")
            print(f"Download failed ({e}); using bundled copy {BUNDLED_XLSX.name}", file=sys.stderr)
            xlsx = BUNDLED_XLSX
    args.out.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.load_workbook(xlsx)
    cv1 = build_cv1(wb["CV1-Actions"], cv3_duty_actions(wb["CV3-Other Constraints"]))
    cv2 = build_cv2(wb["CV2-Purpose Constraints"])
    cv3 = build_cv3(wb["CV3-Other Constraints"], cv1)
    combined = new_graph()
    for name, g in [("cv1-actions", cv1), ("cv2-purposes", cv2), ("cv3-constraints", cv3)]:
        g.serialize(args.out / f"{name}.ttl", format="turtle")
        combined += g
        print(f"{name}.ttl: {len(set(g.subjects(RDF.type, SKOS.Concept)))} concepts, {len(g)} triples")
    combined.serialize(args.out / "cdif-access-vocab.ttl", format="turtle")


if __name__ == "__main__":
    main()
