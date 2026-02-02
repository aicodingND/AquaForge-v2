"use client";

import React, { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

// Type definitions
interface MonteCarloData {
  win_probability: number;
  expected_score: number;
  confidence_interval: [number, number];
  risk_level: "low" | "medium" | "high" | "unknown";
  simulations: number;
}

interface FatigueWarning {
  swimmer: string;
  events: string[];
  total_fatigue: number;
  risk: "medium" | "high";
}

interface NashInsights {
  equilibrium_found: boolean;
  target_rank: number;
  target_points: number;
  stability_score: number;
  insights: string[];
}

interface RelayTradeoff {
  swimmer: string;
  individual_event: string;
  relay_gain: number;
  individual_loss: number;
  recommendation: "swim_relay" | "skip_relay";
}

interface AnalyticsProps {
  analytics: {
    monte_carlo?: MonteCarloData | null;
    fatigue_warnings?: FatigueWarning[] | null;
    nash_insights?: NashInsights | null;
    relay_tradeoffs?: RelayTradeoff[] | null;
  } | null;
  isExpanded?: boolean;
  onToggle?: () => void;
}

/**
 * InfoTooltip - Shows help text on hover
 */
function InfoTooltip({ text }: { text: string }) {
  const [show, setShow] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="text-navy-400 hover:text-gold-400 transition-colors ml-1"
        aria-label="More information"
      >
        <span className="text-xs">ⓘ</span>
      </button>
      {show && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-64 p-3 bg-navy-700 border border-navy-600 rounded-lg shadow-xl text-xs text-navy-100 leading-relaxed">
          {text}
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 rotate-45 w-2 h-2 bg-navy-700 border-r border-b border-navy-600"></div>
        </div>
      )}
    </span>
  );
}

/**
 * ChampionshipAnalytics - Displays advanced analytics for championship results
 *
 * Shows Monte Carlo win probability, fatigue warnings, Nash equilibrium insights,
 * and relay trade-off recommendations with comprehensive explanations.
 */
