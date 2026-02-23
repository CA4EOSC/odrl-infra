import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { FileJson, Plus, CheckCircle, AlertCircle, Sparkles, ExternalLink } from 'lucide-react';
import api from '../services/api';
import ResolverLink from '../components/ResolverLink';
import { cn } from '../lib/utils';
import { Link } from 'react-router-dom';

export default function CroissantsManager() {
    const [croissantUrl, setCroissantUrl] = useState('');
    const [description, setDescription] = useState('');
    const [history, setHistory] = useState(() => JSON.parse(localStorage.getItem('croissants_history') || '[]'));

    useEffect(() => {
        localStorage.setItem('croissants_history', JSON.stringify(history));
    }, [history]);

    const addToHistory = (did, url, desc) => {
        setHistory(prev => [{ did, url, description: desc, timestamp: Date.now() }, ...prev]);
    }

    const createMutation = useMutation({
        mutationFn: async () => {
            // Fetch the croissant data if URL is provided
            const data = {
                url: croissantUrl.trim() || null,
                description: description
            };
            const res = await api.post('/croissants/create', data);
            const payload = {
                type: "Croissant",
                description: description,
                url: croissantUrl,
                timestamp: new Date().toISOString()
            };
            return { ...res.data, originalContent: payload };
        },
        onSuccess: (data) => {
            addToHistory(data.did, croissantUrl, description);
            setCroissantUrl('');
            setDescription('');
        }
    });

    const handleCreate = (e) => {
        e.preventDefault();
        createMutation.mutate();
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div>
                <h2 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">Croissants Manager</h2>
                <p className="text-gray-500 dark:text-gray-400">Manage AI-Ready data by anchoring Croissant JSON-LD as immutable DIDs.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Creation Form */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-gray-200 rounded-xl p-6 dark:bg-[#242424] dark:border-white/10 shadow-sm dark:shadow-none">
                        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                            <Sparkles className="text-orange-500" size={20} /> New Croissant DID
                        </h3>
                        <form onSubmit={handleCreate} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Croissant Export URL</label>
                                <input
                                    type="url"
                                    value={croissantUrl}
                                    onChange={(e) => setCroissantUrl(e.target.value)}
                                    placeholder="https://dataverse.harvard.edu/api/datasets/export?exporter=croissant..."
                                    className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500 transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description (Optional)</label>
                                <input
                                    type="text"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="e.g., Harvard Dataverse Dataset"
                                    className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500 transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={createMutation.isPending}
                                className="w-full bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-lg font-medium transition-colors flex justify-center items-center gap-2 text-white shadow-sm"
                            >
                                {createMutation.isPending ? 'Anchoring...' : (
                                    <>
                                        <Plus size={20} /> Generate DID
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    {createMutation.isError && (
                        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 flex items-center gap-3 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-400">
                            <AlertCircle size={20} />
                            Failed to anchor Croissant. Please try again.
                        </div>
                    )}

                    {createMutation.data && (
                        <div className="p-6 bg-green-50 border border-green-200 rounded-xl dark:bg-green-500/10 dark:border-green-500/20">
                            <h3 className="text-green-600 dark:text-green-400 font-semibold mb-2 flex items-center gap-2">
                                <CheckCircle size={20} /> Croissant Anchored Successfully
                            </h3>
                            <p className="font-mono text-sm break-all text-gray-900 bg-white border border-gray-200 p-3 rounded select-all dark:text-gray-300 dark:bg-black/20 dark:border-transparent">
                                <ResolverLink did={createMutation.data.did} />
                            </p>
                            <p className="text-[10px] text-gray-500 mt-2 italic">Note: Locally anchored DIDs are resolvable via the internal DID Manager.</p>
                        </div>
                    )}
                </div>

                {/* History List */}
                <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <FileJson className="text-orange-500" size={20} /> Recent Croissants
                    </h3>
                    <div className="space-y-3 max-h-[calc(100vh-250px)] overflow-y-auto pr-2 custom-scrollbar">
                        {history.length === 0 && (
                            <p className="text-gray-500 dark:text-gray-400 italic text-sm">No Croissants anchored yet.</p>
                        )}
                        {history.map((item, i) => (
                            <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-orange-300 transition-colors dark:bg-[#242424] dark:border-white/10 dark:hover:border-orange-500/50 shadow-sm dark:shadow-none">
                                <div className="flex justify-between items-start mb-2">
                                    <h4 className="font-medium text-gray-900 dark:text-white truncate pr-2">
                                        {item.description || "Untitled Croissant"}
                                    </h4>
                                    <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                                        {new Date(item.timestamp).toLocaleDateString()}
                                    </span>
                                </div>
                                {item.url && (
                                    <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-600 dark:text-blue-400 flex items-center gap-1 mb-2 hover:underline truncate">
                                        Source URL <ExternalLink size={10} />
                                    </a>
                                )}
                                <div className="flex items-center justify-between">
                                    <ResolverLink did={item.did} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
