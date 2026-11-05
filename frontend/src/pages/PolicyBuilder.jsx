import React, { useMemo, useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
    ShieldCheck,
    CheckCircle2,
    AlertCircle,
    Plus,
    Trash2,
    Copy,
    RefreshCw,
    Sparkles,
    BookOpen,
    Eye,
    Key,
    Layers,
    FileCheck,
    Lock,
    Unlock,
    Info,
    ExternalLink,
    ChevronLeft,
    ChevronRight,
    ArrowLeft,
    ArrowRight
} from 'lucide-react';
import api from '../services/api';
import { cn } from '../lib/utils';
import { VocabBrowser, BrowseIconButton } from '../components/VocabBrowser';
import { BrowseContext, useBrowse, humanize, purposeTree, flatTree, actionTree, conceptFields } from '../lib/vocabTree';

// ODRL 2.2 operators (instances of odrl:Operator) — https://www.w3.org/TR/odrl-vocab/#term-Operator
const ODRL_OPERATORS = [
    { value: 'odrl:eq', label: 'eq (=)', description: 'equal to' },
    { value: 'odrl:neq', label: 'neq (≠)', description: 'not equal to' },
    { value: 'odrl:gt', label: 'gt (>)', description: 'greater than' },
    { value: 'odrl:gteq', label: 'gteq (≥)', description: 'greater than or equal' },
    { value: 'odrl:lt', label: 'lt (<)', description: 'less than' },
    { value: 'odrl:lteq', label: 'lteq (≤)', description: 'less than or equal' },
    { value: 'odrl:isA', label: 'isA', description: 'is an instance of' },
    { value: 'odrl:hasPart', label: 'hasPart', description: 'contains' },
    { value: 'odrl:isPartOf', label: 'isPartOf', description: 'is contained in' },
    { value: 'odrl:isAllOf', label: 'isAllOf', description: 'is all of' },
    { value: 'odrl:isAnyOf', label: 'isAnyOf', description: 'is any of' },
    { value: 'odrl:isNoneOf', label: 'isNoneOf', description: 'is none of' },
];

// Defaults for new rules and rows: a new permission starts as "download" for academic research.
const DEFAULT_PERMISSION_ACTION = 'cdif-access:Download';
const DEFAULT_PURPOSE = 'dpv:AcademicResearch'; // a DPV purpose (CDIF CV2)
const newPurposeConstraint = () => ({ title: '', leftOperand: 'oac:Purpose', operator: 'odrl:isA', rightOperand: DEFAULT_PURPOSE });

// Duty actions (CDIF CV4) attached to a permission (odrl:duty). "beforeUse" adds the constraint
// event lt odrl:policyUsage: the duty must be fulfilled before the permission is exercised.
const DEFAULT_DUTY_ACTION = 'cdif-access:CompleteRegistration';
const newDutyAction = () => ({ action: DEFAULT_DUTY_ACTION, beforeUse: true });
const isBeforeUseConstraint = (c) => {
    const left = c['odrl:leftOperand'] || c['leftOperand'];
    const op = c['odrl:operator'] || c['operator'];
    const right = c['odrl:rightOperand'] || c['rightOperand'];
    const rightId = typeof right === 'object' && right !== null ? right['@id'] : right;
    return ['odrl:event', 'event'].includes(left) && ['odrl:lt', 'lt'].includes(op)
        && ['odrl:policyUsage', 'policyUsage'].includes(rightId);
};

// Compact select for ODRL terms: short names in the list, the description as tooltip.
// Select for vocabulary terms: shows the prefixed term (e.g. odrl:isA), description as tooltip.
// "groups" adds labelled sections, e.g. CDIF CV3 terms before the ODRL left operands.
function TermSelect({ value, terms, groups = [], name, placeholder, ...props }) {
    const all = [...groups.flatMap(g => g.terms), ...terms];
    const selected = all.find(o => o.value === value);
    const option = (o) => <option key={o.value} value={o.value} title={o.description}>{o.value}</option>;
    return (
        <select
            value={value || ''}
            title={selected ? `${selected.value} — ${selected.description}` : value || name}
            {...props}
        >
            {placeholder && <option value="" disabled>{placeholder}</option>}
            {!selected && value && <option value={value}>{value}</option>}
            {groups.map(g => <optgroup key={g.label} label={g.label}>{g.terms.map(option)}</optgroup>)}
            {terms.map(option)}
        </select>
    );
}

// Left operand select (CDIF CV3 from the profile) with a browse icon that opens the browser.
function LeftOperandSelect({ className, onChange, ...props }) {
    const browse = useBrowse();
    const select = (
        <TermSelect terms={browse?.leftOperandTerms || []} name="Left operand" placeholder="Left Operand"
            onChange={onChange} className={cn(className, browse && 'flex-1 min-w-0')} {...props} />
    );
    if (!browse) return select;
    return (
        <div className="flex gap-1 min-w-0">
            {select}
            <BrowseIconButton
                title="Browse left operands"
                onClick={() => browse.openLeftOperands({ value: props.value, onSelect: v => onChange({ target: { value: v } }) })}
            />
        </div>
    );
}
const OperatorSelect = (props) => <TermSelect terms={ODRL_OPERATORS} name="Operator" {...props} />;


// Group CDIF CV2 purposes for the dropdown: each top-level purpose that has narrower purposes
// becomes a heading (itself + its descendants); top-level leaves go under "Other purposes".
// A purpose with several parents is listed once, under the parent with the most children
// (e.g. Commercial Research under Research And Development).
function purposeGroups(concepts) {
    const children = {};
    concepts.forEach(c => (c.broader || []).forEach(b => { (children[b] ||= []).push(c); }));
    const primaryParent = (c) => [...(c.broader || [])]
        .sort((a, b) => (children[b]?.length || 0) - (children[a]?.length || 0))[0];
    const kidsOf = (c) => (children[c.id] || [])
        .filter(k => primaryParent(k) === c.id)
        .sort((a, b) => a.label.localeCompare(b.label));
    const descendants = (c) => kidsOf(c).flatMap(k => [k, ...descendants(k)]);

    const roots = concepts.filter(c => !(c.broader || []).length);
    const tops = roots.flatMap(kidsOf);
    const groups = tops.filter(t => kidsOf(t).length > 0)
        .map(t => ({ label: humanize(t.label), items: [{ c: t, text: `${humanize(t.label)} (any)` },
            ...descendants(t).map(c => ({ c, text: humanize(c.label) }))] }));
    const leaves = tops.filter(t => kidsOf(t).length === 0);
    if (leaves.length) groups.push({ label: 'Other purposes', items: leaves.map(c => ({ c, text: humanize(c.label) })) });
    return { roots, groups };
}

const OTHER_PURPOSE = '__other__';

// Purpose (right operand) picker backed by CDIF CV2; "Other" allows any IRI.
function PurposeSelect({ value, concepts, onChange, className }) {
    const { roots, groups } = useMemo(() => purposeGroups(concepts), [concepts]);
    const known = concepts.find(c => c.value === value);
    const [customMode, setCustomMode] = useState(false);
    const showCustom = customMode;
    const browse = useBrowse();
    return (
        <div className="space-y-1 min-w-0">
            <div className="flex gap-1 min-w-0">
            <select
                value={showCustom ? OTHER_PURPOSE : (value || '')}
                title={known ? `${known.value} — ${known.definition || humanize(known.label)}` : 'Right operand: purpose (CDIF CV2)'}
                onChange={(e) => {
                    if (e.target.value === OTHER_PURPOSE) {
                        setCustomMode(true);
                    } else {
                        setCustomMode(false);
                        onChange(e.target.value);
                    }
                }}
                className={cn(className, 'flex-1 min-w-0')}
            >
                <option value="" disabled>{concepts.length ? 'Right Operand' : 'Loading purposes…'}</option>
                {!known && value && !showCustom && <option value={value}>{value}</option>}
                {roots.map(c => (
                    <option key={c.id} value={c.value} title={c.definition || ''}>{c.value}</option>
                ))}
                {groups.map(g => (
                    <optgroup key={g.label} label={g.label}>
                        {g.items.map(({ c }) => (
                            <option key={c.id} value={c.value} title={c.definition || ''}>{c.value}</option>
                        ))}
                    </optgroup>
                ))}
                <option value={OTHER_PURPOSE}>Other (enter an IRI)…</option>
            </select>
            {browse && (
                <BrowseIconButton
                    title="Browse purposes"
                    onClick={() => browse.openPurposes({ value, onSelect: (v) => { setCustomMode(false); onChange(v); } })}
                />
            )}
            </div>
            {showCustom && (
                <input
                    type="text"
                    autoFocus={customMode}
                    placeholder="e.g. dpv:IdentityVerification"
                    title="Not a CDIF CV2 purpose; validation will show a warning"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className={cn(className, "border-amber-300 dark:border-amber-700")}
                />
            )}
        </div>
    );
}

