'use client';

import { useAppStore } from '@/lib/store';

export default function ActivityLog() {
    const { logs } = useAppStore();

    return (
        <div className="glass-card rounded-xl p-4 sticky top-32">
            <h3 className="text-sm font-medium text-gold-primary mb-3 flex items-center gap-2">
                📋 Activity Log
            </h3>
            <div className="h-64 overflow-y-auto space-y-1 font-mono text-xs">
                {logs.length === 0 ? (
                    <p className="text-white/40">No activity yet...</p>
                ) : (
                    logs.map((log, i) => (
                        // PERFORMANCE FIX: Use log content + index as key for better React reconciliation
                        <p key={`${log}-${i}`} className="text-white/60">{log}</p>
                    ))
                )}
            </div>
        </div>
    );
}
