import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Database, Plus, CheckCircle, AlertCircle, Variable } from 'lucide-react';
import api from '../services/api';
import ResolverLink from '../components/ResolverLink';
import { Link } from 'react-router-dom';

export default function VariablesManager() {
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [unit, setUnit] = useState('');
    const [context, setContext] = useState('');
    const [history, setHistory] = useState(() => JSON.parse(localStorage.getItem('variables_history') || '[]'));

    useEffect(() => {
        localStorage.setItem('variables_history', JSON.stringify(history));
    }, [history]);

    const addToHistory = (did, payload) => {
        setHistory(prev => [{ did, ...payload, timestamp: Date.now() }, ...prev]);
    }

    const createMutation = useMutation({
        mutationFn: async () => {
            let parsedContext = {};
            if (context.trim()) {
                try {
                    parsedContext = JSON.parse(context);
                } catch (e) {
                    throw new Error("Invalid JSON-LD Context");
                }
            }

            const data = {
                name,
                description,
                unit,
                context: parsedContext
            };
            const res = await api.post('/variables/create', data);
            const payload = { ...data, type: "Variable", timestamp: new Date().toISOString() };
            return { ...res.data, originalContent: payload };
        },
        onSuccess: (data) => {
            addToHistory(data.did, data.originalContent);
            setName('');
            setDescription('');
            setUnit('');
            setContext('');
        },
        onError: (error) => {
            if (error.message === "Invalid JSON-LD Context") {
                alert("Invalid JSON format in Context field");
            }
        }
    });

    const handleCreate = (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        createMutation.mutate();
    };

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            <div>
                <h2 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">Variables Manager</h2>
                <p className="text-gray-500 dark:text-gray-400">Define and anchor standardized variables as immutable DIDs.</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Creation Form */}
                <div className="lg:col-span-2 space-y-6">
                    <div className="bg-white border border-gray-200 rounded-xl p-6 dark:bg-[#242424] dark:border-white/10 shadow-sm dark:shadow-none">
                        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
                            <Database className="text-blue-500" size={20} /> New Variable
                        </h3>
                        <form onSubmit={handleCreate} className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Variable Name</label>
                                    <input
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        placeholder="e.g., Temperature"
                                        required
                                        className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Unit of Measurement</label>
                                    <input
                                        type="text"
                                        value={unit}
                                        onChange={(e) => setUnit(e.target.value)}
                                        placeholder="e.g., Celsius, kg, m/s"
                                        className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Description</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    rows={3}
                                    placeholder="Brief description of the variable..."
                                    className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">JSON-LD Context (Optional)</label>
                                <textarea
                                    value={context}
                                    onChange={(e) => setContext(e.target.value)}
                                    rows={4}
                                    placeholder='{"@vocab": "http://schema.org/"}'
                                    className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg p-4 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={createMutation.isPending || !name.trim()}
                                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-lg font-medium transition-colors flex justify-center items-center gap-2 text-black shadow-sm"
                            >
                                {createMutation.isPending ? 'Anchoring...' : (
                                    <>
                                        <Plus size={20} /> Create Variable DID
                                    </>
                                )}
                            </button>
                        </form>
                    </div>

                    {createMutation.isError && (
                        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-600 flex items-center gap-3 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-400">
                            <AlertCircle size={20} />
                            {createMutation.error.message || "Failed to create variable."}
                        </div>
                    )}

                    {createMutation.data && (
                        <div className="p-6 bg-green-50 border border-green-200 rounded-xl dark:bg-green-500/10 dark:border-green-500/20">
                            <h3 className="text-green-600 dark:text-green-400 font-semibold mb-2 flex items-center gap-2">
                                <CheckCircle size={20} /> Variable Anchored Successfully
                            </h3>
                            <div className="font-mono text-sm break-all text-gray-900 bg-white border border-gray-200 p-3 rounded select-all dark:text-gray-300 dark:bg-black/20 dark:border-transparent">
                                <ResolverLink did={createMutation.data.did} />
                            </div>
                            <p className="text-[10px] text-gray-500 mt-2 italic">Note: Locally anchored DIDs are resolvable via the internal DID Manager.</p>
                        </div>
                    )}
                </div>

                {/* History List */}
                <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        <Variable className="text-blue-500" size={20} /> Recent Variables
                    </h3>
                    <div className="space-y-3 max-h-[calc(100vh-250px)] overflow-y-auto pr-2 custom-scrollbar">
                        {history.length === 0 && (
                            <p className="text-gray-500 dark:text-gray-400 italic text-sm">No variables created yet.</p>
                        )}
                        {history.map((item, i) => (
                            <div key={i} className="bg-white border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors dark:bg-[#242424] dark:border-white/10 dark:hover:border-blue-500/50 shadow-sm dark:shadow-none">
                                <div className="flex justify-between items-start mb-2">
                                    <h4 className="font-medium text-gray-900 dark:text-white truncate pr-2">
                                        {item.name}
                                    </h4>
                                    <span className="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                                        {new Date(item.timestamp).toLocaleDateString()}
                                    </span>
                                </div>
                                {item.unit && (
                                    <p className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">
                                        Unit: <span className="font-normal">{item.unit}</span>
                                    </p>
                                )}
                                <p className="text-xs text-gray-500 dark:text-gray-400 font-mono mb-3 line-clamp-2">
                                    {item.description}
                                </p>
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
