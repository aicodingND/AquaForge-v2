'use client';

import { useState, useMemo } from 'react';
import { useAppStore } from '@/lib/store';
import { OptimizationResult } from '@/lib/api';

interface OptimizationRun {
  id: string;
  label: string;
  backend: string;
  timestamp: number;
  results: OptimizationResult[];
  setonScore: number;
  opponentScore: number;
}

export default function ComparisonView() {
  const { optimizationResults, setonScore, opponentScore } = useAppStore();

  const [history, setHistory] = useState<OptimizationRun[]>([]);
  const [selectedRuns, setSelectedRuns] = useState<string[]>([]);

  // Snapshot the current optimization into history
  const handleSnapshot = () => {
    if (!optimizationResults || optimizationResults.length === 0) return;

    const run: OptimizationRun = {
      id: `run-${Date.now()}`,
      label: `Run #${history.length + 1}`,
      backend: 'optimizer',
      timestamp: Date.now(),
      results: optimizationResults,
      setonScore,
      opponentScore,
    };

    setHistory((prev) => {
      const next = [...prev, run];
      // Keep at most 5 runs
      return next.slice(-5);
    });
  };

  const handleClearHistory = () => {
    setHistory([]);
    setSelectedRuns([]);
  };

  const toggleRunSelection = (runId: string) => {
    setSelectedRuns((prev) => {
      if (prev.includes(runId)) {
        return prev.filter((id) => id !== runId);
      }
      // Max 3 selections
      if (prev.length >= 3) {
        return [...prev.slice(1), runId];
      }
      return [...prev, runId];
    });
  };

  // Runs being compared (up to 3)
  const comparedRuns = useMemo(() => {
    return history.filter((r) => selectedRuns.includes(r.id));
  }, [history, selectedRuns]);

  // Build unified event list across all compared runs
  const allEvents = useMemo(() => {
    const eventSet = new Set<string>();
    comparedRuns.forEach((run) => {
      run.results.forEach((r) => eventSet.add(r.event));
    });
    return Array.from(eventSet).sort();
  }, [comparedRuns]);

  // Compute per-event comparison data
  const eventComparison = useMemo(() => {
    return allEvents.map((event) => {
      const runScores = comparedRuns.map((run) => {
        const result = run.results.find((r) => r.event === event);
        return {
          runId: run.id,
          seton: result?.projected_score?.seton ?? 0,
          opponent: result?.projected_score?.opponent ?? 0,
          setonSwimmers: result?.seton_swimmers ?? [],
        };
      });

      // Check if all runs have the same Seton score for this event
      const allSame =
        runScores.length > 1 &&
        runScores.every((s) => s.seton === runScores[0].seton && s.opponent === runScores[0].opponent);

      return { event, runScores, differs: !allSame };
    });
  }, [allEvents, comparedRuns]);

  // Empty state
  if (!optimizationResults || optimizationResults.length === 0) {
    return (
      <div className="glass-card rounded-xl p-8 text-center">
        <svg
          className="w-10 h-10 mx-auto mb-3 text-white/30"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7"
          />
        </svg>
        <p className="text-white/60">No comparison available</p>
        <p className="text-sm text-white/40">
          Run optimizations and save snapshots to compare
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="glass-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <svg
              className="w-5 h-5 text-[#D4AF37]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"
              />
            </svg>
            Lineup Comparison
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSnapshot}
              className="px-3 py-1.5 rounded-lg text-sm font-medium bg-gradient-to-r from-[#D4AF37] to-[#C99700] text-[#091A30] hover:shadow-lg hover:shadow-[#C99700]/30 transition-all"
            >
              Save Current
            </button>
            {history.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="px-3 py-1.5 rounded-lg text-sm font-medium bg-[#1a3a5c] text-white/60 hover:text-red-400 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Run selection chips */}
        {history.length === 0 ? (
          <p className="text-sm text-white/40">
            Save optimization runs to compare them side-by-side. Click "Save
            Current" after each optimization.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {history.map((run) => {
              const isSelected = selectedRuns.includes(run.id);
              const margin = run.setonScore - run.opponentScore;
              const isWin = margin > 0;

              return (
                <button
                  key={run.id}
                  onClick={() => toggleRunSelection(run.id)}
                  className={`
                    flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all border
                    ${isSelected
                      ? 'bg-[#D4AF37]/15 border-[#D4AF37]/40 text-[#D4AF37]'
                      : 'bg-[#0C2340]/50 border-white/10 text-white/60 hover:border-white/20'
                    }
                  `}
                >
                  <span className="font-medium">{run.label}</span>
                  <span
                    className={`text-xs ${isWin ? 'text-green-400' : 'text-red-400'}`}
                  >
                    {run.setonScore}-{run.opponentScore}
                  </span>
                  <span className="text-xs text-white/30">
                    {new Date(run.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {selectedRuns.length > 0 && selectedRuns.length < 2 && (
          <p className="text-xs text-white/30 mt-2">
            Select at least 2 runs to compare
          </p>
        )}
      </div>

      {/* Comparison Table */}
      {comparedRuns.length >= 2 && (
        <div className="glass-card rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#0C2340]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-white/50">
                    Event
                  </th>
                  {comparedRuns.map((run) => (
                    <th
                      key={run.id}
                      className="px-4 py-3 text-center text-xs font-medium text-[#D4AF37]"
                    >
                      <div>{run.label}</div>
                      <div className="text-white/30 font-normal mt-0.5">
                        {run.backend}
                      </div>
                    </th>
                  ))}
                  {comparedRuns.length === 2 && (
                    <th className="px-4 py-3 text-center text-xs font-medium text-white/50">
                      Diff
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1a3a5c]">
                {eventComparison.map(({ event, runScores, differs }) => (
                  <tr
                    key={event}
                    className={`
                      transition-colors
                      ${differs
                        ? 'bg-amber-500/5 hover:bg-amber-500/10'
                        : 'hover:bg-[#0C2340]/50'
                      }
                    `}
                  >
                    <td className="px-4 py-3 text-sm text-white font-medium">
                      {event}
                    </td>
                    {runScores.map((score) => (
                      <td
                        key={score.runId}
                        className="px-4 py-3 text-center text-sm"
                      >
                        <span className="text-[#D4AF37]">{score.seton}</span>
                        <span className="text-white/30 mx-1">-</span>
                        <span className="text-[#7C8B9A]">
                          {score.opponent}
                        </span>
                      </td>
                    ))}
                    {comparedRuns.length === 2 && (
                      <td className="px-4 py-3 text-center text-sm">
                        {differs ? (
                          <DiffBadge
                            a={runScores[0]?.seton - runScores[0]?.opponent}
                            b={runScores[1]?.seton - runScores[1]?.opponent}
                          />
                        ) : (
                          <span className="text-white/20 text-xs">same</span>
                        )}
                      </td>
                    )}
                  </tr>
                ))}

                {/* Total row */}
                <tr className="bg-[#0C2340] font-semibold">
                  <td className="px-4 py-3 text-sm text-white">TOTAL</td>
                  {comparedRuns.map((run) => (
                    <td
                      key={run.id}
                      className="px-4 py-3 text-center text-sm"
                    >
                      <span className="text-[#D4AF37]">{run.setonScore}</span>
                      <span className="text-white/30 mx-1">-</span>
                      <span className="text-[#7C8B9A]">
                        {run.opponentScore}
                      </span>
                    </td>
                  ))}
                  {comparedRuns.length === 2 && (
                    <td className="px-4 py-3 text-center text-sm">
                      <DiffBadge
                        a={
                          comparedRuns[0].setonScore -
                          comparedRuns[0].opponentScore
                        }
                        b={
                          comparedRuns[1].setonScore -
                          comparedRuns[1].opponentScore
                        }
                      />
                    </td>
                  )}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Legend (when comparing) */}
      {comparedRuns.length >= 2 && (
        <div className="flex items-center gap-4 text-xs text-white/30 px-1">
          <span className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-amber-500/10 border border-amber-500/20" />
            Events with different results
          </span>
        </div>
      )}
    </div>
  );
}

/** Small badge showing the net point difference between two run margins. */
function DiffBadge({ a, b }: { a: number; b: number }) {
  const diff = b - a;
  if (diff === 0) {
    return <span className="text-white/20 text-xs">same</span>;
  }
  return (
    <span
      className={`
        text-xs font-semibold px-1.5 py-0.5 rounded
        ${diff > 0
          ? 'text-green-400 bg-green-500/10'
          : 'text-red-400 bg-red-500/10'
        }
      `}
    >
      {diff > 0 ? '+' : ''}
      {diff} pts
    </span>
  );
}
