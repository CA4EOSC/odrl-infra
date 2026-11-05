"""Build the Policy Builder vocabularies (config/cv1..cv4 *.ttl) from the CDIF access profile.

Source of truth: docs/profile.ttl (ODRL Profile for CDIF Access, https://w3id.org/cdif/access).
It is split into four SKOS concept schemes, one per controlled vocabulary used in the UI:

  CV1 actions      cdif-access:actionsCollection members before the "# duty actions" comment
  CV4 duty actions cdif-access:actionsCollection members after the "# duty actions" comment
                   (the profile has no RDF marker for duty actions yet; switch to it once added)
  CV3 constraints  cdif-access:leftOperandsCollection members
  CV2 purposes     DPV purposes (the profile's purposeCollection allows any DPV purpose)

The concepts keep the profile's IRIs (odrl:read, cc:Distribution, cdif-access:Download, ...), so
the term written into a policy is the term in the profile. Labels and definitions come from the
profile when it has them, otherwise from W3C ODRL 2.2 (odrl:/cc: terms) or DPV (purposes); a
cdif-access term without a label gets one from its name ("APIAccess" -> "API Access").
Comments on member lines are kept: "# deprecated" / "# deprecated by <IRI>" mark the term
deprecated (owl:deprecated, dcterms:isReplacedBy), any other comment becomes a skos:editorialNote.

ODRL 2.2 and the DPV purposes module are downloaded; if that fails the copies in sources/ are used
(and refreshed whenever a download succeeds).

Usage (from this directory):
  uv run --no-project --with rdflib python build_config.py
  uv run --no-project --with rdflib python build_config.py --offline   # use sources/ only
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROFILE = ROOT / "docs" / "profile.ttl"
SOURCES = HERE / "sources"
DOWNLOADS = {
    "odrl22.ttl": "https://www.w3.org/ns/odrl/2/ODRL22.ttl",
    "dpv-purposes.ttl": "https://raw.githubusercontent.com/w3c/dpv/master/2.2/dpv/modules/purposes.ttl",
}

CDIF = Namespace("https://w3id.org/cdif/access#")
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
CC = Namespace("http://creativecommons.org/ns#")
DPV = Namespace("https://w3id.org/dpv#")
PROFILE_IRI = URIRef("https://w3id.org/cdif/access")
PREFIXES = {"cdif-access": CDIF, "odrl": ODRL, "cc": CC, "dpv": DPV}

# Collection labels the Policy Builder groups by (frontend/src/lib/vocabTree.js, PolicyBuilder.jsx).
CDIF_ACTIONS = "CDIF-specific actions"
ODRL_ACTIONS = "ODRL Common Vocabulary"
LEFT_OPERANDS = "ODRL left operands used in CDIF"


# --------------------------------------------------------------------------- sources
def source(name, offline):
    path = SOURCES / name
    if not offline:
        try:
            with urllib.request.urlopen(DOWNLOADS[name], timeout=60) as r:
                data = r.read()
            SOURCES.mkdir(exist_ok=True)
            path.write_bytes(data)
            return path
        except OSError as e:
            print(f"Download of {name} failed ({e}); using {path.relative_to(HERE)}", file=sys.stderr)
    if not path.exists():
        sys.exit(f"No copy of {name} at {path}; run once without --offline.")
    return path


def expand(curie):
    prefix, _, local = curie.partition(":")
    if prefix not in PREFIXES:
        raise ValueError(f"unknown prefix in profile member '{curie}'")
    return PREFIXES[prefix][local]


def members_with_comments(text, collection):
    """(curie, comment, after_duty_marker) for each skos:member line of a collection, in order.
    The duty/action split and deprecations only exist as comments, so the Turtle is read as text."""
    block = re.search(rf"^{re.escape(collection)} a skos:Collection ;(.*?)\.\s*$", text, re.S | re.M)
    if not block:
        sys.exit(f"{collection} not found in {PROFILE}")
    out, duties = [], False
    for line in block.group(1).splitlines():
        line = line.strip()
        if re.fullmatch(r"#\s*duty actions\s*", line, re.I):
            duties = True
            continue
        m = re.match(r"skos:member\s+([\w-]+:[\w-]+)\s*[;.]?\s*(?:#\s*(.*))?$", line)
        if m:
            out.append((m.group(1), (m.group(2) or "").strip(), duties))
    return out


# --------------------------------------------------------------------------- concepts
def first(g, s, *props):
    for p in props:
        for o in g.objects(s, p):
            if str(o).strip():
                return o
    return None


def name_label(local):
    """"APIAccess" -> "API Access", "secondaryUse" -> "Secondary Use"."""
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", local)
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", words)
    return words[0].upper() + words[1:]


def scheme(g, key, title, description):
    s = URIRef(f"{PROFILE_IRI}/{key}")
    g.add((s, RDF.type, SKOS.ConceptScheme))
    g.add((s, SKOS.prefLabel, Literal(title, lang="en")))
    g.add((s, DCTERMS.description, Literal(description, lang="en")))
    g.add((s, DCTERMS.source, PROFILE_IRI))
    return s


def add_term(g, s, iri, curie, comment, profile, odrl):
    """One concept for a profile member, described from the profile, else ODRL 2.2."""
    g.add((iri, RDF.type, SKOS.Concept))
    g.add((iri, SKOS.inScheme, s))
    g.add((iri, SKOS.topConceptOf, s))
    label = first(profile, iri, RDFS.label, SKOS.prefLabel) or first(odrl, iri, RDFS.label, SKOS.prefLabel)
    g.add((iri, SKOS.prefLabel, Literal(str(label) if label else name_label(curie.split(":", 1)[1]), lang="en")))
    for prop in (SKOS.definition, SKOS.note, SKOS.scopeNote):
        o = first(profile, iri, prop) or first(odrl, iri, prop)
        if o is not None:
            g.add((iri, prop, Literal(str(o), lang="en")))
    if (iri, None, None) in odrl:   # an ODRL 2.2 (or CC) term
        g.add((iri, RDFS.isDefinedBy, URIRef("http://www.w3.org/ns/odrl/2/")))
    else:
        g.add((iri, RDFS.isDefinedBy, PROFILE_IRI))
    m = re.match(r"deprecated(?:\s+by\s+(\S+))?", comment, re.I)
    if m:
        g.add((iri, OWL.deprecated, Literal(True)))
        if m.group(1):
            g.add((iri, DCTERMS.isReplacedBy, URIRef(m.group(1).replace("https://www.w3.org/ns/odrl/", "http://www.w3.org/ns/odrl/"))))
    elif comment:
        g.add((iri, SKOS.editorialNote, Literal(comment, lang="en")))


def resolve(curie, odrl):
    """The profile IRI for a member; fixes the case of ODRL terms (odrl:PayAmount -> odrl:payAmount)."""
    iri = expand(curie)
    if str(iri).startswith(str(ODRL)) and (iri, None, None) not in odrl:
        local = curie.split(":", 1)[1].lower()
        match = next((t for t in set(odrl.subjects()) if isinstance(t, URIRef)
                      and str(t).startswith(str(ODRL)) and str(t)[len(str(ODRL)):].lower() == local), None)
        if match is not None:
            print(f"profile: {curie} is written {match.n3(odrl.namespace_manager)} in ODRL 2.2; using that", file=sys.stderr)
            return match, f"Written '{curie}' in the profile; ODRL 2.2 term is {match.n3(odrl.namespace_manager)}."
    return iri, None


def collection(g, label, members):
    c = URIRef(f"{PROFILE_IRI}/collection/{re.sub(r'[^A-Za-z]+', '-', label).strip('-').lower()}")
    g.add((c, RDF.type, SKOS.Collection))
    g.add((c, SKOS.prefLabel, Literal(label, lang="en")))
    for m in members:
        g.add((c, SKOS.member, m))


def new_graph():
    g = Graph()
    for p, ns in [("skos", SKOS), ("dcterms", DCTERMS), ("owl", OWL), ("rdfs", RDFS), *PREFIXES.items()]:
        g.bind(p, ns)
    return g


def build_rules(members, key, title, description, profile, odrl):
    g = new_graph()
    s = scheme(g, key, title, description)
    cdif, other = [], []
    for curie, comment, _ in members:
        iri, fixed = resolve(curie, odrl)
        add_term(g, s, iri, curie, comment, profile, odrl)
        if fixed:
            g.add((iri, SKOS.editorialNote, Literal(fixed, lang="en")))
        (cdif if str(iri).startswith(str(CDIF)) else other).append(iri)
    return g, cdif, other


def build_purposes(dpv):
    g = new_graph()
    s = scheme(g, "cv2", "CDIF Purposes (CV2)",
               "Any purpose from the Data Privacy Vocabulary (DPV) can be used as the right operand of "
               "an odrl:purpose constraint (cdif-access:purposeCollection). Taken from the DPV 2.2 "
               "purposes module.")
    concepts = set(dpv.subjects(RDF.type, SKOS.Concept)) | {DPV.Purpose}
    for c in concepts:
        g.add((c, RDF.type, SKOS.Concept))
        g.add((c, SKOS.inScheme, s))
        label = first(dpv, c, SKOS.prefLabel, RDFS.label)
        g.add((c, SKOS.prefLabel, Literal(str(label) if label else "Purpose", lang="en")))
        definition = first(dpv, c, SKOS.definition)
        if definition is not None:
            g.add((c, SKOS.definition, Literal(str(definition), lang="en")))
        for b in dpv.objects(c, SKOS.broader):
            if b in concepts:
                g.add((c, SKOS.broader, b))
        if c == DPV.Purpose:
            g.add((c, SKOS.topConceptOf, s))
    return g


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--profile", type=Path, default=PROFILE)
    ap.add_argument("--out", type=Path, default=ROOT / "config")
    ap.add_argument("--offline", action="store_true", help="use sources/ without downloading")
    args = ap.parse_args()

    text = args.profile.read_text(encoding="utf-8")
    profile = Graph().parse(data=text, format="turtle")
    odrl = Graph().parse(source("odrl22.ttl", args.offline), format="turtle")
    dpv = Graph().parse(source("dpv-purposes.ttl", args.offline), format="turtle")

    actions = members_with_comments(text, "cdif-access:actionsCollection")
    operands = members_with_comments(text, "cdif-access:leftOperandsCollection")
    if not any(d for *_, d in actions):
        sys.exit('No "# duty actions" comment in cdif-access:actionsCollection; cannot split CV1 / CV4.')

    cv1, cdif1, odrl1 = build_rules(
        [m for m in actions if not m[2]], "cv1", "CDIF Actions (CV1)",
        "Actions of the CDIF access profile (cdif-access:actionsCollection, before the duty actions).",
        profile, odrl)
    collection(cv1, CDIF_ACTIONS, cdif1)
    collection(cv1, ODRL_ACTIONS, odrl1)

    cv4, cdif4, odrl4 = build_rules(
        [m for m in actions if m[2]], "cv4", "CDIF Duty Actions (CV4)",
        "Duty actions of the CDIF access profile (cdif-access:actionsCollection, '# duty actions').",
        profile, odrl)
    collection(cv4, CDIF_ACTIONS, cdif4)
    collection(cv4, ODRL_ACTIONS, odrl4)

    cv3, _, odrl3 = build_rules(
        operands, "cv3", "CDIF Other Constraints (CV3)",
        "Left operands of the CDIF access profile (cdif-access:leftOperandsCollection).",
        profile, odrl)
    collection(cv3, LEFT_OPERANDS, odrl3 + _)

    cv2 = build_purposes(dpv)

    args.out.mkdir(parents=True, exist_ok=True)
    for name, g in [("cv1-actions", cv1), ("cv2-purposes", cv2), ("cv3-constraints", cv3),
                    ("cv4-duty-actions", cv4)]:
        g.serialize(args.out / f"{name}.ttl", format="turtle")
        print(f"{name}.ttl: {len(set(g.subjects(RDF.type, SKOS.Concept)))} concepts")


if __name__ == "__main__":
    main()
