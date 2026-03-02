"use client";


interface Strategy {
  id: string;
  name: string;
  icon: string;
  tagline: string;
  detail: string;
  stats: { label: string; value: string; highlight?: boolean }[];
  badge?: string;
  recommended?: boolean;
}

interface ChampionshipStrategySelectorProps {
  selectedStrategy: string;
  onStrategyChange: (strategy: string) => void;
  disabled?: boolean;
}

const strategies: Strategy[] = [
  {
    id: "aqua",
    name: "Best Lineup",
    icon: "🏆",
    tagline: "Maximizes your team score by testing thousands of lineup combinations",
    detail: "Best for championship meets where every point matters",
    stats: [
      { label: "vs Manual", value: "+43%", highlight: true },
      { label: "Speed", value: "~20 sec" },
      { label: "Backtests", value: "3/3 wins", highlight: true },
    ],
    badge: "Recommended",
    recommended: true,
  },
  {
    id: "gurobi",
    name: "Quick Solver",
    icon: "⚡",
    tagline: "Fast mathematical solver for instant what-if scenarios",
    detail: "Great for exploring options during practice planning",
    stats: [
      { label: "vs Manual", value: "-14%" },
      { label: "Speed", value: "< 1 sec", highlight: true },
      { label: "Backtests", value: "0/3 wins" },
    ],
    badge: "Fast",
  },
];

/**
 * Championship strategy selector — coach-friendly cards
 * for picking the optimization approach.
 */
export function ChampionshipStrategySelector({
  selectedStrategy,
  onStrategyChange,
  disabled = false,
}: ChampionshipStrategySelectorProps) {
  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-sm font-medium text-white/60">
          Championship Strategy
        </h3>
        <p className="text-xs text-white/40 mt-0.5">
          Choose how the optimizer builds your lineup
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {strategies.map((s) => {
          const isSelected = selectedStrategy === s.id;

          return (
            <button
              key={s.id}
              type="button"
              onClick={() => !disabled && onStrategyChange(s.id)}
              disabled={disabled}
              className={`
                relative p-4 rounded-xl text-left transition-all duration-200
                ${disabled ? "cursor-not-allowed opacity-40" : "cursor-pointer"}
                ${
                  isSelected
                    ? "bg-gradient-to-br from-[var(--gold-400)]/10 to-[var(--gold-500)]/5 border-2 border-[var(--gold-400)] ring-1 ring-[var(--gold-400)]/30"
                    : "bg-white/5 border border-white/10 hover:border-white/30"
                }
              `}
            >
              {/* Badge */}
              {s.badge && (
                <span
                  className={`absolute -top-2 right-3 px-2 py-0.5 text-[10px] font-bold rounded-full ${
                    s.recommended
                      ? "bg-[var(--gold-500)] text-[var(--navy-900)]"
                      : "bg-cyan-500 text-white"
                  }`}
                >
                  {s.badge}
                </span>
              )}

              {/* Header */}
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{s.icon}</span>
                <div>
                  <p
                    className={`font-semibold ${isSelected ? "text-[var(--gold-400)]" : "text-white"}`}
                  >
                    {s.name}
                  </p>
                </div>
              </div>

              {/* Tagline */}
              <p className="text-xs text-white/50 mb-3 leading-relaxed">
                {s.tagline}
              </p>

              {/* Stats */}
              <div className="flex gap-3 p-2.5 rounded-lg bg-[var(--navy-800)]">
                {s.stats.map((stat) => (
                  <div key={stat.label} className="flex-1 min-w-0">
                    <p className="text-[10px] text-white/40 uppercase tracking-wider">
                      {stat.label}
                    </p>
                    <p
                      className={`text-sm font-semibold ${
                        stat.highlight
                          ? stat.value.startsWith("+")
                            ? "text-[var(--success)]"
                            : "text-[var(--gold-400)]"
                          : stat.value.startsWith("-")
                            ? "text-[var(--error)]"
                            : "text-white/70"
                      }`}
                    >
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>

              {/* Best for */}
              <p className="mt-2.5 text-[10px] text-white/40 italic">
                {s.detail}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default ChampionshipStrategySelector;
