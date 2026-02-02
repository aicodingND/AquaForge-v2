"use client";

import { useEffect, useState } from "react";
import { api, StrategyInfo } from "@/lib/api";
import { useAppStore } from "@/lib/store";

interface StrategySelectorProps {
  className?: string;
}

const strategyIcons: Record<string, string> = {
  maximize_individual: "⚡",
  balanced_approach: "⚖️",
  relay_focused: "🏊",
  conservative: "🛡️",
  aggressive: "🚀",
};

export default function StrategySelector({
  className = "",
}: StrategySelectorProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);

  const {
    selectedStrategy,
    setChampionshipStrategy: setSelectedStrategy,
    availableStrategies,
    setAvailableStrategies,
    addLog,
  } = useAppStore();

  // Fetch strategies on mount
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        setLoading(true);
        const response = await api.getStrategies();
        setAvailableStrategies(response.strategies);

        // Set default if not already set
        if (!selectedStrategy && response.default_strategy) {
          setSelectedStrategy(response.default_strategy);
        }

        addLog(
          `✓ Loaded ${response.strategies.length} optimization strategies`,
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to load strategies";
        setError(message);
        addLog(`✗ Strategy loading failed: ${message}`);
      } finally {
        setLoading(false);
      }
    };

    if (availableStrategies.length === 0) {
      fetchStrategies();
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStrategySelect = (
    strategyKey: string,
    isImplemented: boolean,
  ) => {
    if (!isImplemented) {
      // Don't allow selection of coming soon strategies
      return;
    }
    setSelectedStrategy(strategyKey);
    addLog(`Strategy changed to: ${strategyKey}`);
  };

  const toggleExpanded = (key: string) => {
    setExpandedStrategy(expandedStrategy === key ? null : key);
  };

  if (loading) {
    return (
      <div className={`glass-card rounded-xl p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-[#D4AF37]">🎯</span>
          Championship Strategy
        </h3>
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
          <span className="ml-3 text-white/60">Loading strategies...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`glass-card rounded-xl p-6 ${className}`}>
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="text-[#D4AF37]">🎯</span>
          Championship Strategy
        </h3>
        <div className="text-red-400 text-sm py-4">{error}</div>
      </div>
    );
  }

  return (
    <div className={`glass-card rounded-xl p-6 ${className}`}>
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <span className="text-[#D4AF37]">🎯</span>
        Championship Strategy
      </h3>

      <div className="space-y-3">
        {availableStrategies.map((strategy: StrategyInfo) => {
          const isSelected = selectedStrategy === strategy.key;
          const isImplemented = strategy.is_implemented;
          const icon = strategyIcons[strategy.key] || "📋";

          return (
            <div
              key={strategy.key}
              onClick={() => handleStrategySelect(strategy.key, isImplemented)}
              className={`
                relative rounded-lg p-4 transition-all duration-200
                ${isImplemented ? "cursor-pointer" : "cursor-not-allowed"}
                ${
                  isSelected
                    ? "bg-gradient-to-r from-[#D4AF37]/20 to-[#C99700]/20 border-2 border-[#D4AF37]"
                    : isImplemented
                      ? "bg-[#1a3a5c]/50 border border-[#1a3a5c] hover:border-[#D4AF37]/50 hover:bg-[#1a3a5c]/70"
                      : "bg-[#1a3a5c]/30 border border-[#1a3a5c]/50 opacity-50"
                }
              `}
            >
              {/* Header Row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {/* Selection indicator */}
                  <div
                    className={`
                      w-5 h-5 rounded-full border-2 flex items-center justify-center
                      ${
                        isSelected
                          ? "border-[#D4AF37] bg-[#D4AF37]"
                          : "border-white/30"
                      }
                    `}
                  >
                    {isSelected && (
                      <svg
                        className="w-3 h-3 text-[#091A30]"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    )}
                  </div>

                  <span className="text-xl">{icon}</span>
                  <span
                    className={`font-medium ${isSelected ? "text-white" : "text-white/80"}`}
                  >
                    {strategy.name}
                  </span>
                </div>

                {/* Badges */}
                <div className="flex items-center gap-2">
                  {strategy.key === "maximize_individual" && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-[#D4AF37]/20 text-[#D4AF37] rounded">
                      ★ Default
                    </span>
                  )}
                  {!isImplemented && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-blue-500/20 text-blue-400 rounded">
                      🔜 Coming Soon
                    </span>
                  )}
                </div>
              </div>

              {/* Description */}
              <p className="mt-2 ml-11 text-sm text-white/60 line-clamp-2">
                {strategy.description.split("\n")[1]?.trim() ||
                  strategy.description.trim().split("\n")[0]}
              </p>

              {/* Expandable details */}
              {isImplemented && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleExpanded(strategy.key);
                  }}
                  className="mt-2 ml-11 text-xs text-[#D4AF37] hover:text-[#C99700] transition-colors"
                >
                  {expandedStrategy === strategy.key
                    ? "Hide details ↑"
                    : "Show details ↓"}
                </button>
              )}

              {/* Expanded details */}
              {expandedStrategy === strategy.key && (
                <div className="mt-3 ml-11 pt-3 border-t border-white/10 space-y-3">
                  {/* Pros */}
                  <div>
                    <h4 className="text-xs font-medium text-green-400 mb-1">
                      ✓ Pros
                    </h4>
                    <ul className="text-xs text-white/60 space-y-0.5">
                      {strategy.pros.slice(0, 3).map((pro, i) => (
                        <li key={i}>• {pro}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Cons */}
                  <div>
                    <h4 className="text-xs font-medium text-orange-400 mb-1">
                      ✗ Cons
                    </h4>
                    <ul className="text-xs text-white/60 space-y-0.5">
                      {strategy.cons.slice(0, 3).map((con, i) => (
                        <li key={i}>• {con}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Best For */}
                  <div>
                    <h4 className="text-xs font-medium text-blue-400 mb-1">
                      Best For
                    </h4>
                    <p className="text-xs text-white/60">
                      {strategy.recommended_for.slice(0, 2).join(" • ")}
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer info */}
      <p className="mt-4 text-xs text-white/40 text-center">
        {availableStrategies.filter((s) => s.is_implemented).length} of{" "}
        {availableStrategies.length} strategies available
      </p>
    </div>
  );
}
