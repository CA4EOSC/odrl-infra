#!/usr/bin/env python3
"""Build the HTML documentation of an ODRL profile from its Turtle file.

The output is a ReSpec document (https://respec.org/docs/): when it is opened
in a browser, ReSpec adds the W3C-style header, table of contents, section
numbers and references.

Rerun it whenever the Turtle file changes:

    pip install -r scripts/requirements-docs.txt
    python scripts/build_profile_docs.py

By default it reads docs/profile.ttl and writes docs/profile.html next to it.
Other options (see --help):

    python scripts/build_profile_docs.py path/to/profile.ttl -o path/to/profile.html
    python scripts/build_profile_docs.py --offline   # no downloads; use cached vocabularies, if any
    python scripts/build_profile_docs.py --strict    # exit with status 1 if the profile check finds issues

What ends up in the document:
  * header, abstract and status, from the profile metadata (DCTERMS, OWL, VANN, PROF, ...)
  * the namespaces used and the profile resources (W3C Profiles Vocabulary)
  * one table per SKOS collection, listing every member; labels and definitions
    of adopted terms (ODRL, DPV, ccREL) come from their source vocabularies,
    which are downloaded once and cached
  * a definition table for every term the profile defines; its section id is
    the term's local name, so <namespace>#Term links straight to it
  * example policies stored in an "examples" folder next to the Turtle file (optional)

The script also checks the profile (missing labels and definitions, collection
members that are never defined, deprecated or unknown adopted terms, template
placeholders, ...) and prints what it finds.

Narrative text (introduction, acknowledgements, ...) belongs in
scripts/templates/profile.html.j2; the generated HTML file is overwritten on every run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    from markupsafe import Markup, escape
    from rdflib import BNode, Graph, Literal, Namespace, URIRef
    from rdflib.collection import Collection as RDFList
    from rdflib.namespace import DC, DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, XSD
    from rdflib.util import guess_format
except ImportError as exc:  # pragma: no cover - depends on the environment
    sys.exit(
        f"Missing Python package: {exc.name}\n"
        "Install the dependencies with: pip install -r scripts/requirements-docs.txt"
    )

# ---------------------------------------------------------------------------
# Project settings: change these if the files move (or use the CLI options)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = REPO_ROOT / "docs" / "profile.ttl"
DEFAULT_TEMPLATE = SCRIPT_DIR / "templates" / "profile.html.j2"
DEFAULT_GITHUB_REPO = "CDIF4EOSC/odrl-infra"  # adds "Participate" links; "" to hide them
DEFAULT_BRANCH = "main"
DEFAULT_SPEC_STATUS = "base"  # ReSpec specStatus: "base" (no W3C branding) or "unofficial"
USER_AGENT = "odrl-profile-docs/1.0 (+https://github.com/CDIF4EOSC/odrl-infra)"

# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------
ODRL = Namespace("http://www.w3.org/ns/odrl/2/")
PROF = Namespace("http://www.w3.org/ns/dx/prof/")
ROLE = Namespace("http://www.w3.org/ns/dx/prof/role/")
VANN = Namespace("http://purl.org/vocab/vann/")
SW = Namespace("http://www.w3.org/2003/06/sw-vocab-status/ns#")
BIBO = Namespace("http://purl.org/ontology/bibo/")
SDO = Namespace("https://schema.org/")
SDO_HTTP = Namespace("http://schema.org/")
ORG = Namespace("http://www.w3.org/ns/org#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
ADMS = Namespace("http://www.w3.org/ns/adms#")

ODRL22_TTL = "https://www.w3.org/ns/odrl/2/ODRL22.ttl"


@dataclass(frozen=True)
class Vocab:
    """A well-known vocabulary: how to name it, cite it and look up its terms."""

    prefix: str
    namespace: str
    name: str
    short: str
    url: str  # human-readable documentation
    ref: str = ""  # ReSpec bibliography key ([[KEY]])
    # RDF files with the labels and definitions of the vocabulary's terms. All entries are
    # loaded; an entry that is itself a tuple lists alternatives (the first that loads is used).
    sources: Tuple = ()
    term_url: str = ""  # link pattern for a term's documentation ({local} = local name)


KNOWN_VOCABS: Tuple[Vocab, ...] = (
    Vocab("odrl", str(ODRL), "ODRL Vocabulary & Expression 2.2", "ODRL",
          "https://www.w3.org/TR/odrl-vocab/", "ODRL-VOCAB", (ODRL22_TTL,),
          "https://www.w3.org/TR/odrl-vocab/#term-{local}"),
    Vocab("dpv", "https://w3id.org/dpv#", "Data Privacy Vocabulary (DPV)", "DPV",
          "https://w3id.org/dpv", "DPV", (("https://w3id.org/dpv/dpv.ttl", "https://w3id.org/dpv"),)),
    Vocab("cc", "http://creativecommons.org/ns#",
          "Creative Commons Rights Expression Language (ccREL)", "ccREL",
          "https://creativecommons.org/ns", "CC-REL",
          (ODRL22_TTL, "https://creativecommons.org/schema.rdf")),
    Vocab("skos", str(SKOS), "Simple Knowledge Organization System (SKOS)", "SKOS",
          "https://www.w3.org/TR/skos-reference/", "SKOS-REFERENCE"),
    Vocab("prof", str(PROF), "The Profiles Vocabulary", "PROF",
          "https://www.w3.org/TR/dx-prof/", "DX-PROF"),
    Vocab("role", str(ROLE), "Profiles Vocabulary: resource roles", "PROF",
          "https://www.w3.org/TR/dx-prof/#resource-roles-vocab", "DX-PROF"),
    Vocab("dcterms", str(DCTERMS), "DCMI Metadata Terms", "DCTERMS",
          "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/"),
    Vocab("dc", str(DC), "Dublin Core Metadata Element Set", "DC",
          "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/"),
    Vocab("owl", str(OWL), "OWL 2 Web Ontology Language", "OWL", "https://www.w3.org/TR/owl2-overview/"),
    Vocab("rdf", str(RDF), "RDF 1.1 Concepts", "RDF", "https://www.w3.org/TR/rdf11-concepts/"),
    Vocab("rdfs", str(RDFS), "RDF Schema 1.1", "RDFS", "https://www.w3.org/TR/rdf-schema/"),
    Vocab("xsd", str(XSD), "XML Schema Datatypes", "XSD", "https://www.w3.org/TR/xmlschema11-2/"),
    Vocab("foaf", str(FOAF), "FOAF Vocabulary", "FOAF", "http://xmlns.com/foaf/spec/"),
    Vocab("vann", str(VANN), "VANN: vocabulary for annotating vocabulary descriptions", "VANN",
          "https://vocab.org/vann/"),
    Vocab("bibo", str(BIBO), "Bibliographic Ontology", "BIBO", "http://purl.org/ontology/bibo/"),
    Vocab("sw", str(SW), "Term-centric Semantic Web Vocabulary Annotations", "VS",
          "https://www.w3.org/2003/06/sw-vocab-status/note"),
    Vocab("schema", str(SDO), "Schema.org", "Schema.org", "https://schema.org/"),
)

# Bibliography entries that are not in Specref (https://www.specref.org/).
LOCAL_BIBLIO = {
    "ODRL-PROFILE-BP": {
        "title": "ODRL V2.2 Profile Best Practices",
        "href": "https://www.w3.org/community/reports/odrl/CG-FINAL-profile-bp-20240808.html",
        "publisher": "W3C ODRL Community Group",
        "status": "Final Community Group Report",
        "date": "08 August 2024",
    },
    "DPV": {
        "title": "Data Privacy Vocabulary (DPV)",
        "href": "https://w3id.org/dpv",
        "publisher": "W3C Data Privacy Vocabularies and Controls Community Group",
    },
    "CC-REL": {
        "title": "ccREL: The Creative Commons Rights Expression Language",
        "href": "https://www.w3.org/submissions/ccREL/",
        "authors": ["Hal Abelson", "Ben Adida", "Mike Linksvayer", "Nathan Yergler"],
        "publisher": "W3C",
        "status": "W3C Member Submission",
        "date": "01 May 2008",
    },
}

KNOWN_PROFILES = {"http://www.w3.org/ns/odrl/2/core": "ODRL 2.2 Core Profile"}

LICENSES = {
    "creativecommons.org/licenses/by/4.0": "CC BY 4.0",
    "creativecommons.org/licenses/by-sa/4.0": "CC BY-SA 4.0",
    "creativecommons.org/licenses/by-nc/4.0": "CC BY-NC 4.0",
    "creativecommons.org/publicdomain/zero/1.0": "CC0 1.0",
    "opensource.org/licenses/mit": "MIT License",
    "www.apache.org/licenses/license-2.0": "Apache License 2.0",
    "www.w3.org/consortium/legal/2015/copyright-software-and-document": "W3C Software and Document License",
}

ROLE_LABELS = {
    "specification": "Specification",
    "vocabulary": "Vocabulary",
    "schema": "Schema",
    "validation": "Validation",
    "guidance": "Guidance",
    "example": "Example",
    "constraints": "Constraints",
    "mapping": "Mapping",
}

FORMAT_LABELS = {
    "https://www.w3.org/TR/html/": "HTML",
    "https://www.w3.org/TR/turtle/": "RDF 1.1 Turtle",
    "https://www.w3.org/TR/json-ld/": "JSON-LD",
    "https://www.w3.org/TR/rdf-syntax-grammar/": "RDF/XML",
}
IANA_MEDIA_TYPES = "https://www.iana.org/assignments/media-types/"

LABEL_PREDICATES = (RDFS.label, SKOS.prefLabel, DCTERMS.title, DC.title, SDO.name, SDO_HTTP.name, FOAF.name)
DEFINITION_PREDICATES = (SKOS.definition, RDFS.comment, DCTERMS.description, DC.description)
STRUCTURAL_TYPES = {SKOS.Collection, SKOS.OrderedCollection, SKOS.ConceptScheme,
                    PROF.ResourceDescriptor, PROF.Profile, OWL.Ontology}
PROPERTY_TYPES = {RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty}
CLASS_TYPES = {RDFS.Class, OWL.Class}

# Groups of terms defined by a profile (ODRL Profile Best Practices, section 3).
TERM_KINDS = (
    ("actions", "Actions"),
    ("left-operands", "Constraint left operands"),
    ("operators", "Constraint operators"),
    ("right-operands", "Constraint right operands"),
    ("party-functions", "Party functions"),
    ("asset-relations", "Asset relations"),
    ("logical-constraints", "Logical constraint operands"),
    ("conflict-terms", "Policy conflict strategies"),
    ("policy-types", "Policy types"),
    ("rule-types", "Rule types"),
    ("constraint-types", "Constraint types"),
    ("party-types", "Party types"),
    ("asset-types", "Asset types"),
    ("properties", "Other properties"),
    ("classes", "Other classes"),
    ("concepts", "Other concepts"),
)

# Collections are ordered by the first keyword found in their IRI or label.
COLLECTION_ORDER = ("leftoperand", "rightoperand", "operator", "action", "party", "asset",
                    "logical", "conflict", "rule", "policy")

# Rows shown in the definition table of a term: (row title, predicates). Labels,
# definitions, collections and statuses are added separately.
DETAIL_ROWS = (
    ("Usage note", (SKOS.note,)),
    ("Scope note", (SKOS.scopeNote,)),
    ("Example", (SKOS.example, VANN.example)),
    ("Instance of", (RDF.type,)),
    ("Included in", (ODRL.includedIn,)),
    ("Implies", (ODRL.implies,)),
    ("Broader", (SKOS.broader,)),
    ("Parent class", (RDFS.subClassOf,)),
    ("Parent property", (RDFS.subPropertyOf,)),
    ("Domain", (RDFS.domain,)),
    ("Range", (RDFS.range,)),
    ("Related", (SKOS.related,)),
    ("Equivalent to", (OWL.equivalentClass, OWL.equivalentProperty, OWL.sameAs)),
    ("Mappings", (SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch, SKOS.narrowMatch, SKOS.relatedMatch)),
    ("Replaced by", (DCTERMS.isReplacedBy,)),
    ("Source", (DCTERMS.source,)),
    ("See also", (RDFS.seeAlso,)),
    ("Created", (DCTERMS.created,)),
    ("Modified", (DCTERMS.modified,)),
    ("Contributors", (DCTERMS.creator, DCTERMS.contributor, DC.creator, DC.contributor)),
)
# Predicates that are never listed under "Other properties".
HANDLED_TERM_PREDICATES = {p for _, preds in DETAIL_ROWS for p in preds} | {
    RDFS.label, SKOS.prefLabel, SKOS.altLabel, SKOS.definition, RDFS.comment, DCTERMS.description,
    RDFS.isDefinedBy, OWL.deprecated, SW.term_status, SKOS.inScheme, SKOS.narrower,
}

RESERVED_IDS = {"abstract", "sotd", "toc", "title", "subtitle", "introduction", "summary", "namespaces",
                "resources", "vocabulary", "terms", "examples", "references", "normative-references",
                "informative-references", "conformance", "index", "acknowledgements", "respec-ui"}

EXAMPLE_FORMATS = {  # extension: (rdflib format or None for JSON, ReSpec highlighting class)
    ".ttl": ("turtle", "nohighlight"), ".trig": ("trig", "nohighlight"), ".nt": ("nt", "nohighlight"),
    ".rdf": ("xml", "xml"), ".jsonld": (None, "json"), ".json": (None, "json"),
}

ACCEPT_RDF = ("text/turtle, application/rdf+xml;q=0.9, application/ld+json;q=0.8, "
              "application/n-triples;q=0.7, */*;q=0.1")
FORMAT_BY_MEDIA_TYPE = {
    "text/turtle": "turtle", "application/x-turtle": "turtle", "application/rdf+xml": "xml",
    "application/ld+json": "json-ld", "application/n-triples": "nt", "text/n3": "n3",
    "application/trig": "trig", "application/n-quads": "nquads",
}
EXT_BY_FORMAT = {"turtle": ".ttl", "xml": ".rdf", "json-ld": ".jsonld", "nt": ".nt", "n3": ".n3",
                 "trig": ".trig", "nquads": ".nq"}


class BuildError(Exception):
    """A problem that stops the build (unreadable input, missing template, ...)."""


# ---------------------------------------------------------------------------
# Profile check report
# ---------------------------------------------------------------------------
class Report:
    """Collects issues found while building; issues with the same message are grouped."""

    def __init__(self) -> None:
        self._groups: Dict[str, List[str]] = {}

    def add(self, message: str, item: Optional[str] = None) -> None:
        items = self._groups.setdefault(message, [])
        if item is not None and item not in items:
            items.append(item)

    def __len__(self) -> int:
        return sum(max(1, len(items)) for items in self._groups.values())

    def lines(self) -> List[str]:
        out = []
        for message, items in self._groups.items():
            if not items:
                out.append(f"  - {message}")
            elif len(items) == 1:
                out.append(f"  - {message}: {items[0]}")
            elif any(" " in item for item in items):  # sentences: one per line
                out.append(f"  - {message} ({len(items)}):")
                out.extend(f"      {item}" for item in items)
            else:  # term names: wrapped list
                out.append(f"  - {message} ({len(items)}):")
                out.append(textwrap.fill(", ".join(sorted(items, key=str.lower)), width=100,
                                         initial_indent="      ", subsequent_indent="      ",
                                         break_on_hyphens=False, break_long_words=False))
        return out


# ---------------------------------------------------------------------------
# Small RDF helpers
# ---------------------------------------------------------------------------
def _lang_rank(lit: Literal, lang: str) -> int:
    tag = (lit.language or "").lower()
    if tag == lang:
        return 0
    if tag.startswith(lang + "-"):
        return 1
    return 2 if not tag else 3


def texts(g: Graph, s, *preds, lang: str = "en") -> List[str]:
    """Non-empty literal values of the first predicate that has any, in the best language."""
    for p in preds:
        lits = [o for o in g.objects(s, p) if isinstance(o, Literal) and str(o).strip()]
        if lits:
            best = min(_lang_rank(lit, lang) for lit in lits)
            return sorted({str(lit).strip() for lit in lits if _lang_rank(lit, lang) == best})
    return []


def text(g: Graph, s, *preds, lang: str = "en") -> Optional[str]:
    values = texts(g, s, *preds, lang=lang)
    return values[0] if values else None


def iris(g: Graph, s, *preds) -> List[URIRef]:
    return sorted({o for p in preds for o in g.objects(s, p) if isinstance(o, URIRef)}, key=str)


def value_or_iri(g: Graph, s, *preds) -> Optional[str]:
    """First literal value, or else first IRI, of the given predicates."""
    return text(g, s, *preds) or next((str(o) for o in iris(g, s, *preds)), None)


def is_true(g: Graph, s, p) -> bool:
    return any(str(o).strip().lower() in {"true", "1"} for o in g.objects(s, p))


def local_name(iri: str) -> str:
    return re.split(r"[#/]", iri.rstrip("#/"))[-1] if iri else iri


def iso_date(value: Optional[str]) -> Optional[str]:
    match = re.match(r"\d{4}-\d{2}-\d{2}", value or "")
    return match.group(0) if match else None


def is_unfinished(value: Optional[str]) -> bool:
    """Template text such as "Cite this vocabulary as: " (ends with a colon)."""
    return bool(value) and value.rstrip().endswith(":")


def sort_key(value: str) -> Tuple[str, str]:
    return (value.lower(), value)


def license_label(iri: str) -> str:
    key = re.sub(r"^https?://", "", iri).rstrip("/").lower()
    return LICENSES.get(key, iri)


# ---------------------------------------------------------------------------
# View models handed to the template
# ---------------------------------------------------------------------------
@dataclass
class Ref:
    """Something shown in the document: a link, a code snippet, a placeholder or text."""

    text: str
    href: Optional[str] = None
    code: bool = False
    title: Optional[str] = None
    tbd: bool = False


@dataclass
class MemberRow:
    term: Ref
    label: Optional[str]
    definition: Optional[str]
    source: Ref
    status: Optional[str] = None  # "deprecated" or "not defined"
    replaced_by: List[Ref] = field(default_factory=list)
    order: Tuple = ()
    local: bool = False  # in the profile's own namespace


@dataclass
class CollectionView:
    id: str
    iri: str
    qname: str
    title: str
    label: Optional[str]
    scope_note: Optional[str]
    definition: Optional[str]
    rows: List[MemberRow]
    total: int = 0
    local: int = 0
    undefined: int = 0
    adopted: Dict[str, int] = field(default_factory=dict)


@dataclass
class TermView:
    id: str
    iri: str
    qname: str
    heading: str
    label: Optional[str]
    alt_labels: List[str]
    definition: Optional[str]
    rows: List[Tuple[str, List[Ref]]]
    deprecated: bool = False


# ---------------------------------------------------------------------------
# Input and reference vocabularies
# ---------------------------------------------------------------------------
@dataclass
class Source:
    location: str  # path or URL given on the command line
    is_url: bool
    path: Optional[Path]
    display: str  # path relative to the repository, or the URL
    name: str


def resolve_source(location: str) -> Source:
    if re.match(r"https?://", location):
        # Accept GitHub "blob" links and turn them into raw file links.
        match = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/(.+)", location)
        if match:
            location = "https://raw.githubusercontent.com/{}/{}/{}".format(*match.groups())
        return Source(location, True, None, location, location.rstrip("/").split("/")[-1])
    path = Path(location).expanduser().resolve()
    if not path.is_file():
        raise BuildError(f"Input file not found: {location}")
    try:
        display = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        display = path.name
    return Source(str(path), False, path, display, path.name)


def parse_rdf(location: str, fmt: Optional[str] = None, graph: Optional[Graph] = None) -> Graph:
    g = graph if graph is not None else Graph(bind_namespaces="none")
    g.parse(location, format=fmt or guess_format(location) or "turtle")
    return g


class ReferenceVocabularies:
    """Source vocabularies of adopted terms (ODRL, DPV, ...), downloaded once and cached."""

    def __init__(self, cache_dir: Path, offline: bool, refresh: bool,
                 overrides: Dict[str, List[str]], report: Report) -> None:
        self.cache_dir = cache_dir
        self.offline = offline
        self.refresh = refresh
        self.overrides = overrides
        self.report = report
        self.graph = Graph(bind_namespaces="none")
        self.loaded: Dict[str, Optional[str]] = {}  # source -> None if loaded, else the error
        self.covered: set = set()  # namespaces whose vocabulary was loaded

    def load_for(self, namespaces: Iterable[str]) -> None:
        by_ns = {v.namespace: v for v in KNOWN_VOCABS}
        for ns in sorted(set(namespaces)):
            override = ns in self.overrides
            if override:
                groups = [(src,) for src in self.overrides[ns]]
            else:
                groups = [s if isinstance(s, tuple) else (s,) for s in (by_ns[ns].sources if ns in by_ns else ())]
            failed = []
            for alternatives in groups:
                for src in alternatives:
                    if src not in self.loaded:
                        self.loaded[src] = self._load(src)
                    if self.loaded[src] is None:
                        self.covered.add(ns)
                        break
                    failed.append(src)
            if ns not in self.covered or override:
                for src in failed:
                    if not (self.offline and self.loaded[src] == OFFLINE_NOT_CACHED):
                        self.report.add("Could not load reference vocabularies (adopted terms are shown "
                                        "without labels and definitions; see --vocab)",
                                        f"{src}: {self.loaded[src]}")

    def _load(self, src: str) -> Optional[str]:
        try:
            location, fmt = self._fetch(src)
            parse_rdf(location, fmt, self.graph)
            return None
        except Exception as exc:  # noqa: BLE001 - any failure just disables the lookup
            return str(exc).splitlines()[0][:200] if str(exc) else type(exc).__name__

    def _fetch(self, src: str) -> Tuple[str, str]:
        if not re.match(r"https?://", src):
            path = Path(src).expanduser()
            if not path.is_file():
                raise FileNotFoundError("file not found")
            return str(path), guess_format(str(path)) or "turtle"
        key = hashlib.sha256(src.encode("utf-8")).hexdigest()[:20]
        cached = sorted(self.cache_dir.glob(key + ".*"))
        if cached and (self.offline or not self.refresh):
            return str(cached[0]), _format_from_ext(cached[0].suffix)
        if self.offline:
            raise LookupError(OFFLINE_NOT_CACHED)
        try:
            request = urllib.request.Request(src, headers={"Accept": ACCEPT_RDF, "User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read()
                media_type = response.headers.get_content_type()
                final_url = response.geturl()
        except (urllib.error.URLError, OSError, ValueError):
            if cached:  # keep using the old copy
                return str(cached[0]), _format_from_ext(cached[0].suffix)
            raise
        if media_type == "text/html":
            raise ValueError("got an HTML page instead of RDF")
        fmt = FORMAT_BY_MEDIA_TYPE.get(media_type) or guess_format(final_url) or guess_format(src) or "turtle"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for old in cached:
            old.unlink()
        path = self.cache_dir / f"{key}{EXT_BY_FORMAT.get(fmt, '.ttl')}"
        path.write_bytes(data)
        return str(path), fmt

    def describe(self, iri: URIRef) -> Optional[dict]:
        g = self.graph
        if (iri, None, None) not in g:
            return None
        status = (text(g, iri, SW.term_status, ADMS.status) or "").lower()
        deprecated = is_true(g, iri, OWL.deprecated) or status in {"deprecated", "obsolete"}
        replaced = iris(g, iri, DCTERMS.isReplacedBy)
        if deprecated and not replaced:
            replaced = iris(g, iri, SKOS.exactMatch, OWL.sameAs)
        return {
            "label": text(g, iri, *LABEL_PREDICATES),
            "definition": text(g, iri, *DEFINITION_PREDICATES),
            "deprecated": deprecated,
            "replaced_by": replaced,
        }


OFFLINE_NOT_CACHED = "not downloaded (--offline) and not in the cache"


def _format_from_ext(ext: str) -> str:
    return next((fmt for fmt, e in EXT_BY_FORMAT.items() if e == ext), "turtle")


def default_cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "odrl-profile-docs"


# ---------------------------------------------------------------------------
# The document builder
# ---------------------------------------------------------------------------
class DocBuilder:
    def __init__(self, g: Graph, source: Source, output: Path, args: argparse.Namespace,
                 report: Report) -> None:
        self.g = g
        self.source = source
        self.output = output
        self.out_dir = output.parent
        self.args = args
        self.report = report
        self.vocabs = {v.namespace: v for v in KNOWN_VOCABS}

        # Prefixes: the ones declared in the Turtle file win over the well-known ones.
        self.prefixes: Dict[str, str] = {v.namespace: v.prefix for v in KNOWN_VOCABS}
        declared = {str(ns): prefix for prefix, ns in g.namespaces() if prefix and prefix != "xml"}
        self.prefixes.update(declared)
        self.declared = declared
        self._ns_by_length = sorted(self.prefixes, key=len, reverse=True)

        self.profile = self._find_profile()
        self.namespace, self.prefix = self._profile_namespace()
        self.collections = sorted((c for c in set(g.subjects(RDF.type, SKOS.Collection))
                                   | set(g.subjects(RDF.type, SKOS.OrderedCollection))
                                   if isinstance(c, URIRef)), key=str)
        self.members = {c: self._members(c) for c in self.collections}
        self.terms = self._defined_terms()
        self.ids: Dict[str, str] = {}
        self._used_ids = set(RESERVED_IDS)
        for c in self.collections:
            self._allocate_id(c)
        for t in sorted(self.terms, key=lambda t: sort_key(str(t))):
            self._allocate_id(t)
        self.refvocabs = ReferenceVocabularies(
            Path(args.cache_dir), args.offline, args.refresh_vocabs, args.vocab_overrides, report)

    # -- discovery ---------------------------------------------------------
    def _find_profile(self) -> URIRef:
        g = self.g
        candidates = [s for s in set(g.subjects(RDF.type, OWL.Ontology)) | set(g.subjects(RDF.type, PROF.Profile))
                      if isinstance(s, URIRef)]
        if not candidates:
            raise BuildError("No resource typed owl:Ontology or prof:Profile found in the Turtle file.")
        return sorted(candidates, key=lambda s: (-((s, RDF.type, OWL.Ontology) in g)
                                                 - ((s, RDF.type, PROF.Profile) in g), str(s)))[0]

    def _profile_namespace(self) -> Tuple[str, Optional[str]]:
        g, p = self.g, self.profile
        prefix = text(g, p, VANN.preferredNamespacePrefix)
        ns = value_or_iri(g, p, VANN.preferredNamespaceUri)
        if not ns and prefix:
            ns = next((n for n, pf in self.declared.items() if pf == prefix), None)
        if not ns:
            ns = str(p) if str(p).endswith(("#", "/")) else str(p) + "#"
        if not prefix:
            prefix = self.declared.get(ns)
        if prefix and ns not in self.declared:
            self.prefixes[ns] = prefix
            self._ns_by_length = sorted(self.prefixes, key=len, reverse=True)
        return ns, prefix

    def _members(self, collection: URIRef) -> List:
        g = self.g
        members = set(g.objects(collection, SKOS.member))
        for head in g.objects(collection, SKOS.memberList):
            members.update(RDFList(g, head))
        return sorted(members, key=lambda m: sort_key(str(m)))

    def _defined_terms(self) -> set:
        g = self.g
        owners = {str(self.profile), self.namespace, self.namespace.rstrip("#/")}
        owners.update(str(o) for o in g.objects(self.profile, OWL.versionIRI))
        terms = {s for s, o in g.subject_objects(RDFS.isDefinedBy)
                 if isinstance(s, URIRef) and str(o) in owners}
        terms.update(s for s in set(g.subjects())
                     if isinstance(s, URIRef) and str(s).startswith(self.namespace) and str(s) != self.namespace)
        return {t for t in terms if t != self.profile and not (set(g.objects(t, RDF.type)) & STRUCTURAL_TYPES)}

    def _allocate_id(self, node: URIRef) -> None:
        # The id is the term's local name, so that <namespace>#Term opens its section.
        iri = str(node)
        wanted = iri[len(self.namespace):] if iri.startswith(self.namespace) else ""
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*", wanted):
            wanted = local_name(iri)
        base = re.sub(r"[^A-Za-z0-9_.-]+", "-", wanted).strip("-") or "term"
        candidate, n = base, 2
        while candidate in self._used_ids:
            candidate, n = f"{base}-{n}", n + 1
        self._used_ids.add(candidate)
        self.ids[iri] = candidate

    # -- naming and links --------------------------------------------------
    def split(self, iri: str) -> Tuple[Optional[str], str]:
        for ns in self._ns_by_length:
            if iri.startswith(ns) and re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*|", iri[len(ns):]):
                return ns, iri[len(ns):]
        return None, iri

    def qname(self, iri: str) -> str:
        ns, local = self.split(iri)
        return f"{self.prefixes[ns]}:{local}" if ns is not None else iri

    def vocab_of(self, iri: str) -> Optional[Vocab]:
        ns, _ = self.split(iri)
        return self.vocabs.get(ns) if ns else None

    def local_file(self, iri: str, relative_to: Optional[Path] = None) -> Optional[Tuple[str, bool]]:
        """IRIs that were relative in the Turtle file: (path relative to the output, file exists).

        rdflib resolves relative IRIs such as <path/to/your/logo> against the
        location of the Turtle file, which gives file: IRIs; they are turned
        back into relative links so that no local paths end up in the HTML.
        """
        if self.source.is_url or not iri.startswith("file:"):
            return None
        parsed = urllib.parse.urlparse(iri)
        path = Path(urllib.request.url2pathname(parsed.path))
        rel = Path(os.path.relpath(path, relative_to or self.out_dir)).as_posix()
        return rel + (f"#{parsed.fragment}" if parsed.fragment else ""), path.exists()

    def as_written(self, iri: str) -> str:
        """A relative IRI as it was written in the Turtle file (for messages)."""
        local = self.local_file(iri, self.source.path.parent) if self.source.path else None
        return local[0] if local else iri

    def ref(self, node, term: bool = False) -> Ref:
        if isinstance(node, Literal):
            return Ref(str(node).strip())
        if isinstance(node, BNode):
            return Ref(text(self.g, node, *LABEL_PREDICATES) or "(blank node)")
        iri = str(node)
        if iri in self.ids:
            return Ref(self.qname(iri), "#" + self.ids[iri], code=True, title=iri)
        local = self.local_file(iri)
        if local:
            rel, exists = local
            return Ref(rel, rel, code=True) if exists else \
                Ref("TBD", title=f"Placeholder: {self.as_written(iri)}", tbd=True)
        href = iri
        vocab = self.vocab_of(iri)
        if term and vocab and vocab.term_url:
            href = vocab.term_url.format(local=self.split(iri)[1])
        return Ref(self.qname(iri), href, code=True, title=iri)

    # -- profile check helpers ----------------------------------------------
    def check_resource(self, node, what: str) -> None:
        """Report empty values, placeholder paths and doubled slashes on a metadata resource."""
        g = self.g
        for p in sorted(set(g.predicates(node)), key=str):
            values = list(g.objects(node, p))
            if values and all(isinstance(v, Literal) and not str(v).strip() for v in values):
                self.report.add(f"Empty value on {what}", self.qname(str(p)))
            for v in values:
                if not isinstance(v, URIRef):
                    continue
                local = self.local_file(str(v))
                if local and not local[1]:
                    self.report.add(f"Placeholder or missing file on {what}",
                                    f"{self.qname(str(p))} <{self.as_written(str(v))}>")
                elif "//" in urllib.parse.urlparse(str(v)).path:
                    self.report.add(f"IRI with a doubled slash on {what} (typo?)",
                                    f"{self.qname(str(p))} <{v}>")

    # -- building the template context --------------------------------------
    def build(self) -> dict:
        adopted_ns = {self.split(str(m))[0] for ms in self.members.values() for m in ms
                      if isinstance(m, URIRef) and str(m) not in self.ids}
        adopted_ns.discard(None)
        if not self.args.no_lookup:
            self.refvocabs.load_for(adopted_ns)

        profile = self.profile_metadata()
        collections = sorted((self.collection_view(c) for c in self.collections), key=self._collection_order)
        term_groups = self.term_groups()
        self.check_terms()
        return {
            "profile": profile,
            "respec_config": self.respec_config(profile),
            "source": {"name": self.source.name, "display": self.source.display, "href": self.ttl_href()},
            "namespaces": self.namespace_rows(),
            "resources": self.resources(),
            "collections": collections,
            "term_groups": term_groups,
            "term_count": sum(len(g["terms"]) for g in term_groups),
            "term_namespaces": self.term_namespaces(),
            "examples": self.examples(),
            "vocabularies": self.adopted_vocabularies(collections),
            "github": self.args.github or None,
        }

    def ttl_href(self) -> str:
        if self.source.is_url or self.source.path is None:
            return self.source.location
        return Path(os.path.relpath(self.source.path, self.out_dir)).as_posix()

    def profile_metadata(self) -> dict:
        g, p = self.g, self.profile
        title = text(g, p, DCTERMS.title, RDFS.label, SKOS.prefLabel, DC.title)
        abstract = text(g, p, DCTERMS.abstract, DCTERMS.description, RDFS.comment, DC.description)
        description = text(g, p, DCTERMS.description, RDFS.comment, DC.description)
        citation = text(g, p, DCTERMS.bibliographicCitation)
        meta = {
            "iri": str(p),
            "title": title or local_name(str(p)) or "ODRL profile",
            "abstract": abstract,
            "description": description if description and description != abstract else None,
            "version": text(g, p, OWL.versionInfo, SDO.version, SDO_HTTP.version),
            "version_iri": next((str(o) for o in iris(g, p, OWL.versionIRI)), None),
            "prior_version": next((str(o) for o in iris(g, p, OWL.priorVersion)), None),
            "created": iso_date(text(g, p, DCTERMS.created)),
            "issued": iso_date(text(g, p, DCTERMS.issued)),
            "modified": iso_date(text(g, p, DCTERMS.modified)),
            "status": text(g, p, SW.term_status, BIBO.status, ADMS.status),
            "namespace": self.namespace,
            "prefix": self.prefix,
            "profile_of": [{"iri": str(o), "label": KNOWN_PROFILES.get(str(o))
                            or text(g, o, DCTERMS.title, RDFS.label) or self.qname(str(o))}
                           for o in iris(g, p, PROF.isProfileOf)],
            "creators": self.people(p, DCTERMS.creator, DC.creator),
            "contributors": self.people(p, DCTERMS.contributor, DC.contributor),
            "publishers": self.people(p, DCTERMS.publisher, DC.publisher),
            "license": value_or_iri(g, p, DCTERMS.license, SDO.license, SDO_HTTP.license),
            "rights": text(g, p, DCTERMS.rights),
            "rights_holder": next((self.person(o)["name"] for o in self._objects(p, DCTERMS.rightsHolder)), None),
            "doi": text(g, p, BIBO.doi),
            "citation": None if is_unfinished(citation) else citation,
            "logo": None,
        }
        meta["date"] = meta["modified"] or meta["issued"] or meta["created"]
        lic = meta["license"]
        meta["license_label"] = license_label(lic) if lic else None
        meta["license_href"] = lic if lic and re.match(r"https?://", lic) else None
        logo = next((str(o) for o in iris(g, p, FOAF.logo, SDO.logo, SDO_HTTP.logo)), None)
        if logo:
            local = self.local_file(logo)
            if local is None or local[1]:
                meta["logo"] = local[0] if local else logo

        # Profile check: the metadata asked for by the ODRL Profile Best Practices.
        required = (("title", "dcterms:title"), ("abstract", "dcterms:abstract or dcterms:description"),
                    ("version", "owl:versionInfo"), ("date", "dcterms:issued or dcterms:modified"),
                    ("license", "dcterms:license"))
        for key, prop in required:
            if not meta[key]:
                self.report.add("Profile metadata missing", prop)
        if not meta["creators"]:
            self.report.add("Profile metadata missing", "dcterms:creator")
        if not meta["profile_of"]:
            self.report.add("Profile metadata missing", "prof:isProfileOf (e.g. <http://www.w3.org/ns/odrl/2/core>)")
        if is_unfinished(citation):
            self.report.add("Looks unfinished, not shown", f'dcterms:bibliographicCitation "{citation}"')
        self.check_resource(p, "the profile")
        return meta

    def _objects(self, s, *preds) -> List:
        found = [o for p in preds for o in self.g.objects(s, p)
                 if not (isinstance(o, Literal) and not str(o).strip())]
        return sorted(set(found), key=lambda o: sort_key(str(o)))

    def people(self, s, *preds) -> List[dict]:
        # RDF has no order, so people are listed alphabetically.
        return sorted((self.person(o) for o in self._objects(s, *preds)), key=lambda x: sort_key(x["name"]))

    def person(self, node) -> dict:
        g = self.g
        if isinstance(node, Literal):
            return {"name": str(node).strip()}
        entry = {"name": text(g, node, FOAF.name, SDO.name, SDO_HTTP.name, VCARD.fn, RDFS.label)
                 or (self.qname(str(node)) if isinstance(node, URIRef) else "Unnamed")}
        if isinstance(node, URIRef):
            entry["orcid" if "orcid.org/" in str(node) else "url"] = str(node)
        mbox = next((str(o) for o in iris(g, node, FOAF.mbox, SDO.email, VCARD.hasEmail)), None)
        if mbox:
            entry["mailto"] = mbox.replace("mailto:", "")
        for org in self._objects(node, SDO.affiliation, SDO_HTTP.affiliation, ORG.memberOf, SDO.worksFor):
            entry["company"] = (str(org).strip() if isinstance(org, Literal)
                                else text(g, org, FOAF.name, SDO.name, SDO_HTTP.name, RDFS.label) or str(org))
            if isinstance(org, URIRef):
                entry["companyURL"] = str(org)
            break
        return entry

    def respec_config(self, meta: dict) -> dict:
        def add(key: str, *entries) -> None:
            entries = [e for e in entries if e]
            if entries:
                other_links.append({"key": key, "data": list(entries)})

        # The license goes into the copyright line of the template (class="copyright").
        other_links: List[dict] = []
        add("Version:", meta["version"] and {"value": meta["version"]})
        add("Status:", meta["status"] and {"value": meta["status"][:1].upper() + meta["status"][1:]})
        add("Profile of:", *[{"value": p["label"], "href": p["iri"]} for p in meta["profile_of"]])
        add("Namespace:", {"value": meta["namespace"], "href": meta["namespace"]})
        add("Preferred prefix:", meta["prefix"] and {"value": meta["prefix"]})
        add("Created:", meta["created"] and meta["created"] != meta["date"] and {"value": meta["created"]})
        add("Download serialization:", {"value": "Turtle", "href": self.ttl_href()})
        add("Publisher:", *[self._person_link(x) for x in meta["publishers"]])
        add("Contributors:", *[self._person_link(x) for x in meta["contributors"]])
        add("DOI:", meta["doi"] and {"value": meta["doi"],
                                     "href": "https://doi.org/" + re.sub(r"^https?://(dx\.)?doi\.org/", "", meta["doi"])})
        add("Cite as:", meta["citation"] and {"value": meta["citation"]})
        repo = self.args.github
        if repo:
            base = f"https://github.com/{repo}"
            in_repo = self.source.display if not self.source.is_url and self.source.display != self.source.name else ""
            history = f"{base}/commits/{DEFAULT_BRANCH}/{in_repo}" if in_repo else f"{base}/commits/{DEFAULT_BRANCH}"
            add("Participate:", {"value": f"GitHub {repo}", "href": base},
                {"value": "File an issue", "href": f"{base}/issues/new"},
                {"value": "Commit history", "href": history},
                {"value": "Pull requests", "href": f"{base}/pulls"})

        config = {
            "specStatus": self.args.spec_status,
            "shortName": meta["prefix"] or re.sub(r"[^a-z0-9]+", "-", meta["title"].lower()).strip("-"),
            "latestVersion": meta["iri"],
            "editors": meta["creators"] or [{"name": "To be announced"}],
            "otherLinks": other_links,
            "localBiblio": LOCAL_BIBLIO,
        }
        if meta["date"]:
            config["publishDate"] = meta["date"]
        if meta["version_iri"]:
            config["thisVersion"] = meta["version_iri"]
        if meta["prior_version"]:
            config["prevVersion"] = meta["prior_version"]
        if meta["logo"]:
            config["logos"] = [{"src": meta["logo"], "alt": meta["title"], "href": meta["iri"], "height": 64}]
        return config

    @staticmethod
    def _person_link(person: dict) -> dict:
        href = person.get("url") or person.get("orcid") or (f"mailto:{person['mailto']}" if person.get("mailto") else None)
        return {"value": person["name"], "href": href} if href else {"value": person["name"]}

    def namespace_rows(self) -> List[dict]:
        used = set()
        for triple in self.g:
            for node in triple:
                if isinstance(node, URIRef):
                    used.add(self.split(str(node))[0])
                elif isinstance(node, Literal) and node.datatype is not None:
                    used.add(self.split(str(node.datatype))[0])
        own = {self.namespace} | {self.split(str(t))[0] for t in self.terms}
        used |= own
        rows = []
        for ns in used:
            if ns is None or ns not in self.prefixes:
                continue
            vocab = self.vocabs.get(ns)
            if ns in own:
                description, href, ref = "This profile", "#terms", ""
            else:
                description, href, ref = (vocab.name, vocab.url, vocab.ref) if vocab else ("", "", "")
            rows.append({"prefix": self.prefixes[ns], "namespace": ns, "description": description,
                         "href": href, "ref": ref, "own": ns in own})
        return sorted(rows, key=lambda r: (not r["own"], r["prefix"]))

    def resources(self) -> List[dict]:
        g = self.g
        rows = []
        for res in sorted(set(g.objects(self.profile, PROF.hasResource)), key=str):
            roles = [ROLE_LABELS.get(local_name(str(r)), local_name(str(r)).capitalize())
                     for r in iris(g, res, PROF.hasRole)]
            formats = []
            for f in iris(g, res, DCTERMS.format):
                f = str(f)
                formats.append(f[len(IANA_MEDIA_TYPES):] if f.startswith(IANA_MEDIA_TYPES) else self.qname(f))
            formats += texts(g, res, DCTERMS.format)
            rows.append({
                "title": text(g, res, DCTERMS.title, RDFS.label) or self.qname(str(res)),
                "description": text(g, res, DCTERMS.description, RDFS.comment),
                "roles": roles,
                "artifacts": [self.ref(a) for a in self._objects(res, PROF.hasArtifact)],
                "formats": formats,
                "conforms_to": [Ref(FORMAT_LABELS.get(str(c), self.qname(str(c))), str(c))
                                for c in iris(g, res, DCTERMS.conformsTo)],
            })
            self.check_resource(res, f"resource {self.qname(str(res))}")
        return rows

    # -- collections ----------------------------------------------------------
    def _collection_order(self, view: CollectionView) -> Tuple:
        if view.iri.rstrip("#/") == str(self.profile).rstrip("#/"):
            return (-1, "")
        haystack = (local_name(view.iri) + " " + (view.label or "")).lower().replace(" ", "")
        rank = next((i for i, k in enumerate(COLLECTION_ORDER) if k in haystack), len(COLLECTION_ORDER))
        return (rank, view.title.lower())

    def collection_title(self, c: URIRef) -> str:
        """Section title of a collection: its label, minus a leading "<profile name> - "."""
        title = text(self.g, c, SKOS.prefLabel, RDFS.label, DCTERMS.title) or local_name(str(c))
        parts = re.split(r"\s+[-–—:]\s+", title)
        if len(parts) > 1 and "profile" in parts[0].lower():
            title = parts[-1][:1].upper() + parts[-1][1:]  # "ODRL X profile - action concepts" -> "Action concepts"
        return title

    def collection_view(self, c: URIRef) -> CollectionView:
        g = self.g
        label = text(g, c, SKOS.prefLabel, RDFS.label, DCTERMS.title)
        title = self.collection_title(c)
        view = CollectionView(id=self.ids[str(c)], iri=str(c), qname=self.qname(str(c)), title=title,
                              label=label, scope_note=text(g, c, SKOS.scopeNote),
                              definition=text(g, c, SKOS.definition, DCTERMS.description, RDFS.comment), rows=[])
        adopted: Counter = Counter()
        for m in self.members[c]:
            row = self.member_row(m)
            view.rows.append(row)
            if row.status == "not defined":
                view.undefined += 1
            elif row.source.text == "This profile":
                view.local += 1
            else:
                adopted[row.source.text] += 1
        view.rows.sort(key=lambda r: r.order)
        view.total = len(view.rows)
        view.adopted = dict(sorted(adopted.items()))
        if not self.members[c]:
            self.report.add("SKOS collection without members", view.qname)
        self.check_resource(c, f"collection {view.qname}")
        return view

    def member_row(self, m) -> MemberRow:
        g = self.g
        if not isinstance(m, URIRef):
            return MemberRow(self.ref(m), None, None, Ref("—"), order=(9, str(m)))
        iri = str(m)
        name = self.split(iri)[1].lower()
        if iri in self.ids and m in self.collections:
            return MemberRow(self.ref(m), text(g, m, SKOS.prefLabel, RDFS.label), None,
                             Ref("This profile"), order=(0, name))
        if iri in self.ids:
            deprecated = is_true(g, m, OWL.deprecated) or \
                (text(g, m, SW.term_status) or "").lower() in {"deprecated", "obsolete"}
            return MemberRow(self.ref(m, term=True), text(g, m, *LABEL_PREDICATES),
                             text(g, m, *DEFINITION_PREDICATES), Ref("This profile"),
                             status="deprecated" if deprecated else None,
                             replaced_by=[self.ref(r) for r in iris(g, m, DCTERMS.isReplacedBy)],
                             order=(0, name), local=True)
        if iri.startswith(self.namespace):
            self.report.add(f"Collection members in the {self.prefix or self.namespace} namespace "
                            "that are not defined in the Turtle file", self.qname(iri))
            return MemberRow(Ref(self.qname(iri), code=True, title=iri), None, None,
                             Ref("This profile"), status="not defined", order=(1, name), local=True)

        vocab = self.vocab_of(iri)
        ns = self.split(iri)[0]
        info = self.refvocabs.describe(m) or {}
        label = text(g, m, *LABEL_PREDICATES) or info.get("label")
        definition = text(g, m, *DEFINITION_PREDICATES) or info.get("definition")
        if ns in self.refvocabs.covered and not info and (m, None, None) not in g:
            self.report.add(f"Adopted terms not found in {vocab.short if vocab else ns} "
                            "(typo, or not in the current version?)", self.qname(iri))
        replaced = [self.ref(r, term=True) for r in info.get("replaced_by", [])]
        if info.get("deprecated"):
            hint = f" (use {', '.join(r.text for r in replaced)})" if replaced else ""
            self.report.add("Adopted terms that are deprecated", self.qname(iri) + hint)
        if vocab:
            source = Ref(vocab.short, vocab.url, title=vocab.name)
        else:
            source = Ref(self.prefixes.get(ns, "external") if ns else "external", ns or iri)
        return MemberRow(self.ref(m, term=True), label, definition, source,
                         status="deprecated" if info.get("deprecated") else None,
                         replaced_by=replaced, order=(2, source.text.lower(), name))

    def adopted_vocabularies(self, collections: List[CollectionView]) -> List[dict]:
        names = {name for c in collections for name in c.adopted}
        out = []
        for v in KNOWN_VOCABS:
            if v.short in names:
                out.append({"short": v.short, "name": v.name, "url": v.url, "ref": v.ref})
                names.discard(v.short)
        out += [{"short": n, "name": n, "url": "", "ref": ""} for n in sorted(names)]
        return out

    # -- terms ---------------------------------------------------------------
    def term_kind(self, t: URIRef) -> str:
        g = self.g
        types = set(g.objects(t, RDF.type))
        parents = set(g.transitive_objects(t, RDFS.subClassOf)) - {t}
        super_props = set(g.transitive_objects(t, RDFS.subPropertyOf)) - {t}
        checks = (
            ("actions", ODRL.Action in types),
            ("left-operands", ODRL.LeftOperand in types),
            ("operators", ODRL.Operator in types),
            ("right-operands", ODRL.RightOperand in types),
            ("conflict-terms", ODRL.ConflictTerm in types),
            ("party-functions", ODRL.function in super_props),
            ("asset-relations", ODRL.relation in super_props),
            ("logical-constraints", ODRL.operand in super_props),
            ("policy-types", bool(parents & {ODRL.Policy, ODRL.Set, ODRL.Offer, ODRL.Agreement})),
            ("rule-types", bool(parents & {ODRL.Rule, ODRL.Permission, ODRL.Prohibition, ODRL.Duty})),
            ("constraint-types", bool(parents & {ODRL.Constraint, ODRL.LogicalConstraint})),
            ("party-types", bool(parents & {ODRL.Party, ODRL.PartyCollection})),
            ("asset-types", bool(parents & {ODRL.Asset, ODRL.AssetCollection})),
            ("properties", bool(types & PROPERTY_TYPES)),
            ("classes", bool(types & CLASS_TYPES)),
        )
        return next((kind for kind, matches in checks if matches), "concepts")

    def term_namespaces(self) -> List[dict]:
        found = sorted({self.split(str(t))[0] or str(t) for t in self.terms})
        return [{"namespace": ns, "prefix": self.prefixes.get(ns)} for ns in found]

    def term_groups(self) -> List[dict]:
        grouped: Dict[str, List[TermView]] = defaultdict(list)
        for t in self.terms:
            grouped[self.term_kind(t)].append(self.term_view(t))
        groups = []
        for kind, title in TERM_KINDS:
            if grouped.get(kind):
                terms = sorted(grouped[kind], key=lambda v: sort_key(v.qname))
                groups.append({"id": f"terms-{kind}", "title": title, "terms": terms})
        return groups

    def term_view(self, t: URIRef) -> TermView:
        g = self.g
        iri = str(t)
        label = text(g, t, RDFS.label, SKOS.prefLabel)
        definition = text(g, t, *DEFINITION_PREDICATES)
        rows: List[Tuple[str, List[Ref]]] = []
        for title, preds in DETAIL_ROWS:
            values = self._objects(t, *preds)
            if title == "Contributors":
                refs = [Ref(self.person(v)["name"], self._person_link(self.person(v)).get("href")) for v in values]
            else:
                refs = [self.ref(v, term=True) for v in values]
            if title == "Instance of":
                refs = sorted((r for r in refs if r.text != "rdfs:Resource"), key=lambda r: sort_key(r.text))
            if refs:
                rows.append((title, refs))
        narrower = sorted({s for s in g.subjects(SKOS.broader, t)} | set(g.objects(t, SKOS.narrower)), key=str)
        if narrower:
            rows.append(("Narrower", [self.ref(n, term=True) for n in narrower]))
        subclasses = sorted(s for s in g.subjects(RDFS.subClassOf, t) if isinstance(s, URIRef))
        if subclasses:
            rows.append(("Subclasses", [self.ref(s, term=True) for s in subclasses]))
        member_of = [c for c in self.collections if t in self.members[c]]
        if member_of:
            rows.append(("Member of", [Ref(self.collection_title(c), "#" + self.ids[str(c)]) for c in member_of]))
        status = text(g, t, SW.term_status)
        deprecated = is_true(g, t, OWL.deprecated) or (status or "").lower() in {"deprecated", "obsolete"}
        if status or deprecated:
            rows.append(("Status", [Ref(status or "deprecated")]))
        other: Dict[str, List[Ref]] = defaultdict(list)
        for p, o in sorted(g.predicate_objects(t), key=lambda po: (str(po[0]), str(po[1]))):
            if p in HANDLED_TERM_PREDICATES or (isinstance(o, Literal) and not str(o).strip()):
                continue
            other[self.qname(str(p))].append(self.ref(o, term=True))
        rows.extend(other.items())
        return TermView(id=self.ids[iri], iri=iri, qname=self.qname(iri),
                        heading=label or local_name(iri), label=label,
                        alt_labels=texts(g, t, SKOS.altLabel), definition=definition,
                        rows=rows, deprecated=deprecated)

    def check_terms(self) -> None:
        g = self.g
        in_collections = {m for ms in self.members.values() for m in ms}
        for t in self.terms:
            q = self.qname(str(t))
            if not text(g, t, RDFS.label, SKOS.prefLabel):
                self.report.add("Terms without a label", q)
            if not text(g, t, *DEFINITION_PREDICATES):
                self.report.add("Terms without a definition", q)
            if self.collections and t not in in_collections:
                self.report.add("Terms not in any SKOS collection (Profile BP: every concept must be a member)", q)
            if not set(g.objects(t, RDF.type)):
                self.report.add("Terms without rdf:type", q)
        if self.collections and not any(c.rstrip("#/") == str(self.profile).rstrip("#/") for c in map(str, self.collections)):
            self.report.add("No SKOS collection identified by the profile IRI listing all its concepts "
                            "(recommended by the ODRL Profile Best Practices)")

    # -- examples ------------------------------------------------------------
    def examples(self) -> List[dict]:
        folder = Path(self.args.examples) if self.args.examples else (
            self.source.path.parent / "examples" if self.source.path else None)
        if folder is None or not folder.is_dir():
            return []
        out = []
        for f in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if f.suffix.lower() not in EXAMPLE_FORMATS or not f.is_file():
                continue
            rdf_format, css = EXAMPLE_FORMATS[f.suffix.lower()]
            content = f.read_text(encoding="utf-8")
            try:
                if rdf_format:
                    Graph().parse(data=content, format=rdf_format)
                else:
                    json.loads(content)
            except Exception as exc:  # noqa: BLE001
                self.report.add("Example files that do not parse", f"{f.name} ({str(exc).splitlines()[0]})")
            title = re.sub(r"^\d+[-_. ]*", "", f.stem).replace("_", " ").replace("-", " ").strip() or f.stem
            out.append({"title": title[:1].upper() + title[1:], "file": f.name,
                        "href": Path(os.path.relpath(f, self.out_dir)).as_posix(),
                        "css": css, "content": content.rstrip()})
        return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
URL_RE = re.compile(r"https?://[^\s<>\"]+")


def linkify(value) -> Markup:
    """Escape text, turn URLs into links and keep line breaks."""
    if value is None:
        return Markup("")

    def repl(match: re.Match) -> str:
        url = match.group(0)
        trail = ""
        while url and url[-1] in ".,;:!?)]'":
            trail, url = url[-1] + trail, url[:-1]
        return f'<a href="{url}">{url}</a>{trail}'

    escaped = str(escape(str(value)))
    return Markup(URL_RE.sub(repl, escaped).replace("\n", "<br>\n"))


RFC2119_RE = re.compile(r"\b(?:MUST|SHOULD|SHALL|MAY|REQUIRED|RECOMMENDED|OPTIONAL)\b")


def needs_conformance(html: str) -> bool:
    """ReSpec warns when RFC 2119 key words (MUST, SHOULD, ...) appear without a conformance section."""
    if 'id="conformance"' in html:
        return False
    body = html[html.find("<body"):]
    body = re.sub(r"<(pre|script|style)\b.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->|<[^>]+>", " ", body, flags=re.S)
    return bool(RFC2119_RE.search(body))


def render(template_path: Path, context: dict) -> str:
    if not template_path.is_file():
        raise BuildError(f"Template not found: {template_path}")
    env = Environment(loader=FileSystemLoader(str(template_path.parent)), autoescape=True,
                      undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True,
                      keep_trailing_newline=True)
    env.filters["text"] = linkify
    env.policies["json.dumps_kwargs"] = {"sort_keys": False, "ensure_ascii": False}
    template = env.get_template(template_path.name)
    html = template.render(**context, conformance=False)
    if needs_conformance(html):
        html = template.render(**context, conformance=True)
    return html


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
def _shown(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the ReSpec HTML documentation of an ODRL profile from its Turtle file.",
        epilog="examples:\n"
               "  python scripts/build_profile_docs.py\n"
               "  python scripts/build_profile_docs.py docs/profile.ttl -o docs/index.html\n"
               "  python scripts/build_profile_docs.py --offline --strict\n",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", default=str(DEFAULT_INPUT),
                        help=f"profile Turtle file, path or URL (default: {_shown(DEFAULT_INPUT)})")
    parser.add_argument("-o", "--output", help="HTML file to write (default: the input file with .html)")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE),
                        help=f"Jinja2/ReSpec template (default: {_shown(DEFAULT_TEMPLATE)})")
    parser.add_argument("--github", default=DEFAULT_GITHUB_REPO,
                        help=f"GitHub repository for the 'Participate' links, '' to hide them "
                             f"(default: {DEFAULT_GITHUB_REPO})")
    parser.add_argument("--spec-status", default=DEFAULT_SPEC_STATUS,
                        help=f"ReSpec specStatus (default: {DEFAULT_SPEC_STATUS})")
    parser.add_argument("--examples", help="folder with example policies (default: 'examples' next to the input)")
    parser.add_argument("--offline", action="store_true",
                        help="do not download reference vocabularies (cached copies are still used)")
    parser.add_argument("--no-lookup", action="store_true",
                        help="do not look up labels and definitions of adopted terms at all")
    parser.add_argument("--refresh-vocabs", action="store_true", help="download the reference vocabularies again")
    parser.add_argument("--vocab", action="append", default=[], metavar="PREFIX=URL_OR_FILE",
                        help="source for the terms of a prefix declared in the Turtle file, replacing the "
                             "built-in one, e.g. dpv=https://w3id.org/dpv/dpv.ttl (repeatable)")
    parser.add_argument("--cache-dir", default=str(default_cache_dir()),
                        help="where downloaded vocabularies are kept (default: %(default)s)")
    parser.add_argument("--strict", action="store_true", help="exit with status 1 if the profile check finds issues")
    parser.add_argument("-q", "--quiet", action="store_true", help="only print errors")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    report = Report()
    try:
        source = resolve_source(args.input)
        if args.output:
            output = Path(args.output).expanduser().resolve()
        elif source.path is not None:
            output = source.path.with_suffix(".html")
        else:
            raise BuildError("Use --output to say where to write the HTML when the input is a URL.")
        try:
            g = parse_rdf(source.location)
        except Exception as exc:  # noqa: BLE001 - report syntax errors nicely
            raise BuildError(f"Could not parse {source.display}:\n{exc}") from exc

        declared = {prefix: str(ns) for prefix, ns in g.namespaces()}
        args.vocab_overrides = {}
        for item in args.vocab:
            prefix, sep, location = item.partition("=")
            if not sep or prefix not in declared:
                raise BuildError(f"--vocab {item!r}: use PREFIX=URL with a prefix declared in the Turtle file")
            args.vocab_overrides.setdefault(declared[prefix], []).append(location)

        builder = DocBuilder(g, source, output, args, report)
        context = builder.build()
        html = render(Path(args.template), context)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    changed = not output.exists() or output.read_text(encoding="utf-8") != html
    if changed:
        output.write_text(html, encoding="utf-8")

    if not args.quiet:
        members = sum(c.total for c in context["collections"])
        print(f"{'Wrote' if changed else 'Unchanged:'} {_shown(output)} - {context['term_count']} terms defined, "
              f"{len(context['collections'])} collections with {members} members.")
        if report:
            print(f"Profile check: {len(report)} item(s) to look at")
            print("\n".join(report.lines()))
        else:
            print("Profile check: no issues found.")
    return 1 if (args.strict and report) else 0


if __name__ == "__main__":
    sys.exit(main())