export default function PolicyBuilder() {
    // Basic Policy Metadata
    const [policyType, setPolicyType] = useState('Offer');
    const [uid, setUid] = useState(`did:oyd:${crypto.randomUUID()}`);
    const [profile, setProfile] = useState('oac:');
    const [description, setDescription] = useState('Offer to read identifier data for identity verification and age data if purpose is not commercial research.');
    const [policyTarget, setPolicyTarget] = useState('duodrl:TemplateDataset');
    const [policyAssigner, setPolicyAssigner] = useState('https://solidweb.me/besteves4/profile/card#me');

    // Descriptive metadata (dcterms + owl:versionInfo)
    const [creator, setCreator] = useState('');
    const [publisher, setPublisher] = useState('');
    const [source, setSource] = useState('');
    const [versionInfo, setVersionInfo] = useState('1.0');
    // System-generated dates (YYYY-MM-DD). created/issued are kept from a loaded policy;
    // modified is always today. The backend stamps the final values on save.
    const [createdDate, setCreatedDate] = useState(null);
    const [issuedDate, setIssuedDate] = useState(null);
    const today = new Date().toISOString().slice(0, 10);

    // Rules
    const [permissions, setPermissions] = useState([
        {
            action: 'oac:Read',
            refinements: [],
            duties: [],
            constraints: [
                {
                    title: 'Purpose for access is to verify the identity of the assigner.',
                    leftOperand: 'oac:Purpose',
                    operator: 'odrl:isA',
                    rightOperand: 'dpv:IdentityVerification'
                }
            ],
            otherConstraints: []
        }
    ]);

    const [prohibitions, setProhibitions] = useState([
        {
            target: 'duodrl:TemplateDataset',
            action: 'odrl:distribute',
            refinements: [],
            output: 'duodrl:ResultsOfStudies',
            constraints: [
                {
                    leftOperand: 'odrl:dateTime',
                    operator: 'odrl:lt',
                    rightOperand: 'duodrl:TemplateStudyResultsPublicationDate'
                }
            ]
        }
    ]);

    const [duties, setDuties] = useState([
        {
            action: 'odrl:attribute',
            target: '',
            assignee: '',
            refinements: [],
            constraints: [
                {
                    title: 'Attribution requirement',
                    leftOperand: 'odrl:recipient',
                    operator: 'odrl:eq',
                    rightOperand: 'https://solidweb.me/besteves4/profile/card#me'
                }
            ]
        }
    ]);

    const [copied, setCopied] = useState(false);
    // Action Vocabulary Profile Selection: W3C ODRL 2.2 vs CDIF ODRL v2.3
    const [actionPickerTarget, setActionPickerTarget] = useState(null); // { type: 'permission'|'prohibition'|'duty', index: number } | null
    // Hierarchical browse window for purposes / left operands: { title, subtitle, nodes, value, selectLabel, onSelect } | null
    const [browser, setBrowser] = useState(null);
    // Main Tabs: 'specification' | 'permissions' | 'prohibitions' | 'duodrl'
    const [activeTab, setActiveTab] = useState('specification');
    // Modal views triggered from Policy Operations menu
    const [operationModal, setOperationModal] = useState(null); // 'json' | 'vocab' | null
    const [shaclFeedback, setShaclFeedback] = useState(null);

    // Fetch Vocabularies & Helpers from FastAPI backend
    const { data: vocabActions } = useQuery({
        queryKey: ['vocab-actions'],
        queryFn: async () => {
            const res = await api.get('/policy/vocab/actions');
            return res.data;
        }
    });

    const { data: vocabHelpers } = useQuery({
        queryKey: ['vocab-helpers'],
        queryFn: async () => {
            const res = await api.get('/policy/vocab/helpers');
            return res.data;
        }
    });

    // CDIF access vocabularies (SKOS, config/*.ttl): CV1 actions, CV2 purposes, CV3 other constraints
    const { data: cdifVocab } = useQuery({
        queryKey: ['vocab-cdif'],
        queryFn: async () => {
            const res = await api.get('/policy/vocab/cdif');
            return res.data;
        }
    });
    const cdifPurposes = cdifVocab?.purposes?.concepts || [];
    const cdifConstraintTypes = cdifVocab?.constraints?.concepts || [];
    // CDIF CV4 duty actions ("value" is the ODRL term when the duty maps to one, e.g. odrl:anonymize)
    const cv4DutyTerms = (cdifVocab?.duties?.concepts || []).filter(c => !c.deprecated).map(c => ({
        value: c.value,
        label: (l => l.charAt(0).toUpperCase() + l.slice(1))(humanize(c.label)),
        description: [c.definition, ...(c.notes || [])].filter(Boolean).join(' — '),
    }));
    // CV3: the left operands of the CDIF access profile; deprecated operands are hidden.
    const cv3Term = (c) => ({
        value: c.value,
        label: c.label,
        description: [c.definition, ...(c.notes || [])].filter(Boolean).join(' — ') || humanize(c.label),
        ...conceptFields(c),
    });
    const cv3LeftOperandTerms = cdifConstraintTypes.filter(c => !c.deprecated).map(cv3Term);

    // CV1 actions from the CDIF access profile: ODRL/CC terms and cdif-access: terms
    const cdifCv1Actions = (cdifVocab?.actions?.concepts || []).map(c => ({
        iri: c.value,
        name: c.label,
        description: [c.definition, ...(c.notes || [])].filter(Boolean).join(' — ')
            + (c.replacedBy ? ` Use ${c.replacedBy} instead.` : ''),
        ...conceptFields(c),
        deprecated: c.deprecated,
        id: c.id,
        collections: c.collections || []
    }));

    const cv4Concepts = cdifVocab?.duties?.concepts || [];

    // Actions in odrl:action fields: CDIF CV1 from the profile only; deprecated actions are hidden
    // (a loaded policy can still use one, and validation warns about it)
    const currentActionsList = cdifCv1Actions.filter(a => !a.deprecated);

    // Preset loader mutation
    const loadPresetMutation = useMutation({
        mutationFn: async (presetName) => {
            const res = await api.get(`/policy/presets/${presetName}`);
            return res.data;
        },
        onSuccess: (data) => {
            if (data['@type'] || data['type']) setPolicyType(data['@type'] || data['type']);
            if (data['odrl:uid'] || data['uid']) setUid(data['odrl:uid'] || data['uid']);
            if (data['odrl:profile']) setProfile(data['odrl:profile']);
            if (data['dcterms:description']) setDescription(data['dcterms:description']);
            setCreator(data['dcterms:creator'] || '');
            setPublisher(data['dcterms:publisher'] || '');
            setSource(Array.isArray(data['dcterms:source']) ? data['dcterms:source'].join(', ') : (data['dcterms:source'] || ''));
            setVersionInfo(data['owl:versionInfo'] || '1.0');
            setCreatedDate(data['dcterms:created']?.slice(0, 10) || null);
            setIssuedDate(data['dcterms:issued']?.slice(0, 10) || null);
            if (data['odrl:target'] || data['target']) setPolicyTarget(data['odrl:target'] || data['target'] || '');
            if (data['odrl:assigner'] || data['assigner']) setPolicyAssigner(data['odrl:assigner'] || data['assigner'] || '');

            // Helper to parse action and its refinements
            const parseActionAndRefinements = (rawAction) => {
                if (typeof rawAction === 'string') {
                    return { actionName: rawAction, refinements: [] };
                }
                if (typeof rawAction === 'object' && rawAction !== null) {
                    const actionName = rawAction['rdf:value']?.['@id'] || rawAction['rdf:value'] || rawAction['@id'] || rawAction['value'] || 'odrl:use';
                    const rawRefinements = rawAction['odrl:refinement'] || rawAction['refinement'] || [];
                    const refinementsList = Array.isArray(rawRefinements) ? rawRefinements : [rawRefinements];
                    const refinements = refinementsList.map(r => ({
                        title: r['dcterms:title'] || r['title'] || '',
                        leftOperand: r['odrl:leftOperand'] || r['leftOperand'] || '',
                        operator: r['odrl:operator'] || r['operator'] || 'odrl:eq',
                        rightOperand: r['odrl:rightOperand'] || r['rightOperand'] || ''
                    }));
                    return { actionName, refinements };
                }
                return { actionName: 'odrl:use', refinements: [] };
            };

            // Parse Permissions
            const perms = (data['odrl:permission'] || data['permission'] || []).map(p => {
                const { actionName, refinements } = parseActionAndRefinements(p['odrl:action'] || p['action']);
                const rawConstraints = (p['odrl:constraint'] || p['constraint'] || []).map(c => ({
                    title: c['dcterms:title'] || c['title'] || '',
                    category: c['dcterms:type']?.['@id'] || c['dcterms:type'] || '',
                    leftOperand: c['odrl:leftOperand'] || c['leftOperand'] || '',
                    operator: c['odrl:operator'] || c['operator'] || 'odrl:eq',
                    rightOperand: c['odrl:rightOperand'] || c['rightOperand'] || ''
                }));
                // Separate purposes from other constraints if distinguishable
                const purposes = rawConstraints.filter(c =>
                    c.leftOperand === 'oac:Purpose' ||
                    c.leftOperand === 'odrl:purpose' ||
                    c.leftOperand === 'purpose'
                );
                const other = rawConstraints.filter(c =>
                    c.leftOperand !== 'oac:Purpose' &&
                    c.leftOperand !== 'odrl:purpose' &&
                    c.leftOperand !== 'purpose'
                );
                const rawPermDuties = p['odrl:duty'] || p['duty'] || [];
                const permDuties = (Array.isArray(rawPermDuties) ? rawPermDuties : [rawPermDuties]).map(d => {
                    const rawDutyAction = d['odrl:action'] || d['action'];
                    const { actionName: dutyAction, refinements: dutyRefinements } =
                        parseActionAndRefinements(Array.isArray(rawDutyAction) ? rawDutyAction[0] : rawDutyAction);
                    const dc = d['odrl:constraint'] || d['constraint'] || [];
                    const dutyConstraints = Array.isArray(dc) ? dc : [dc];
                    return {
                        action: dutyAction,
                        beforeUse: dutyConstraints.some(isBeforeUseConstraint),
                        // kept as loaded so presets round-trip; not editable in the UI
                        refinements: dutyRefinements,
                        extraConstraints: dutyConstraints.filter(c => !isBeforeUseConstraint(c)),
                    };
                });
                return {
                    target: p['odrl:target'] || p['target'] || '',
                    action: actionName,
                    refinements: refinements,
                    duties: permDuties,
                    hasContext: p['dpv:hasContext'] || p['hasContext'] || '',
                    assigner: p['odrl:assigner'] || p['assigner'] || '',
                    constraints: purposes.length > 0 || other.length === 0 ? purposes : rawConstraints,
                    otherConstraints: purposes.length > 0 ? other : []
                };
            });
            setPermissions(perms);

            // Parse Prohibitions
            const prohibs = (data['odrl:prohibition'] || data['prohibition'] || []).map(p => {
                const { actionName, refinements } = parseActionAndRefinements(p['odrl:action'] || p['action']);
                return {
                    target: p['odrl:target'] || p['target'] || '',
                    action: actionName,
                    refinements: refinements,
                    output: p['odrl:output'] || p['output'] || '',
                    constraints: (p['odrl:constraint'] || p['constraint'] || []).map(c => ({
                        title: c['dcterms:title'] || c['title'] || '',
                        leftOperand: c['odrl:leftOperand'] || c['leftOperand'] || '',
                        operator: c['odrl:operator'] || c['operator'] || 'odrl:lt',
                        rightOperand: c['odrl:rightOperand'] || c['rightOperand'] || ''
                    }))
                };
            });
            setProhibitions(prohibs);

            // Parse Obligations / Duties
            const rawDuties = data['odrl:obligation'] || data['obligation'] || data['odrl:duty'] || data['duty'] || [];
            const parsedDuties = rawDuties.map(d => {
                const { actionName, refinements } = parseActionAndRefinements(d['odrl:action'] || d['action']);
                return {
                    action: actionName,
                    target: d['odrl:target'] || d['target'] || '',
                    assignee: d['odrl:assignee'] || d['assignee'] || '',
                    refinements: refinements,
                    constraints: (d['odrl:constraint'] || d['constraint'] || []).map(c => ({
                        title: c['dcterms:title'] || c['title'] || '',
                        leftOperand: c['odrl:leftOperand'] || c['leftOperand'] || '',
                        operator: c['odrl:operator'] || c['operator'] || 'odrl:eq',
                        rightOperand: c['odrl:rightOperand'] || c['rightOperand'] || ''
                    }))
                };
            });
            if (parsedDuties.length > 0) {
                setDuties(parsedDuties);
            }
            setShaclFeedback({ status: 'info', message: 'Preset loaded successfully!' });
        }
    });

    // Compile JSON-LD
    const compilePolicyJson = () => {
        const policy = {
            "@context": [
                "http://www.w3.org/ns/odrl.jsonld",
                "https://w3id.org/oac/context.json",
                {
                    "duodrl": "https://w3id.org/duodrl#",
                    "obo": "http://purl.obolibrary.org/obo/",
                    "skos": "http://www.w3.org/2004/02/skos/core#",
                    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                    "cc": "http://creativecommons.org/ns#",
                    "cdif-access": "https://w3id.org/cdif/access#",
                    "dcterms": "http://purl.org/dc/terms/",
                    "owl": "http://www.w3.org/2002/07/owl#"
                }
            ],
            "@type": policyType,
            "type": policyType,
            "odrl:uid": uid,
            "odrl:profile": profile
        };

        if (creator.trim()) policy["dcterms:creator"] = creator.trim();
        if (publisher.trim()) policy["dcterms:publisher"] = publisher.trim();
        if (description.trim()) policy["dcterms:description"] = description.trim();
        const sources = source.split(',').map(s => s.trim()).filter(Boolean);
        if (sources.length) policy["dcterms:source"] = sources.length === 1 ? sources[0] : sources;
        policy["dcterms:created"] = createdDate || today;
        policy["dcterms:modified"] = today;
        policy["dcterms:issued"] = issuedDate || today;
        policy["owl:versionInfo"] = versionInfo.trim() || '1.0';

        if (policyTarget.trim()) {
            policy["odrl:target"] = policyTarget.trim();
        }

        if (policyAssigner.trim()) {
            policy["odrl:assigner"] = policyAssigner.trim();
        }

        // Helper to format action with or without refinement
        const formatAction = (actionName, refinements) => {
            if (!refinements || refinements.length === 0) {
                return actionName;
            }
            return {
                "rdf:value": { "@id": actionName },
                "odrl:refinement": refinements.map(r => {
                    const refObj = {
                        "odrl:leftOperand": r.leftOperand,
                        "odrl:operator": r.operator,
                        "odrl:rightOperand": r.rightOperand
                    };
                    if (r.title) refObj["dcterms:title"] = r.title;
                    return refObj;
                })
            };
        };

        if (permissions.length > 0) {
            policy["odrl:permission"] = permissions.map(p => {
                const rule = {
                    "odrl:action": formatAction(p.action, p.refinements)
                };
                if (p.target) rule["odrl:target"] = p.target;
                if (p.hasContext) rule["dpv:hasContext"] = p.hasContext;
                if (p.assigner) rule["odrl:assigner"] = p.assigner;

                const allConstraints = [
                    ...(p.constraints || []),
                    ...(p.otherConstraints || [])
                ];

                if (allConstraints.length > 0) {
                    rule["odrl:constraint"] = allConstraints.map(c => {
                        const constraintObj = {
                            "odrl:leftOperand": c.leftOperand,
                            "odrl:operator": c.operator,
                            "odrl:rightOperand": c.rightOperand
                        };
                        if (c.title) constraintObj["dcterms:title"] = c.title;
                        if (c.category) constraintObj["dcterms:type"] = { "@id": c.category };
                        return constraintObj;
                    });
                }
                const permDuties = (p.duties || []).filter(d => d.action);
                if (permDuties.length > 0) {
                    rule["odrl:duty"] = permDuties.map(d => {
                        const duty = { "odrl:action": formatAction(d.action, d.refinements) };
                        const dutyConstraints = [
                            ...(d.beforeUse ? [{
                                "odrl:leftOperand": "odrl:event",
                                "odrl:operator": "odrl:lt",
                                "odrl:rightOperand": { "@id": "odrl:policyUsage" }
                            }] : []),
                            ...(d.extraConstraints || [])
                        ];
                        if (dutyConstraints.length > 0) duty["odrl:constraint"] = dutyConstraints;
                        return duty;
                    });
                }
                return rule;
            });
        }

        if (prohibitions.length > 0) {
            policy["odrl:prohibition"] = prohibitions.map(p => {
                const rule = {
                    "odrl:target": p.target,
                    "odrl:action": formatAction(p.action, p.refinements)
                };
                if (p.output) rule["odrl:output"] = p.output;
                if (p.constraints && p.constraints.length > 0) {
                    rule["odrl:constraint"] = p.constraints.map(c => {
                        const constraintObj = {
                            "odrl:leftOperand": c.leftOperand,
                            "odrl:operator": c.operator,
                            "odrl:rightOperand": c.rightOperand
                        };
                        if (c.title) constraintObj["dcterms:title"] = c.title;
                        return constraintObj;
                    });
                }
                return rule;
            });
        }

        if (duties.length > 0) {
            policy["odrl:obligation"] = duties.map(d => {
                const rule = {
                    "odrl:action": formatAction(d.action, d.refinements)
                };
                if (d.target) rule["odrl:target"] = d.target;
                if (d.assignee) rule["odrl:assignee"] = d.assignee;
                if (d.constraints && d.constraints.length > 0) {
                    rule["odrl:constraint"] = d.constraints.map(c => {
                        const constraintObj = {
                            "odrl:leftOperand": c.leftOperand,
                            "odrl:operator": c.operator,
                            "odrl:rightOperand": c.rightOperand
                        };
                        if (c.title) constraintObj["dcterms:title"] = c.title;
                        return constraintObj;
                    });
                }
                return rule;
            });
        }

        return policy;
    };

    // Validation Mutation
    const validateMutation = useMutation({
        mutationFn: async (policyObj) => {
            const res = await api.post('/policy/validate', { policy: policyObj });
            return res.data;
        },
        onSuccess: (data) => {
            const warnings = data.warnings || [];
            if (data.valid) {
                setShaclFeedback({
                    status: 'success',
                    message: warnings.length > 0
                        ? 'SHACL & ODRL 2.2 Validation Passed, with CDIF vocabulary warnings:'
                        : 'SHACL & ODRL 2.2 Validation Passed! Conforms to W3C specification.',
                    errors: warnings
                });
            } else {
                setShaclFeedback({
                    status: 'error',
                    message: 'Validation failed',
                    errors: [...data.errors, ...warnings]
                });
            }
        },
        onError: (err) => {
            setShaclFeedback({
                status: 'error',
                message: err.response?.data?.detail || err.message
            });
        }
    });

    // Save & Anchor Mutation
    const saveMutation = useMutation({
        mutationFn: async (policyObj) => {
            const res = await api.post('/policy/create', { policy: policyObj, anchor_did: true });
            return res.data;
        },
        onSuccess: (data) => {
            if (data.policy?.['dcterms:created']) setCreatedDate(data.policy['dcterms:created']);
            if (data.policy?.['dcterms:issued']) setIssuedDate(data.policy['dcterms:issued']);
            setShaclFeedback({
                status: 'success',
                message: `Policy anchored successfully! UID / DID: ${data.uid}`
            });
        },
        onError: (err) => {
            setShaclFeedback({
                status: 'error',
                message: 'Failed to create policy',
                errors: err.response?.data?.detail?.errors || [err.message]
            });
        }
    });

    const handleCopy = () => {
        navigator.clipboard.writeText(JSON.stringify(compilePolicyJson(), null, 2));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const addPermission = () => {
        setPermissions([
            ...permissions,
            {
                action: DEFAULT_PERMISSION_ACTION,
                refinements: [],
                duties: [],
                constraints: [newPurposeConstraint()],
                otherConstraints: []
            }
        ]);
    };

    const removePermission = (index) => {
        setPermissions(permissions.filter((_, i) => i !== index));
    };

    const addPermissionDuty = (pIndex) => {
        const next = [...permissions];
        next[pIndex].duties = [...(next[pIndex].duties || []), newDutyAction()];
        setPermissions(next);
    };

    const updatePermissionDuty = (pIndex, dIndex, field, value) => {
        const next = [...permissions];
        next[pIndex].duties[dIndex] = { ...next[pIndex].duties[dIndex], [field]: value };
        setPermissions(next);
    };

    const removePermissionDuty = (pIndex, dIndex) => {
        const next = [...permissions];
        next[pIndex].duties = next[pIndex].duties.filter((_, i) => i !== dIndex);
        setPermissions(next);
    };

    const addPermissionConstraint = (pIndex) => {
        const next = [...permissions];
        next[pIndex].constraints.push(newPurposeConstraint());
        setPermissions(next);
    };

    const removePermissionConstraint = (pIndex, cIndex) => {
        const next = [...permissions];
        next[pIndex].constraints = next[pIndex].constraints.filter((_, i) => i !== cIndex);
        setPermissions(next);
    };

    const addPermissionOtherConstraint = (pIndex) => {
        const next = [...permissions];
        if (!next[pIndex].otherConstraints) next[pIndex].otherConstraints = [];
        next[pIndex].otherConstraints.push({
            title: '',
            category: '',
            leftOperand: 'odrl:spatial',
            operator: 'odrl:eq',
            rightOperand: 'https://sws.geonames.org/2921044/'
        });
        setPermissions(next);
    };

    const removePermissionOtherConstraint = (pIndex, cIndex) => {
        const next = [...permissions];
        next[pIndex].otherConstraints = next[pIndex].otherConstraints.filter((_, i) => i !== cIndex);
        setPermissions(next);
    };

    const addProhibition = () => {
        setProhibitions([
            ...prohibitions,
            {
                target: 'duodrl:TemplateDataset',
                action: 'odrl:distribute',
                refinements: [],
                output: '',
                constraints: []
            }
        ]);
    };

    const removeProhibition = (index) => {
        setProhibitions(prohibitions.filter((_, i) => i !== index));
    };

    const addProhibitionRefinement = (pIndex) => {
        const next = [...prohibitions];
        if (!next[pIndex].refinements) next[pIndex].refinements = [];
        next[pIndex].refinements.push({
            title: '',
            leftOperand: 'odrl:spatial',
            operator: 'odrl:eq',
            rightOperand: 'https://sws.geonames.org/2921044/'
        });
        setProhibitions(next);
    };

    const removeProhibitionRefinement = (pIndex, rIndex) => {
        const next = [...prohibitions];
        next[pIndex].refinements = next[pIndex].refinements.filter((_, i) => i !== rIndex);
        setProhibitions(next);
    };

    const addProhibitionConstraint = (pIndex) => {
        const next = [...prohibitions];
        next[pIndex].constraints.push({
            title: '',
            leftOperand: 'odrl:dateTime',
            operator: 'odrl:lt',
            rightOperand: '2026-12-31T23:59:59Z'
        });
        setProhibitions(next);
    };

    const removeProhibitionConstraint = (pIndex, cIndex) => {
        const next = [...prohibitions];
        next[pIndex].constraints = next[pIndex].constraints.filter((_, i) => i !== cIndex);
        setProhibitions(next);
    };

    const addDuty = () => {
        setDuties([
            ...duties,
            {
                action: 'odrl:attribute',
                target: '',
                assignee: '',
                refinements: [],
                constraints: []
            }
        ]);
    };

    const removeDuty = (index) => {
        setDuties(duties.filter((_, i) => i !== index));
    };

    const addDutyRefinement = (dIndex) => {
        const next = [...duties];
        if (!next[dIndex].refinements) next[dIndex].refinements = [];
        next[dIndex].refinements.push({
            title: '',
            leftOperand: 'odrl:payAmount',
            operator: 'odrl:eq',
            rightOperand: '10.00'
        });
        setDuties(next);
    };

    const removeDutyRefinement = (dIndex, rIndex) => {
        const next = [...duties];
        next[dIndex].refinements = next[dIndex].refinements.filter((_, i) => i !== rIndex);
        setDuties(next);
    };

    const addDutyConstraint = (dIndex) => {
        const next = [...duties];
        next[dIndex].constraints.push({
            title: '',
            leftOperand: 'odrl:recipient',
            operator: 'odrl:eq',
            rightOperand: 'https://solidweb.me/besteves4/profile/card#me'
        });
        setDuties(next);
    };

    const removeDutyConstraint = (dIndex, cIndex) => {
        const next = [...duties];
        next[dIndex].constraints = next[dIndex].constraints.filter((_, i) => i !== cIndex);
        setDuties(next);
    };

    // Browse windows. onSelect receives the chosen term; the window closes afterwards.
    const openBrowser = (opts) => setBrowser({
        ...opts,
        onSelect: (v) => { opts.onSelect(v); setBrowser(null); },
    });
    const browseApi = {
        openPurposes: ({ value, onSelect, selectLabel = 'Use this purpose' }) => openBrowser({
            title: 'Browse purposes',
            subtitle: 'CDIF CV2: DPV purposes. A broader purpose includes all purposes under it.',
            nodes: purposeTree(cdifPurposes),
            value, selectLabel, onSelect,
        }),
        openLeftOperands: ({ value, onSelect, selectLabel = 'Use this left operand' }) => openBrowser({
            title: 'Browse constraints',
            subtitle: 'CDIF CV3: the left operands of the CDIF access profile.',
            nodes: flatTree(cv3LeftOperandTerms),
            value, selectLabel, onSelect,
        }),
        openDuties: ({ value, onSelect, selectLabel = 'Use this duty action' }) => openBrowser({
            title: 'Browse duty actions',
            subtitle: 'CDIF CV4 duty actions: what the assignee must do to exercise the permission.',
            nodes: flatTree(cv4Concepts.filter(c => !c.deprecated).map(c => ({ ...c, ...conceptFields(c) }))),
            value, selectLabel, onSelect,
        }),
        leftOperandTerms: cv3LeftOperandTerms,
    };
    // Handler to apply selected action to the active rule
    const selectActionForTarget = (actionIri) => {
        if (!actionPickerTarget) return;
        const { type, index } = actionPickerTarget;
        if (type === 'permission') {
            const next = [...permissions];
            if (next[index]) next[index].action = actionIri;
            setPermissions(next);
        } else if (type === 'prohibition') {
            const next = [...prohibitions];
            if (next[index]) next[index].action = actionIri;
            setProhibitions(next);
        } else if (type === 'duty') {
            const next = [...duties];
            if (next[index]) next[index].action = actionIri;
            setDuties(next);
        }
        setActionPickerTarget(null);
    };

    return (
        <BrowseContext.Provider value={browseApi}>
        <div className="space-y-8 animate-in fade-in duration-500">
            {/* Header */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 dark:border-white/10 pb-6">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 dark:text-white flex items-center gap-3">
                        <ShieldCheck className="text-indigo-600 dark:text-indigo-400" size={32} />
                        W3C ODRL & OAC Policy Studio
                    </h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                        Step-by-step interactive policy creator based on W3C Action Concepts, OAC Privacy Profiles, and SHACL validation.
                    </p>
                </div>

                {/* Preset Fast Actions */}
                <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 flex items-center gap-1 mr-1">
                        <Sparkles size={14} className="text-amber-500" /> Presets:
                    </span>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('listing-4.2')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/40 dark:hover:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 transition-all"
                    >
                        Listing 4.2 (OAC Offer)
                    </button>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('duo-0000042')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:hover:bg-emerald-900/40 text-emerald-600 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 transition-all"
                    >
                        DUO_0000042 (GRU)
                    </button>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('duo-0000024')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/40 dark:hover:bg-purple-900/40 text-purple-600 dark:text-purple-300 border border-purple-200 dark:border-purple-800 transition-all"
                    >
                        DUO_0000024 (MOR)
                    </button>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('duo-0000004')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 dark:hover:bg-rose-900/40 text-rose-600 dark:text-rose-300 border border-rose-200 dark:border-rose-800 transition-all"
                    >
                        DUO_0000004 (NPOA)
                    </button>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('duo-0000043')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-cyan-50 hover:bg-cyan-100 dark:bg-cyan-950/40 dark:hover:bg-cyan-900/40 text-cyan-600 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800 transition-all"
                    >
                        DUO_0000043 (HMB)
                    </button>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('duo-0000046')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 dark:hover:bg-amber-900/40 text-amber-600 dark:text-amber-300 border border-amber-200 dark:border-amber-800 transition-all"
                    >
                        DUO_0000046 (IRB)
                    </button>
                    <button
                        type="button"
                        onClick={() => loadPresetMutation.mutate('read-only')}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-white/10 transition-all"
                    >
                        Read-Only Set
                    </button>
                </div>
            </div>

            {/* Validation Feedback Banner */}
            {shaclFeedback && (
                <div className={cn(
                    "p-4 rounded-xl border flex items-start gap-3 transition-all",
                    shaclFeedback.status === 'success' ? "bg-emerald-50 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300" :
                    shaclFeedback.status === 'error' ? "bg-rose-50 dark:bg-rose-950/30 border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300" :
                    "bg-blue-50 dark:bg-blue-950/30 border-blue-300 dark:border-blue-800 text-blue-800 dark:text-blue-300"
                )}>
                    {shaclFeedback.status === 'success' ? <CheckCircle2 size={20} className="shrink-0 mt-0.5 text-emerald-600" /> :
                     shaclFeedback.status === 'error' ? <AlertCircle size={20} className="shrink-0 mt-0.5 text-rose-600" /> :
                     <Sparkles size={20} className="shrink-0 mt-0.5 text-blue-600" />}
                    <div className="flex-1 text-sm">
                        <p className="font-bold">{shaclFeedback.message}</p>
                        {shaclFeedback.errors && shaclFeedback.errors.length > 0 && (
                            <ul className="mt-2 list-disc list-inside space-y-1 text-xs opacity-90">
                                {shaclFeedback.errors.map((err, i) => (
                                    <li key={i}>{err}</li>
                                ))}
                            </ul>
                        )}
                    </div>
                </div>
            )}

            {/* Main Tabs: Specification | Permissions | Prohibitions | DUODRL */}
            <div className="flex items-center gap-3 border-b border-gray-200 dark:border-white/10">
                <button
                    onClick={() => setActiveTab('specification')}
                    className={cn(
                        "pb-3 text-sm font-bold transition-all border-b-2 flex items-center gap-2",
                        activeTab === 'specification'
                            ? "border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400"
                            : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    )}
                >
                    <Key size={16} /> Policy Specification
                </button>
                <button
                    onClick={() => setActiveTab('permissions')}
                    className={cn(
                        "pb-3 text-sm font-bold transition-all border-b-2 flex items-center gap-2",
                        activeTab === 'permissions'
                            ? "border-emerald-600 text-emerald-600 dark:border-emerald-400 dark:text-emerald-400"
                            : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    )}
                >
                    <CheckCircle2 size={16} /> Permissions ({permissions.length})
                </button>
                <button
                    onClick={() => setActiveTab('prohibitions')}
                    className={cn(
                        "pb-3 text-sm font-bold transition-all border-b-2 flex items-center gap-2",
                        activeTab === 'prohibitions'
                            ? "border-rose-600 text-rose-600 dark:border-rose-400 dark:text-rose-400"
                            : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    )}
                >
                    <AlertCircle size={16} /> Prohibitions ({prohibitions.length})
                </button>
                <button
                    onClick={() => setActiveTab('duodrl')}
                    className={cn(
                        "pb-3 text-sm font-bold transition-all border-b-2 flex items-center gap-2",
                        activeTab === 'duodrl'
                            ? "border-amber-600 text-amber-600 dark:border-amber-400 dark:text-amber-400"
                            : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400"
                    )}
                >
                    <FileCheck size={16} /> Duty ({duties.length})
                </button>
            </div>

            {/* Layout Grid: Tab Content on the Left, Policy Operations on the Right */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Left 2 Cols: Active Tab Content */}
                <div className="lg:col-span-2 space-y-6">

                    {/* TAB 1: POLICY SPECIFICATION */}
                    {activeTab === 'specification' && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-white/[0.03] border border-gray-200 dark:border-white/10 shadow-sm space-y-5">
                            <div className="border-b border-gray-200 dark:border-white/5 pb-3">
                                <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                    <Key size={18} className="text-indigo-500" />
                                    Policy Specification & Header
                                </h2>
                                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                    Set the ODRL policy type, unique identifier, profile URI, and author metadata.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Policy Type (@type)
                                    </label>
                                    <select
                                        value={policyType}
                                        onChange={(e) => setPolicyType(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-medium focus:ring-2 focus:ring-indigo-500"
                                    >
                                        <option value="Offer">Offer (odrl:Offer issued by assigner)</option>
                                        <option value="Agreement">Agreement (Bilateral agreement)</option>
                                        <option value="Set">Set (General Policy Definition)</option>
                                        <option value="Request">Request (Client request)</option>
                                        <option value="Preference">Preference (User privacy preference)</option>
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Profile (odrl:profile)
                                    </label>
                                    <input
                                        type="text"
                                        value={profile}
                                        onChange={(e) => setProfile(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                            </div>

                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <label className="text-xs font-bold text-gray-600 dark:text-gray-300 uppercase">
                                        Policy Identifier (odrl:uid)
                                    </label>
                                    <button
                                        type="button"
                                        onClick={() => setUid(`did:oyd:${crypto.randomUUID()}`)}
                                        className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
                                    >
                                        <RefreshCw size={12} /> Regenerate
                                    </button>
                                </div>
                                <input
                                    type="text"
                                    value={uid}
                                    onChange={(e) => setUid(e.target.value)}
                                    className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                />
                            </div>

                            <div>
                                <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                    Description (dcterms:description)
                                </label>
                                <textarea
                                    rows={3}
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm focus:ring-2 focus:ring-indigo-500"
                                />
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Target (odrl:target)
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="e.g. duodrl:TemplateDataset or https://example.org/dataset/1"
                                        value={policyTarget}
                                        onChange={(e) => setPolicyTarget(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Assigner (odrl:assigner)
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="e.g. https://solidweb.me/user/profile/card#me or did:oyd:..."
                                        value={policyAssigner}
                                        onChange={(e) => setPolicyAssigner(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Author / Contributor (dcterms:creator)
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="e.g. https://orcid.org/0000-0002-1825-0097"
                                        value={creator}
                                        onChange={(e) => setCreator(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Publisher (dcterms:publisher)
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="e.g. https://ror.org/02nkf1q06"
                                        value={publisher}
                                        onChange={(e) => setPublisher(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-[1fr_10rem] gap-4">
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Source (dcterms:source, comma-separated)
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="optional"
                                        value={source}
                                        onChange={(e) => setSource(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-600 dark:text-gray-300 uppercase mb-1">
                                        Version (owl:versionInfo)
                                    </label>
                                    <input
                                        type="text"
                                        placeholder="1.0"
                                        value={versionInfo}
                                        onChange={(e) => setVersionInfo(e.target.value)}
                                        className="w-full px-3 py-2 rounded-xl bg-gray-50 dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                                    />
                                </div>
                            </div>

                            <div className="rounded-xl bg-gray-50 dark:bg-black/20 border border-dashed border-gray-300 dark:border-white/10 px-3 py-2">
                                <div className="text-[11px] font-bold text-gray-500 dark:text-gray-400 uppercase mb-1">
                                    System-generated dates
                                </div>
                                <dl className="grid grid-cols-1 sm:grid-cols-3 gap-x-4 gap-y-1 text-xs font-mono text-gray-700 dark:text-gray-300">
                                    <div><dt className="text-gray-500">dcterms:created</dt><dd>{createdDate || today}</dd></div>
                                    <div><dt className="text-gray-500">dcterms:modified</dt><dd>{today}</dd></div>
                                    <div><dt className="text-gray-500">dcterms:issued</dt><dd>{issuedDate || today}</dd></div>
                                </dl>
                            </div>

                            {/* Wizard Navigation */}
                            <div className="pt-4 border-t border-gray-200 dark:border-white/10 flex items-center justify-between">
                                <span className="text-xs text-gray-400">Step 1 of 4: Specification</span>
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('permissions')}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 shadow-sm transition-all"
                                >
                                    <span>Next: Permissions ({permissions.length})</span>
                                    <ArrowRight size={14} />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* TAB 2: PERMISSIONS */}
                    {activeTab === 'permissions' && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-white/[0.03] border border-gray-200 dark:border-white/10 shadow-sm space-y-4">
                            <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/5 pb-3">
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                        <CheckCircle2 size={18} className="text-emerald-500" />
                                        Permissions List ({permissions.length})
                                    </h2>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        Specify allowed actions, the duties that come with them, and access purposes.
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={addPermission}
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1 transition-all"
                                >
                                    <Plus size={14} /> Add Permission
                                </button>
                            </div>

                            {permissions.length === 0 ? (
                                <div className="text-center py-8 text-gray-400">
                                    <Unlock size={32} className="mx-auto mb-2 opacity-40" />
                                    <p className="text-sm font-medium">No permissions defined.</p>
                                    <button
                                        type="button"
                                        onClick={addPermission}
                                        className="mt-3 text-xs text-emerald-600 dark:text-emerald-400 font-bold hover:underline"
                                    >
                                        + Add the first permission rule
                                    </button>
                                </div>
                            ) : (
                                permissions.map((p, pIdx) => (
                                    <div key={pIdx} className="p-5 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.01] space-y-3">
                                        <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/5 pb-2">
                                            <span className="text-xs font-extrabold uppercase text-emerald-600 dark:text-emerald-400">
                                                Permission #{pIdx + 1}
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() => removePermission(pIdx)}
                                                className="text-xs text-rose-500 hover:text-rose-700 flex items-center gap-1"
                                            >
                                                <Trash2 size={14} /> Remove
                                            </button>
                                        </div>

                                        <div className="grid grid-cols-1 gap-3">
                                            <div>
                                                <div className="flex items-center justify-between mb-1">
                                                    <label className="block text-[11px] font-bold text-gray-500 uppercase">
                                                        Action (odrl:action)
                                                    </label>
                                                    {!(p.duties && p.duties.length > 0) && (
                                                        <button
                                                            type="button"
                                                            onClick={() => addPermissionDuty(pIdx)}
                                                            className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-0.5"
                                                        >
                                                            <Plus size={11} /> Add duty action
                                                        </button>
                                                    )}
                                                </div>
                                                <div className="flex gap-1.5">
                                                    <input
                                                        type="text"
                                                        value={p.action}
                                                        onChange={(e) => {
                                                            const next = [...permissions];
                                                            next[pIdx].action = e.target.value;
                                                            setPermissions(next);
                                                        }}
                                                        className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono flex-1 min-w-0"
                                                    />
                                                    <BrowseIconButton
                                                        title="Browse actions"
                                                        onClick={() => setActionPickerTarget({ type: 'permission', index: pIdx })}
                                                    />
                                                </div>
                                            </div>
                                        </div>

                                        {/* Duty Actions Section (odrl:duty, CDIF CV4) */}
                                        {p.duties && p.duties.length > 0 && (
                                            <div className="pt-2 pl-3 border-l-2 border-indigo-400 dark:border-indigo-600 bg-indigo-50/30 dark:bg-indigo-950/20 p-2.5 rounded-r-lg">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-[11px] font-bold text-indigo-700 dark:text-indigo-300 uppercase flex items-center gap-1">
                                                        <Sparkles size={12} />
                                                        Duty Actions ({p.duties.length})
                                                    </span>
                                                    <button
                                                        type="button"
                                                        onClick={() => addPermissionDuty(pIdx)}
                                                        className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-0.5"
                                                    >
                                                        <Plus size={12} /> Add duty action
                                                    </button>
                                                </div>
                                                <p className="text-[11px] text-gray-500 dark:text-gray-400 mb-2">
                                                    What the assignee must do to exercise this permission (CDIF CV4 duty actions).
                                                </p>

                                                <div className="space-y-2">
                                                {p.duties.map((d, dIdx) => {
                                                    const term = cv4DutyTerms.find(t => t.value === d.action);
                                                    const openDutyBrowser = () => browseApi.openDuties({
                                                        value: d.action,
                                                        onSelect: (v) => updatePermissionDuty(pIdx, dIdx, 'action', v),
                                                    });
                                                    return (
                                                        <div key={dIdx}>
                                                            <div className="flex items-center justify-between mb-1">
                                                                <label className="block text-[11px] font-bold text-gray-500 uppercase">
                                                                    Duty action #{dIdx + 1}{term ? ` · ${term.label}` : ''}
                                                                </label>
                                                                <div className="flex items-center gap-3">
                                                                    <label
                                                                        className="flex items-center gap-1 text-[11px] text-gray-600 dark:text-gray-300 whitespace-nowrap cursor-pointer"
                                                                        title="Adds the constraint odrl:event odrl:lt odrl:policyUsage"
                                                                    >
                                                                        <input
                                                                            type="checkbox"
                                                                            checked={!!d.beforeUse}
                                                                            onChange={(e) => updatePermissionDuty(pIdx, dIdx, 'beforeUse', e.target.checked)}
                                                                        />
                                                                        Before use
                                                                    </label>
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => removePermissionDuty(pIdx, dIdx)}
                                                                        className="text-rose-500 hover:text-rose-700"
                                                                        title="Remove duty action"
                                                                    >
                                                                        <Trash2 size={12} />
                                                                    </button>
                                                                </div>
                                                            </div>
                                                            <div className="flex gap-1.5">
                                                                <input
                                                                    type="text"
                                                                    value={d.action || ''}
                                                                    title={term ? `${term.value} — ${term.description}` : d.action}
                                                                    onChange={(e) => updatePermissionDuty(pIdx, dIdx, 'action', e.target.value)}
                                                                    className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono flex-1 min-w-0"
                                                                />
                                                                <BrowseIconButton title="Browse duty actions" onClick={openDutyBrowser} />
                                                            </div>
                                                            {term?.description && (
                                                                <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">{term.description}</p>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                                </div>
                                            </div>
                                        )}

                                        {/* Purposes Section */}
                                        <div className="pt-2">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[11px] font-bold text-gray-500 uppercase">
                                                    Purposes ({p.constraints.length})
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => addPermissionConstraint(pIdx)}
                                                    className="text-[11px] text-emerald-600 dark:text-emerald-400 hover:underline flex items-center gap-0.5"
                                                >
                                                    <Plus size={12} /> Add Purpose
                                                </button>
                                            </div>

                                            {p.constraints.length === 0 && (
                                                <p className="text-[11px] text-gray-400 dark:text-gray-500 italic mb-2">
                                                    No purpose restriction: this permission applies to any purpose.
                                                </p>
                                            )}

                                            {p.constraints.map((c, cIdx) => {
                                                const update = (field, value) => {
                                                    const next = [...permissions];
                                                    next[pIdx].constraints[cIdx][field] = value;
                                                    setPermissions(next);
                                                };
                                                const fieldCls = "w-full px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono";
                                                return (
                                                    <div key={cIdx} className="p-2.5 mb-2 rounded-lg bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 text-xs space-y-2">
                                                        <div className="flex items-center justify-between">
                                                            <input
                                                                type="text"
                                                                placeholder="Purpose Title (dcterms:title)"
                                                                value={c.title}
                                                                onChange={(e) => update('title', e.target.value)}
                                                                className="flex-1 mr-2 px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs"
                                                            />
                                                            <button
                                                                type="button"
                                                                onClick={() => removePermissionConstraint(pIdx, cIdx)}
                                                                className="text-rose-500 hover:text-rose-700"
                                                            >
                                                                <Trash2 size={12} />
                                                            </button>
                                                        </div>
                                                        <div className="grid grid-cols-3 gap-2">
                                                            <input
                                                                type="text"
                                                                readOnly
                                                                value={c.leftOperand || 'oac:Purpose'}
                                                                title="Left operand of a purpose constraint (fixed)"
                                                                className={cn(fieldCls, "text-gray-500 dark:text-gray-400 cursor-default focus:outline-none")}
                                                            />
                                                            <OperatorSelect
                                                                value={c.operator}
                                                                onChange={(e) => update('operator', e.target.value)}
                                                                className={fieldCls}
                                                            />
                                                            <PurposeSelect
                                                                value={c.rightOperand}
                                                                concepts={cdifPurposes}
                                                                onChange={(v) => update('rightOperand', v)}
                                                                className={fieldCls}
                                                            />
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>

                                        {/* Other Constraints Section */}
                                        <div className="pt-2 border-t border-gray-100 dark:border-white/5">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[11px] font-bold text-gray-500 uppercase">
                                                    Other Constraints ({(p.otherConstraints || []).length})
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => addPermissionOtherConstraint(pIdx)}
                                                    className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-0.5"
                                                >
                                                    <Plus size={12} /> Add Constraint
                                                </button>
                                            </div>

                                            {(p.otherConstraints || []).map((c, cIdx) => (
                                                <div key={cIdx} className="p-2.5 mb-2 rounded-lg bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 text-xs space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <input
                                                            type="text"
                                                            placeholder="Constraint Title (dcterms:title)"
                                                            value={c.title}
                                                            onChange={(e) => {
                                                                const next = [...permissions];
                                                                next[pIdx].otherConstraints[cIdx].title = e.target.value;
                                                                setPermissions(next);
                                                            }}
                                                            className="flex-1 mr-2 px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs"
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() => removePermissionOtherConstraint(pIdx, cIdx)}
                                                            className="text-rose-500 hover:text-rose-700"
                                                        >
                                                            <Trash2 size={12} />
                                                        </button>
                                                    </div>
                                                    <div className="grid grid-cols-3 gap-2">
                                                        <LeftOperandSelect
                                                            value={c.leftOperand}
                                                            onChange={(e) => {
                                                                const next = [...permissions];
                                                                next[pIdx].otherConstraints[cIdx].leftOperand = e.target.value;
                                                                setPermissions(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                        <OperatorSelect
                                                            value={c.operator}
                                                            onChange={(e) => {
                                                                const next = [...permissions];
                                                                next[pIdx].otherConstraints[cIdx].operator = e.target.value;
                                                                setPermissions(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                        <input
                                                            type="text"
                                                            placeholder="Right Operand"
                                                            value={c.rightOperand}
                                                            onChange={(e) => {
                                                                const next = [...permissions];
                                                                next[pIdx].otherConstraints[cIdx].rightOperand = e.target.value;
                                                                setPermissions(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
                            )}

                            {/* Wizard Navigation */}
                            <div className="pt-4 border-t border-gray-200 dark:border-white/10 flex items-center justify-between">
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('specification')}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 flex items-center gap-2 border border-gray-200 dark:border-white/10 transition-all"
                                >
                                    <ArrowLeft size={14} />
                                    <span>Previous: Specification</span>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('prohibitions')}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 shadow-sm transition-all"
                                >
                                    <span>Next: Prohibitions ({prohibitions.length})</span>
                                    <ArrowRight size={14} />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* TAB 3: PROHIBITIONS */}
                    {activeTab === 'prohibitions' && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-white/[0.03] border border-gray-200 dark:border-white/10 shadow-sm space-y-4">
                            <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/5 pb-3">
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                        <AlertCircle size={18} className="text-rose-500" />
                                        Prohibitions List ({prohibitions.length})
                                    </h2>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        Explicitly forbidden actions (e.g. publication moratorium, commercial use, unapproved distribution).
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={addProhibition}
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-600 hover:bg-rose-700 text-white flex items-center gap-1 transition-all"
                                >
                                    <Plus size={14} /> Add Prohibition
                                </button>
                            </div>

                            {prohibitions.length === 0 ? (
                                <div className="text-center py-8 text-gray-400">
                                    <Lock size={32} className="mx-auto mb-2 opacity-40" />
                                    <p className="text-sm font-medium">No prohibitions defined.</p>
                                    <button
                                        type="button"
                                        onClick={addProhibition}
                                        className="mt-3 text-xs text-rose-600 dark:text-rose-400 font-bold hover:underline"
                                    >
                                        + Add the first prohibition rule
                                    </button>
                                </div>
                            ) : (
                                prohibitions.map((p, pIdx) => (
                                    <div key={pIdx} className="p-5 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.01] space-y-3">
                                        <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/5 pb-2">
                                            <span className="text-xs font-extrabold uppercase text-rose-600 dark:text-rose-400">
                                                Prohibition #{pIdx + 1}
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() => removeProhibition(pIdx)}
                                                className="text-xs text-rose-500 hover:text-rose-700 flex items-center gap-1"
                                            >
                                                <Trash2 size={14} /> Remove
                                            </button>
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                            <div>
                                                <div className="flex items-center justify-between mb-1">
                                                    <label className="block text-[11px] font-bold text-gray-500 uppercase">
                                                        Action (odrl:action)
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={() => addProhibitionRefinement(pIdx)}
                                                            className="text-[11px] text-rose-600 dark:text-rose-400 hover:underline flex items-center gap-0.5"
                                                        >
                                                            <Plus size={11} /> Add refinement
                                                        </button>
                                                    </div>
                                                </div>
                                                <div className="flex gap-1.5">
                                                    <input
                                                        type="text"
                                                        value={p.action}
                                                        onChange={(e) => {
                                                            const next = [...prohibitions];
                                                            next[pIdx].action = e.target.value;
                                                            setProhibitions(next);
                                                        }}
                                                        className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono flex-1 min-w-0"
                                                    />
                                                    <BrowseIconButton
                                                        title="Browse actions"
                                                        onClick={() => setActionPickerTarget({ type: 'prohibition', index: pIdx })}
                                                    />
                                                </div>
                                            </div>

                                            <div>
                                                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                                                    Target Asset (odrl:target)
                                                </label>
                                                <input
                                                    type="text"
                                                    value={p.target}
                                                    onChange={(e) => {
                                                        const next = [...prohibitions];
                                                        next[pIdx].target = e.target.value;
                                                        setProhibitions(next);
                                                    }}
                                                    className="w-full px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                                                    Output Asset (odrl:output)
                                                </label>
                                                <input
                                                    type="text"
                                                    placeholder="e.g. duodrl:ResultsOfStudies"
                                                    value={p.output || ''}
                                                    onChange={(e) => {
                                                        const next = [...prohibitions];
                                                        next[pIdx].output = e.target.value;
                                                        setProhibitions(next);
                                                    }}
                                                    className="w-full px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono"
                                                />
                                            </div>
                                        </div>

                                        {/* Action Refinements Section */}
                                        {p.refinements && p.refinements.length > 0 && (
                                            <div className="pt-2 pl-3 border-l-2 border-rose-400 dark:border-rose-600 bg-rose-50/30 dark:bg-rose-950/20 p-2.5 rounded-r-lg">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-[11px] font-bold text-rose-700 dark:text-rose-300 uppercase flex items-center gap-1">
                                                        <Sparkles size={12} />
                                                        Action Refinements ({p.refinements.length})
                                                    </span>
                                                    <button
                                                        type="button"
                                                        onClick={() => addProhibitionRefinement(pIdx)}
                                                        className="text-[11px] text-rose-600 dark:text-rose-400 hover:underline flex items-center gap-0.5"
                                                    >
                                                        <Plus size={12} /> Add refinement
                                                    </button>
                                                </div>

                                                {p.refinements.map((r, rIdx) => (
                                                    <div key={rIdx} className="p-2 mb-2 rounded-lg bg-white dark:bg-black/30 border border-rose-100 dark:border-rose-900/40 text-xs space-y-2">
                                                        <div className="flex items-center justify-between">
                                                            <input
                                                                type="text"
                                                                placeholder="Refinement Title (dcterms:title)"
                                                                value={r.title || ''}
                                                                onChange={(e) => {
                                                                    const next = [...prohibitions];
                                                                    next[pIdx].refinements[rIdx].title = e.target.value;
                                                                    setProhibitions(next);
                                                                }}
                                                                className="flex-1 mr-2 px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs"
                                                            />
                                                            <button
                                                                type="button"
                                                                onClick={() => removeProhibitionRefinement(pIdx, rIdx)}
                                                                className="text-rose-500 hover:text-rose-700"
                                                            >
                                                                <Trash2 size={12} />
                                                            </button>
                                                        </div>
                                                        <div className="grid grid-cols-3 gap-2">
                                                            <LeftOperandSelect
                                                                value={r.leftOperand}
                                                                onChange={(e) => {
                                                                    const next = [...prohibitions];
                                                                    next[pIdx].refinements[rIdx].leftOperand = e.target.value;
                                                                    setProhibitions(next);
                                                                }}
                                                                className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                            />
                                                            <OperatorSelect
                                                                value={r.operator}
                                                                onChange={(e) => {
                                                                    const next = [...prohibitions];
                                                                    next[pIdx].refinements[rIdx].operator = e.target.value;
                                                                    setProhibitions(next);
                                                                }}
                                                                className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                            />
                                                            <input
                                                                type="text"
                                                                placeholder="Right Operand"
                                                                value={r.rightOperand}
                                                                onChange={(e) => {
                                                                    const next = [...prohibitions];
                                                                    next[pIdx].refinements[rIdx].rightOperand = e.target.value;
                                                                    setProhibitions(next);
                                                                }}
                                                                className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                            />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Constraints */}
                                        <div className="pt-2">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[11px] font-bold text-gray-500 uppercase">
                                                    Constraints ({p.constraints.length})
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => addProhibitionConstraint(pIdx)}
                                                    className="text-[11px] text-rose-600 dark:text-rose-400 hover:underline flex items-center gap-0.5"
                                                >
                                                    <Plus size={12} /> Add Constraint
                                                </button>
                                            </div>

                                            {p.constraints.map((c, cIdx) => (
                                                <div key={cIdx} className="p-2.5 mb-2 rounded-lg bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 text-xs space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <input
                                                            type="text"
                                                            placeholder="Constraint Title (dcterms:title)"
                                                            value={c.title}
                                                            onChange={(e) => {
                                                                const next = [...prohibitions];
                                                                next[pIdx].constraints[cIdx].title = e.target.value;
                                                                setProhibitions(next);
                                                            }}
                                                            className="flex-1 mr-2 px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs"
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() => removeProhibitionConstraint(pIdx, cIdx)}
                                                            className="text-rose-500 hover:text-rose-700"
                                                        >
                                                            <Trash2 size={12} />
                                                        </button>
                                                    </div>
                                                    <div className="grid grid-cols-3 gap-2">
                                                        <LeftOperandSelect
                                                            value={c.leftOperand}
                                                            onChange={(e) => {
                                                                const next = [...prohibitions];
                                                                next[pIdx].constraints[cIdx].leftOperand = e.target.value;
                                                                setProhibitions(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                        <OperatorSelect
                                                            value={c.operator}
                                                            onChange={(e) => {
                                                                const next = [...prohibitions];
                                                                next[pIdx].constraints[cIdx].operator = e.target.value;
                                                                setProhibitions(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                        <input
                                                            type="text"
                                                            placeholder="Right Operand"
                                                            value={c.rightOperand}
                                                            onChange={(e) => {
                                                                const next = [...prohibitions];
                                                                next[pIdx].constraints[cIdx].rightOperand = e.target.value;
                                                                setProhibitions(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
                            )}

                            {/* Wizard Navigation */}
                            <div className="pt-4 border-t border-gray-200 dark:border-white/10 flex items-center justify-between">
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('permissions')}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 flex items-center gap-2 border border-gray-200 dark:border-white/10 transition-all"
                                >
                                    <ArrowLeft size={14} />
                                    <span>Previous: Permissions</span>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('duodrl')}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 shadow-sm transition-all"
                                >
                                    <span>Next: Duty ({duties.length})</span>
                                    <ArrowRight size={14} />
                                </button>
                            </div>
                        </div>
                    )}

                    {/* TAB 4: DUTIES / OBLIGATIONS */}
                    {activeTab === 'duodrl' && (
                        <div className="p-6 rounded-2xl bg-white dark:bg-white/[0.03] border border-gray-200 dark:border-white/10 shadow-sm space-y-4">
                            <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/5 pb-3">
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                        <FileCheck size={18} className="text-amber-500" />
                                        Duties & Obligations List ({duties.length})
                                    </h2>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                                        Specify required actions to fulfill (e.g. odrl:attribute, odrl:compensate, odrl:delete, odrl:obtainConsent).
                                    </p>
                                </div>
                                <button
                                    type="button"
                                    onClick={addDuty}
                                    className="px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-600 hover:bg-amber-700 text-white flex items-center gap-1 transition-all"
                                >
                                    <Plus size={14} /> Add Duty
                                </button>
                            </div>

                            {duties.length === 0 ? (
                                <div className="text-center py-8 text-gray-400">
                                    <FileCheck size={32} className="mx-auto mb-2 opacity-40 text-amber-500" />
                                    <p className="text-sm font-medium">No duties defined.</p>
                                    <button
                                        type="button"
                                        onClick={addDuty}
                                        className="mt-3 text-xs text-amber-600 dark:text-amber-400 font-bold hover:underline"
                                    >
                                        + Add the first duty rule
                                    </button>
                                </div>
                            ) : (
                                duties.map((d, dIdx) => (
                                    <div key={dIdx} className="p-5 rounded-xl border border-gray-200 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.01] space-y-3">
                                        <div className="flex items-center justify-between border-b border-gray-200 dark:border-white/5 pb-2">
                                            <span className="text-xs font-extrabold uppercase text-amber-600 dark:text-amber-400">
                                                Duty #{dIdx + 1}
                                            </span>
                                            <button
                                                type="button"
                                                onClick={() => removeDuty(dIdx)}
                                                className="text-xs text-rose-500 hover:text-rose-700 flex items-center gap-1"
                                            >
                                                <Trash2 size={14} /> Remove
                                            </button>
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                            <div>
                                                <div className="flex items-center justify-between mb-1">
                                                    <label className="block text-[11px] font-bold text-gray-500 uppercase">
                                                        Action (odrl:action)
                                                    </label>
                                                    <div className="flex items-center gap-2">
                                                        <button
                                                            type="button"
                                                            onClick={() => addDutyRefinement(dIdx)}
                                                            className="text-[11px] text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-0.5"
                                                        >
                                                            <Plus size={11} /> Add refinement
                                                        </button>
                                                    </div>
                                                </div>
                                                <div className="flex gap-1.5">
                                                    <input
                                                        type="text"
                                                        placeholder="e.g. cdif-access:CompleteRegistration"
                                                        value={d.action}
                                                        onChange={(e) => {
                                                            const next = [...duties];
                                                            next[dIdx].action = e.target.value;
                                                            setDuties(next);
                                                        }}
                                                        className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono flex-1 min-w-0"
                                                    />
                                                    <BrowseIconButton
                                                        title="Browse duty actions"
                                                        onClick={() => browseApi.openDuties({
                                                            value: d.action,
                                                            onSelect: (v) => {
                                                                const next = [...duties];
                                                                next[dIdx].action = v;
                                                                setDuties(next);
                                                            },
                                                        })}
                                                    />
                                                </div>
                                            </div>

                                            <div>
                                                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                                                    Target Asset (odrl:target)
                                                </label>
                                                <input
                                                    type="text"
                                                    placeholder="Optional target asset"
                                                    value={d.target || ''}
                                                    onChange={(e) => {
                                                        const next = [...duties];
                                                        next[dIdx].target = e.target.value;
                                                        setDuties(next);
                                                    }}
                                                    className="w-full px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono"
                                                />
                                            </div>

                                            <div>
                                                <label className="block text-[11px] font-bold text-gray-500 uppercase mb-1">
                                                    Assignee (odrl:assignee)
                                                </label>
                                                <input
                                                    type="text"
                                                    placeholder="Party fulfilling duty (did:oyd:...)"
                                                    value={d.assignee || ''}
                                                    onChange={(e) => {
                                                        const next = [...duties];
                                                        next[dIdx].assignee = e.target.value;
                                                        setDuties(next);
                                                    }}
                                                    className="w-full px-2.5 py-1.5 rounded-lg bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs font-mono"
                                                />
                                            </div>
                                        </div>

                                        {/* Action Refinements Section */}
                                        {d.refinements && d.refinements.length > 0 && (
                                            <div className="pt-2 pl-3 border-l-2 border-amber-400 dark:border-amber-600 bg-amber-50/30 dark:bg-amber-950/20 p-2.5 rounded-r-lg">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className="text-[11px] font-bold text-amber-700 dark:text-amber-300 uppercase flex items-center gap-1">
                                                        <Sparkles size={12} />
                                                        Action Refinements ({d.refinements.length})
                                                    </span>
                                                    <button
                                                        type="button"
                                                        onClick={() => addDutyRefinement(dIdx)}
                                                        className="text-[11px] text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-0.5"
                                                    >
                                                        <Plus size={12} /> Add refinement
                                                    </button>
                                                </div>

                                                {d.refinements.map((r, rIdx) => (
                                                    <div key={rIdx} className="p-2 mb-2 rounded-lg bg-white dark:bg-black/30 border border-amber-100 dark:border-amber-900/40 text-xs space-y-2">
                                                        <div className="flex items-center justify-between">
                                                            <input
                                                                type="text"
                                                                placeholder="Refinement Title (dcterms:title)"
                                                                value={r.title || ''}
                                                                onChange={(e) => {
                                                                    const next = [...duties];
                                                                    next[dIdx].refinements[rIdx].title = e.target.value;
                                                                    setDuties(next);
                                                                }}
                                                                className="flex-1 mr-2 px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs"
                                                            />
                                                            <button
                                                                type="button"
                                                                onClick={() => removeDutyRefinement(dIdx, rIdx)}
                                                                className="text-rose-500 hover:text-rose-700"
                                                            >
                                                                <Trash2 size={12} />
                                                            </button>
                                                        </div>
                                                        <div className="grid grid-cols-3 gap-2">
                                                            <LeftOperandSelect
                                                                value={r.leftOperand}
                                                                onChange={(e) => {
                                                                    const next = [...duties];
                                                                    next[dIdx].refinements[rIdx].leftOperand = e.target.value;
                                                                    setDuties(next);
                                                                }}
                                                                className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                            />
                                                            <OperatorSelect
                                                                value={r.operator}
                                                                onChange={(e) => {
                                                                    const next = [...duties];
                                                                    next[dIdx].refinements[rIdx].operator = e.target.value;
                                                                    setDuties(next);
                                                                }}
                                                                className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                            />
                                                            <input
                                                                type="text"
                                                                placeholder="Right Operand (e.g. 10.00)"
                                                                value={r.rightOperand}
                                                                onChange={(e) => {
                                                                    const next = [...duties];
                                                                    next[dIdx].refinements[rIdx].rightOperand = e.target.value;
                                                                    setDuties(next);
                                                                }}
                                                                className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                            />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Duty Constraints Section */}
                                        <div className="pt-2">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-[11px] font-bold text-gray-500 uppercase">
                                                    Constraints ({d.constraints.length})
                                                </span>
                                                <button
                                                    type="button"
                                                    onClick={() => addDutyConstraint(dIdx)}
                                                    className="text-[11px] text-amber-600 dark:text-amber-400 hover:underline flex items-center gap-0.5"
                                                >
                                                    <Plus size={12} /> Add Constraint
                                                </button>
                                            </div>

                                            {d.constraints.map((c, cIdx) => (
                                                <div key={cIdx} className="p-2.5 mb-2 rounded-lg bg-white dark:bg-black/30 border border-gray-200 dark:border-white/10 text-xs space-y-2">
                                                    <div className="flex items-center justify-between">
                                                        <input
                                                            type="text"
                                                            placeholder="Constraint Title (dcterms:title)"
                                                            value={c.title}
                                                            onChange={(e) => {
                                                                const next = [...duties];
                                                                next[dIdx].constraints[cIdx].title = e.target.value;
                                                                setDuties(next);
                                                            }}
                                                            className="flex-1 mr-2 px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs"
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() => removeDutyConstraint(dIdx, cIdx)}
                                                            className="text-rose-500 hover:text-rose-700"
                                                        >
                                                            <Trash2 size={12} />
                                                        </button>
                                                    </div>
                                                    <div className="grid grid-cols-3 gap-2">
                                                        <LeftOperandSelect
                                                            value={c.leftOperand}
                                                            onChange={(e) => {
                                                                const next = [...duties];
                                                                next[dIdx].constraints[cIdx].leftOperand = e.target.value;
                                                                setDuties(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                        <OperatorSelect
                                                            value={c.operator}
                                                            onChange={(e) => {
                                                                const next = [...duties];
                                                                next[dIdx].constraints[cIdx].operator = e.target.value;
                                                                setDuties(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                        <input
                                                            type="text"
                                                            placeholder="Right Operand"
                                                            value={c.rightOperand}
                                                            onChange={(e) => {
                                                                const next = [...duties];
                                                                next[dIdx].constraints[cIdx].rightOperand = e.target.value;
                                                                setDuties(next);
                                                            }}
                                                            className="px-2 py-1 rounded bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10 text-xs font-mono"
                                                        />
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                ))
                            )}

                            {/* Wizard Navigation */}
                            <div className="pt-4 border-t border-gray-200 dark:border-white/10 flex items-center justify-between">
                                <button
                                    type="button"
                                    onClick={() => setActiveTab('prohibitions')}
                                    className="px-4 py-2 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 flex items-center gap-2 border border-gray-200 dark:border-white/10 transition-all"
                                >
                                    <ArrowLeft size={14} />
                                    <span>Previous: Prohibitions</span>
                                </button>
                                <span className="text-xs text-gray-400">Step 4 of 4: Duty & Obligations</span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Right Col: POLICY OPERATIONS MENU */}
                <div className="space-y-6">
                    <div className="p-6 rounded-2xl bg-white dark:bg-white/[0.03] border border-gray-200 dark:border-white/10 shadow-sm sticky top-24 space-y-4">
                        <div className="border-b border-gray-200 dark:border-white/5 pb-3">
                            <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <FileCheck size={18} className="text-indigo-600 dark:text-indigo-400" />
                                Policy Operations
                            </h3>
                            <p className="text-xs text-gray-500 mt-0.5">
                                Validate, inspect, browse actions, and anchor to decentralized identity.
                            </p>
                        </div>

                        {/* Summary Badges */}
                        <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/30">
                                <span className="block text-base font-extrabold text-emerald-600 dark:text-emerald-400">
                                    {permissions.length}
                                </span>
                                <span className="text-[10px] font-bold text-gray-500 uppercase">Permissions</span>
                            </div>
                            <div className="p-2 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/30">
                                <span className="block text-base font-extrabold text-rose-600 dark:text-rose-400">
                                    {prohibitions.length}
                                </span>
                                <span className="text-[10px] font-bold text-gray-500 uppercase">Prohibitions</span>
                            </div>
                            <div className="p-2 rounded-xl bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30">
                                <span className="block text-base font-extrabold text-amber-600 dark:text-amber-400">
                                    {duties.length}
                                </span>
                                <span className="text-[10px] font-bold text-gray-500 uppercase">Duties</span>
                            </div>
                        </div>

                        <div className="space-y-2.5 pt-2">
                            {/* 1. JSON-LD Preview & SHACL Modal Trigger */}
                            <button
                                type="button"
                                onClick={() => setOperationModal('json')}
                                className="w-full py-2.5 px-4 rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 active:scale-95 text-gray-900 dark:text-white font-bold text-xs flex items-center justify-between transition-all border border-gray-200 dark:border-white/10"
                            >
                                <span className="flex items-center gap-2">
                                    <Eye size={16} className="text-indigo-500" />
                                    JSON-LD Preview & SHACL
                                </span>
                                <ExternalLink size={14} className="opacity-50" />
                            </button>

                            {/* 2. W3C Action Concepts Directory Trigger */}
                            <button
                                type="button"
                                onClick={() => setOperationModal('vocab')}
                                className="w-full py-2.5 px-4 rounded-xl bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 active:scale-95 text-gray-900 dark:text-white font-bold text-xs flex items-center justify-between transition-all border border-gray-200 dark:border-white/10"
                            >
                                <span className="flex items-center gap-2">
                                    <BookOpen size={16} className="text-purple-500" />
                                    W3C Action Concepts ({vocabActions?.count || 54})
                                </span>
                                <ExternalLink size={14} className="opacity-50" />
                            </button>

                            {/* 3. SHACL Validation */}
                            <button
                                type="button"
                                onClick={() => validateMutation.mutate(compilePolicyJson())}
                                disabled={validateMutation.isPending}
                                className="w-full py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-600 active:scale-95 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-amber-500/20"
                            >
                                <ShieldCheck size={16} />
                                {validateMutation.isPending ? 'Validating...' : 'Validate SHACL & ODRL'}
                            </button>

                            {/* 4. Save & Anchor DID */}
                            <button
                                type="button"
                                onClick={() => saveMutation.mutate(compilePolicyJson())}
                                disabled={saveMutation.isPending}
                                className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-95 text-white font-bold text-xs flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-600/30"
                            >
                                <Key size={16} />
                                {saveMutation.isPending ? 'Anchoring...' : 'Save & Anchor DID'}
                            </button>

                            {/* 5. Copy JSON-LD */}
                            <button
                                type="button"
                                onClick={handleCopy}
                                className="w-full py-2.5 px-4 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-white/[0.02] dark:hover:bg-white/[0.06] active:scale-95 text-gray-700 dark:text-gray-300 font-bold text-xs flex items-center justify-center gap-2 transition-all border border-gray-200 dark:border-white/10"
                            >
                                <Copy size={16} />
                                {copied ? 'Copied to Clipboard!' : 'Copy JSON-LD'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* MODAL 1: JSON-LD Preview & SHACL Viewer */}
            {operationModal === 'json' && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="w-full max-w-4xl bg-white dark:bg-[#121212] rounded-3xl border border-gray-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="p-6 border-b border-gray-200 dark:border-white/10 flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                    <Eye size={20} className="text-indigo-600 dark:text-indigo-400" />
                                    JSON-LD Preview & SHACL
                                </h3>
                                <p className="text-xs text-gray-500 mt-0.5">
                                    Generated JSON-LD document with embedded W3C ODRL, OAC, and DUODRL context definitions.
                                </p>
                            </div>
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    onClick={() => validateMutation.mutate(compilePolicyJson())}
                                    className="px-3 py-1.5 rounded-xl text-xs font-bold bg-amber-500 hover:bg-amber-600 text-white flex items-center gap-1 transition-all"
                                >
                                    <ShieldCheck size={14} /> Validate
                                </button>
                                <button
                                    type="button"
                                    onClick={handleCopy}
                                    className="px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1 transition-all"
                                >
                                    <Copy size={14} /> {copied ? 'Copied!' : 'Copy'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setOperationModal(null)}
                                    className="px-3 py-1.5 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/10 text-gray-700 dark:text-gray-300 transition-all"
                                >
                                    Close
                                </button>
                            </div>
                        </div>

                        <div className="p-6 overflow-y-auto font-mono text-xs leading-relaxed bg-gray-950 text-emerald-400 custom-scrollbar">
                            <pre>{JSON.stringify(compilePolicyJson(), null, 2)}</pre>
                        </div>
                    </div>
                </div>
            )}

            {/* MODAL 2: W3C Action Concepts Directory */}
            {operationModal === 'vocab' && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
                    <div className="w-full max-w-5xl bg-white dark:bg-[#121212] rounded-3xl border border-gray-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
                        <div className="p-6 border-b border-gray-200 dark:border-white/10 flex items-center justify-between">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                    <BookOpen size={20} className="text-purple-600 dark:text-purple-400" />
                                    W3C Action Concepts ({vocabActions?.count || 54})
                                </h3>
                                <p className="text-xs text-gray-500 mt-0.5">
                                    Canonical ODRL 2.2 operations specified in <code className="font-mono">https://www.w3.org/TR/odrl-vocab/#actionConcepts</code>.
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => setOperationModal(null)}
                                className="px-4 py-2 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/10 text-gray-700 dark:text-gray-300 transition-all"
                            >
                                Close
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto space-y-6 custom-scrollbar">
                            {vocabActions?.categories && Object.entries(vocabActions.categories).map(([category, items]) => (
                                <div key={category} className="p-5 rounded-2xl bg-gray-50/70 dark:bg-white/[0.02] border border-gray-200 dark:border-white/5 space-y-3">
                                    <h4 className="text-xs font-extrabold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
                                        {category} ({items.length})
                                    </h4>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                        {items.map((act) => (
                                            <div key={act.name} className="p-3 rounded-xl bg-white dark:bg-white/5 border border-gray-200 dark:border-white/5 text-xs shadow-xs">
                                                <div className="flex items-center justify-between font-mono font-bold text-gray-900 dark:text-white">
                                                    <span>{act.iri}</span>
                                                    {act.includedIn && (
                                                        <span className="text-[10px] text-gray-400 font-sans">
                                                            includedIn: {act.includedIn}
                                                        </span>
                                                    )}
                                                </div>
                                                <p className="text-gray-500 dark:text-gray-400 text-[11px] mt-1 leading-snug">
                                                    {act.description}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Action Picker: hierarchical browse window */}
            {actionPickerTarget && (() => {
                const { type, index } = actionPickerTarget;
                const rules = { permission: permissions, prohibition: prohibitions, duty: duties }[type] || [];
                const ruleType = type.charAt(0).toUpperCase() + type.slice(1);
                return (
                    <VocabBrowser
                        title={`Select action for ${ruleType} #${index + 1}`}
                        subtitle="CDIF CV1 actions from the CDIF access profile: CDIF-specific actions and the ODRL Common Vocabulary."
                        nodes={actionTree(currentActionsList)}
                        value={rules[index]?.action}
                        selectLabel="Use this action"
                        onSelect={selectActionForTarget}
                        onClose={() => setActionPickerTarget(null)}
                    />
                );
            })()}

            {/* Hierarchical browse window (purposes, constraints) */}
            {browser && (
                <VocabBrowser
                    title={browser.title}
                    subtitle={browser.subtitle}
                    nodes={browser.nodes}
                    value={browser.value}
                    selectLabel={browser.selectLabel}
                    onSelect={browser.onSelect}
                    onClose={() => setBrowser(null)}
                />
            )}
        </div>
        </BrowseContext.Provider>
    );
}
