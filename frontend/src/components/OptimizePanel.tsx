"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import StrategySelector from "./StrategySelector";

export default function OptimizePanel() {
  const [backend, setBackend] = useState<"heuristic" | "gurobi">("gurobi"); // Default to GUROBI for accuracy
  const [enforceFatigue, setEnforceFatigue] = useState(true);

  const {
    setonTeam,
    opponentTeam,
    meetMode,
    selectedStrategy,
    isOptimizing,
    setOptimizing,
    setResults,
    addLog,
  } = useAppStore();

  const canOptimize = setonTeam && opponentTeam && !isOptimizing;

  const handleOptimize = async () => {
    if (!setonTeam || !opponentTeam) return;

    setOptimizing(true);
    addLog("Starting optimization...");

    try {
      const startTime = Date.now();

      // Log strategy for championship mode
      if (meetMode === "championship") {
        addLog(`Using strategy: ${selectedStrategy}`);
      }

      const response = await api.optimize({
        seton_data: setonTeam.data,
        opponent_data: opponentTeam.data,
        optimizer_backend: backend,
        enforce_fatigue: enforceFatigue,
        robust_mode: false,
        scoring_type:
          meetMode === "championship" ? "vcac_championship" : "visaa_top7",
        strategy: meetMode === "championship" ? selectedStrategy : undefined,
      });

      if (response.success) {
        const elapsed = Date.now() - startTime;
        setResults(
          response.results,
          response.seton_score,
          response.opponent_score,
        );
        addLog(`✓ Optimization complete in ${elapsed}ms`);
        addLog(`  Score: ${response.seton_score} - ${response.opponent_score}`);
      } else {
        addLog("✗ Optimization failed");
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Optimization failed";
      addLog(`✗ Error: ${message}`);
    } finally {
      setOptimizing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Strategy Selector - Only for Championship Mode */}
      {meetMode === "championship" && <StrategySelector />}

      <div className="glass-card rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-[#D4AF37]">⚡</span>
          Optimization Settings
        </h3>

        {/* Backend Selection */}
        <div className="mb-4">
          <label className="block text-sm text-white/60 mb-2">
            Optimizer Backend
          </label>
          <div className="flex gap-2">
            {(["heuristic", "gurobi"] as const).map((opt) => (
              <button
                key={opt}
                onClick={() => setBackend(opt)}
                className={`
                flex-1 py-2 px-4 rounded-lg font-medium transition-all
                ${
                  backend === opt
                    ? "bg-gradient-to-r from-[#D4AF37] to-[#C99700] text-[#091A30]"
                    : "bg-[#1a3a5c] text-white/70 hover:bg-[#1a3a5c]/80"
                }
              `}
              >
                {opt === "heuristic" ? "⚡ Heuristic" : "🎯 Gurobi"}
              </button>
            ))}
          </div>
          <p className="text-xs text-white/40 mt-1">
            {backend === "heuristic"
              ? "Fast approximation algorithm"
              : "Optimal solution (requires solver)"}
          </p>
        </div>

        {/* Fatigue Toggle */}
        <div className="mb-6">
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              onClick={() => setEnforceFatigue(!enforceFatigue)}
              className={`
              w-12 h-6 rounded-full transition-colors relative
              ${enforceFatigue ? "bg-[#C99700]" : "bg-[#1a3a5c]"}
            `}
            >
              <div
                className={`
              absolute top-1 w-4 h-4 rounded-full bg-white transition-transform
              ${enforceFatigue ? "left-7" : "left-1"}
            `}
              />
            </div>
            <span className="text-white/80">Enforce Fatigue Rules</span>
          </label>
          <p className="text-xs text-white/40 mt-1 ml-15">
            Limits consecutive events per swimmer
          </p>
        </div>

        {/* Optimize Button */}
        <button
          onClick={handleOptimize}
          disabled={!canOptimize}
          className={`
          w-full py-3 px-6 rounded-xl font-semibold text-lg
          flex items-center justify-center gap-2
          transition-all duration-200
          ${
            canOptimize
              ? "bg-gradient-to-r from-[#D4AF37] to-[#C99700] text-[#091A30] hover:shadow-lg hover:shadow-[#C99700]/30"
              : "bg-[#1a3a5c] text-white/40 cursor-not-allowed"
          }
        `}
        >
          {isOptimizing ? (
            <>
              <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
              Optimizing...
            </>
          ) : (
            <>
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
              Run Optimization
            </>
          )}
        </button>

        {/* Status */}
        {!setonTeam && !opponentTeam && (
          <p className="text-sm text-white/40 text-center mt-3">
            Upload both teams to enable optimization
          </p>
        )}
        {setonTeam && !opponentTeam && (
          <p className="text-sm text-white/40 text-center mt-3">
            Upload opponent team to enable optimization
          </p>
        )}
        {!setonTeam && opponentTeam && (
          <p className="text-sm text-white/40 text-center mt-3">
            Upload Seton team to enable optimization
          </p>
        )}
      </div>
    </div>
  );
}
