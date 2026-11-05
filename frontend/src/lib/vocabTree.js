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
    cv1: 'https://odrl.codata.org/cv1/',
    cv2: 'https://odrl.codata.org/cv2/',
    cv3: 'https://odrl.codata.org/cv3/',
    cv4: 'https://odrl.codata.org/cv4/',
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

// CDIF CV2 purposes as a tree built from skos:broader. The root (cv2:Purpose) becomes
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

// Left operands: optional vocabulary groups (e.g. CDIF CV3), then ODRL 2.2 split into categories.
export function leftOperandTree(groups, odrlTerms) {
    const term = (prefix) => (t) => ({
        key: `${prefix}/${t.value}`,
        value: t.value,
        label: t.label || t.value.split(':').pop(),
        definition: t.definition ?? t.description ?? '',
        notes: t.notes || [],
        concept: t.concept,
        deprecated: t.deprecated,
    });
    const nodes = groups.map(g => ({
        key: g.label,
        label: g.label,
        // prefixed sheet labels ("ai:AISystem", "dpv:Purpose") are shown as written
        children: g.terms.map(t => ({ ...term(g.label)(t), label: t.label?.includes(':') ? t.label : humanize(t.value.split(':').pop()) })),
    }));
    const categories = [];
    odrlTerms.forEach(t => {
        const cat = t.group || 'Other';
        let node = categories.find(c => c.label === cat);
        if (!node) categories.push(node = { key: `odrl/${cat}`, label: cat, children: [] });
        node.children.push(term(`odrl/${cat}`)(t));
    });
    nodes.push({ key: 'odrl', label: 'ODRL 2.2 left operands', children: categories });
    return nodes;
}


// Generic grouped tree: each item is placed at one or more category paths (e.g. ['CDIF-specific', 'Duty']).
// An item under several paths appears under each, with the others listed in alsoUnder.
// order: optional { [groupLabel]: rank } to sort sibling groups; default is first-seen order.
export function groupedTree(items, { pathsOf, nodeOf, order = {} }) {
    const roots = [];
    const groupAt = (list, label, key) => {
        let g = list.find(n => n.key === key);
        if (!g) list.push(g = { key, label, children: [] });
        return g;
    };
    items.forEach(item => {
        const paths = pathsOf(item);
        paths.forEach((path, i) => {
            let list = roots, key = '';
            path.forEach(label => { key += `/${label}`; list = groupAt(list, label, key).children; });
            const node = nodeOf(item);
            list.push({
                ...node,
                key: `${key}/${node.value}`,
                alsoUnder: paths.filter((_, j) => j !== i).map(p => p.join(' › ')),
            });
        });
    });
    const sort = (list) => {
        list.sort((a, b) => {
            if (!a.value !== !b.value) return a.value ? 1 : -1; // groups before terms
            if (!a.value) return (order[a.label] ?? 99) - (order[b.label] ?? 99);
            return a.label.localeCompare(b.label);
        });
        list.forEach(n => n.children && sort(n.children));
        return list;
    };
    return sort(roots);
}

// Actions: CDIF CV1 by source vocabulary, then by the rule type it is typically used in;
// other profiles by their category.
const RULE_GROUPS = { Permission: 'Typically in a permission', Duty: 'Typically in a duty', Prohibition: 'Typically in a prohibition' };
export const ruleGroupLabel = (ruleType) => RULE_GROUPS[ruleType];

export function actionTree(actions) {
    const isCdif = actions.some(a => a.collections);
    return groupedTree(actions, {
        pathsOf: (a) => {
            if (!isCdif) return [[a.category || 'Other']];
            const source = (a.collections || []).includes('CDIF-specific actions') ? 'CDIF-specific actions' : 'ODRL Common Vocabulary';
            const rules = (a.collections || []).map(l => (l.match(/ODRL (Permission|Duty|Prohibition)/) || [])[1]).filter(Boolean);
            return (rules.length ? rules.map(r => RULE_GROUPS[r]) : ['Any rule type']).map(g => [source, g]);
        },
        nodeOf: (a) => ({
            value: a.iri,
            label: a.name,
            definition: a.definition ?? a.description ?? '',
            notes: a.notes || [],
            concept: a.concept,
            deprecated: a.deprecated,
            meta: a.meta || [],
        }),
        order: {
            'CDIF-specific actions': 0, 'ODRL Common Vocabulary': 1,
            [RULE_GROUPS.Permission]: 0, [RULE_GROUPS.Duty]: 1, [RULE_GROUPS.Prohibition]: 2, 'Any rule type': 3,
        },
    });
}

// Duty actions (CDIF CV4). The scheme is flat, so terms are grouped by whether they map to an
// ODRL 2.2 action (value odrl:<term>) or are CDIF-specific (value cv4:<term>).
export function dutyTree(concepts) {
    return groupedTree(concepts.filter(c => !c.deprecated), {
        pathsOf: (c) => [[(c.value || '').startsWith('odrl:') ? 'ODRL 2.2 actions' : 'CDIF-specific duty actions']],
        nodeOf: (c) => ({
            value: c.value,
            label: capitalize(humanize(c.label)),
            ...conceptFields(c),
        }),
        order: { 'CDIF-specific duty actions': 0, 'ODRL 2.2 actions': 1 },
    });
}
