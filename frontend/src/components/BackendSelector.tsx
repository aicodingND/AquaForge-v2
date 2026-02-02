"use client";

import { useState, useEffect } from "react";
import { useAppStore } from "@/lib/store";

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

const backendIcons: Record<string, string> = {
  aqua: "🌊",
  highs: "📊",
  heuristic: "⚡",
  gurobi: "🔷",
  stackelberg: "♟️",
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

  const { selectedBackend, setSelectedBackend, addLog } = useAppStore();

  useEffect(() => {
    const fetchBackends = async () => {
      try {
        const response = await fetch("/api/optimize/backends");
        if (!response.ok) throw new Error("Failed to fetch backends");
        const data: BackendsResponse = await response.json();
        setBackends(data.backends);
        setRecommended(data.recommended);

        // Set default if not already set
        if (!selectedBackend) {
          setSelectedBackend(data.default);
        }
        addLog(
          `✓ Loaded ${Object.keys(data.backends).length} optimizer backends`,
        );
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load backends",
        );
      } finally {
        setLoading(false);
      }
    };

    fetchBackends();
  }, []);

  const handleSelect = (key: string) => {
    if (!backends[key]?.available) return;
    setSelectedBackend(key);
    addLog(`⚙️ Backend changed to: ${key}`);
  };

  if (loading) {
    return (
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-medium text-white/60 mb-3 flex items-center gap-2">
          <span>⚙️</span> Optimizer Engine
        </h4>
        <div className="flex items-center gap-2 text-white/40 text-sm">
          <div className="w-4 h-4 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
          Loading...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card rounded-xl p-4">
        <h4 className="text-sm font-medium text-white/60 mb-2">
          ⚙️ Optimizer Engine
        </h4>
        <p className="text-red-400 text-xs">{error}</p>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl p-4">
      <h4 className="text-sm font-medium text-white/60 mb-3 flex items-center gap-2">
        <span>⚙️</span> Optimizer Engine
      </h4>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {Object.entries(backends).map(([key, info]) => {
          const isSelected = selectedBackend === key;
          const isRecommended = key === recommended;
          const icon = backendIcons[key] || "⚙️";
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
              title={info.description}
            >
              {/* Recommended badge */}
              {isRecommended && (
                <span className="absolute -top-1 -right-1 px-1.5 py-0.5 text-[10px] font-bold bg-cyan-500 text-white rounded">
                  ★
                </span>
              )}

              <div className="flex items-center gap-2">
                <span className="text-lg">{icon}</span>
                <span
                  className={`text-sm font-medium ${isSelected ? "text-white" : "text-white/70"}`}
                >
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </span>
              </div>

              <p className="mt-1 text-[10px] text-white/40 line-clamp-1">
                {info.license}
              </p>
            </button>
          );
        })}
      </div>

      {/* Selected backend description */}
      {selectedBackend && backends[selectedBackend] && (
        <p className="mt-3 text-xs text-white/50">
          {backends[selectedBackend].description}
        </p>
      )}
    </div>
  );
}
