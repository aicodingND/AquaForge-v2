"use client";

import { useAppStore } from "@/lib/store";
import { useShallow } from "zustand/react/shallow";
import Link from "next/link";
import { useState, useEffect } from "react";

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
    sensitivity,
    relayAssignments,
    coachLockedEvents,
    excludedSwimmers,
    swimmerTimeOverrides,
    lockSwimmerEvent,
    unlockSwimmerEvent,
  } = useAppStore(useShallow(s => ({
    optimizationResults: s.optimizationResults,
    setonScore: s.setonScore,
    opponentScore: s.opponentScore,
    setonTeam: s.setonTeam,
    opponentTeam: s.opponentTeam,
    meetMode: s.meetMode,
    championshipStandings: s.championshipStandings,
    swingEvents: s.swingEvents,
    sensitivity: s.sensitivity,
    relayAssignments: s.relayAssignments,
    coachLockedEvents: s.coachLockedEvents,
    excludedSwimmers: s.excludedSwimmers,
    swimmerTimeOverrides: s.swimmerTimeOverrides,
    lockSwimmerEvent: s.lockSwimmerEvent,
    unlockSwimmerEvent: s.unlockSwimmerEvent,
  })));
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);
  const [previousScore, setPreviousScore] = useState<number | null>(null);

  const flatLockCount = coachLockedEvents.reduce((n, l) => n + l.events.length, 0);
  const isLocked = (swimmer: string, event: string) =>
    coachLockedEvents.some(l => l.swimmer === swimmer && l.events.includes(event));

  const hasResults = optimizationResults && optimizationResults.length > 0;
  const scoreDelta = setonScore - opponentScore;
  const isWinning = scoreDelta > 0;
  const isTied = scoreDelta === 0;
  const isChampionship = meetMode === "championship";

  // Fetch previous run for historical comparison
  useEffect(() => {
    if (!hasResults || !opponentTeam?.name) return;
    let cancelled = false;
    (async () => {
      try {
        const { api } = await import("@/lib/api");
        const history = await api.getHistory(opponentTeam.name, 1);
        if (!cancelled && history.runs.length > 0) {
          const prev = history.runs[0];
          const prevMargin = prev.our_score - prev.opponent_score;
          setPreviousScore(prevMargin);
        }
      } catch {
        // History not available, no-op
      }
    })();
    return () => { cancelled = true; };
  }, [hasResults, opponentTeam?.name]);

  const handleExport = async (format: "csv" | "html" | "pdf" | "xlsx") => {
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
      const ext = format === "xlsx" ? "xlsx" : format === "pdf" ? "pdf" : format;
      a.download = `aquaforge-results.${ext}`;
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
              Export CSV
            </button>
            <button
              onClick={() => handleExport("html")}
              className="btn btn-outline btn-sm"
            >
              Export HTML
            </button>
            <button
              onClick={() => handleExport("pdf")}
              className="btn btn-outline btn-sm"
            >
              Export PDF
            </button>
            <button
              onClick={() => handleExport("xlsx")}
              className="btn btn-outline btn-sm"
            >
              Export Excel
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
          {/* What-If Active Banner */}
          {(() => {
            const flatLocks = coachLockedEvents.flatMap(l => l.events.map(e => ({ swimmer: l.swimmer, event: e })));
            const totalMods = flatLocks.length + excludedSwimmers.length + swimmerTimeOverrides.length;
            if (totalMods === 0) return null;
            return (
              <div className="mb-4 p-3 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-start gap-3">
                <span className="text-blue-400 text-sm mt-0.5">&#9432;</span>
                <div className="text-sm">
                  <p className="text-blue-200 font-medium">What-If mode active</p>
                  <p className="text-white/50 text-xs mt-1">
                    {[
                      flatLocks.length > 0 && `${flatLocks.length} locked (${flatLocks.map(l => `${l.swimmer.split(" ").pop()} in ${l.event.replace(/^(Girls |Boys )/, "")}`).join(", ")})`,
                      excludedSwimmers.length > 0 && `${excludedSwimmers.length} excluded (${excludedSwimmers.join(", ")})`,
                      swimmerTimeOverrides.length > 0 && `${swimmerTimeOverrides.length} time override${swimmerTimeOverrides.length > 1 ? "s" : ""}`,
                    ].filter(Boolean).join(" · ")}
                  </p>
                  <Link href="/optimize" className="text-blue-400 text-xs hover:text-blue-300 mt-1 inline-block">
                    Modify in What-If panel &rarr;
                  </Link>
                </div>
              </div>
            );
          })()}

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
              <div className="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-12">
                <div className="text-center">
                  <p className="text-white/60 text-sm uppercase tracking-wider mb-1">
                    {setonTeam?.name || "Seton"}
                  </p>
                  <p className="score-value text-3xl sm:text-[4rem]">{setonScore}</p>
                </div>

                <div className="flex flex-col items-center">
                  <div
                    className={`text-2xl sm:text-4xl font-bold ${isWinning ? "text-[var(--success)]" : isTied ? "text-[var(--gold-400)]" : "text-[var(--error)]"}`}
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
                  {previousScore !== null && (() => {
                    const improvement = scoreDelta - previousScore;
                    if (Math.abs(improvement) < 0.1) return null;
                    const improved = improvement > 0;
                    return (
                      <div className={`mt-2 text-xs font-medium ${improved ? "text-green-400" : "text-red-400"}`}>
                        {improved ? "+" : ""}{improvement.toFixed(0)} vs last run
                      </div>
                    );
                  })()}
                </div>

                <div className="text-center">
                  <p className="text-white/60 text-sm uppercase tracking-wider mb-1">
                    {opponentTeam?.name || "Opponent"}
                  </p>
                  <p className="text-3xl sm:text-4xl font-bold text-white/70">
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

          {/* At Risk Assignments Summary */}
          {sensitivity && sensitivity.length > 0 && (() => {
            const atRisk = sensitivity.filter(s => s.risk_level === "at_risk");
            const competitive = sensitivity.filter(s => s.risk_level === "competitive");
            if (atRisk.length === 0 && competitive.length === 0) return null;
            return (
              <div className="glass-card overflow-hidden">
                <div className="p-4 border-b border-[var(--navy-500)]">
                  <h3 className="font-semibold text-white flex items-center gap-2">
                    <span className="text-red-400">!</span> Assignment Risk Summary
                  </h3>
                </div>
                <div className="p-4 space-y-2">
                  {atRisk.length > 0 && (
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                      <span className="w-3 h-3 mt-0.5 rounded-full bg-red-500 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-red-300">
                          {atRisk.length} At Risk ({`<`}0.5s gap)
                        </p>
                        <p className="text-xs text-white/50 mt-1">
                          {atRisk.map(s => `${s.swimmer} in ${s.event}`).join(", ")}
                        </p>
                      </div>
                    </div>
                  )}
                  {competitive.length > 0 && (
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                      <span className="w-3 h-3 mt-0.5 rounded-full bg-yellow-500 shrink-0" />
                      <div>
                        <p className="text-sm font-medium text-yellow-300">
                          {competitive.length} Competitive (0.5-2s gap)
                        </p>
                        <p className="text-xs text-white/50 mt-1">
                          {competitive.map(s => `${s.swimmer} in ${s.event}`).join(", ")}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })()}

          {/* Relay Team Compositions */}
          {relayAssignments && relayAssignments.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="p-4 border-b border-[var(--navy-500)]">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  Relay Teams
                </h3>
              </div>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 p-4">
                {relayAssignments.map((relay, i) => {
                  const isMedley = relay.relay_event.toLowerCase().includes("medley");
                  const legLabels = isMedley
                    ? ["Back", "Breast", "Fly", "Free"]
                    : ["Leg 1", "Leg 2", "Leg 3", "Leg 4"];
                  return (
                    <div key={i} className="p-4 rounded-lg bg-[var(--navy-800)] border border-[var(--navy-600)]">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium text-white text-sm">
                          {relay.relay_event}
                        </h4>
                        <span className="px-2 py-0.5 rounded text-xs font-bold bg-[var(--gold-500)] text-[var(--navy-900)]">
                          {relay.team}
                        </span>
                      </div>
                      <div className="space-y-1">
                        {relay.legs.map((swimmer, legIdx) => (
                          <div key={legIdx} className="flex items-center justify-between text-sm">
                            <span className="text-white/50">{legLabels[legIdx]}</span>
                            <span className="text-white font-medium">{swimmer}</span>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 pt-2 border-t border-[var(--navy-600)] text-right">
                        <span className="text-white/40 text-xs">Predicted: </span>
                        <span className="text-[var(--gold-400)] font-mono text-sm">
                          {relay.predicted_time.toFixed(2)}s
                        </span>
                      </div>
                    </div>
                  );
                })}
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
                          {result.seton_swimmers.map((swimmer, i) => {
                            const sens = sensitivity?.find(
                              s => s.swimmer === swimmer && s.event === result.event
                            );
                            const riskColor = sens?.risk_level === "at_risk"
                              ? "bg-red-500"
                              : sens?.risk_level === "competitive"
                                ? "bg-yellow-500"
                                : "bg-green-500";
                            const locked = isLocked(swimmer, result.event);
                            return (
                              <div
                                key={i}
                                className={`flex items-center justify-between py-1.5 px-2 -mx-2 rounded transition-colors ${locked ? "bg-blue-500/10" : "hover:bg-white/3"}`}
                              >
                                <span className="text-white text-sm flex items-center gap-2">
                                  {sens && (
                                    <span
                                      className={`w-2 h-2 rounded-full ${riskColor}`}
                                      title={`${sens.risk_level}: gap ${sens.gap_to_next_place?.toFixed(2) ?? "?"}s`}
                                    />
                                  )}
                                  {swimmer}
                                  {locked && (
                                    <span className="text-blue-400 text-[10px] uppercase tracking-wider font-bold">
                                      locked
                                    </span>
                                  )}
                                </span>
                                <span className="flex items-center gap-2">
                                  <span className="text-white/60 font-mono text-sm">
                                    {result.seton_times[i]}
                                    {sens?.gap_to_next_place != null && (
                                      <span className={`ml-2 text-xs ${sens.risk_level === "at_risk" ? "text-red-400" : sens.risk_level === "competitive" ? "text-yellow-400" : "text-green-400"}`}>
                                        +{sens.gap_to_next_place.toFixed(2)}s
                                      </span>
                                    )}
                                  </span>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      if (locked) {
                                        unlockSwimmerEvent(swimmer, result.event);
                                      } else {
                                        lockSwimmerEvent(swimmer, result.event);
                                      }
                                    }}
                                    disabled={!locked && flatLockCount >= 3}
                                    title={
                                      locked
                                        ? `Unlock ${swimmer} from ${result.event}`
                                        : flatLockCount >= 3
                                          ? "Max 3 locks reached"
                                          : `Lock ${swimmer} into ${result.event}`
                                    }
                                    className={`w-6 h-6 rounded flex items-center justify-center transition-colors ${
                                      locked
                                        ? "bg-blue-500/30 text-blue-300 hover:bg-blue-500/50"
                                        : flatLockCount >= 3
                                          ? "text-white/10 cursor-not-allowed"
                                          : "text-white/20 hover:text-white/50 hover:bg-white/5"
                                    }`}
                                  >
                                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      {locked ? (
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                      ) : (
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
                                      )}
                                    </svg>
                                  </button>
                                </span>
                              </div>
                            );
                          })}
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
