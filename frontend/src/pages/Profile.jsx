import React from 'react';
import { useUser } from '../context/UserContext';
import { UserCircle, ShieldCheck, Mail, LogOut, Copy } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Profile() {
    const { user, logout } = useUser();
    const navigate = useNavigate();

    if (!user) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[500px] text-gray-500">
                <UserCircle size={64} className="mb-4 opacity-30" />
                <h2 className="text-xl font-medium text-gray-700 dark:text-gray-300">Not Logged In</h2>
                <p className="mt-2 mb-6 text-sm">Please issue credentials to create your profile.</p>
                <button 
                    onClick={() => navigate('/vcs')}
                    className="px-6 py-2 bg-indigo-600 text-white rounded-lg shadow-md hover:bg-indigo-700"
                >
                    Go to VC Wallet
                </button>
            </div>
        );
    }

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        alert('Copied to clipboard');
    };

    return (
        <div className="max-w-2xl mx-auto">
            <h2 className="text-3xl font-bold mb-8">Your Profile</h2>

            <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm dark:bg-[#242424] dark:border-white/10 relative">
                {/* Header background */}
                <div className="h-32 bg-gradient-to-r from-indigo-500 to-purple-600 w-full" />
                
                <div className="px-6 pb-6 pt-0 relative flex flex-col items-center sm:items-start sm:flex-row gap-6">
                    {/* Avatar */}
                    <div className="w-24 h-24 rounded-2xl bg-white p-1 shadow-lg -mt-12 dark:bg-[#1a1a1a] flex-shrink-0">
                        {user.picture ? (
                            <img src={user.picture} alt="Avatar" className="w-full h-full rounded-xl object-cover" />
                        ) : (
                            <div className="w-full h-full rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400">
                                <UserCircle size={48} />
                            </div>
                        )}
                    </div>
                    
                    {/* Info */}
                    <div className="flex-1 text-center sm:text-left mt-2">
                        <h3 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center justify-center sm:justify-start gap-2">
                            {user.name || "Anonymous User"}
                            {user.name && <ShieldCheck className="text-green-500" size={20} />}
                        </h3>
                        {user.email && (
                            <div className="flex items-center justify-center sm:justify-start gap-1.5 text-gray-500 mt-1 dark:text-gray-400">
                                <Mail size={14} />
                                <span className="text-sm">{user.email}</span>
                            </div>
                        )}
                    </div>
                </div>

                <div className="px-6 pb-6">
                    <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 dark:bg-black/20 dark:border-white/5 space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Your Decentralized ID (DID)</span>
                            <button onClick={() => copyToClipboard(user.did)} className="text-gray-400 hover:text-indigo-600 transition-colors">
                                <Copy size={16} />
                            </button>
                        </div>
                        <div className="font-mono text-sm text-gray-800 break-all dark:text-gray-200 bg-white p-3 rounded border border-gray-200 dark:bg-black/40 dark:border-white/5">
                            {user.did}
                        </div>
                    </div>
                </div>
            </div>

            <div className="mt-8 flex justify-center">
                <button 
                    onClick={() => { logout(); navigate('/'); }}
                    className="flex items-center gap-2 px-6 py-2.5 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors font-medium border border-red-200 dark:bg-red-900/20 dark:border-red-900/30 dark:text-red-400 dark:hover:bg-red-900/40"
                >
                    <LogOut size={18} />
                    Sign Out
                </button>
            </div>
        </div>
    );
}
