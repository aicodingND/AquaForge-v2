'use client';

import { api } from '@/lib/api';
import { useAppStore } from '@/lib/store';

export default function ResultsTable() {
    const { optimizationResults, setonScore, opponentScore, setResults, addLog } = useAppStore();
    const clearResults = () => setResults([], 0, 0);

    if (!optimizationResults || optimizationResults.length === 0) {
        return (
            <div className="glass-card rounded-xl p-8 text-center">
                <span className="text-4xl mb-3 block">📊</span>
                <p className="text-white/60">No results yet</p>
                <p className="text-sm text-white/40">Run an optimization to see results</p>
            </div>
        );
    }

    const margin = setonScore - opponentScore;
    const isWinning = margin > 0;

    const handleExport = async (format: 'csv' | 'html') => {
        try {
            addLog(`Exporting as ${format.toUpperCase()}...`);
            const blob = await api.exportResults(format, optimizationResults, {
                seton: setonScore,
                opponent: opponentScore,
            });

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `aquaforge_results.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            addLog(`✓ Downloaded ${format.toUpperCase()} file`);
        } catch (err) {
            addLog(`✗ Export failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
        }
    };

    return (
        <div className="space-y-4">
            {/* Score Banner */}
            <div className={`
        rounded-xl p-6 text-center
        ${isWinning
                    ? 'bg-gradient-to-r from-green-600/20 to-green-800/20 border border-green-500/30'
                    : 'bg-gradient-to-r from-red-600/20 to-red-800/20 border border-red-500/30'
                }
      `}>
                <p className="text-white/60 text-sm mb-2">Projected Score</p>
                <div className="flex items-center justify-center gap-4">
                    <div className="text-center">
                        <p className="text-3xl font-bold text-[#D4AF37]">{setonScore}</p>
                        <p className="text-xs text-white/50">Seton</p>
                    </div>
                    <span className="text-2xl text-white/30">—</span>
                    <div className="text-center">
                        <p className="text-3xl font-bold text-[#7C8B9A]">{opponentScore}</p>
                        <p className="text-xs text-white/50">Opponent</p>
                    </div>
                </div>
                <p className={`mt-2 font-semibold ${isWinning ? 'text-green-400' : 'text-red-400'}`}>
                    {isWinning ? `+${margin} Win` : `${margin} Loss`}
                </p>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
                <button
                    onClick={() => handleExport('csv')}
                    className="flex-1 py-2 px-4 rounded-lg bg-[#1a3a5c] text-white/80 hover:bg-[#1a3a5c]/80 transition-colors flex items-center justify-center gap-2"
                >
                    📥 Export CSV
                </button>
                <button
                    onClick={() => handleExport('html')}
                    className="flex-1 py-2 px-4 rounded-lg bg-[#1a3a5c] text-white/80 hover:bg-[#1a3a5c]/80 transition-colors flex items-center justify-center gap-2"
                >
                    📄 Export HTML
                </button>
                <button
                    onClick={clearResults}
                    className="py-2 px-4 rounded-lg bg-[#0C2340] text-white/40 hover:text-red-400 hover:bg-[#1a3a5c] transition-colors"
                    title="Clear results"
                >
                    🗑️
                </button>
            </div>

            {/* Results Table */}
            <div className="glass-card rounded-xl overflow-hidden">
                <table className="w-full">
                    <thead className="bg-[#0C2340]">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-white/50">#</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-white/50">Event</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-[#D4AF37]">Seton</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-[#7C8B9A]">Opponent</th>
                            <th className="px-4 py-3 text-center text-xs font-medium text-white/50">Score</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#1a3a5c]">
                        {optimizationResults.map((result, idx) => (
                            <tr key={idx} className="hover:bg-[#0C2340]/50 transition-colors">
                                <td className="px-4 py-3 text-sm text-white/50">{result.event_number}</td>
                                <td className="px-4 py-3 text-sm text-white font-medium">{result.event}</td>
                                <td className="px-4 py-3 text-sm text-[#D4AF37]">
                                    {result.seton_swimmers?.slice(0, 2).join(', ') || '-'}
                                </td>
                                <td className="px-4 py-3 text-sm text-[#7C8B9A]">
                                    {result.opponent_swimmers?.slice(0, 2).join(', ') || '-'}
                                </td>
                                <td className="px-4 py-3 text-center">
                                    <span className="text-[#D4AF37]">{result.projected_score?.seton || 0}</span>
                                    <span className="text-white/30 mx-1">-</span>
                                    <span className="text-[#7C8B9A]">{result.projected_score?.opponent || 0}</span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
