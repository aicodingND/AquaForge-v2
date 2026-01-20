'use client';

import { useAppStore } from '@/lib/store';

interface TeamCardProps {
    teamType: 'seton' | 'opponent';
}

export default function TeamCard({ teamType }: TeamCardProps) {
    const { setonTeam, opponentTeam, setSetonTeam, setOpponentTeam } = useAppStore();

    const team = teamType === 'seton' ? setonTeam : opponentTeam;
    const gradientFrom = teamType === 'seton' ? 'from-[#D4AF37]' : 'from-[#7C8B9A]';
    const gradientTo = teamType === 'seton' ? 'to-[#C99700]' : 'to-[#5A6A7A]';
    const accentColor = teamType === 'seton' ? 'text-[#D4AF37]' : 'text-[#7C8B9A]';
    const label = teamType === 'seton' ? 'Seton Team' : 'Opponent Team';

    const handleClear = () => {
        if (teamType === 'seton') {
            setSetonTeam(null);
        } else {
            setOpponentTeam(null);
        }
    };

    if (!team) {
        return (
            <div className="rounded-xl border border-[#1a3a5c] bg-[#0C2340]/30 p-6">
                <div className="flex items-center gap-3 text-white/40">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                    <div>
                        <p className="font-medium text-white/60">{label}</p>
                        <p className="text-sm">No team loaded</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className={`rounded-xl bg-gradient-to-br ${gradientFrom} ${gradientTo} p-[1px] shadow-lg`}>
            <div className="rounded-xl bg-[#091A30]/95 backdrop-blur p-5">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <p className="text-sm text-white/50">{label}</p>
                        <h3 className={`text-lg font-semibold ${accentColor}`}>{team.name}</h3>
                        <p className="text-xs text-white/40 truncate max-w-48">{team.filename}</p>
                    </div>
                    <button
                        onClick={handleClear}
                        className="text-white/40 hover:text-red-400 transition-colors p-1"
                        title="Remove team"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-3">
                    <StatItem label="Swimmers" value={team.swimmerCount.toString()} />
                    <StatItem label="Entries" value={team.entryCount.toString()} />
                    <StatItem label="Events" value={team.events.length.toString()} className="col-span-2" />
                </div>

                {/* Event Tags */}
                <div className="mt-4 flex flex-wrap gap-1.5">
                    {team.events.slice(0, 6).map((event) => (
                        <span
                            key={event}
                            className="text-xs px-2 py-0.5 rounded-full bg-[#1a3a5c] text-white/60 border border-[#1a3a5c]"
                        >
                            {event.replace(/^\d+\s*/, '')}
                        </span>
                    ))}
                    {team.events.length > 6 && (
                        <span className="text-xs px-2 py-0.5 text-white/40">
                            +{team.events.length - 6} more
                        </span>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatItem({ label, value, className = '' }: { label: string; value: string; className?: string }) {
    return (
        <div className={`bg-[#0C2340]/50 rounded-lg p-3 ${className}`}>
            <p className="text-2xl font-bold text-white">{value}</p>
            <p className="text-xs text-white/50">{label}</p>
        </div>
    );
}
