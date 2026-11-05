import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { LayoutDashboard, Wallet, ScrollText, PlayCircle, Sun, Moon, LogOut, CheckCircle, Menu, X, FileText, Database, ShieldCheck, FileKey, Play, MessageSquare, FileJson, Users, ExternalLink } from 'lucide-react';
import { cn } from '../lib/utils';
import { ThemeToggle } from './ThemeToggle';
import { useUser } from '../context/UserContext';
import { THEME_CONFIG } from '../config';
import api from '../services/api';

const NavItem = ({ to, icon: Icon, label, description, isActive }) => {
    return (
        <Link
            to={to}
            className={cn(
                "group relative flex items-start gap-3 px-5 py-3 rounded-2xl transition-all duration-400",
                isActive
                    ? "bg-indigo-600/20 text-indigo-600 dark:bg-indigo-500/30 dark:text-indigo-400 shadow-[0_4px_25px_rgba(79,70,229,0.2)] ring-1 ring-white/20"
                    : "text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white"
            )}
        >
            {isActive && (
                <div className="absolute left-0 w-1.5 h-8 bg-indigo-600 dark:bg-indigo-500 rounded-r-full shadow-[0_0_15px_0_rgba(79,70,229,0.8)] top-1/2 -translate-y-1/2" />
            )}

            <div className={cn(
                "p-2 rounded-xl transition-all duration-400 group-hover:rotate-6 group-hover:scale-110 shrink-0",
                isActive
                    ? "bg-gradient-to-br from-indigo-500 to-indigo-600 text-white shadow-lg dark:shadow-indigo-400/50"
                    : "bg-gray-200 dark:bg-white/10 text-gray-500 dark:text-gray-400 group-hover:bg-indigo-50 dark:group-hover:bg-indigo-500/20 group-hover:text-indigo-600 dark:group-hover:text-indigo-300"
            )}>
                <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
            </div>

            <div className="flex flex-col gap-0.5 min-w-0">
                <span className={cn(
                    "font-bold text-[15px] tracking-tight transition-all duration-400",
                    isActive ? "translate-x-1" : "group-hover:translate-x-1"
                )}>
                    {label}
                </span>
                <span className={cn(
                    "text-[11px] font-semibold leading-tight transition-all duration-400 truncate",
                    isActive
                        ? "text-indigo-600/80 dark:text-indigo-400/80 translate-x-1"
                        : "text-gray-500 dark:text-gray-400 group-hover:translate-x-1"
                )}>
                    {description}
                </span>
            </div>

            {!isActive && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500 opacity-0 transition-all duration-400 group-hover:opacity-100 group-hover:scale-125 shadow-[0_0_10px_rgba(99,102,241,0.8)] self-center" />
            )}
        </Link>
    );
};

