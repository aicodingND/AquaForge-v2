"use client";

import React from "react";

/**
 * Optimizer strategy for championship meets.
 */
interface OptimizerStrategy {
  id: string;
  name: string;
  description: string;
  recommended: boolean;
  performance: {
    avg_improvement_vs_coach: string;
    avg_improvement_vs_gurobi?: string;
    execution_time: string;
    wins_in_backtest?: number;
    total_backtests?: number;
  };
  best_for: string;
  badge?: string;
}

interface ChampionshipStrategySelectorProps {
  selectedStrategy: string;
  onStrategyChange: (strategy: string) => void;
  disabled?: boolean;
}

/**
 * ChampionshipStrategySelector
 *
 * Allows users to select between AquaOptimizer (recommended, +43% vs coach)
 * and Gurobi MILP (fast) for championship optimization.
 */
export function ChampionshipStrategySelector({
  selectedStrategy,
  onStrategyChange,
  disabled = false,
}: ChampionshipStrategySelectorProps) {
  const strategies: OptimizerStrategy[] = [
    {
      id: "aqua",
      name: "AquaOptimizer",
      description:
        "Nash+Beam+SimAnnealing ensemble - highest quality solutions",
      recommended: true,
      performance: {
        avg_improvement_vs_coach: "+43%",
        avg_improvement_vs_gurobi: "+99%",
        execution_time: "~20 seconds",
        wins_in_backtest: 3,
        total_backtests: 3,
      },
      best_for: "Championship meets where every point matters",
      badge: "RECOMMENDED",
    },
    {
      id: "gurobi",
      name: "Gurobi MILP",
      description: "Fast exact solver using Mixed Integer Linear Programming",
      recommended: false,
      performance: {
        avg_improvement_vs_coach: "-14%",
        execution_time: "~100 milliseconds",
        wins_in_backtest: 0,
        total_backtests: 3,
      },
      best_for: "Quick what-if scenarios during practice",
      badge: "FAST",
    },
  ];

  return (
    <div className="strategy-selector">
      <div className="strategy-header">
        <h3>🎯 Championship Optimization Strategy</h3>
        <p className="strategy-subtitle">
          Select the optimizer for your championship lineup
        </p>
      </div>

      <div className="strategy-cards">
        {strategies.map((strategy) => (
          <div
            key={strategy.id}
            className={`strategy-card ${selectedStrategy === strategy.id ? "selected" : ""} ${disabled ? "disabled" : ""}`}
            onClick={() => !disabled && onStrategyChange(strategy.id)}
            role="button"
            tabIndex={disabled ? -1 : 0}
            onKeyDown={(e) => {
              if ((e.key === "Enter" || e.key === " ") && !disabled) {
                onStrategyChange(strategy.id);
              }
            }}
          >
            {/* Badge */}
            {strategy.badge && (
              <span
                className={`strategy-badge ${strategy.badge.toLowerCase()}`}
              >
                {strategy.badge}
              </span>
            )}

            {/* Selection Indicator */}
            <div className="selection-indicator">
              {selectedStrategy === strategy.id ? (
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <circle cx="12" cy="12" r="10" fill="#38a169" />
                  <path
                    d="M9 12l2 2 4-4"
                    stroke="white"
                    strokeWidth="2"
                    fill="none"
                    strokeLinecap="round"
                  />
                </svg>
              ) : (
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <circle cx="12" cy="12" r="10" strokeWidth="2" />
                </svg>
              )}
            </div>

            {/* Header */}
            <div className="strategy-card-header">
              <h4 className="strategy-name">{strategy.name}</h4>
            </div>

            {/* Description */}
            <p className="strategy-description">{strategy.description}</p>

            {/* Performance Stats */}
            <div className="performance-stats">
              <div className="stat">
                <span className="stat-label">vs Coach</span>
                <span
                  className={`stat-value ${strategy.performance.avg_improvement_vs_coach.startsWith("+") ? "positive" : "negative"}`}
                >
                  {strategy.performance.avg_improvement_vs_coach}
                </span>
              </div>
              <div className="stat">
                <span className="stat-label">Time</span>
                <span className="stat-value">
                  {strategy.performance.execution_time}
                </span>
              </div>
              {strategy.performance.wins_in_backtest !== undefined && (
                <div className="stat">
                  <span className="stat-label">Backtest</span>
                  <span className="stat-value">
                    {strategy.performance.wins_in_backtest}/
                    {strategy.performance.total_backtests} wins
                  </span>
                </div>
              )}
            </div>

            {/* Best For */}
            <div className="best-for">
              <span className="best-for-label">Best for:</span>
              <span className="best-for-value">{strategy.best_for}</span>
            </div>
          </div>
        ))}
      </div>

      <style jsx>{`
        .strategy-selector {
          margin: 1.5rem 0;
        }

        .strategy-header {
          margin-bottom: 1rem;
        }

        .strategy-header h3 {
          font-size: 1.1rem;
          font-weight: 600;
          color: #1a365d;
          margin: 0;
        }

        .strategy-subtitle {
          color: #718096;
          font-size: 0.875rem;
          margin: 0.25rem 0 0 0;
        }

        .strategy-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1rem;
        }

        .strategy-card {
          position: relative;
          background: white;
          border: 2px solid #e2e8f0;
          border-radius: 12px;
          padding: 1.25rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .strategy-card:hover:not(.disabled) {
          border-color: #2b6cb0;
          box-shadow: 0 4px 12px rgba(43, 108, 176, 0.15);
        }

        .strategy-card.selected {
          border-color: #38a169;
          background: linear-gradient(135deg, #f0fff4 0%, #e6fffa 100%);
        }

        .strategy-card.disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        .strategy-badge {
          position: absolute;
          top: -8px;
          right: 12px;
          padding: 0.25rem 0.75rem;
          font-size: 0.7rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          border-radius: 10px;
        }

        .strategy-badge.recommended {
          background: linear-gradient(135deg, #38a169, #2f855a);
          color: white;
        }

        .strategy-badge.fast {
          background: linear-gradient(135deg, #d69e2e, #b7791f);
          color: white;
        }

        .selection-indicator {
          position: absolute;
          top: 12px;
          left: 12px;
          color: #a0aec0;
        }

        .strategy-card.selected .selection-indicator {
          color: #38a169;
        }

        .strategy-card-header {
          margin-left: 2rem;
          margin-bottom: 0.5rem;
        }

        .strategy-name {
          font-size: 1.1rem;
          font-weight: 600;
          color: #1a365d;
          margin: 0;
        }

        .strategy-description {
          color: #4a5568;
          font-size: 0.875rem;
          margin: 0 0 1rem 0;
          line-height: 1.4;
        }

        .performance-stats {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          margin-bottom: 0.75rem;
          padding: 0.75rem;
          background: #f8fafc;
          border-radius: 8px;
        }

        .stat {
          display: flex;
          flex-direction: column;
          flex: 1;
          min-width: 70px;
        }

        .stat-label {
          font-size: 0.7rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #718096;
        }

        .stat-value {
          font-size: 0.95rem;
          font-weight: 600;
          color: #2d3748;
        }

        .stat-value.positive {
          color: #38a169;
        }

        .stat-value.negative {
          color: #e53e3e;
        }

        .best-for {
          display: flex;
          gap: 0.5rem;
          font-size: 0.8rem;
        }

        .best-for-label {
          color: #718096;
        }

        .best-for-value {
          color: #4a5568;
          font-style: italic;
        }
      `}</style>
    </div>
  );
}

export default ChampionshipStrategySelector;
