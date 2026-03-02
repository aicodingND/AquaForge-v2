"use client";

import { useAppStore } from "@/lib/store";
import { useShallow } from "zustand/react/shallow";
import Link from "next/link";

export default function AnalyticsPage() {
  const { setonTeam, opponentTeam, meetMode, championshipStandings, swingEvents } = useAppStore(useShallow(s => ({ setonTeam: s.setonTeam, opponentTeam: s.opponentTeam, meetMode: s.meetMode, championshipStandings: s.championshipStandings, swingEvents: s.swingEvents })));

  const isDual = meetMode === "dual";
  const hasTeams = isDual ? (setonTeam && opponentTeam) : !!setonTeam;

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Analytics</h1>
        <p className="text-white/50 text-sm mt-1">
          Team comparison and performance insights
        </p>
      </div>

      {!hasTeams ? (
        /* No Data State */
        <div className="glass-card p-12 text-center">
          <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-[var(--navy-600)] flex items-center justify-center">
            <span className="text-4xl">📈</span>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">
            No Data to Analyze
          </h2>
          <p className="text-white/50 mb-6 max-w-md mx-auto">
            Upload team files to see detailed analytics and comparisons.
          </p>
          <Link href="/meet" className="btn btn-gold">
            Go to Meet Setup →
          </Link>
        </div>
      ) : !isDual ? (
        /* Championship Analytics */
        <>
          {/* Team Overview */}
          <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--gold-400)] to-[var(--gold-500)] flex items-center justify-center font-bold text-[var(--navy-900)]">
                S
              </div>
              <div>
                <h3 className="font-semibold text-white">{setonTeam?.name || "Seton"}</h3>
                <p className="text-xs text-white/50">Championship Analysis</p>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-white/50 text-sm">Swimmers</p>
                <p className="text-white font-bold text-2xl">{setonTeam?.swimmerCount}</p>
              </div>
              <div>
                <p className="text-white/50 text-sm">Entries</p>
                <p className="text-white font-bold text-2xl">{setonTeam?.entryCount}</p>
              </div>
              <div>
                <p className="text-white/50 text-sm">Events</p>
                <p className="text-white font-bold text-2xl">{setonTeam?.events?.length}</p>
              </div>
              <div>
                <p className="text-white/50 text-sm">Teams in Meet</p>
                <p className="text-white font-bold text-2xl">{setonTeam?.teams?.length || "—"}</p>
              </div>
            </div>
          </div>

          {/* Championship Standings */}
          {championshipStandings && championshipStandings.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="p-4 border-b border-[var(--navy-500)]">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <span className="text-[var(--gold-400)]">🏆</span> Team Standings
                </h3>
              </div>
              <div className="divide-y divide-[var(--navy-600)]">
                {championshipStandings.map((team) => {
                  const isSeton = team.team === "SST" || team.team.toLowerCase().includes("seton");
                  return (
                    <div key={team.team} className={`flex items-center gap-4 p-4 ${isSeton ? "bg-[var(--gold-muted)]" : ""}`}>
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                        team.rank === 1 ? "bg-[var(--gold-500)] text-[var(--navy-900)]" :
                        team.rank === 2 ? "bg-gray-300 text-[var(--navy-900)]" :
                        team.rank === 3 ? "bg-amber-600 text-white" :
                        "bg-[var(--navy-600)] text-white/70"
                      }`}>
                        {team.rank}
                      </div>
                      <div className="flex-1">
                        <p className={`font-medium ${isSeton ? "text-[var(--gold-400)]" : "text-white"}`}>{team.team}</p>
                      </div>
                      <p className={`font-bold text-lg ${isSeton ? "text-[var(--gold-400)]" : "text-white"}`}>
                        {team.points.toFixed(1)} pts
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Coaching Insights — Swing Events */}
          {swingEvents && swingEvents.length > 0 && (
            <div className="glass-card overflow-hidden">
              <div className="p-4 border-b border-[var(--navy-500)]">
                <h3 className="font-semibold text-white flex items-center gap-2">
                  <span className="text-[var(--gold-400)]">💡</span> Where to Focus in Practice
                </h3>
                <p className="text-xs text-white/50 mt-1">Swimmers closest to moving up a scoring position</p>
              </div>
              <div className="divide-y divide-[var(--navy-600)]">
                {swingEvents.slice(0, 8).map((swing, i) => (
                  <div key={i} className="p-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium text-white">{swing.swimmer}</p>
                      <p className="text-sm text-white/50">{swing.event}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[var(--success)] font-bold">+{swing.point_gain?.toFixed(1)} pts</p>
                      <p className="text-xs text-white/50">#{swing.current_place} → #{swing.target_place}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No results yet — prompt to optimize */}
          {!championshipStandings && (
            <div className="glass-card p-8 text-center">
              <p className="text-white/50 mb-4">Run a championship optimization to see team standings and coaching insights.</p>
              <Link href="/optimize" className="btn btn-gold">Go to Optimizer →</Link>
            </div>
          )}
        </>
      ) : (
        <>
          {/* Dual Meet Team Comparison */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Seton Analysis */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--gold-400)] to-[var(--gold-500)] flex items-center justify-center font-bold text-[var(--navy-900)]">
                  S
                </div>
                <div>
                  <h3 className="font-semibold text-white">
                    {setonTeam?.name || "Seton"}
                  </h3>
                  <p className="text-xs text-white/50">Team Analysis</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Swimmers</span>
                  <span className="text-white font-bold text-lg">
                    {setonTeam?.swimmerCount}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Total Entries</span>
                  <span className="text-white font-bold text-lg">
                    {setonTeam?.entryCount}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Events Covered</span>
                  <span className="text-white font-bold text-lg">
                    {setonTeam?.events?.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Avg Entries/Swimmer</span>
                  <span className="text-white font-bold text-lg">
                    {setonTeam?.swimmerCount
                      ? (setonTeam.entryCount / setonTeam.swimmerCount).toFixed(
                          1,
                        )
                      : "—"}
                  </span>
                </div>
              </div>
            </div>

            {/* Opponent Analysis */}
            <div className="glass-card p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-[var(--navy-500)] flex items-center justify-center font-bold text-white/70">
                  O
                </div>
                <div>
                  <h3 className="font-semibold text-white">
                    {opponentTeam?.name || "Opponent"}
                  </h3>
                  <p className="text-xs text-white/50">Team Analysis</p>
                </div>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Swimmers</span>
                  <span className="text-white font-bold text-lg">
                    {opponentTeam?.swimmerCount}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Total Entries</span>
                  <span className="text-white font-bold text-lg">
                    {opponentTeam?.entryCount}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Events Covered</span>
                  <span className="text-white font-bold text-lg">
                    {opponentTeam?.events?.length}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Avg Entries/Swimmer</span>
                  <span className="text-white font-bold text-lg">
                    {opponentTeam?.swimmerCount
                      ? (
                          opponentTeam.entryCount / opponentTeam.swimmerCount
                        ).toFixed(1)
                      : "—"}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Event Coverage */}
          <div className="glass-card p-6">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <span className="text-[var(--gold-400)]">📊</span> Event Coverage
            </h3>

            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              {setonTeam?.events?.map((event, i) => {
                const opponentHas = opponentTeam?.events?.includes(event);
                return (
                  <div
                    key={i}
                    className={`p-3 rounded-lg text-center ${
                      opponentHas
                        ? "bg-[var(--success-muted)] border border-[var(--success)]"
                        : "bg-[var(--warning-muted)] border border-[var(--warning)]"
                    }`}
                  >
                    <p className="text-xs text-white/80 truncate">{event}</p>
                    <p className="text-xs mt-1 text-white/50">
                      {opponentHas ? "✓ Both" : "⚠ Seton only"}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Depth Comparison */}
          <div className="glass-card p-6">
            <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
              <span className="text-[var(--gold-400)]">📈</span> Team Depth
              Comparison
            </h3>

            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white/60">Roster Size</span>
                </div>
                <div className="flex gap-2 h-8">
                  <div
                    className="bg-gradient-to-r from-[var(--gold-500)] to-[var(--gold-400)] rounded-lg flex items-center justify-end px-3"
                    style={{
                      width: `${((setonTeam?.swimmerCount || 0) / Math.max(setonTeam?.swimmerCount || 1, opponentTeam?.swimmerCount || 1)) * 50}%`,
                    }}
                  >
                    <span className="text-xs font-bold text-[var(--navy-900)]">
                      {setonTeam?.swimmerCount}
                    </span>
                  </div>
                  <div
                    className="bg-[var(--navy-500)] rounded-lg flex items-center px-3"
                    style={{
                      width: `${((opponentTeam?.swimmerCount || 0) / Math.max(setonTeam?.swimmerCount || 1, opponentTeam?.swimmerCount || 1)) * 50}%`,
                    }}
                  >
                    <span className="text-xs font-medium text-white/70">
                      {opponentTeam?.swimmerCount}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-white/60">Total Entries</span>
                </div>
                <div className="flex gap-2 h-8">
                  <div
                    className="bg-gradient-to-r from-[var(--gold-500)] to-[var(--gold-400)] rounded-lg flex items-center justify-end px-3"
                    style={{
                      width: `${((setonTeam?.entryCount || 0) / Math.max(setonTeam?.entryCount || 1, opponentTeam?.entryCount || 1)) * 50}%`,
                    }}
                  >
                    <span className="text-xs font-bold text-[var(--navy-900)]">
                      {setonTeam?.entryCount}
                    </span>
                  </div>
                  <div
                    className="bg-[var(--navy-500)] rounded-lg flex items-center px-3"
                    style={{
                      width: `${((opponentTeam?.entryCount || 0) / Math.max(setonTeam?.entryCount || 1, opponentTeam?.entryCount || 1)) * 50}%`,
                    }}
                  >
                    <span className="text-xs font-medium text-white/70">
                      {opponentTeam?.entryCount}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center gap-8 mt-6 pt-4 border-t border-[var(--navy-500)]">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[var(--gold-500)]" />
                <span className="text-xs text-white/60">
                  {setonTeam?.name || "Seton"}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-[var(--navy-500)]" />
                <span className="text-xs text-white/60">
                  {opponentTeam?.name || "Opponent"}
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
