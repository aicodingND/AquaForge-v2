"use client";

import { useAppStore } from "@/lib/store";
import Link from "next/link";
import { useState } from "react";

export default function ResultsPage() {
  const {
    optimizationResults,
    setonScore,
    opponentScore,
    setonTeam,
    opponentTeam,
    meetMode,
    championshipStandings,
    swingEvents,
  } = useAppStore();
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);

  const hasResults = optimizationResults && optimizationResults.length > 0;
  const scoreDelta = setonScore - opponentScore;
  const isWinning = scoreDelta > 0;
  const isTied = scoreDelta === 0;
  const isChampionship = meetMode === "championship";

  const handleExport = async (format: "csv" | "html") => {
    if (!optimizationResults) return;

    try {
      const { api } = await import("@/lib/api");
      const blob = await api.exportResults(format, optimizationResults, {
        seton: setonScore,
        opponent: opponentScore,
      });

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `aquaforge-results.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  // Find Seton's rank in championship standings
  const setonRank =
    championshipStandings?.find(
      (t) => t.team === "SST" || t.team.toLowerCase().includes("seton"),
    )?.rank || 1;

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Results</h1>
          <p className="text-white/50 text-sm mt-1">
            {isChampionship
              ? "Championship projections and team standings"
              : "Optimization results and lineup assignments"}
          </p>
        </div>

        {hasResults && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport("csv")}
              className="btn btn-outline btn-sm"
            >
              📄 Export CSV
            </button>
            <button
              onClick={() => handleExport("html")}
              className="btn btn-outline btn-sm"
            >
              🌐 Export HTML
            </button>
          </div>
        )}
      </div>

      {!hasResults ? (
        /* No Results State */
        <div className="glass-card p-12 text-center">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-[var(--navy-600)] flex items-center justify-center">
            <span className="text-4xl">📊</span>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">
            No Results Yet
          </h2>
          <p className="text-white/50 mb-6 max-w-md mx-auto">
            Run an optimization to see detailed results and lineup assignments.
          </p>
          <Link href="/optimize" className="btn btn-gold">
            Go to Optimizer →
          </Link>
        </div>
      ) : (
        <>
          {/* Score Hero - Different layout for Championship vs Dual */}
          {isChampionship ? (
            <div className="score-hero">
              <div className="flex flex-col items-center gap-4">
                {/* Main Optimized Score */}
                <div className="text-center">
                  <p className="text-white/60 text-sm uppercase tracking-wider mb-1">
                    {setonTeam?.name || "Seton"} — Optimized Individual Events
                  </p>
                  <p className="score-value">{setonScore}</p>
                  <p className="text-xs text-white/40 mt-1">
                    Points from individual swims (excludes relays & diving)
                  </p>
                </div>

                {/* Standing & Full Projected */}
                <div className="flex items-center gap-6 mt-2">
                  <div className="badge badge-gold">
                    #{setonRank} of {championshipStandings?.length || "?"} teams
                  </div>

                  {/* Show full projected score if different from optimization */}
                  {championshipStandings &&
                    (() => {
                      const setonStanding = championshipStandings.find(
                        (t) =>
                          t.team === "SST" ||
                          t.team.toLowerCase().includes("seton"),
                      );
                      if (
                        setonStanding &&
                        Math.abs(setonStanding.points - setonScore) > 0.1
                      ) {
                        return (
                          <div className="text-center px-4 py-2 bg-[var(--navy-700)] rounded-lg">
                            <p className="text-xs text-white/50 uppercase">
                              Full Projected
                            </p>
                            <p className="text-lg font-bold text-white">
                              {setonStanding.points.toFixed(0)}
                            </p>
                            <p className="text-xs text-white/40">
                              incl. relays & diving
                            </p>
                          </div>
                        );
                      }
                      return null;
                    })()}
                </div>
              </div>
            </div>
          ) : (
            <div className="score-hero">
              <div className="flex items-center justify-center gap-12">
                <div className="text-center">
                  <p className="text-white/60 text-sm uppercase tracking-wider mb-1">
                    {setonTeam?.name || "Seton"}
                  </p>
                  <p className="score-value">{setonScore}</p>
                </div>

                <div className="flex flex-col items-center">
                  <div
                    className={`text-4xl font-bold ${isWinning ? "text-[var(--success)]" : isTied ? "text-[var(--gold-400)]" : "text-[var(--error)]"}`}
                  >
                    {isWinning ? "WIN" : isTied ? "TIE" : "LOSS"}
                  </div>
                  <div
                    className={`badge mt-2 ${isWinning ? "badge-success" : isTied ? "badge-gold" : "badge-error"}`}
                  >
                    {isWinning
                      ? `+${scoreDelta}`
                      : scoreDelta === 0
                        ? "Even"
                        : scoreDelta}{" "}
                    points
                  </div>
                </div>

                <div className="text-center">
                  <p className="text-white/60 text-sm uppercase tracking-wider mb-1">
                    {opponentTeam?.name || "Opponent"}
                  </p>
                  <p className="text-4xl font-bold text-white/70">
                    {opponentScore}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Championship Team Standings */}
          {isChampionship &&
            championshipStandings &&
            championshipStandings.length > 0 && (
              <div className="glass-card overflow-hidden">
                <div className="p-4 border-b border-[var(--navy-500)]">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <span className="text-[var(--gold-400)]">🏆</span> Projected Team
                    Standings
                  </h3>
                </div>
                <div className="divide-y divide-[var(--navy-600)]">
                  {championshipStandings.map((team) => {
                    const isSeton =
                      team.team === "SST" ||
                      team.team.toLowerCase().includes("seton");
                    return (
                      <div
                        key={team.team}
                        className={`flex items-center gap-4 p-4 ${isSeton ? "bg-[var(--gold-muted)]" : "hover:bg-white/2"}`}
                      >
                        <div
                          className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                            team.rank === 1
                              ? "bg-[var(--gold-500)] text-[var(--navy-900)]"
                              : team.rank === 2
                                ? "bg-gray-300 text-[var(--navy-900)]"
                                : team.rank === 3
                                  ? "bg-amber-600 text-white"
                                  : "bg-[var(--navy-600)] text-white/70"
                          }`}
                        >
                          {team.rank}
                        </div>
                        <div className="flex-1">
                          <p
                            className={`font-medium ${isSeton ? "text-[var(--gold-400)]" : "text-white"}`}
                          >
                            {team.team}
                          </p>
                        </div>
                        <div className="text-right">
                          <p
                            className={`font-bold text-lg ${isSeton ? "text-[var(--gold-400)]" : "text-white"}`}
                          >
                            {team.points.toFixed(1)}
                          </p>
                          <p className="text-xs text-white/50">points</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

          {/* Swing Events (Championship mode) */}
          {isChampionship && swingEvents && swingEvents.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="p-4 border-b border-[var(--navy-500)]">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <span className="text-[var(--gold-400)]">💡</span> Swing Events
                  (Improvement Opportunities)
                </h3>
              </div>
              <div className="divide-y divide-[var(--navy-600)]">
                {(
                  swingEvents as Array<{
                    swimmer?: string;
                    event?: string;
                    point_gain?: number;
                    current_place?: number;
                    target_place?: number;
                  }>
                )
                  .slice(0, 5)
                  .map(
                    (
                      swing: {
                        swimmer?: string;
                        event?: string;
                        point_gain?: number;
                        current_place?: number;
                        target_place?: number;
                      },
                      index,
                    ) => (
                      <div key={index} className="p-4 hover:bg-white/2">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-white">
                              {swing.swimmer}
                            </p>
                            <p className="text-sm text-white/50">
                              {swing.event}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-[var(--success)] font-bold">
                              +{swing.point_gain?.toFixed(1) || "?"} pts
                            </p>
                            <p className="text-xs text-white/50">
                              Move #{swing.current_place} → #
                              {swing.target_place}
                            </p>
                          </div>
                        </div>
                      </div>
                    ),
                  )}
              </div>
            </div>
          )}

          {/* Event Results Table */}
          <div className="glass-card overflow-hidden">
            <div className="p-4 border-b border-[var(--navy-500)]">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <span className="text-[var(--gold-400)]">🏊</span>
                {isChampionship ? "Event Entries & Points" : "Event Results"}
              </h3>
            </div>

            <div className="divide-y divide-[var(--navy-600)]">
              {optimizationResults.map((result, index) => (
                <div key={index} className="hover:bg-white/2 transition-colors">
                  {/* Event Header */}
                  <button
                    onClick={() =>
                      setExpandedEvent(expandedEvent === index ? null : index)
                    }
                    className="w-full p-4 flex items-center gap-4 text-left"
                    aria-label={`Toggle details for ${result.event}`}
                  >
                    <div className="w-8 h-8 rounded-full bg-[var(--navy-600)] flex items-center justify-center text-sm font-medium text-white/70">
                      {result.event_number}
                    </div>

                    <div className="flex-1">
                      <p className="font-medium text-white">{result.event}</p>
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <p className="text-[10px] text-white/40 uppercase tracking-wider mb-0.5">
                          Event Pts
                        </p>
                        <span className="text-[var(--gold-400)] font-bold text-lg">
                          {result.projected_score.seton}
                        </span>
                        {!isChampionship && (
                          <>
                            <span className="text-white/30 mx-2">—</span>
                            <span className="text-white/70 text-lg">
                              {result.projected_score.opponent}
                            </span>
                          </>
                        )}
                      </div>

                      <div
                        className={`w-6 h-6 rounded flex items-center justify-center text-xs transition-transform ${expandedEvent === index ? "rotate-180" : ""}`}
                      >
                        ▼
                      </div>
                    </div>
                  </button>

                  {/* Expanded Details */}
                  {expandedEvent === index && (
                    <div className="px-4 pb-4 animate-fade-in">
                      <div
                        className={`${isChampionship ? "" : "grid grid-cols-2 gap-4"} p-4 bg-[var(--navy-800)] rounded-lg`}
                      >
                        <div>
                          <p className="text-xs text-[var(--gold-400)] uppercase tracking-wider mb-2">
                            {setonTeam?.name || "Seton"} Entries
                          </p>
                          {result.seton_swimmers.map((swimmer, i) => (
                            <div
                              key={i}
                              className="flex items-center justify-between py-1"
                            >
                              <span className="text-white text-sm">
                                {swimmer}
                              </span>
                              <span className="text-white/60 font-mono text-sm">
                                {result.seton_times[i]}
                              </span>
                            </div>
                          ))}
                        </div>
                        {!isChampionship && (
                          <div>
                            <p className="text-xs text-white/60 uppercase tracking-wider mb-2">
                              {opponentTeam?.name || "Opponent"}
                            </p>
                            {result.opponent_swimmers.map((swimmer, i) => (
                              <div
                                key={i}
                                className="flex items-center justify-between py-1"
                              >
                                <span className="text-white/70 text-sm">
                                  {swimmer}
                                </span>
                                <span className="text-white/50 font-mono text-sm">
                                  {result.opponent_times[i]}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
