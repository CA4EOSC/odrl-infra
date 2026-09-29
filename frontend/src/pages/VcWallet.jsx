import React, { useState, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Mail, Github, Terminal, Fingerprint, ChevronRight, CheckCircle, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { cn } from '../lib/utils';
import { useUser } from '../context/UserContext';

import { OAUTH_CONFIG } from '../config';

const VC_TYPES = [
    { id: 'google', name: 'Google Account', icon: Mail, description: 'Prove ownership of a Google email address.', endpoint: '/vc/google' },
    { id: 'github', name: 'GitHub Account', icon: Github, description: 'Prove ownership of a GitHub username.', endpoint: '/vc/github' },
    { id: 'ssh', name: 'SSH Key', icon: Terminal, description: 'Link an SSH public key to your DID.', endpoint: '/vc/ssh' },
    { id: 'orcid', name: 'ORCID iD', icon: Fingerprint, description: 'Link your ORCID researcher identifier.', endpoint: '/vc/orcid' },
];

export default function VcWallet() {
    const [selectedType, setSelectedType] = useState(null);
    const [formData, setFormData] = useState({ token: '', subject_did: '', username: '', public_key: '', signature: '', orcid: '' });
    const [result, setResult] = useState(null);
    const [googleProfile, setGoogleProfile] = useState(null);
    const { login } = useUser();

    useEffect(() => {
        const handleMessage = async (event) => {
            if (event.data?.type === 'OAUTH_CALLBACK') {
                const { provider, token, orcid } = event.data;
                
                setFormData(prev => {
                    const newData = { ...prev, token };
                    if (provider === 'orcid' && orcid) newData.orcid = orcid;
                    return newData;
                });

                if (provider === 'google') {
                    try {
                        const payload = JSON.parse(atob(token.split('.')[1]));
                        const profile = {
                            name: payload.name,
                            email: payload.email,
                            picture: payload.picture
                        };
                        setGoogleProfile(profile);

                        try {
                            const res = await api.get(`/registry/${encodeURIComponent(profile.email)}`);
                            if (res.data && res.data.did) {
                                const existingDid = res.data.did;
                                setFormData(prev => ({ ...prev, subject_did: existingDid }));
                                login(profile, existingDid);
                            }
                        } catch (apiErr) {
                            // If 404, it means it's not in the registry yet, which is fine
                            if (apiErr.response?.status !== 404) {
                                console.error("Failed to fetch DID from registry", apiErr);
                            }
                        }
                    } catch (e) {
                        console.error("Failed to parse Google JWT token", e);
                    }
                }
            }
        };
        
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    const issueMutation = useMutation({
        mutationFn: async (data) => {
            const endpoint = VC_TYPES.find(t => t.id === selectedType).endpoint;
            const res = await api.post(endpoint, data);
            return { data: res.data, submittedData: data };
        },
        onSuccess: ({ data, submittedData }) => {
            setResult(data);
            
            // Log the user in context to display profile
            const profile = googleProfile || { name: submittedData.username || 'User' };
            login(profile, submittedData.subject_did);
        },
        onError: (err) => alert(err.response?.data?.detail || "Failed to issue VC")
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        let submitData = { ...formData };

        if (!submitData.subject_did) {
            try {
                const payload = googleProfile 
                    ? { name: googleProfile.name, email: googleProfile.email } 
                    : { purpose: "vc-subject" };
                
                const res = await api.post('/did/create', { payload });
                if (res.data && res.data.did) {
                    const newDid = res.data.did;
                    submitData.subject_did = newDid;
                    setFormData(prev => ({ ...prev, subject_did: newDid }));
                    
                    if (googleProfile?.email) {
                        try {
                            await api.post('/registry', {
                                email: googleProfile.email,
                                did: newDid
                            });
                        } catch (err) {
                            console.error("Failed to save to server registry", err);
                        }
                    }
                } else {
                    throw new Error("Invalid response from DID creation");
                }
            } catch (err) {
                alert("Failed to auto-generate DID: " + (err.response?.data?.detail || err.message));
                return;
            }
        }

        issueMutation.mutate(submitData);
    };

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSocialLogin = (provider) => {
        const config = OAUTH_CONFIG[provider];
        if (!config) return;

        const params = new URLSearchParams({
            client_id: config.clientId,
            redirect_uri: config.redirectUri,
            response_type: 'token', // or 'code' depending on flow, using token for implicit demo or code for backend exchange
            scope: config.scope,
            state: 'random_state_string', // Should be random for security
        });

        // Google uses 'response_type=id_token' for OIDC if not using code flow
        if (provider === 'google') {
            params.set('response_type', 'id_token');
            params.set('nonce', 'random_nonce');
        }

        window.open(`${config.authUrl}?${params.toString()}`, '_blank', 'width=500,height=600');
    };

    return (
        <div className="max-w-4xl mx-auto">
            <h2 className="text-3xl font-bold mb-2">VC Wallet</h2>
            <p className="text-gray-400 mb-8">Issue Verifiable Credentials to prove your identity.</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Helper / Selection */}
                <div className="space-y-4">
                    <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Available Credentials</h3>
                    {VC_TYPES.map((type) => (
                        <div
                            key={type.id}
                            onClick={() => { setSelectedType(type.id); setResult(null); issueMutation.reset(); }}
                            className={cn(
                                "group p-4 rounded-xl border cursor-pointer transition-all flex items-center justify-between",
                                selectedType === type.id
                                    ? "bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500 dark:bg-indigo-600/20 dark:border-indigo-500"
                                    : "bg-white border-gray-200 hover:border-gray-300 hover:bg-gray-50 dark:bg-[#242424] dark:border-white/10 dark:hover:border-white/20 dark:hover:bg-white/5"
                            )}
                        >
                            <div className="flex items-center gap-4">
                                <div className={cn("p-2 rounded-lg", selectedType === type.id ? "bg-indigo-600 text-white dark:bg-indigo-500" : "bg-gray-100 text-gray-500 dark:bg-white/5 dark:text-gray-400")}>
                                    <type.icon size={24} />
                                </div>
                                <div>
                                    <h4 className="font-medium text-gray-900 dark:text-white">{type.name}</h4>
                                    <p className="text-xs text-gray-500 dark:text-gray-400">{type.description}</p>
                                </div>
                            </div>
                            <ChevronRight size={16} className={cn("transition-transform text-gray-500", selectedType === type.id && "rotate-90 text-indigo-600 dark:text-indigo-400")} />
                        </div>
                    ))}
                </div>

                {/* Form View */}
                <div className="bg-white border border-gray-200 rounded-xl p-6 min-h-[400px] flex flex-col dark:bg-[#242424] dark:border-white/10 shadow-sm dark:shadow-none">
                    {!selectedType ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-gray-500 text-center p-8">
                            <ShieldCheck size={48} className="mb-4 opacity-50" />
                            <p>Select a credential type to start issuance.</p>
                        </div>
                    ) : (
                        <div className="fade-in">
                            <div className="flex items-center gap-2 mb-6 pb-4 border-b border-gray-200 dark:border-white/10">
                                <span className="text-indigo-600 dark:text-indigo-400 text-sm font-mono uppercase">Issuing:</span>
                                <span className="font-bold text-gray-900 dark:text-white">{VC_TYPES.find(t => t.id === selectedType).name}</span>
                            </div>

                            <form onSubmit={handleSubmit} className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Subject DID</label>
                                    <input
                                        name="subject_did"
                                        placeholder="Leave empty to auto-generate"
                                        className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                        value={formData.subject_did}
                                        onChange={handleChange}
                                    />
                                </div>

                                {selectedType === 'google' && (
                                    <div>
                                        <div className="flex justify-between items-center mb-1">
                                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">Google ID Token</label>
                                            {!googleProfile && (
                                                <button
                                                    type="button"
                                                    onClick={() => handleSocialLogin('google')}
                                                    className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-2 py-1 rounded border border-red-200 transition-colors dark:bg-red-900/20 dark:text-red-400 dark:border-red-900/30"
                                                >
                                                    Connect Google Account
                                                </button>
                                            )}
                                        </div>
                                        {googleProfile && (
                                            <div className="flex items-center gap-3 p-3 bg-gray-50 border border-gray-200 rounded-lg mb-3 dark:bg-white/5 dark:border-white/10">
                                                {googleProfile.picture && (
                                                    <img src={googleProfile.picture} alt="Profile" className="w-10 h-10 rounded-full" />
                                                )}
                                                <div>
                                                    <div className="text-sm font-medium text-gray-900 dark:text-white">{googleProfile.name}</div>
                                                    <div className="text-xs text-gray-500 dark:text-gray-400">{googleProfile.email}</div>
                                                </div>
                                                <button 
                                                    type="button" 
                                                    onClick={() => setGoogleProfile(null) || setFormData({...formData, token: ''})}
                                                    className="ml-auto text-xs text-red-500 hover:text-red-700 underline"
                                                >
                                                    Disconnect
                                                </button>
                                            </div>
                                        )}
                                        <textarea
                                            name="token"
                                            rows={4}
                                            placeholder="eyJhbGci..."
                                            className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors font-mono dark:bg-black/20 dark:border-white/10 dark:text-white"
                                            value={formData.token}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                )}

                                {selectedType === 'github' && (
                                    <div>
                                        <div className="flex justify-between items-center mb-1">
                                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">GitHub Access Token</label>
                                            <button
                                                type="button"
                                                onClick={() => handleSocialLogin('github')}
                                                className="text-xs bg-gray-100 text-gray-700 hover:bg-gray-200 px-2 py-1 rounded border border-gray-300 transition-colors dark:bg-white/10 dark:text-gray-300 dark:border-white/20 dark:hover:bg-white/20"
                                            >
                                                Connect GitHub Account
                                            </button>
                                        </div>
                                        <input
                                            name="token"
                                            type="password"
                                            placeholder="ghp_..."
                                            className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors font-mono dark:bg-black/20 dark:border-white/10 dark:text-white"
                                            value={formData.token}
                                            onChange={handleChange}
                                            required
                                        />
                                    </div>
                                )}

                                {selectedType === 'orcid' && (
                                    <>
                                        <div>
                                            <div className="flex justify-between items-center mb-1">
                                                <label className="block text-sm font-medium text-gray-500 dark:text-gray-400">ORCID iD</label>
                                                <button
                                                    type="button"
                                                    onClick={() => handleSocialLogin('orcid')}
                                                    className="text-xs bg-green-50 text-green-600 hover:bg-green-100 px-2 py-1 rounded border border-green-200 transition-colors dark:bg-green-900/20 dark:text-green-400 dark:border-green-900/30"
                                                >
                                                    Connect ORCID
                                                </button>
                                            </div>
                                            <input
                                                name="orcid"
                                                placeholder="0000-0000-0000-0000"
                                                className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors font-mono dark:bg-black/20 dark:border-white/10 dark:text-white"
                                                value={formData.orcid}
                                                onChange={handleChange}
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Access Token</label>
                                            <input
                                                name="token"
                                                type="password"
                                                className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors font-mono dark:bg-black/20 dark:border-white/10 dark:text-white"
                                                value={formData.token}
                                                onChange={handleChange}
                                                required
                                            />
                                        </div>
                                    </>
                                )}

                                {selectedType === 'ssh' && (
                                    <>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Username (Principal)</label>
                                            <input
                                                name="username"
                                                className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors dark:bg-black/20 dark:border-white/10 dark:text-white"
                                                value={formData.username}
                                                onChange={handleChange}
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">SSH Public Key</label>
                                            <input
                                                name="public_key"
                                                placeholder="ssh-ed25519 ..."
                                                className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors font-mono dark:bg-black/20 dark:border-white/10 dark:text-white"
                                                value={formData.public_key}
                                                onChange={handleChange}
                                                required
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">Signature</label>
                                            <textarea
                                                name="signature"
                                                rows={3}
                                                placeholder="-----BEGIN SSH SIGNATURE----- ..."
                                                className="w-full bg-gray-50 border border-gray-300 rounded-lg px-4 py-3 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-colors font-mono dark:bg-black/20 dark:border-white/10 dark:text-white"
                                                value={formData.signature}
                                                onChange={handleChange}
                                                required
                                            />
                                            <p className="text-[10px] text-gray-500 mt-1">
                                                Sign your subject DID string using: <code>ssh-keygen -Y sign -f key -n oydid data_file</code>
                                            </p>
                                        </div>
                                    </>
                                )}

                                <button
                                    type="submit"
                                    disabled={issueMutation.isPending}
                                    className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-6 py-3 rounded-lg font-medium transition-colors mt-4 text-white shadow-sm"
                                >
                                    {issueMutation.isPending ? 'Issuing...' : 'Issue Credential'}
                                </button>
                            </form>

                            {result && (
                                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg dark:bg-green-500/10 dark:border-green-500/20">
                                    <h3 className="text-green-600 dark:text-green-400 font-semibold mb-2 flex items-center gap-2">
                                        <CheckCircle size={18} /> Credentials Issued!
                                    </h3>
                                    <pre className="bg-white border border-gray-200 p-3 rounded overflow-auto max-h-96 text-xs font-mono text-gray-900 dark:bg-black/30 dark:text-gray-300 dark:border-transparent custom-scrollbar">
                                        {JSON.stringify(result, null, 2)}
                                    </pre>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

// Helper icon
function ShieldCheck(props) {
    return <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /><path d="m9 12 2 2 4-4" /></svg>
}
