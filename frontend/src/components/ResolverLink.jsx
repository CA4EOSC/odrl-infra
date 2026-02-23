import React from 'react';
import { ExternalLink } from 'lucide-react';

/**
 * ResolverLink component for pointing DIDs to the Universal Resolver.
 * @param {string} did - The Decentralized Identifier to link.
 * @param {boolean} icon - Whether to show the ExternalLink icon.
 * @param {string} className - Optional tailwind classes.
 */
const ResolverLink = ({ did, icon = true, className = "" }) => {
    if (!did) return null;

    return (
        <a
            href={`https://dev.uniresolver.io/#${did}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`text-indigo-600 hover:text-indigo-800 hover:underline inline-flex items-center gap-1 dark:text-indigo-400 dark:hover:text-indigo-300 break-all ${className}`}
            title="View on Universal Resolver"
        >
            {did} {icon && <ExternalLink size={12} className="shrink-0" />}
        </a>
    );
};

export default ResolverLink;
