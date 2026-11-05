import React, { useEffect, useId, useRef, useState } from 'react';
import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { Search, X, Loader2, Database, Sparkles } from 'lucide-react';
import api from '../services/api';
import { cn } from '../lib/utils';

// Search box over existing policies (stored policies + built-in presets, GET /policy/existing).
// Picking a result calls onSelect(policyJsonLd, result) so the builder can fill all its fields.
export default function PolicySearch({ onSelect }) {
    const [query, setQuery] = useState('');
    const [debounced, setDebounced] = useState('');
    const [open, setOpen] = useState(false);
    const [active, setActive] = useState(0);
    const boxRef = useRef(null);
    const listId = useId();

    useEffect(() => {
        const t = setTimeout(() => setDebounced(query.trim()), 200);
        return () => clearTimeout(t);
    }, [query]);

    const { data, isFetching, isError } = useQuery({
        queryKey: ['existing-policies', debounced],
        queryFn: async () => (await api.get('/policy/existing', { params: { q: debounced, limit: 50 } })).data,
        enabled: open,
        placeholderData: keepPreviousData,
    });
    const results = data?.results || [];

    // close when clicking outside
    useEffect(() => {
        const onDown = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
        document.addEventListener('mousedown', onDown);
        return () => document.removeEventListener('mousedown', onDown);
    }, []);

    const pick = (r) => {
        onSelect(r.policy, r);
        setOpen(false);
        setQuery('');
    };

    const onKeyDown = (e) => {
        if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); setActive(i => Math.min(i + 1, results.length - 1)); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(i => Math.max(i - 1, 0)); }
        else if (e.key === 'Enter' && open && results[active]) { e.preventDefault(); pick(results[active]); }
        else if (e.key === 'Escape') { setOpen(false); }
    };

    return (
        <div ref={boxRef} className="relative">
            <label htmlFor={`${listId}-input`} className="block text-xs font-semibold text-gray-500 dark:text-gray-400 mb-1.5">
                Start from an existing policy
            </label>
            <div className="relative">
                <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <input
                    id={`${listId}-input`}
                    type="text"
                    role="combobox"
                    aria-expanded={open}
                    aria-controls={listId}
                    aria-autocomplete="list"
                    autoComplete="off"
                    placeholder="Search by title, description, UID, target, action or purpose…"
                    value={query}
                    onChange={(e) => { setQuery(e.target.value); setOpen(true); setActive(0); }}
                    onFocus={() => setOpen(true)}
                    onKeyDown={onKeyDown}
                    className="w-full pl-9 pr-9 py-2.5 rounded-xl bg-white dark:bg-black/30 border border-gray-300 dark:border-white/10 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
                {isFetching ? (
                    <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />
                ) : query && (
                    <button type="button" aria-label="Clear search" onClick={() => { setQuery(''); setActive(0); }}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                        <X size={16} />
                    </button>
                )}
            </div>

            {open && (
                <div className="absolute z-30 mt-1 w-full rounded-xl border border-gray-200 dark:border-white/10 bg-white dark:bg-gray-900 shadow-xl overflow-hidden">
                    <div className="px-3 py-1.5 text-[11px] text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-white/5 flex justify-between">
                        <span>{isError ? 'Could not load policies' : data ? `${data.total} ${data.total === 1 ? 'policy' : 'policies'}` : 'Loading…'}</span>
                        {data && !data.stored_available && <span className="text-amber-600">Stored policies unavailable (index offline); presets only</span>}
                    </div>
                    <ul id={listId} role="listbox" className="max-h-80 overflow-y-auto">
                        {results.map((r, i) => (
                            <li
                                key={`${r.source}:${r.uid}:${i}`}
                                role="option"
                                aria-selected={i === active}
                                onMouseEnter={() => setActive(i)}
                                onMouseDown={(e) => { e.preventDefault(); pick(r); }}
                                className={cn(
                                    "px-3 py-2 cursor-pointer border-b border-gray-50 dark:border-white/5 last:border-0",
                                    i === active ? "bg-indigo-50 dark:bg-indigo-950/40" : ""
                                )}
                            >
                                <div className="flex items-center gap-2 text-sm">
                                    {r.source === 'stored'
                                        ? <Database size={13} className="shrink-0 text-emerald-600" aria-label="Stored policy" />
                                        : <Sparkles size={13} className="shrink-0 text-amber-500" aria-label="Preset" />}
                                    <span className="font-semibold text-gray-900 dark:text-white truncate">
                                        {r.title || r.description || `Untitled ${r.type || 'policy'}${r.creator ? ` by ${r.creator}` : ''}`}
                                    </span>
                                    {r.type && (
                                        <span className="ml-auto shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold bg-gray-100 dark:bg-white/10 text-gray-600 dark:text-gray-300">
                                            {r.type}
                                        </span>
                                    )}
                                </div>
                                {r.title && r.description && (
                                    <p className="text-xs text-gray-600 dark:text-gray-300 truncate mt-0.5">{r.description}</p>
                                )}
                                <p className="text-[11px] text-gray-500 dark:text-gray-400 truncate mt-0.5 font-mono">
                                    {r.uid}{r.target ? ` · ${r.target}` : ''}{r.created ? ` · ${r.created.slice(0, 10)}` : ''}
                                </p>
                            </li>
                        ))}
                        {data && results.length === 0 && (
                            <li className="px-3 py-4 text-sm text-center text-gray-500">No policy matches “{debounced}”.</li>
                        )}
                    </ul>
                </div>
            )}
        </div>
    );
}
