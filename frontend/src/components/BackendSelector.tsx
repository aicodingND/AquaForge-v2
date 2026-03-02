"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/lib/store";
import { useShallow } from "zustand/react/shallow";
import { api } from "@/lib/api";

interface BackendInfo {
  available: boolean;
  description: string;
  recommended_for: string;
  license: string;
}

interface BackendsResponse {
  backends: Record<string, BackendInfo>;
  default: string;
  recommended: string;
}

// Coach-friendly names and descriptions for each optimizer engine
const coachLabels: Record<string, { name: string; tagline: string; icon: string }> = {
  aqua: {
    name: "Best Lineup",
    tagline: "Finds the highest-scoring lineup by testing thousands of combinations",
    icon: "🌊",
  },
  highs: {
    name: "Quick Solver",
    tagline: "Fast mathematical solver for a strong lineup in seconds",
    icon: "📊",
  },
  heuristic: {
    name: "Fast Preview",
    tagline: "Instant lineup estimate — great for exploring options quickly",
    icon: "⚡",
  },
  gurobi: {
    name: "Precision Solver",
    tagline: "Industry-grade optimizer for the most precise results",
    icon: "🔷",
  },
  stackelberg: {
    name: "Strategic Mode",
    tagline: "Accounts for how your opponent might change their lineup",
    icon: "♟️",
  },
};

const backendColors: Record<string, string> = {
  aqua: "from-cyan-500/20 to-blue-500/20 border-cyan-400",
  highs: "from-green-500/20 to-emerald-500/20 border-green-400",
  heuristic: "from-yellow-500/20 to-orange-500/20 border-yellow-400",
  gurobi: "from-purple-500/20 to-indigo-500/20 border-purple-400",
  stackelberg: "from-pink-500/20 to-rose-500/20 border-pink-400",
};

export default function BackendSelector() {
  const [backends, setBackends] = useState<Record<string, BackendInfo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recommended, setRecommended] = useState("aqua");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const { selectedBackend, setSelectedBackend } = useAppStore(useShallow(s => ({ selectedBackend: s.selectedBackend, setSelectedBackend: s.setSelectedBackend })));

  useEffect(() => {
    const fetchBackends = async () => {
      try {
        const data = await api.listBackends() as unknown as BackendsResponse;
        setBackends(data.backends);
        setRecommended(data.recommended);

        if (!selectedBackend) {
          setSelectedBackend(data.default);
        }
      } catch {
        // Fallback: use the default backend without showing an error
        // The optimizer will still work with whatever backend is selected
        setError("Could not load optimizer options. Using default settings.");
      } finally {
        setLoading(false);
      }
    };

    fetchBackends();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSelect = (key: string) => {
    if (!backends[key]?.available) return;
    setSelectedBackend(key);
  };

  const getLabel = (key: string) => coachLabels[key] || { name: key, tagline: "", icon: "⚙️" };
  const currentLabel = getLabel(selectedBackend || recommended);

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-medium text-white/60 mb-3">Lineup Strategy</h4>
        <div className="flex items-center gap-2 text-white/40 text-sm">
          <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          Loading options...
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-white/60">Lineup Strategy</h4>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-white/40 hover:text-white/60 transition-colors"
        >
          {showAdvanced ? "Simple" : "Advanced"}
        </button>
      </div>

      {/* Default: show just the current selection with a brief description */}
      {!showAdvanced ? (
        <div className="flex items-center gap-3 p-3 rounded-lg bg-[var(--navy-800)]">
          <span className="text-2xl">{currentLabel.icon}</span>
          <div className="flex-1">
            <p className="text-white font-medium">{currentLabel.name}</p>
            <p className="text-xs text-white/50">{currentLabel.tagline}</p>
          </div>
          {selectedBackend === recommended && (
            <span className="badge badge-success text-xs">Recommended</span>
          )}
        </div>
      ) : (
        /* Advanced: show all backends */
        <>
          {error && (
            <p className="text-xs text-white/40 mb-2">{error}</p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {Object.entries(backends).map(([key, info]) => {
              const isSelected = selectedBackend === key;
              const isRecommended = key === recommended;
              const label = getLabel(key);
              const colorClass =
                backendColors[key] ||
                "from-gray-500/20 to-gray-600/20 border-gray-400";

              return (
                <button
                  key={key}
                  onClick={() => handleSelect(key)}
                  disabled={!info.available}
                  className={`
                    relative p-3 rounded-lg text-left transition-all duration-200
                    ${info.available ? "cursor-pointer" : "cursor-not-allowed opacity-40"}
                    ${
                      isSelected
                        ? `bg-gradient-to-br ${colorClass} border-2`
                        : "bg-white/5 border border-white/10 hover:border-white/30"
                    }
                  `}
                  title={label.tagline}
                >
                  {isRecommended && (
                    <span className="absolute -top-1 -right-1 px-1.5 py-0.5 text-[10px] font-bold bg-cyan-500 text-white rounded">
                      ★
                    </span>
                  )}

                  <div className="flex items-center gap-2">
                    <span className="text-lg">{label.icon}</span>
                    <span
                      className={`text-sm font-medium ${isSelected ? "text-white" : "text-white/70"}`}
                    >
                      {label.name}
                    </span>
                  </div>

                  <p className="mt-1 text-[10px] text-white/40 line-clamp-2">
                    {label.tagline}
                  </p>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
