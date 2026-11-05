import React from 'react';
import { GitCommit } from 'lucide-react';

/* global __BUILD_INFO__ */
// Set at build time in vite.config.js (git commit of the deployed frontend).
const info = typeof __BUILD_INFO__ !== 'undefined' ? __BUILD_INFO__ : {};
const REPO = 'https://github.com/CDIF4EOSC/odrl-infra';

const day = (iso) => (iso ? iso.slice(0, 10) : '');

export default function BuildVersion() {
    const short = info.commit ? info.commit.slice(0, 7) : null;
    const title = short
        ? [
            `Commit ${info.commit}${info.dirty ? ' (with uncommitted changes)' : ''}`,
            info.branch && `Branch ${info.branch}`,
            info.date && `Committed ${day(info.date)}`,
            info.builtAt && `Built ${info.builtAt.replace('T', ' ').slice(0, 16)} UTC`,
        ].filter(Boolean).join('\n')
        : 'Version unknown: built without git information';

    const label = (
        <>
            <GitCommit size={12} className="shrink-0" />
            <span className="font-mono">{short || 'unknown'}{info.dirty ? '+' : ''}</span>
            {info.branch && <span className="truncate">· {info.branch}</span>}
            {info.date && <span className="shrink-0">· {day(info.date)}</span>}
        </>
    );
    const cls = "mt-2 flex items-center gap-1.5 text-[10px] text-gray-400 dark:text-gray-500 min-w-0";

    return short ? (
        <a href={`${REPO}/commit/${info.commit}`} target="_blank" rel="noreferrer" title={title}
            className={`${cls} hover:text-indigo-600 dark:hover:text-indigo-400`}>
            {label}
        </a>
    ) : (
        <div className={cls} title={title}>{label}</div>
    );
}
