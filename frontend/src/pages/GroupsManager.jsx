import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Users, Plus, CheckCircle, AlertCircle, Shield, Building, UserPlus, Info } from 'lucide-react';
import api from '../services/api';
import ResolverLink from '../components/ResolverLink';
import { cn } from '../lib/utils';
import { Link } from 'react-router-dom';

const ROLES = [
    { id: 'admin', label: 'Administrator', description: 'Full control over the organization' },
    { id: 'manager', label: 'Manager', description: 'Management of sub-units and members' },
    { id: 'member', label: 'Member', description: 'Standard organizational member' },
];

export default function GroupsManager() {
    const [orgName, setOrgName] = useState('');
    const [orgDesc, setOrgDesc] = useState('');
    const [members, setMembers] = useState([{ did: '', role: 'member' }]);
    const [history, setHistory] = useState(() => JSON.parse(localStorage.getItem('groups_history') || '[]'));

    useEffect(() => {
        localStorage.setItem('groups_history', JSON.stringify(history));
    }, [history]);

    const addToHistory = (did, payload) => {
        setHistory(prev => [{ did, ...payload, timestamp: Date.now() }, ...prev]);
    }

    const createMutation = useMutation({
        mutationFn: async () => {
            const data = {
                name: orgName,
                description: orgDesc,
                members: members.filter(m => m.did.trim()).map(m => ({
                    member: m.did,
                    role: m.role
                }))
            };
            const res = await api.post('/groups/create', data);
            const payload = {
                "@context": "http://www.w3.org/ns/org#",
                "type": "Organization",
                "name": orgName,
                "description": orgDesc,
                "hasMember": data.members.map(m => ({
                    "type": "Membership",
                    "member": m.member,
                    "role": m.role
                })),
                "timestamp": new Date().toISOString()
            };
            return { ...res.data, originalContent: payload };
        },
        onSuccess: (data) => {
            addToHistory(data.did, data.originalContent);
            setOrgName('');
            setOrgDesc('');
            setMembers([{ did: '', role: 'member' }]);
        }
    });

    const handleAddMember = () => {
        setMembers([...members, { did: '', role: 'member' }]);
    };

    const handleMemberChange = (index, field, value) => {
        const newMembers = [...members];
        newMembers[index][field] = value;
        setMembers(newMembers);
    };

    const handleCreate = (e) => {
        e.preventDefault();
        if (!orgName.trim()) return;
        createMutation.mutate();
    };

    return (
        <div className="max-w-5xl mx-auto space-y-8">
            <header className="flex justify-between items-start">
                <div>
                    <h2 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">Groups Manager</h2>
                    <p className="text-gray-500 dark:text-gray-400">Define organizations and manage memberships using the W3C Organization Ontology.</p>
                </div>
                <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3 flex items-center gap-3 dark:bg-indigo-500/10 dark:border-indigo-500/20">
                    <Shield className="text-indigo-600 dark:text-indigo-400" size={24} />
                    <div className="text-xs">
                        <p className="font-bold text-indigo-900 dark:text-indigo-300">Trust Layer Enabled</p>
                        <p className="text-indigo-700 dark:text-indigo-400/70 text-[10px]">All groups are anchored as immutable DIDs.</p>
                    </div>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Creation Form */}
                <div className="lg:col-span-2 space-y-6">
                    <form onSubmit={handleCreate} className="bg-white border border-gray-200 rounded-2xl p-8 dark:bg-[#242424] dark:border-white/10 shadow-sm dark:shadow-none space-y-6">
                        <section className="space-y-4">
                            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                <Building className="text-indigo-500" size={20} /> Organization Details
                            </h3>
                            <div>
                                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Organization Name</label>
                                <input
                                    type="text"
                                    value={orgName}
                                    onChange={(e) => setOrgName(e.target.value)}
                                    placeholder="e.g., Open Data Initiative"
                                    required
                                    className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all dark:bg-black/20 dark:border-white/10 dark:text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">Description</label>
                                <textarea
                                    value={orgDesc}
                                    onChange={(e) => setOrgDesc(e.target.value)}
                                    rows={3}
                                    placeholder="Describe the purpose of this group..."
                                    className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all dark:bg-black/20 dark:border-white/10 dark:text-white"
                                />
                            </div>
                        </section>

                        <section className="space-y-4 pt-6 border-t border-gray-100 dark:border-white/5">
                            <div className="flex justify-between items-center">
                                <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                                    <UserPlus className="text-indigo-500" size={20} /> Members & Roles
                                </h3>
                                <button
                                    type="button"
                                    onClick={handleAddMember}
                                    className="text-xs font-bold text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 flex items-center gap-1"
                                >
                                    <Plus size={14} /> Add Member
                                </button>
                            </div>

                            <div className="space-y-3">
                                {members.map((m, i) => (
                                    <div key={i} className="flex gap-3 items-end group animate-in slide-in-from-top-2 duration-300">
                                        <div className="flex-1">
                                            {i === 0 && <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Member DID</label>}
                                            <input
                                                type="text"
                                                value={m.did}
                                                onChange={(e) => handleMemberChange(i, 'did', e.target.value)}
                                                placeholder="did:oyd:..."
                                                className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-black/20 dark:border-white/10 dark:text-white"
                                            />
                                        </div>
                                        <div className="w-32">
                                            {i === 0 && <label className="block text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Role</label>}
                                            <select
                                                value={m.role}
                                                onChange={(e) => handleMemberChange(i, 'role', e.target.value)}
                                                className="w-full bg-gray-50 border border-gray-300 text-gray-900 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:bg-black/20 dark:border-white/10 dark:text-white"
                                            >
                                                {ROLES.map(r => <option key={r.id} value={r.id}>{r.label}</option>)}
                                            </select>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>

                        <button
                            type="submit"
                            disabled={createMutation.isPending || !orgName.trim()}
                            className="w-full bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-4 rounded-xl font-bold text-lg transition-all flex justify-center items-center gap-2 text-white shadow-lg shadow-indigo-600/20"
                        >
                            {createMutation.isPending ? 'Anchoring Organization...' : (
                                <>
                                    <Plus size={22} /> Create Group DID
                                </>
                            )}
                        </button>
                    </form>

                    {createMutation.isError && (
                        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-600 flex items-center gap-3 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-400">
                            <AlertCircle size={20} />
                            Failed to anchor group metadata.
                        </div>
                    )}

                    {createMutation.data && (
                        <div className="p-6 bg-green-50 border border-green-200 rounded-2xl dark:bg-green-500/10 dark:border-green-500/20 animate-in zoom-in-95 duration-500">
                            <h3 className="text-green-600 dark:text-green-400 font-bold mb-3 flex items-center gap-2">
                                <CheckCircle size={20} /> Group Anchored Successfully
                            </h3>
                            <div className="bg-white border border-green-100 rounded-xl p-4 flex flex-col gap-2 dark:bg-black/20 dark:border-transparent">
                                <label className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Organization DID (Local Anchor)</label>
                                <ResolverLink did={createMutation.data.did} />
                                <p className="text-[10px] text-gray-500 mt-1 italic">Note: Locally anchored DIDs are resolvable via this application's DID Manager.</p>
                            </div>
                        </div>
                    )}
                </div>

                {/* Info & History List */}
                <div className="space-y-6">
                    <div className="bg-indigo-600 rounded-2xl p-6 text-white shadow-xl shadow-indigo-600/20 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 blur-3xl -translate-y-1/2 translate-x-1/2 rounded-full transition-transform duration-700 group-hover:scale-150" />
                        <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                            <Info size={20} /> W3C Org Ontology
                        </h3>
                        <p className="text-indigo-100 text-sm leading-relaxed mb-4">
                            The Organization Ontology enables publication of information on organizational structures, including governmental and private entities.
                        </p>
                        <div className="space-y-2">
                            <div className="flex items-center gap-2 text-xs font-medium bg-white/10 rounded-lg p-2">
                                <CheckCircle size={14} className="text-indigo-300" /> org:Organization
                            </div>
                            <div className="flex items-center gap-2 text-xs font-medium bg-white/10 rounded-lg p-2">
                                <CheckCircle size={14} className="text-indigo-300" /> org:Membership
                            </div>
                            <div className="flex items-center gap-2 text-xs font-medium bg-white/10 rounded-lg p-2">
                                <CheckCircle size={14} className="text-indigo-300" /> org:Role
                            </div>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
                            <Users className="text-indigo-500" size={20} /> Recent Groups
                        </h3>
                        <div className="space-y-3 max-h-[calc(100vh-450px)] overflow-y-auto pr-2 custom-scrollbar">
                            {history.length === 0 && (
                                <p className="text-gray-500 dark:text-gray-400 italic text-sm p-4 bg-gray-50 dark:bg-white/5 rounded-xl text-center">No groups anchored yet.</p>
                            )}
                            {history.map((item, i) => (
                                <div key={i} className="bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-300 transition-all dark:bg-[#242424] dark:border-white/10 dark:hover:border-indigo-500/50 group/item">
                                    <div className="flex justify-between items-start mb-2">
                                        <h4 className="font-bold text-gray-900 dark:text-white group-hover/item:text-indigo-600 dark:group-hover/item:text-indigo-400 transition-colors">
                                            {item.name}
                                        </h4>
                                        <span className="text-[10px] bg-gray-100 dark:bg-white/5 px-2 py-1 rounded-full text-gray-500 font-bold uppercase tracking-wider">
                                            {new Date(item.timestamp).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mb-3">
                                        {item.description}
                                    </p>
                                    <div className="flex items-center justify-between pt-3 border-t border-gray-50 dark:border-white/5">
                                        <div className="flex -space-x-2">
                                            {(item.hasMember || []).slice(0, 3).map((_, idx) => (
                                                <div key={idx} className="w-6 h-6 rounded-full bg-indigo-100 border-2 border-white flex items-center justify-center dark:bg-indigo-500/20 dark:border-[#242424]">
                                                    <Users size={10} className="text-indigo-600 dark:text-indigo-400" />
                                                </div>
                                            ))}
                                            {(item.hasMember || []).length > 3 && (
                                                <div className="w-6 h-6 rounded-full bg-gray-100 border-2 border-white flex items-center justify-center text-[8px] font-bold dark:bg-white/5 dark:border-[#242424]">
                                                    +{(item.hasMember || []).length - 3}
                                                </div>
                                            )}
                                        </div>
                                        <ResolverLink did={item.did} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
