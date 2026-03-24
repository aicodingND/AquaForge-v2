"use client";

import { useState } from "react";
import { useAppStore } from "@/lib/store";
import { useShallow } from "zustand/react/shallow";
import { api } from "@/lib/api";
import Link from "next/link";
import BackendSelector from "@/components/BackendSelector";
import ChampionshipStrategySelector from "@/components/ChampionshipStrategySelector";
import WhatIfPanel from "@/components/WhatIfPanel";

export default function OptimizePage() {
  const {
    setonTeam,
    opponentTeam,
    meetMode,
    isOptimizing,
    selectedBackend,
    enforceFatigue,
    robustMode,
    scoringType,
    coachLockedEvents,
    excludedSwimmers,
    swimmerTimeOverrides,
    setOptimizing,
    setResults,
    setOptimizerSettings,
    addLog,
  } = useAppStore(useShallow(s => ({
    setonTeam: s.setonTeam,
    opponentTeam: s.opponentTeam,
    meetMode: s.meetMode,
    isOptimizing: s.isOptimizing,
    selectedBackend: s.selectedBackend,
    enforceFatigue: s.enforceFatigue,
    robustMode: s.robustMode,
    scoringType: s.scoringType,
    coachLockedEvents: s.coachLockedEvents,
    excludedSwimmers: s.excludedSwimmers,
    swimmerTimeOverrides: s.swimmerTimeOverrides,
    setOptimizing: s.setOptimizing,
    setResults: s.setResults,
    setOptimizerSettings: s.setOptimizerSettings,
    addLog: s.addLog,
  })));
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [localResult, setLocalResult] = useState<{
    seton: number;
    opponent: number;
  } | null>(null);
  const [championshipStrategy, setChampionshipStrategy] =
    useState<string>("aqua");

  const canOptimize =
    meetMode === "championship"
      ? !!setonTeam && !isOptimizing
      : !!setonTeam && !!opponentTeam && !isOptimizing;

  const handleOptimize = async () => {
    if (!canOptimize || !setonTeam) return;

    if (!setonTeam.data || setonTeam.data.length === 0) {
      setError("Seton team data is empty. Please re-upload.");
      return;
    }

    if (
      meetMode === "dual" &&
      (!opponentTeam?.data || opponentTeam.data.length === 0)
    ) {
      setError("Opponent team data is empty. Please re-upload.");
      return;
    }

    setOptimizing(true);
    setProgress(0);
    setError(null);
    addLog(`🚀 Starting ${meetMode} optimization...`);

    try {
      setProgress(20);

      // Build locked assignments from store (flatten CoachLockEntry[] to {swimmer, event}[])
      const lockedAssignments = coachLockedEvents.flatMap(lock =>
        lock.events.map(event => ({ swimmer: lock.swimmer, event }))
      );

      const data = await api.optimize({
        seton_data: setonTeam.data,
        opponent_data: meetMode === "dual" ? opponentTeam?.data || [] : [],
        optimizer_backend: selectedBackend,
        enforce_fatigue: enforceFatigue,
        robust_mode: meetMode === "dual" ? robustMode : false,
        scoring_type: scoringType,
        strategy:
          meetMode === "championship" ? championshipStrategy : undefined,
        locked_assignments: lockedAssignments.length > 0 ? lockedAssignments : undefined,
        excluded_swimmers: excludedSwimmers.length > 0 ? excludedSwimmers : undefined,
        time_overrides: swimmerTimeOverrides.length > 0 ? swimmerTimeOverrides : undefined,
      });

      setProgress(100);

      // Debug logging for championship mode
      if (meetMode === "championship") {
        console.log("🏆 Championship Response:", {
          success: data.success,
          seton_score: data.seton_score,
          has_standings: !!data.championship_standings,
          num_teams: data.championship_standings?.length || 0,
          standings_preview: data.championship_standings?.slice(0, 3),
        });
      }

      if (data.success) {
        // Pass championship-specific data if available
        setResults(
          data.results,
          data.seton_score,
          data.opponent_score,
          meetMode === "championship"
            ? {
                standings: data.championship_standings,
                eventBreakdowns: data.event_breakdowns,
                swingEvents: data.swing_events,
              }
            : undefined,
          data.sensitivity,
          data.relay_assignments,
        );
        setLocalResult({
          seton: data.seton_score,
          opponent: data.opponent_score,
        });
        addLog(
          meetMode === "championship"
            ? `✓ Projected Score: ${data.seton_score} points`
            : `✓ Score: ${data.seton_score} - ${data.opponent_score}`,
        );
      } else {
        throw new Error("Optimization failed");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
      addLog(`✗ Error: ${message}`);
    } finally {
      setOptimizing(false);
    }
  };

  const setScoring = (
    scoring:
      | "visaa_top7"
      | "standard_top5"
      | "vcac_championship"
      | "visaa_state",
  ) => setOptimizerSettings({ scoring });
  const toggleFatigue = () =>
    setOptimizerSettings({ fatigue: !enforceFatigue });
  const toggleRobust = () =>
    setOptimizerSettings({ robust: !robustMode });

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header — Mode-specific labeling */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {meetMode === "championship" ? "🏆 Championship Optimizer" : "⚡ Dual Meet Optimizer"}
          </h1>
          <p className="text-white/50 text-sm mt-1">
            {meetMode === "championship"
              ? "Optimize entries across all events for maximum team score"
              : "Configure head-to-head lineup optimization"}
          </p>
        </div>
        <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider ${
          meetMode === "dual"
            ? "bg-blue-500/20 text-blue-300 border border-blue-400/30"
            : "bg-purple-500/20 text-purple-300 border border-purple-400/30"
        }`}>
          <span className="w-2 h-2 rounded-full bg-current" />
          {meetMode === "dual" ? "Dual Meet" : "Championship"}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Settings Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Engine - Now using dynamic BackendSelector */}
          <BackendSelector />

          {/* Championship Strategy Selector - Only in championship mode */}
          {meetMode === "championship" && (
            <div className="glass-card p-6">
              <ChampionshipStrategySelector
                selectedStrategy={championshipStrategy}
                onStrategyChange={setChampionshipStrategy}
                disabled={isOptimizing}
              />
            </div>
          )}

          {/* Scoring */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              ⚖️ Scoring System
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {meetMode === "dual" ? (
                <>
                  <button
                    onClick={() => setScoring("visaa_top7")}
                    className={`px-4 py-3 rounded-lg text-sm font-medium ${scoringType === "visaa_top7" ? "bg-[var(--gold-500)] text-[var(--navy-900)]" : "bg-[var(--navy-700)] text-white/60"}`}
                  >
                    VISAA (Top 7)
                  </button>
                  <button
                    onClick={() => setScoring("standard_top5")}
                    className={`px-4 py-3 rounded-lg text-sm font-medium ${scoringType === "standard_top5" ? "bg-[var(--gold-500)] text-[var(--navy-900)]" : "bg-[var(--navy-700)] text-white/60"}`}
                  >
                    Standard (Top 5)
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setScoring("vcac_championship")}
                    className={`px-4 py-3 rounded-lg text-sm font-medium ${scoringType === "vcac_championship" ? "bg-[var(--gold-500)] text-[var(--navy-900)]" : "bg-[var(--navy-700)] text-white/60"}`}
                  >
                    VCAC (Top 12)
                  </button>
                  <button
                    onClick={() => setScoring("visaa_state")}
                    className={`px-4 py-3 rounded-lg text-sm font-medium ${scoringType === "visaa_state" ? "bg-[var(--gold-500)] text-[var(--navy-900)]" : "bg-[var(--navy-700)] text-white/60"}`}
                  >
                    VISAA State (Top 16)
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Constraints */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              ⛓️ Constraints
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--navy-800)]">
                <div>
                  <p className="text-white font-medium text-sm">
                    Fatigue Management
                  </p>
                  <p className="text-xs text-white/50">
                    Prevent back-to-back events
                  </p>
                </div>
                <button
                  onClick={toggleFatigue}
                  aria-label={
                    enforceFatigue
                      ? "Disable fatigue constraints"
                      : "Enable fatigue constraints"
                  }
                  className={`w-12 h-6 rounded-full transition-colors ${enforceFatigue ? "bg-[var(--gold-500)]" : "bg-[var(--navy-500)]"}`}
                >
                  <div
                    className={`w-5 h-5 rounded-full bg-white transition-transform ${enforceFatigue ? "translate-x-6" : "translate-x-1"}`}
                  />
                </button>
              </div>
              {meetMode === "dual" && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--navy-800)]">
                  <div>
                    <p className="text-white font-medium text-sm">
                      Robust Mode
                    </p>
                    <p className="text-xs text-white/50">
                      Optimize for worst-case
                    </p>
                  </div>
                  <button
                    onClick={toggleRobust}
                    aria-label={
                      robustMode ? "Disable robust mode" : "Enable robust mode"
                    }
                    title={
                      robustMode ? "Disable robust mode" : "Enable robust mode"
                    }
                    className={`w-12 h-6 rounded-full transition-colors ${robustMode ? "bg-[var(--gold-500)]" : "bg-[var(--navy-500)]"}`}
                  >
                    <div
                      className={`w-5 h-5 rounded-full bg-white transition-transform ${robustMode ? "translate-x-6" : "translate-x-1"}`}
                    />
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* What-If Panel */}
          <WhatIfPanel />
        </div>

        {/* Action Panel */}
        <div>
          <div className="glass-card p-6 sticky top-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              ⚡ Run Optimization
            </h3>

            {/* Team Summary */}
            <div className="space-y-2 mb-6 bg-[var(--navy-800)] p-4 rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <span className="text-white/60">Seton</span>
                <span className="text-white font-medium">
                  {setonTeam?.swimmerCount || 0} swimmers
                </span>
              </div>
              {meetMode === "dual" && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white/60">Opponent</span>
                  <span className="text-white font-medium">
                    {opponentTeam?.swimmerCount || 0} swimmers
                  </span>
                </div>
              )}
            </div>

            {/* Progress */}
            {isOptimizing && (
              <div className="mb-4">
                <div className="flex justify-between text-xs text-white/50 mb-1">
                  <span>Processing...</span>
                  <span>{progress}%</span>
                </div>
                <div className="h-2 bg-[var(--navy-600)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[var(--gold-400)] to-[var(--gold-500)] transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30">
                <p className="text-red-400 text-sm">{error}</p>
              </div>
            )}

            {/* Success */}
            {localResult && (
              <div className="mb-4 p-4 rounded-lg bg-[var(--gold-muted)] border border-[var(--gold-500)]">
                {meetMode === "championship" ? (
                  <>
                    <p className="text-white font-bold text-2xl text-center">
                      {localResult.seton}
                    </p>
                    <p className="text-white/60 text-sm text-center">
                      Projected Score
                    </p>
                  </>
                ) : (
                  <>
                    <p className="text-white font-bold text-xl text-center">
                      {localResult.seton} - {localResult.opponent}
                    </p>
                    <p className="text-white/60 text-sm text-center">
                      Seton vs Opponent
                    </p>
                  </>
                )}
                <Link href="/results" className="btn btn-gold w-full mt-3">
                  View Results →
                </Link>
              </div>
            )}

            {/* Button */}
            <button
              onClick={handleOptimize}
              disabled={!canOptimize || isOptimizing}
              className={`btn w-full py-4 text-lg ${canOptimize && !isOptimizing ? "btn-gold" : "bg-[var(--navy-600)] text-white/40 cursor-not-allowed"}`}
            >
              {isOptimizing ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-5 h-5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Optimizing...
                </span>
              ) : (
                "⚡ Run Optimization"
              )}
            </button>

            {!canOptimize && !isOptimizing && (
              <p className="text-xs text-white/40 text-center mt-3">
                {meetMode === "dual"
                  ? "Upload both teams first"
                  : "Upload psych sheet first"}
              </p>
            )}

            {!setonTeam && (
              <Link href="/meet" className="btn btn-outline w-full mt-3">
                ← Go to Meet Setup
              </Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
