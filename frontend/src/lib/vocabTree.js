import { createContext, useContext } from 'react';

// Tree builders and context for the hierarchical vocabulary browser (components/VocabBrowser.jsx).
//
// A tree node: { key, value, label, definition, notes, concept, children, alsoUnder, deprecated, meta }
//   key        unique per tree position (a concept with several parents appears more than once)
//   value      the term written into the policy; nodes without one are headings only
//   definition skos:definition (or the term's description); the detail pane always shows this slot
//   notes      scope/editorial notes, shown under the definition
//   concept    IRI of the CDIF concept when it differs from the term written into the policy
//   alsoUnder  labels of the other parents of a polyhierarchical concept
//   meta       extra [label, value] rows for the detail pane
// Every term browser shows the same detail pane: label, term, definition, notes, IRI.

// Lets operand fields open the browser without threading callbacks through every rule row.
export const BrowseContext = createContext(null);
export const useBrowse = () => useContext(BrowseContext);

// "AcademicResearch" / "Non-Commercial Research" -> "Academic Research" / "Non Commercial Research"
// Namespaces used by the vocabularies in the browse windows, to show full IRIs for prefixed terms.
const PREFIXES = {
    odrl: 'http://www.w3.org/ns/odrl/2/',
    cc: 'http://creativecommons.org/ns#',
    dpv: 'https://w3id.org/dpv#',
    oac: 'https://w3id.org/oac#',
    duodrl: 'https://w3id.org/duodrl#',
    obo: 'http://purl.obolibrary.org/obo/',
    dcterms: 'http://purl.org/dc/terms/',
    'cdif-access': 'https://w3id.org/cdif/access#',
};
export const expandIri = (term) => {
    if (!term || /^https?:\/\//.test(term)) return term || '';
    const [prefix, local] = term.split(/:(.*)/s);
    return PREFIXES[prefix] !== undefined && local !== undefined ? PREFIXES[prefix] + local : term;
};

const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);

// The detail-pane fields of a SKOS concept from /api/policy/vocab/cdif.
export const conceptFields = (c) => ({
    definition: c.definition || '',
    notes: c.notes || [],
    concept: c.iri && c.iri !== expandIri(c.value) ? c.iri : undefined,
    meta: c.replacedBy ? [['Replaced by', c.replacedBy]] : [],
});

export const humanize = (label) => label.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/[-_]+/g, ' ').replace(/\s+/g, ' ').trim();

// CDIF CV2 (DPV) purposes as a tree built from skos:broader. The root (dpv:Purpose) becomes
// "Any purpose"; a purpose with several parents is shown under each of them.
export function purposeTree(concepts) {
    const byId = Object.fromEntries(concepts.map(c => [c.id, c]));
    const children = {};
    concepts.forEach(c => (c.broader || []).forEach(b => { (children[b] ||= []).push(c); }));
    const build = (c, path) => {
        const key = `${path}/${c.id}`;
        const isRoot = !(c.broader || []).length;
        const parentId = path.split('/').pop();
        const kids = (children[c.id] || [])
            .slice()
            .sort((a, b) => humanize(a.label).localeCompare(humanize(b.label)))
            .map(k => build(k, key));
        return {
            key,
            value: c.value,
            label: isRoot ? `Any purpose` : humanize(c.label),
            ...conceptFields(c),
            deprecated: c.deprecated,
            alsoUnder: (c.broader || []).filter(b => b !== parentId).map(b => humanize(byId[b]?.label || b)),
            children: kids,
        };
    };
    return concepts.filter(c => !(c.broader || []).length).map(c => build(c, ''));
}

// A flat, alphabetical list of vocabulary terms (CV3 left operands, CV4 duty actions):
// items carry value, label and the conceptFields (definition, notes, concept).
export function flatTree(items) {
    return items
        .map(t => ({
            key: t.value,
            value: t.value,
            label: capitalize(humanize(t.label || t.value.split(':').pop())),
            definition: t.definition || '',
            notes: t.notes || [],
            concept: t.concept,
            deprecated: t.deprecated,
            meta: t.meta || [],
        }))
        .sort((a, b) => (!!a.deprecated - !!b.deprecated) || a.label.localeCompare(b.label)); // deprecated last
}

// Actions: CDIF CV1 from the profile as one alphabetical list.
export function actionTree(actions) {
    return flatTree(actions.map(a => ({
        value: a.iri,
        label: a.name,
        definition: a.definition ?? a.description ?? '',
        notes: a.notes || [],
        concept: a.concept,
        deprecated: a.deprecated,
        meta: a.meta || [],
    })));
}