export default function Layout({ children }) {
    const location = useLocation();
    const { user } = useUser();

    // Fetch theme configuration from backend (supports templates and environment variables)
    const { data: themeConfig } = useQuery({
        queryKey: ['theme-config'],
        queryFn: async () => {
            try {
                const res = await api.get('/theme/config');
                return res.data;
            } catch (err) {
                console.warn('Could not load theme config from backend, using defaults', err);
                return null;
            }
        },
        staleTime: 60 * 1000
    });

    const logoUrl = themeConfig?.logo_url || THEME_CONFIG.defaultLogoUrl;
    const footerText = themeConfig?.footer_text || THEME_CONFIG.defaultFooterText;
    const headerHtml = themeConfig?.header_html;
    const footerHtml = themeConfig?.footer_html;

    return (
        <div className="flex h-screen bg-white text-gray-900 dark:bg-[#050505] dark:text-white overflow-hidden selection:bg-indigo-500/30">
            {/* Sidebar */}
            <aside className="w-72 glass border-r border-gray-200 dark:border-white/5 flex flex-col relative z-20">
                <div className="p-6 mb-2">
                    {/* Logo on top of ODRL Infra & Protocol Layer */}
                    {logoUrl && (
                        <div className="mb-4">
                            <a
                                href="https://cdif4eosc.eu"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="block transition-opacity hover:opacity-85"
                                title="CDIF4EOSC Project"
                            >
                                <img
                                    src={logoUrl}
                                    alt="CDIF4EOSC Logo"
                                    className="max-h-12 w-auto max-w-[200px] object-contain rounded"
                                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                                />
                            </a>
                        </div>
                    )}

                    <div className="flex items-center gap-3 group cursor-default">
                        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-700 flex items-center justify-center shadow-lg shadow-indigo-600/20 group-hover:scale-110 transition-transform duration-500 overflow-hidden shrink-0">
                            <ShieldCheck className="text-white" size={24} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black tracking-tight bg-gradient-to-r from-gray-900 via-indigo-800 to-gray-900 dark:from-white dark:via-indigo-300 dark:to-white bg-[length:200%_auto] animate-gradient-x bg-clip-text text-transparent">
                                ODRL Infra
                            </h1>
                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-600/60 dark:text-indigo-400/60 uppercase tracking-widest leading-none">
                                <span className="flex h-1 w-1 rounded-full bg-indigo-500 animate-pulse" />
                                Protocol Layer
                            </div>
                        </div>
                    </div>
                </div>

                <div className="flex-1 px-4 overflow-y-auto no-scrollbar space-y-1">
                    <NavItem to="/demo" icon={Play} label="Live Demo" description="Test all applications" isActive={location.pathname === "/demo"} />
                    <NavItem to="/" icon={LayoutDashboard} label="Dashboard" description="Explore infrastructure" isActive={location.pathname === "/"} />
                    <NavItem to="/dids" icon={FileKey} label="DID Manager" description="Bookmarks and resolver" isActive={location.pathname === "/dids"} />
                    <NavItem to="/vcs" icon={Wallet} label="VC Wallet" description="Google, Github, ORCID and SSH" isActive={location.pathname === "/vcs"} />
                    <NavItem to="/policies" icon={ShieldCheck} label="Policy Builder" description="Create your policy" isActive={location.pathname === "/policies"} />
                    <NavItem to="/prompts" icon={MessageSquare} label="Prompts Manager" description="FAIR LLM prompts" isActive={location.pathname === "/prompts"} />
                    <NavItem to="/variables" icon={Database} label="Variables" description="Cross-Domain Interoperability" isActive={location.pathname === "/variables"} />
                    <NavItem to="/groups" icon={Users} label="Groups" description="Organization Ontology" isActive={location.pathname === "/groups"} />
                    <NavItem to="/croissants" icon={FileJson} label="Croissants" description="AI-Ready data" isActive={location.pathname === "/croissants"} />
                </div>

                {/* Sidebar footer on the same level as System Online */}
                <div className="p-4 px-5 mt-auto border-t border-gray-100 dark:border-white/5 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                            <div className="relative flex items-center justify-center">
                                <div className="absolute w-2.5 h-2.5 rounded-full bg-green-500/40 animate-ping" />
                                <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                            </div>
                            <span className="text-[11px] font-extrabold text-gray-500 dark:text-gray-400 tracking-tight uppercase">System Online</span>
                        </div>
                        <a
                            href="https://cdif4eosc.eu"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[10px] text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 flex items-center gap-1 transition-colors"
                        >
                            cdif4eosc.eu
                            <ExternalLink size={10} />
                        </a>
                    </div>
                    {footerHtml ? (
                        <div
                            className="custom-sidebar-footer text-[10px] text-gray-500 dark:text-gray-400"
                            dangerouslySetInnerHTML={{ __html: footerHtml }}
                        />
                    ) : (
                        <p className="text-[10px] leading-tight text-gray-500 dark:text-gray-400 line-clamp-3 hover:line-clamp-none transition-all">
                            {footerText}
                        </p>
                    )}
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-x-hidden overflow-y-auto custom-scrollbar bg-[#fdfdfd] dark:bg-[#0a0a0a] relative h-full flex flex-col justify-between">
                <div>
                    {/* Top Bar */}
                    <header className="sticky top-0 z-30 flex items-center justify-between gap-4 p-4 md:px-8 glass border-b border-gray-200 dark:border-white/5 animate-in slide-in-from-top-4 duration-500">
                        {headerHtml ? (
                            <div
                                className="custom-header-template flex items-center"
                                dangerouslySetInnerHTML={{ __html: headerHtml }}
                            />
                        ) : (
                            <div />
                        )}

                        <div className="flex items-center gap-4 ml-auto">
                            {user ? (
                                <Link
                                    to="/profile"
                                    className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-white border border-gray-200 hover:bg-gray-50 transition-colors shadow-sm dark:bg-[#242424] dark:border-white/10 dark:hover:bg-white/5"
                                >
                                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{user.name || 'Profile'}</span>
                                    {user.picture ? (
                                        <img src={user.picture} alt="Profile" className="w-7 h-7 rounded-full object-cover" />
                                    ) : (
                                        <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400">
                                            <Users size={14} />
                                        </div>
                                    )}
                                </Link>
                            ) : (
                                <Link
                                    to="/vcs"
                                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold transition-all shadow-lg shadow-indigo-600/20 active:scale-95 group"
                                >
                                    <Wallet size={16} className="group-hover:rotate-12 transition-transform" />
                                    Login
                                </Link>
                            )}
                            <div className="w-px h-6 bg-gray-200 dark:bg-white/10 mx-1" />
                            <ThemeToggle />
                        </div>
                    </header>

                    <div className="relative flex-1">
                        {/* Background Decorations */}
                        <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-indigo-500/5 blur-[120px] pointer-events-none rounded-full -translate-y-1/2 translate-x-1/4" />
                        <div className="absolute bottom-0 left-0 w-1/3 h-1/3 bg-purple-500/5 blur-[100px] pointer-events-none rounded-full translate-y-1/2 -translate-x-1/4" />

                        <div className="p-4 md:p-8 lg:p-10 max-w-7xl mx-auto relative z-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
                            {children}
                        </div>
                    </div>
                </div>

                {/* Main page footer (renders custom footer template if provided) */}
                {footerHtml && (
                    <footer className="mt-auto border-t border-gray-200 dark:border-white/10 bg-white/70 dark:bg-black/40 backdrop-blur-md px-6 py-4 text-xs text-gray-500 dark:text-gray-400">
                        <div
                            className="custom-footer-template"
                            dangerouslySetInnerHTML={{ __html: footerHtml }}
                        />
                    </footer>
                )}
            </main>
        </div>
    );
}