export default function ChampionshipAnalytics({
  analytics,
  isExpanded = true,
  onToggle,
}: AnalyticsProps) {
  const [showHelp, setShowHelp] = useState(false);

  if (!analytics) return null;

  const { monte_carlo, fatigue_warnings, nash_insights, relay_tradeoffs } =
    analytics;

  // Don't render if no analytics data
  if (!monte_carlo && !fatigue_warnings && !nash_insights && !relay_tradeoffs) {
    return null;
  }

  // Generate AI prediction summary
  const getPredictionSummary = () => {
    const predictions: string[] = [];

    if (monte_carlo) {
      if (monte_carlo.win_probability >= 75) {
        predictions.push(
          `🏆 Strong favorite (${monte_carlo.win_probability.toFixed(0)}% win probability) - Focus on executing clean swims`,
        );
      } else if (monte_carlo.win_probability >= 50) {
        predictions.push(
          `⚔️ Competitive position (${monte_carlo.win_probability.toFixed(0)}% win) - Key events will determine outcome`,
        );
      } else if (monte_carlo.win_probability >= 25) {
        predictions.push(
          `🎯 Underdog position (${monte_carlo.win_probability.toFixed(0)}%) - Target high-variance events for upset potential`,
        );
      } else {
        predictions.push(
          `📈 Developing team - Focus on individual improvements and experience`,
        );
      }
    }

    if (nash_insights?.equilibrium_found === false) {
      predictions.push(
        "⚠️ Unstable field - Opponents may adjust strategy, be prepared to adapt",
      );
    }

    if (fatigue_warnings && fatigue_warnings.length >= 3) {
      predictions.push(
        `🔋 High fatigue load on ${fatigue_warnings.length} swimmers - Consider rest between events`,
      );
    }

    return predictions;
  };

  // Generate pros and cons
  const getProsAndCons = () => {
    const pros: string[] = [];
    const cons: string[] = [];

    if (monte_carlo) {
      if (monte_carlo.win_probability >= 50) {
        pros.push("Statistical favorite to win");
      } else {
        cons.push("Below 50% win probability");
      }

      const range =
        monte_carlo.confidence_interval[1] - monte_carlo.confidence_interval[0];
      if (range <= 30) {
        pros.push(
          "Consistent performance expected (tight confidence interval)",
        );
      } else {
        cons.push("High variance in outcomes - results could swing either way");
      }
    }

    if (nash_insights) {
      if (nash_insights.equilibrium_found) {
        pros.push("Strategic position is stable against opponent changes");
      } else {
        cons.push("Position vulnerable to opponent adjustments");
      }

      if (nash_insights.target_rank <= 3) {
        pros.push(
          `Projected podium finish (${nash_insights.target_rank}${nash_insights.target_rank === 1 ? "st" : nash_insights.target_rank === 2 ? "nd" : "rd"} place)`,
        );
      }
    }

    if (!fatigue_warnings || fatigue_warnings.length === 0) {
      pros.push("No significant fatigue concerns");
    } else {
      cons.push(`${fatigue_warnings.length} swimmer(s) at fatigue risk`);
    }

    return { pros, cons };
  };

  // Generate actionable suggestions
  const getSuggestions = () => {
    const suggestions: string[] = [];

    if (monte_carlo?.risk_level === "high") {
      suggestions.push(
        "Consider conservative event assignments for reliable scorers",
      );
    }

    if (fatigue_warnings && fatigue_warnings.length > 0) {
      const highFatigue = fatigue_warnings.filter((w) => w.risk === "high");
      if (highFatigue.length > 0) {
        suggestions.push(
          `Reduce event load for ${highFatigue.map((w) => w.swimmer).join(", ")}`,
        );
      }
    }

    if (nash_insights && !nash_insights.equilibrium_found) {
      suggestions.push("Monitor opponent lane assignments for late changes");
    }

    if (monte_carlo && monte_carlo.win_probability < 50) {
      suggestions.push(
        "Focus on high-variance events where upsets are possible",
      );
      suggestions.push("Ensure relay teams are optimized for maximum points");
    }

    return suggestions;
  };

  const predictions = getPredictionSummary();
  const { pros, cons } = getProsAndCons();
  const suggestions = getSuggestions();

  return (
    <div className="bg-navy-900/50 rounded-xl border border-navy-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-3 flex justify-between items-center bg-navy-800/50 hover:bg-navy-800 transition-colors"
        aria-label="Toggle analytics panel"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">📊</span>
          <h3 className="font-semibold text-white">Advanced Analytics</h3>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowHelp(!showHelp);
            }}
            className="text-xs px-2 py-0.5 rounded-full bg-navy-700 text-navy-300 hover:bg-navy-600 hover:text-white"
            aria-label="Toggle help panel"
          >
            {showHelp ? "Hide Help" : "What's This?"}
          </button>
        </div>
        <span className="text-navy-400">{isExpanded ? "▲" : "▼"}</span>
      </button>

      {/* Help Panel */}
      {showHelp && (
        <div className="px-4 py-3 bg-navy-800 border-b border-navy-700 text-sm">
          <h4 className="font-medium text-gold-400 mb-2">
            Understanding Analytics
          </h4>
          <div className="grid md:grid-cols-2 gap-3 text-navy-200">
            <div>
              <b className="text-white">🎲 Monte Carlo:</b> Runs 5,000+
              simulated meets with random performance variance to predict win
              probability.
            </div>
            <div>
              <b className="text-white">⚠️ Fatigue:</b> Tracks cumulative load
              from multiple events and back-to-back swims.
            </div>
            <div>
              <b className="text-white">⚔️ Nash Equilibrium:</b> Game theory
              analysis of how all teams&apos; strategies interact.
            </div>
            <div>
              <b className="text-white">🏊 Relay Trade-offs:</b> Point analysis
              for 400FR swimmer decisions.
            </div>
          </div>
        </div>
      )}

      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* AI Prediction Summary - NEW */}
          {predictions.length > 0 && (
            <div className="bg-gradient-to-r from-gold-900/30 to-navy-800/30 border border-gold-600/30 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gold-400 mb-2 flex items-center gap-2">
                🤖 AI Prediction Summary
              </h4>
              <div className="space-y-1">
                {predictions.map((pred, idx) => (
                  <div key={idx} className="text-sm text-white">
                    {pred}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Pros & Cons Panel - NEW */}
          {(pros.length > 0 || cons.length > 0) && (
            <div className="grid md:grid-cols-2 gap-3">
              {/* Pros */}
              <div className="bg-green-900/20 border border-green-600/30 rounded-lg p-3">
                <h5 className="text-xs font-medium text-green-400 mb-2">
                  ✅ Strengths
                </h5>
                <ul className="space-y-1">
                  {pros.map((pro, idx) => (
                    <li
                      key={idx}
                      className="text-xs text-green-200 flex items-start gap-1"
                    >
                      <span>•</span> {pro}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Cons */}
              <div className="bg-red-900/20 border border-red-600/30 rounded-lg p-3">
                <h5 className="text-xs font-medium text-red-400 mb-2">
                  ⚠️ Challenges
                </h5>
                <ul className="space-y-1">
                  {cons.map((con, idx) => (
                    <li
                      key={idx}
                      className="text-xs text-red-200 flex items-start gap-1"
                    >
                      <span>•</span> {con}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {/* Actionable Suggestions - NEW */}
          {suggestions.length > 0 && (
            <div className="bg-blue-900/20 border border-blue-600/30 rounded-lg p-3">
              <h5 className="text-xs font-medium text-blue-400 mb-2">
                💡 Coach Suggestions
              </h5>
              <ul className="space-y-1">
                {suggestions.map((sug, idx) => (
                  <li
                    key={idx}
                    className="text-xs text-blue-200 flex items-start gap-1"
                  >
                    <span>{idx + 1}.</span> {sug}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Monte Carlo Panel */}
          {monte_carlo && (
            <div className="bg-navy-800/40 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gold-400 mb-3 flex items-center gap-2">
                🎲 Monte Carlo Simulation
                <InfoTooltip text="Monte Carlo runs thousands of simulated meets with random performance variations based on historical swimmer consistency. The win probability shows how often your team wins in these simulations." />
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                {/* Win Probability Pie Chart */}
                <div className="h-48 relative">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: "Win", value: monte_carlo.win_probability },
                          {
                            name: "Loss",
                            value: 100 - monte_carlo.win_probability,
                          },
                        ]}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        stroke="none"
                      >
                        <Cell
                          key="win"
                          fill={
                            monte_carlo.win_probability >= 50
                              ? "#10B981"
                              : "#FBBF24"
                          }
                        />
                        <Cell key="loss" fill="#1e293b" />
                      </Pie>
                      <RechartsTooltip
                        contentStyle={{
                          backgroundColor: "#0f172a",
                          borderColor: "#1e293b",
                          borderRadius: "8px",
                          color: "#fff",
                        }}
                        itemStyle={{ color: "#fff" }}
                        formatter={(value) => `${Number(value).toFixed(1)}%`}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Centered Label */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-2xl font-bold text-white leading-none">
                      {monte_carlo.win_probability.toFixed(0)}%
                    </span>
                    <span className="text-xs text-navy-400 mt-1">Win Prob</span>
                  </div>
                </div>

                {/* Key Metrics Grid */}
                <div className="grid grid-cols-2 gap-3">
                  {/* Expected Score */}
                  <div className="bg-navy-900/50 rounded p-3 border border-navy-700">
                    <div className="text-xs text-navy-400 mb-1">
                      Expected Points
                    </div>
                    <div className="text-xl font-bold text-white">
                      {monte_carlo.expected_score.toFixed(1)}
                    </div>
                  </div>
                  {/* Confidence */}
                  <div className="bg-navy-900/50 rounded p-3 border border-navy-700">
                    <div className="text-xs text-navy-400 mb-1">95% Range</div>
                    <div className="text-sm font-medium text-white">
                      {monte_carlo.confidence_interval[0].toFixed(0)} -{" "}
                      {monte_carlo.confidence_interval[1].toFixed(0)}
                    </div>
                  </div>
                  {/* Risk Level */}
                  <div className="bg-navy-900/50 rounded p-3 border border-navy-700">
                    <div className="text-xs text-navy-400 mb-1">Risk Level</div>
                    <div
                      className={`text-sm font-medium capitalize ${
                        monte_carlo.risk_level === "high"
                          ? "text-red-400"
                          : monte_carlo.risk_level === "medium"
                            ? "text-yellow-400"
                            : "text-green-400"
                      }`}
                    >
                      {monte_carlo.risk_level}
                    </div>
                  </div>
                  {/* Simulations */}
                  <div className="bg-navy-900/50 rounded p-3 border border-navy-700">
                    <div className="text-xs text-navy-400 mb-1">
                      Simulations
                    </div>
                    <div className="text-sm font-medium text-white">
                      {monte_carlo.simulations.toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Fatigue Warnings */}
          {fatigue_warnings && fatigue_warnings.length > 0 && (
            <div className="bg-navy-800/40 border border-yellow-600/20 rounded-lg p-4">
              <h4 className="text-sm font-medium text-yellow-400 mb-3 flex items-center gap-2">
                ⚠️ Fatigue Analysis
                <InfoTooltip text="Swimmers with high accumulated fatigue from multiple events. This backend enforces fatigue penalties." />
              </h4>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={fatigue_warnings.map((w) => ({
                      name: w.swimmer.split(",")[0],
                      full_name: w.swimmer,
                      fatigue: w.total_fatigue * 100,
                      risk: w.risk,
                    }))}
                    layout="vertical"
                    margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#334155"
                      horizontal={false}
                      vertical={true}
                    />
                    <XAxis
                      type="number"
                      domain={[0, "auto"]}
                      stroke="#475569"
                    />
                    <YAxis
                      dataKey="name"
                      type="category"
                      width={100}
                      tick={{ fill: "#94a3b8", fontSize: 12 }}
                      stroke="#475569"
                    />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#1e293b",
                        borderRadius: "8px",
                        color: "#fff",
                      }}
                      cursor={{ fill: "#1e293b" }}
                      formatter={(value: number | undefined) => [
                        `${Number(value || 0).toFixed(1)}%`,
                        "Fatigue",
                      ]}
                      labelFormatter={(label, payload) => {
                        if (payload && payload.length > 0)
                          return payload[0].payload.full_name;
                        return label;
                      }}
                    />
                    <Bar dataKey="fatigue" radius={[0, 4, 4, 0]} barSize={24}>
                      {fatigue_warnings.map((w, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={
                            w.risk === "high"
                              ? "#EF4444"
                              : w.risk === "medium"
                                ? "#FBBF24"
                                : "#10B981"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <p className="text-xs text-yellow-400/70 mt-4 text-center">
                💡 <b>Suggestion:</b> Consider spreading events across the meet
                or providing adequate warm-down time between races.
              </p>
            </div>
          )}

          {/* Nash Equilibrium Insights */}
          {nash_insights && (
            <div className="bg-navy-800/40 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gold-400 mb-3 flex items-center gap-2">
                ⚔️ Strategic Position (Nash Equilibrium)
                <InfoTooltip text="Nash Equilibrium is a game theory concept where no team can improve their position by unilaterally changing strategy. When equilibrium is 'found', your strategy is stable against opponent changes." />
              </h4>

              <div className="grid grid-cols-3 gap-4 mb-3">
                {/* Rank */}
                <div className="text-center">
                  <div className="text-2xl font-bold text-white">
                    #{nash_insights.target_rank}
                  </div>
                  <div className="text-xs text-navy-400">Projected Rank</div>
                  <div className="text-xs text-navy-500 mt-1">
                    {nash_insights.target_rank === 1
                      ? "🥇 Champion"
                      : nash_insights.target_rank === 2
                        ? "🥈 Runner-up"
                        : nash_insights.target_rank === 3
                          ? "🥉 Podium"
                          : `${nash_insights.target_rank}th place`}
                  </div>
                </div>

                {/* Points */}
                <div className="text-center">
                  <div className="text-2xl font-bold text-gold-400">
                    {nash_insights.target_points.toFixed(1)}
                  </div>
                  <div className="text-xs text-navy-400">Projected Points</div>
                </div>

                {/* Stability */}
                <div className="text-center">
                  <div
                    className={`text-lg font-medium ${
                      nash_insights.equilibrium_found
                        ? "text-green-400"
                        : "text-yellow-400"
                    }`}
                  >
                    {nash_insights.equilibrium_found
                      ? "✓ Stable"
                      : "⚡ Unstable"}
                  </div>
                  <div className="text-xs text-navy-400">Equilibrium</div>
                  <div className="text-xs text-navy-500 mt-1">
                    {nash_insights.equilibrium_found
                      ? "Position is secure"
                      : "May shift with changes"}
                  </div>
                </div>
              </div>

              {/* Insights List */}
              {nash_insights.insights && nash_insights.insights.length > 0 && (
                <div className="mt-3 space-y-1 border-t border-navy-700 pt-3">
                  <div className="text-xs text-navy-400 mb-2">
                    Strategic Insights:
                  </div>
                  {nash_insights.insights.map((insight, idx) => (
                    <div
                      key={idx}
                      className="text-sm text-navy-200 flex items-start gap-2"
                    >
                      <span className="text-gold-400">•</span>
                      {insight}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Relay Trade-offs */}
          {relay_tradeoffs && relay_tradeoffs.length > 0 && (
            <div className="bg-navy-800/40 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gold-400 mb-3 flex items-center gap-2">
                🏊 400 Free Relay Trade-offs
                <InfoTooltip text="The 400 Free Relay often conflicts with the 400 Free individual event. This shows the point trade-off: what you'd gain from the relay vs. what you'd lose from moving the swimmer's individual event." />
              </h4>

              <div className="space-y-2">
                {relay_tradeoffs.map((tradeoff, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center bg-navy-700/50 rounded px-3 py-2"
                  >
                    <div>
                      <span className="font-medium text-white">
                        {tradeoff.swimmer}
                      </span>
                      <span className="text-sm text-navy-400 ml-2">
                        ({tradeoff.individual_event})
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-green-400">
                        +{tradeoff.relay_gain} relay pts
                      </span>
                      <span className="text-sm text-red-400">
                        -{tradeoff.individual_loss} ind. pts
                      </span>
                      <span
                        className={`text-sm font-bold px-2 py-0.5 rounded ${
                          tradeoff.recommendation === "swim_relay"
                            ? "bg-green-900/50 text-green-300"
                            : "bg-yellow-900/50 text-yellow-300"
                        }`}
                      >
                        {tradeoff.recommendation === "swim_relay"
                          ? "✓ Swim Relay"
                          : "✗ Skip Relay"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-xs text-navy-400 mt-2">
                💡 Net point difference determines recommendation. Consider
                fatigue if swimmer has other events nearby.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
