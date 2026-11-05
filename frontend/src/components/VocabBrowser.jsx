import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { BookOpen, ChevronDown, ChevronRight, Search, Layers } from 'lucide-react';
import { cn } from '../lib/utils';

// Hierarchical vocabulary browser (purposes, left operands, ...). Trees come from lib/vocabTree.js.

const countDescendants = (n) => (n.children || []).reduce((s, k) => s + 1 + countDescendants(k), 0);

const matches = (n, q) =>
    n.label.toLowerCase().includes(q) ||
    (n.value || '').toLowerCase().includes(q) ||
    (n.description || '').toLowerCase().includes(q);

export function VocabBrowser({ title, subtitle, nodes, value, selectLabel = 'Use this term', onSelect, onClose, toolbar, defaultExpanded = [] }) {
    const [query, setQuery] = useState('');

    // Index every node with its ancestors, for breadcrumbs and keyboard navigation.
    const index = useMemo(() => {
        const map = new Map();
        const walk = (list, ancestors) => list.forEach(n => {
            map.set(n.key, { node: n, ancestors });
            walk(n.children || [], [...ancestors, n]);
        });
        walk(nodes, []);
        return map;
    }, [nodes]);

    // Start with the top level open, plus the path to the current value.
    const initial = useMemo(() => {
        const open = new Set([...nodes.map(n => n.key), ...defaultExpanded]);
        const current = [...index.values()].find(e => e.node.value && e.node.value === value);
        current?.ancestors.forEach(a => open.add(a.key));
        return { open, selected: current?.node.key || null };
    }, [index, nodes, value, defaultExpanded]);

    const [expanded, setExpanded] = useState(initial.open);
    const [selectedKey, setSelectedKey] = useState(initial.selected);
    const listRef = useRef(null);
    const q = query.toLowerCase().trim();

    // Visible rows: everything under expanded nodes, or (when searching) matches plus their ancestors.
    const rows = useMemo(() => {
        const out = [];
        const keep = (n) => matches(n, q) || (n.children || []).some(keep);
        const walk = (list, depth) => list.forEach(n => {
            if (q && !keep(n)) return;
            out.push({ node: n, depth, hit: q && matches(n, q) });
            const open = q ? (n.children || []).some(keep) : expanded.has(n.key);
            if (open) walk(n.children || [], depth + 1);
        });
        walk(nodes, 0);
        return out;
    }, [nodes, expanded, q]);

    // While searching, the active row falls back to the first match so Enter picks it straight away.
    const activeKey = useMemo(() => {
        if (!q || rows.some(r => r.node.key === selectedKey)) return selectedKey;
        return (rows.find(r => r.hit && r.node.value) || rows.find(r => r.hit))?.node.key ?? selectedKey;
    }, [q, rows, selectedKey]);

    useEffect(() => {
        listRef.current?.querySelector('[data-selected="true"]')?.scrollIntoView({ block: 'nearest' });
    }, [activeKey]);

    const toggle = (key, open) => setExpanded(prev => {
        const next = new Set(prev);
        (open ?? !next.has(key)) ? next.add(key) : next.delete(key);
        return next;
    });
    const expandAll = () => setExpanded(new Set([...index.values()].filter(e => e.node.children?.length).map(e => e.node.key)));
    const collapseAll = () => setExpanded(new Set());

    const selected = activeKey ? index.get(activeKey) : null;
    const choose = (n) => n?.value && onSelect(n.value);

    const onKeyDown = (e) => {
        if (e.key === 'Escape') { e.preventDefault(); onClose(); return; }
        const i = rows.findIndex(r => r.node.key === activeKey);
        const cur = rows[i]?.node;
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            const next = rows[Math.max(0, Math.min(rows.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))];
            if (next) setSelectedKey(next.node.key);
        } else if (e.key === 'ArrowRight' && cur?.children?.length && !q) {
            e.preventDefault();
            if (!expanded.has(cur.key)) toggle(cur.key, true);
            else setSelectedKey(cur.children[0].key);
        } else if (e.key === 'ArrowLeft' && cur && !q) {
            e.preventDefault();
            if (cur.children?.length && expanded.has(cur.key)) toggle(cur.key, false);
            else { const parent = index.get(cur.key)?.ancestors.at(-1); if (parent) setSelectedKey(parent.key); }
        } else if (e.key === 'Enter' && cur?.value) {
            e.preventDefault();
            choose(cur);
        }
    };

    const n = selected?.node;
    const narrower = n ? countDescendants(n) : 0;

    // Portal to <body>: the page's animated wrapper would otherwise trap position:fixed under the sidebar.
    return createPortal(
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200"
            onMouseDown={(e) => e.target === e.currentTarget && onClose()}
        >
            <div
                className="w-full max-w-3xl bg-white dark:bg-[#121212] rounded-3xl border border-gray-200 dark:border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
                onKeyDown={onKeyDown}
            >
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200 dark:border-white/10 flex items-center justify-between gap-4 bg-gray-50/50 dark:bg-white/[0.02]">
                    <div className="space-y-1 min-w-0">
                        <h3 className="text-base font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            <BookOpen size={18} className="text-indigo-600 dark:text-indigo-400" />
                            {title}
                        </h3>
                        {subtitle && <p className="text-xs text-gray-500 dark:text-gray-400">{subtitle}</p>}
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gray-100 hover:bg-gray-200 dark:bg-white/10 text-gray-700 dark:text-gray-300 transition-all"
                    >
                        Cancel
                    </button>
                </div>

                {/* Search */}
                <div className="px-4 py-3 border-b border-gray-200 dark:border-white/10 bg-gray-50/30 dark:bg-white/[0.01] flex items-center gap-2">
                    <div className="relative flex-1">
                        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                            type="text"
                            placeholder="Search by name, term, or definition…"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            autoFocus
                            className="w-full pl-8 pr-3 py-2 rounded-xl bg-white dark:bg-black/40 border border-gray-300 dark:border-white/10 text-xs focus:ring-2 focus:ring-indigo-500"
                        />
                    </div>
                    {toolbar}
                    <button type="button" onClick={expandAll} disabled={!!q}
                        className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-40 disabled:no-underline">
                        Expand all
                    </button>
                    <span className="text-gray-300 dark:text-gray-600">|</span>
                    <button type="button" onClick={collapseAll} disabled={!!q}
                        className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline disabled:opacity-40 disabled:no-underline">
                        Collapse
                    </button>
                </div>

                {/* Tree + detail */}
                <div className="flex-1 min-h-0 grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_17rem]">
                    <div ref={listRef} role="tree" className="overflow-y-auto custom-scrollbar py-2 min-h-[12rem] max-h-[40vh] sm:max-h-none">
                        {rows.length === 0 && (
                            <div className="text-center py-10 text-xs text-gray-500 dark:text-gray-400">
                                No terms matching &ldquo;{query}&rdquo;.
                            </div>
                        )}
                        {rows.map(({ node: r, depth, hit }) => {
                            const hasKids = !!r.children?.length;
                            const open = q ? true : expanded.has(r.key);
                            const isSel = r.key === activeKey;
                            const isCurrent = r.value && r.value === value;
                            return (
                                <div
                                    key={r.key}
                                    role="treeitem"
                                    aria-expanded={hasKids ? open : undefined}
                                    aria-selected={isSel}
                                    data-selected={isSel}
                                    onClick={() => setSelectedKey(r.key)}
                                    onDoubleClick={() => (r.value ? choose(r) : hasKids && toggle(r.key))}
                                    style={{ paddingLeft: `${0.75 + depth * 1.1}rem` }}
                                    className={cn(
                                        'flex items-center gap-1.5 pr-3 py-1.5 cursor-pointer select-none text-xs',
                                        isSel ? 'bg-indigo-50 dark:bg-indigo-950/40' : 'hover:bg-gray-50 dark:hover:bg-white/[0.03]'
                                    )}
                                >
                                    <button
                                        type="button"
                                        tabIndex={-1}
                                        onClick={(e) => { e.stopPropagation(); hasKids && !q && toggle(r.key); }}
                                        className={cn('w-4 h-4 flex items-center justify-center text-gray-400 shrink-0', !hasKids && 'invisible')}
                                        aria-label={open ? 'Collapse' : 'Expand'}
                                    >
                                        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                                    </button>
                                    {!r.value && <Layers size={12} className="text-gray-400 shrink-0" />}
                                    <span className={cn(
                                        'truncate',
                                        r.value ? 'text-gray-900 dark:text-gray-100' : 'font-bold text-gray-600 dark:text-gray-300 uppercase text-[10px] tracking-wide',
                                        isSel && 'text-indigo-700 dark:text-indigo-300',
                                        hit && 'font-semibold',
                                        r.deprecated && 'line-through opacity-60'
                                    )}>
                                        {r.label}
                                    </span>
                                    {r.alsoUnder?.length > 0 && (
                                        <span title={`Also under: ${r.alsoUnder.join(', ')}`}
                                            className="text-[10px] px-1 rounded bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 shrink-0">
                                            ⧉
                                        </span>
                                    )}
                                    {hasKids && !open && (
                                        <span className="text-[10px] text-gray-400 shrink-0">({r.children.length})</span>
                                    )}
                                    {isCurrent && (
                                        <span className="ml-auto text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 shrink-0">current</span>
                                    )}
                                </div>
                            );
                        })}
                    </div>

                    <div className="border-t sm:border-t-0 sm:border-l border-gray-200 dark:border-white/10 p-4 overflow-y-auto custom-scrollbar bg-gray-50/40 dark:bg-white/[0.01] flex flex-col gap-3 text-xs">
                        {!n ? (
                            <p className="text-gray-400 dark:text-gray-500 italic">
                                Select a term to see its definition. Double-click or press Enter to use it.
                            </p>
                        ) : (
                            <>
                                {selected.ancestors.length > 0 && (
                                    <div className="text-[10px] text-gray-500 dark:text-gray-400 flex flex-wrap items-center gap-0.5">
                                        {selected.ancestors.map(a => (
                                            <React.Fragment key={a.key}>
                                                <button type="button" onClick={() => setSelectedKey(a.key)} className="hover:underline">{a.label}</button>
                                                <ChevronRight size={10} />
                                            </React.Fragment>
                                        ))}
                                    </div>
                                )}
                                <div>
                                    <div className={cn('text-sm font-bold text-gray-900 dark:text-white', n.deprecated && 'line-through opacity-60')}>
                                        {n.label}
                                    </div>
                                    {n.value && <code className="font-mono text-[11px] text-indigo-600 dark:text-indigo-400 break-all">{n.value}</code>}
                                    {n.deprecated && <div className="text-[10px] font-semibold text-amber-600 mt-0.5">Deprecated</div>}
                                </div>
                                {n.description && <p className="text-gray-600 dark:text-gray-300 leading-relaxed">{n.description}</p>}
                                {(n.meta?.length > 0 || n.alsoUnder?.length > 0) && (
                                    <dl className="space-y-1 text-[11px]">
                                        {n.alsoUnder?.length > 0 && (
                                            <div><dt className="inline text-gray-500">Also under: </dt><dd className="inline text-gray-700 dark:text-gray-300">{n.alsoUnder.join(', ')}</dd></div>
                                        )}
                                        {n.meta?.map(([k, v]) => (
                                            <div key={k + v}><dt className="inline text-gray-500">{k}: </dt><dd className="inline font-mono text-gray-700 dark:text-gray-300 break-all">{v}</dd></div>
                                        ))}
                                    </dl>
                                )}
                                {n.value && narrower > 0 && (
                                    <p className="text-[11px] text-gray-500 dark:text-gray-400">
                                        Includes {narrower} narrower term{narrower === 1 ? '' : 's'}.
                                    </p>
                                )}
                                {!n.value && (
                                    <p className="text-[11px] text-gray-500 dark:text-gray-400 italic">
                                        Category with {narrower} term{narrower === 1 ? '' : 's'}. Pick one inside it.
                                    </p>
                                )}
                                <div className="mt-auto pt-2">
                                    <button
                                        type="button"
                                        disabled={!n.value}
                                        onClick={() => choose(n)}
                                        className="w-full px-3 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                                    >
                                        {selectLabel}
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </div>,
        document.body
    );
}

// Small book icon placed next to an operand field.
export function BrowseIconButton({ onClick, title }) {
    return (
        <button
            type="button"
            onClick={onClick}
            title={title}
            aria-label={title}
            className="shrink-0 px-1.5 rounded border border-gray-200 dark:border-white/10 bg-gray-50 dark:bg-white/5 text-purple-600 dark:text-purple-400 hover:border-purple-400 hover:bg-purple-50 dark:hover:bg-purple-950/30"
        >
            <BookOpen size={12} />
        </button>
    );
}
