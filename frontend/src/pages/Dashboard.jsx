import { Link } from 'react-router-dom';
import {
    FileKey, Wallet, ShieldCheck, MessageSquare,
    Database, Users, FileJson, Sparkles, Play, LayoutDashboard
} from 'lucide-react';
import { cn } from '../lib/utils';

const DashboardCard = ({ to, title, description, icon: Icon, color, delay }) => {
    const isStatic = to.startsWith('/.well-known');
    const content = (
        <>
            <div className={cn(
                "w-12 h-12 rounded-xl mb-4 flex items-center justify-center transition-transform group-hover:scale-110 duration-300",
                `bg-${color}-500/10 text-${color}-600 dark:text-${color}-400`
            )}>
                <Icon size={24} />
            </div>
            <h3 className="text-xl font-bold mb-2 text-gray-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                {title}
            </h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed">
                {description}
            </p>
            <div className={cn(
                "absolute top-0 right-0 p-4 opacity-5 transition-opacity group-hover:opacity-10 dark:text-white",
                `text-${color}-600`
            )}>
                <Icon size={80} />
            </div>
        </>
    );

    const commonClasses = cn(
        "group p-6 rounded-2xl bg-white border border-gray-200 dark:bg-[#242424] dark:border-white/10 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 relative overflow-hidden",
        `hover:border-${color}-500/50`
    );

    if (isStatic) {
        return (
            <a
                href={to}
                target="_blank"
                rel="noopener noreferrer"
                className={commonClasses}
                style={{ animationDelay: `${delay}ms` }}
            >
                {content}
            </a>
        );
    }

    return (
        <Link
            to={to}
            className={commonClasses}
            style={{ animationDelay: `${delay}ms` }}
        >
            {content}
        </Link>
    );
};

export default function Dashboard() {
    return (
        <div className="space-y-10 py-4 max-w-7xl mx-auto">
            <header className="relative">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-600 dark:text-indigo-400">
                        <Sparkles size={20} className="animate-pulse" />
                    </div>
                    <span className="text-xs font-black uppercase tracking-[0.3em] text-indigo-600/60 dark:text-indigo-400/60">
                        Next-Generation Infrastructure
                    </span>
                </div>
                <h2 className="text-4xl md:text-5xl font-black text-gray-900 dark:text-white tracking-tight">
                    ODRL <span className="text-indigo-600 dark:text-indigo-400">Protocol Layer</span>
                </h2>
                <p className="text-gray-500 dark:text-gray-400 mt-4 max-w-2xl text-lg leading-relaxed">
                    Manage your decentralized identifiers, verify organizational metadata, and deploy sophisticated access control policies with Open Digital Rights Language and semantic indexing.
                </p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                <DashboardCard
                    to="/demo"
                    title="Live Demo"
                    description="Automated end-to-end verification of policies and group metadata."
                    icon={Play}
                    color="green"
                    delay={0}
                />
                <DashboardCard
                    to="/dids"
                    title="DID Manager"
                    description="Create and resolve bookmarks as Decentralized Identifiers."
                    icon={FileKey}
                    color="indigo"
                    delay={50}
                />
                <DashboardCard
                    to="/vcs"
                    title="VC Wallet"
                    description="Issue Verifiable Credentials for GitHub, Google, and more."
                    icon={Wallet}
                    color="cyan"
                    delay={100}
                />
                <DashboardCard
                    to="/policies"
                    title="Policy Builder"
                    description="Design ODRL access policies with granular permissions."
                    icon={ShieldCheck}
                    color="purple"
                    delay={150}
                />
                <DashboardCard
                    to="/prompts"
                    title="Prompts Manager"
                    description="Anchor and share FAIR AI prompts on the protocol layer."
                    icon={MessageSquare}
                    color="pink"
                    delay={200}
                />
                <DashboardCard
                    to="/variables"
                    title="Variables"
                    description="Standardize cross-domain interoperability descriptors."
                    icon={Database}
                    color="blue"
                    delay={250}
                />
                <DashboardCard
                    to="/groups"
                    title="Groups Manager"
                    description="Manage organizational structures using W3C Org Ontology."
                    icon={Users}
                    color="violet"
                    delay={300}
                />
                <DashboardCard
                    to="/croissants"
                    title="Croissants"
                    description="Make data AI-Ready by anchoring Croissant metadata."
                    icon={FileJson}
                    color="orange"
                    delay={350}
                />
                <DashboardCard
                    to="/.well-known/did.json"
                    title="System Identity"
                    description="Explore the W3C DID document for the ODRL protocol infrastructure."
                    icon={LayoutDashboard}
                    color="red"
                    delay={400}
                />
            </div>
        </div>
    );
}
