import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Search, Plus, Bookmark, Hash, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../services/api';
import ResolverLink from '../components/ResolverLink';
import { cn } from '../lib/utils';

const Tabs = ({ active, onChange, options }) => (
    <div className="flex space-x-1 bg-gray-100 dark:bg-[#242424] p-1 rounded-lg w-fit mb-6 transition-colors">
        {options.map((opt) => (
            <button
                key={opt.id}
                onClick={() => onChange(opt.id)}
                className={cn(
                    "px-4 py-2 text-sm font-medium rounded-md transition-all",
                    active === opt.id
                        ? "bg-white text-indigo-600 shadow-sm dark:bg-indigo-600 dark:text-white"
                        : "text-gray-600 hover:text-gray-900 hover:bg-gray-200 dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/5"
                )}
            >
                <div className="flex items-center gap-2">
                    {opt.icon && <opt.icon size={16} />}
                    {opt.label}
                </div>
            </button>
        ))}
    </div>
);

import { useSearchParams } from 'react-router-dom';

export default function DidManager() {
    const [searchParams] = useSearchParams();
    const [activeTab, setActiveTab] = useState('resolve');
    const [didInput, setDidInput] = useState(searchParams.get('resolve') || '');
    const [createPayload, setCreatePayload] = useState('{\n  "hello": "world"\n}');
    const [bookmarkUrl, setBookmarkUrl] = useState('');
    const [history, setHistory] = useState(() => JSON.parse(localStorage.getItem('did_history') || '[]'));

    useEffect(() => {
        localStorage.setItem('did_history', JSON.stringify(history));
    }, [history]);

    useEffect(() => {
        const resolveParam = searchParams.get('resolve');
        if (resolveParam) {
            setDidInput(resolveParam);
            resolveMutation.mutate(resolveParam);
        }
    }, [searchParams]);

    // Correction for slice
    const safeAddToHistory = (did, type) => {
        setHistory(prev => {
            const filtered = prev.filter(h => h.did !== did);
            return [{ did, type, timestamp: Date.now() }, ...filtered].slice(0, 10);
        });
    }



    // --- Queries & Mutations ---

    const resolveMutation = useMutation({
        mutationFn: async (did) => {
            const res = await api.get(`/did/${did}`);
            return res.data;
        },
        onSuccess: (_, did) => safeAddToHistory(did, 'resolved')
    });

    const createMutation = useMutation({
        mutationFn: async (payloadStr) => {
            const payload = JSON.parse(payloadStr);
            const res = await api.post('/did/create', { payload });
            return res.data;
        },
        onSuccess: (data) => safeAddToHistory(data.did, 'created')
    });

    const bookmarkMutation = useMutation({
        mutationFn: async (url) => {
            const res = await api.get(`/did/create_from_url?url=${encodeURIComponent(url)}`);
            return res.data;
        },
        onSuccess: (data) => safeAddToHistory(data.did, 'bookmarked')
    });

    // --- Handlers ---

    const handleResolve = (e) => {
        e.preventDefault();
        if (didInput.trim()) resolveMutation.mutate(didInput);
    };

    const handleCreate = (e) => {
        e.preventDefault();
        try {
            JSON.parse(createPayload); // Validate format
            createMutation.mutate(createPayload);
        } catch (err) {
            alert("Invalid JSON payload");
        }
    };

    const handleBookmark = (e) => {
        e.preventDefault();
        if (bookmarkUrl.trim()) bookmarkMutation.mutate(bookmarkUrl);
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div>
                <h2 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">DID Manager</h2>
                <p className="text-gray-500 dark:text-gray-400">Create, manage, and resolve Decentralized Identifiers.</p>
            </div>

            <Tabs
                active={activeTab}
                onChange={setActiveTab}
                options={[
                    { id: 'resolve', label: 'Resolve DID', icon: Search },
                    { id: 'create', label: 'Create Raw', icon: Plus },
                    { id: 'bookmark', label: 'Bookmark URL', icon: Bookmark },
                ]}
            />

            {/* --- Resolve Tab --- */}
            {activeTab === 'resolve' && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    <div className="md:col-span-2 space-y-6">
                        <form onSubmit={handleResolve} className="flex gap-4">
                            <input
                                type="text"
                                value={didInput}
                                onChange={(e) => setDidInput(e.target.value)}
                                placeholder="did:oyd:..."
                                className="flex-1 bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-3 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors dark:bg-[#242424] dark:border-white/10 dark:text-white"
                            />
                            <button
                                type="submit"
                                disabled={resolveMutation.isPending}
                                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-6 py-3 rounded-lg font-medium transition-colors text-white shadow-sm"
                            >
                                {resolveMutation.isPending ? 'Resolving...' : 'Resolve'}
                            </button>
                        </form>

                        {resolveMutation.isError && (
                            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 flex items-center gap-3 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-400">
                                <AlertCircle size={20} />
                                Failed to resolve DID. Check format or existence.
                            </div>
                        )}

                        {resolveMutation.data && (
                            <div className="bg-white border border-gray-200 rounded-xl p-6 relative overflow-hidden dark:bg-[#242424] dark:border-white/10 shadow-sm dark:shadow-none">
                                <div className="absolute top-0 right-0 p-4 opacity-10 text-gray-900 dark:text-white">
                                    <Hash size={100} />
                                </div>
                                <h3 className="text-lg font-semibold text-green-600 dark:text-green-400 mb-4 flex items-center gap-2">
                                    <CheckCircle size={18} /> Resolved Document
                                </h3>
                                <ResolverLink did={didInput} className="block mb-2 text-sm" />
                                <pre className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-96 font-mono text-sm text-gray-900 dark:bg-black/30 dark:text-gray-300 border border-gray-100 dark:border-transparent custom-scrollbar">
                                    {JSON.stringify(resolveMutation.data, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>

                    <div className="bg-white border border-gray-200 rounded-xl p-6 h-fit dark:bg-[#242424] dark:border-white/10 shadow-sm dark:shadow-none">
                        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Recent DIDs</h3>
                        <div className="space-y-3">
                            {history.length === 0 && <p className="text-sm text-gray-500 italic">No history yet.</p>}
                            {history.map((item, i) => (
                                <div
                                    key={i}
                                    onClick={() => { setDidInput(item.did); setActiveTab('resolve'); resolveMutation.mutate(item.did); }}
                                    className="group flex flex-col gap-1 p-3 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors border border-transparent hover:border-gray-200 dark:hover:bg-white/5 dark:hover:border-white/5"
                                >
                                    <ResolverLink did={item.did} icon={false} className="text-xs font-mono" />
                                    <div className="flex justify-between items-center">
                                        <span className="text-[10px] uppercase bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 group-hover:bg-gray-200 dark:bg-white/10 dark:text-gray-400 dark:group-hover:bg-white/20">{item.type}</span>
                                        <span className="text-[10px] text-gray-400 dark:text-gray-600">{new Date(item.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* --- Create Tab --- */}
            {activeTab === 'create' && (
                <div className="max-w-2xl">
                    <form onSubmit={handleCreate} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">JSON Payload</label>
                            <textarea
                                value={createPayload}
                                onChange={(e) => setCreatePayload(e.target.value)}
                                rows={8}
                                className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg p-4 font-mono text-sm focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors dark:bg-[#242424] dark:border-white/10 dark:text-white"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={createMutation.isPending}
                            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-6 py-3 rounded-lg font-medium transition-colors flex justify-center items-center gap-2 text-white shadow-sm"
                        >
                            {createMutation.isPending ? 'Creating...' : (
                                <>
                                    <Plus size={20} /> Create DID
                                </>
                            )}
                        </button>
                    </form>

                    {createMutation.data && (
                        <div className="mt-8 p-6 bg-green-50 border border-green-200 rounded-xl dark:bg-green-500/10 dark:border-green-500/20">
                            <h3 className="text-green-600 dark:text-green-400 font-semibold mb-2 flex items-center gap-2">
                                <CheckCircle size={20} /> DID Created Successfully
                            </h3>
                            <ResolverLink did={createMutation.data.did} />
                        </div>
                    )}
                </div>
            )}

            {/* --- Bookmark Tab --- */}
            {activeTab === 'bookmark' && (
                <div className="max-w-2xl">
                    <form onSubmit={handleBookmark} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Resource URL</label>
                            <input
                                type="url"
                                value={bookmarkUrl}
                                onChange={(e) => setBookmarkUrl(e.target.value)}
                                placeholder="https://example.com/article OR https://.../data.ttl"
                                className="w-full bg-white border border-gray-300 text-gray-900 rounded-lg px-4 py-3 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors dark:bg-[#242424] dark:border-white/10 dark:text-white"
                            />
                            <p className="text-xs text-gray-500 mt-2">Supports HTML pages (title extraction) and RDF Turtle files.</p>
                        </div>
                        <button
                            type="submit"
                            disabled={bookmarkMutation.isPending}
                            className="w-full bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 px-6 py-3 rounded-lg font-medium transition-colors flex justify-center items-center gap-2 text-white shadow-sm"
                        >
                            {bookmarkMutation.isPending ? 'Bookmarking...' : (
                                <>
                                    <Bookmark size={20} /> Create Bookmark DID
                                </>
                            )}
                        </button>
                    </form>

                    {bookmarkMutation.data && (
                        <div className="mt-8 p-6 bg-cyan-50 border border-cyan-200 rounded-xl dark:bg-cyan-500/10 dark:border-cyan-500/20">
                            <h3 className="text-cyan-600 dark:text-cyan-400 font-semibold mb-2 flex items-center gap-2">
                                <CheckCircle size={20} /> Bookmark Created
                            </h3>
                            <div className="space-y-2">
                                <p className="text-sm text-gray-500 dark:text-gray-400">DID:</p>
                                <p className="font-mono text-sm break-all text-gray-900 bg-white border border-gray-200 p-3 rounded select-all dark:text-gray-300 dark:bg-black/20 dark:border-transparent">
                                    {bookmarkMutation.data.did}
                                </p>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Payload:</p>
                                <pre className="bg-gray-50 border border-gray-200 p-3 rounded overflow-x-auto text-xs font-mono text-gray-900 dark:bg-black/20 dark:text-gray-300 dark:border-transparent">
                                    {JSON.stringify(bookmarkMutation.data.payload || bookmarkMutation.data, null, 2)}
                                </pre>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
