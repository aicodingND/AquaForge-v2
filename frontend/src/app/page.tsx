"use client";

import Link from "next/link";
import { useAppStore } from "@/lib/store";

export default function Dashboard() {
  const {
    setonTeam,
    opponentTeam,
    setonScore,
    opponentScore,
    optimizationResults,
    logs,
  } = useAppStore();

  const hasTeams = setonTeam && opponentTeam;
  const hasResults = optimizationResults && optimizationResults.length > 0;
  const scoreDelta = setonScore - opponentScore;
  const isWinning = scoreDelta > 0;
  const isTied = scoreDelta === 0 && hasResults;

  // Calculate quick stats
  const totalEvents = setonTeam?.events?.length || 0;

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-white/50 text-sm mt-1">
            Overview of your swim meet optimization
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/meet" className="btn btn-outline btn-sm">
            📋 Setup Meet
          </Link>
          <Link href="/optimize" className="btn btn-gold btn-sm">
            ⚡ Optimize
          </Link>
        </div>
      </div>

      {/* Hero Score Card */}
      {hasResults ? (
        <div className="score-hero animate-scale-in">
          <p className="text-white/60 text-sm uppercase tracking-wider mb-2">
            Meet Score
          </p>
          <div className="flex items-center justify-center gap-8">
            <div className="text-center">
              <p className="score-value">{setonScore}</p>
              <p className="text-white/70 mt-1">{setonTeam?.name || "Seton"}</p>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-3xl text-white/30">—</span>
              <div
                className={`badge mt-2 ${isWinning ? "badge-success" : isTied ? "badge-gold" : "badge-error"}`}
              >
                {isWinning ? `+${scoreDelta}` : isTied ? "TIE" : scoreDelta}
              </div>
            </div>
            <div className="text-center">
              <p className="text-4xl font-bold text-white/70">
                {opponentScore}
              </p>
              <p className="text-white/50 mt-1">
                {opponentTeam?.name || "Opponent"}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-card p-8 text-center animate-fade-in">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--gold-muted)] flex items-center justify-center border border-[var(--gold-500)] shadow-[var(--shadow-gold)]">
            <span className="text-3xl animate-pulse">🏊</span>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">
            Ready to Optimize
          </h2>
          <p className="text-white/50 mb-6 max-w-md mx-auto">
            Upload your team rosters and run optimization to see projected
            scores and optimal lineups.
          </p>
          <Link
            href="/meet"
            className="btn btn-gold shadow-[var(--shadow-gold)] hover:shadow-[var(--shadow-gold-lg)] transition-all"
          >
            Get Started →
          </Link>
        </div>
      )}

      {/* Quick Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="card-stat animate-fade-in stagger-1">
          <p className="text-xs text-white/50 uppercase tracking-wider">
            Seton Swimmers
          </p>
          <p className="text-2xl font-bold text-white mt-1">
            {setonTeam?.swimmerCount || 0}
          </p>
          {setonTeam && (
            <span className="badge badge-success text-xs mt-2">Loaded</span>
          )}
        </div>
        <div className="card-stat animate-fade-in stagger-2">
          <p className="text-xs text-white/50 uppercase tracking-wider">
            Opponent Swimmers
          </p>
          <p className="text-2xl font-bold text-white mt-1">
            {opponentTeam?.swimmerCount || 0}
          </p>
          {opponentTeam && (
            <span className="badge badge-success text-xs mt-2">Loaded</span>
          )}
        </div>
        <div className="card-stat animate-fade-in stagger-3">
          <p className="text-xs text-white/50 uppercase tracking-wider">
            Events
          </p>
          <p className="text-2xl font-bold text-white mt-1">{totalEvents}</p>
        </div>
        <div className="card-stat animate-fade-in stagger-4">
          <p className="text-xs text-white/50 uppercase tracking-wider">
            Status
          </p>
          <p className="text-2xl font-bold text-white mt-1">
            {hasResults ? "✓" : hasTeams ? "⏳" : "—"}
          </p>
          <span
            className={`badge text-xs mt-2 ${hasResults ? "badge-success" : hasTeams ? "badge-warning" : "badge-info"}`}
          >
            {hasResults ? "Optimized" : hasTeams ? "Ready" : "Setup Needed"}
          </span>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Team Cards Column */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-[var(--gold-400)]">👥</span> Teams
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Seton Team Card */}
            <div
              className={`glass-card p-5 ${setonTeam ? "border-l-4 border-l-[var(--gold-500)]" : ""}`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white">
                  {setonTeam?.name || "Seton Team"}
                </h3>
                {setonTeam ? (
                  <span className="badge badge-success">✓ Loaded</span>
                ) : (
                  <span className="badge badge-warning">Not loaded</span>
                )}
              </div>
              {setonTeam ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-white/60">
                    <span>Swimmers</span>
                    <span className="text-white font-medium">
                      {setonTeam.swimmerCount}
                    </span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Entries</span>
                    <span className="text-white font-medium">
                      {setonTeam.entryCount}
                    </span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>File</span>
                    <span className="text-white/80 truncate max-w-[150px]">
                      {setonTeam.filename}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-white/40 text-sm">
                  Upload Seton team file to get started
                </p>
              )}
            </div>

            {/* Opponent Team Card */}
            <div
              className={`glass-card p-5 ${opponentTeam ? "border-l-4 border-l-white/30" : ""}`}
            >
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white">
                  {opponentTeam?.name || "Opponent Team"}
                </h3>
                {opponentTeam ? (
                  <span className="badge badge-success">✓ Loaded</span>
                ) : (
                  <span className="badge badge-warning">Not loaded</span>
                )}
              </div>
              {opponentTeam ? (
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-white/60">
                    <span>Swimmers</span>
                    <span className="text-white font-medium">
                      {opponentTeam.swimmerCount}
                    </span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Entries</span>
                    <span className="text-white font-medium">
                      {opponentTeam.entryCount}
                    </span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>File</span>
                    <span className="text-white/80 truncate max-w-[150px]">
                      {opponentTeam.filename}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-white/40 text-sm">
                  Upload opponent team file
                </p>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          {hasTeams && !hasResults && (
            <div className="glass-card p-4 border-[var(--gold-500)] animate-pulse-gold">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">⚡</span>
                  <div>
                    <p className="font-medium text-white">Ready to Optimize</p>
                    <p className="text-sm text-white/50">
                      Both teams loaded successfully
                    </p>
                  </div>
                </div>
                <Link
                  href="/optimize"
                  className="btn btn-gold animate-pulse-gold"
                >
                  Run Optimization
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Activity Log Column */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-[var(--gold-400)]">📋</span> Activity
          </h2>

          <div className="glass-card p-4 h-[300px] flex flex-col">
            <div className="flex-1 overflow-y-auto space-y-2 font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-white/40">No activity yet...</p>
              ) : (
                logs.slice(-20).map((log, i) => (
                  <p key={i} className="text-white/60 leading-relaxed">
                    {log}
                  </p>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
