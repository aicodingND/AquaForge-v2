'use client';

import { useState, useMemo } from 'react';

interface SwingEvent {
  event: string;
  seton_points: number;
  opponent_points: number;
  point_differential: number;
  swing_potential: number;
  risk_level: 'high' | 'medium' | 'low';
  closest_gap_seconds: number;
  recommendation: string;
}

interface CoachingSummary {
  score_status: string;
  margin: number;
  top_opportunities: SwingEvent[];
  risk_events: SwingEvent[];
  total_swing_potential: number;
  focus_recommendations: string[];
}

interface PointSwingPanelProps {
  swingAnalysis: SwingEvent[];
  coachingSummary: CoachingSummary;
}

type SortField = 'swing_potential' | 'closest_gap_seconds' | 'point_differential';

export default function PointSwingPanel({
  swingAnalysis,
  coachingSummary,
}: PointSwingPanelProps) {
  const [sortBy, setSortBy] = useState<SortField>('swing_potential');
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);

  const isWinning = coachingSummary.margin > 0;

  const sortedAnalysis = useMemo(() => {
    return [...swingAnalysis].sort((a, b) => {
      switch (sortBy) {
        case 'swing_potential':
          return b.swing_potential - a.swing_potential;
        case 'closest_gap_seconds':
          return a.closest_gap_seconds - b.closest_gap_seconds;
        case 'point_differential':
          return b.point_differential - a.point_differential;
        default:
          return 0;
      }
    });
  }, [swingAnalysis, sortBy]);

  const riskColorMap: Record<string, string> = {
    high: 'text-red-400',
    medium: 'text-amber-400',
    low: 'text-green-400',
  };

  const riskBgMap: Record<string, string> = {
    high: 'bg-red-500/10 border-red-500/20',
    medium: 'bg-amber-500/10 border-amber-500/20',
    low: 'bg-green-500/10 border-green-500/20',
  };

  // Empty state
  if (!swingAnalysis || swingAnalysis.length === 0) {
    return (
      <div className="glass-card rounded-xl p-8 text-center">
        <svg
          className="w-10 h-10 mx-auto mb-3 text-white/30"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
          />
        </svg>
        <p className="text-white/60">No swing analysis available</p>
        <p className="text-sm text-white/40">
          Run an optimization to see point swing insights
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Coaching Summary Header */}
      <div className="glass-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <svg
              className="w-5 h-5 text-[#D4AF37]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            Coaching Insights
          </h3>

          {/* Score status badge */}
          <span
            className={`
              text-sm font-semibold px-3 py-1 rounded-full
              ${isWinning
                ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                : 'bg-red-500/10 text-red-400 border border-red-500/20'
              }
            `}
          >
            {coachingSummary.score_status}
          </span>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-[#0C2340]/50 rounded-lg p-3 text-center">
            <p
              className={`text-2xl font-bold ${isWinning ? 'text-green-400' : 'text-red-400'}`}
            >
              {coachingSummary.margin > 0 ? '+' : ''}
              {coachingSummary.margin}
            </p>
            <p className="text-xs text-white/50">Margin</p>
          </div>
          <div className="bg-[#0C2340]/50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-[#D4AF37]">
              +{coachingSummary.total_swing_potential}
            </p>
            <p className="text-xs text-white/50">Swing Potential</p>
          </div>
          <div className="bg-[#0C2340]/50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-amber-400">
              {coachingSummary.risk_events.length}
            </p>
            <p className="text-xs text-white/50">At-Risk Events</p>
          </div>
        </div>
      </div>

      {/* Top Opportunities */}
      {coachingSummary.top_opportunities.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-sm font-semibold text-green-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
            Top Opportunities
          </h4>
          <div className="space-y-2">
            {coachingSummary.top_opportunities.map((opp) => (
              <div
                key={opp.event}
                className="bg-green-500/5 border border-green-500/15 rounded-lg p-3"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm text-white font-medium">
                      {opp.event}
                    </p>
                    <p className="text-xs text-white/50 mt-1">
                      {opp.recommendation}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-green-400 flex-shrink-0 ml-3">
                    +{opp.swing_potential} pts
                  </span>
                </div>
                {opp.closest_gap_seconds > 0 && (
                  <p className="text-xs text-green-400/60 mt-1">
                    Gap: {opp.closest_gap_seconds.toFixed(1)}s to next place
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Risk Events */}
      {coachingSummary.risk_events.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-sm font-semibold text-amber-400 uppercase tracking-wider mb-3 flex items-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
            Risk Events
          </h4>
          <div className="space-y-2">
            {coachingSummary.risk_events.map((risk) => (
              <div
                key={risk.event}
                className={`rounded-lg p-3 border ${riskBgMap[risk.risk_level] ?? riskBgMap.medium}`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-white font-medium">
                        {risk.event}
                      </p>
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded ${riskColorMap[risk.risk_level] ?? riskColorMap.medium} bg-white/5`}
                      >
                        {risk.risk_level}
                      </span>
                    </div>
                    <p className="text-xs text-white/50 mt-1">
                      {risk.recommendation}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-red-400 flex-shrink-0 ml-3">
                    -{Math.abs(risk.swing_potential)} pts
                  </span>
                </div>
                {risk.closest_gap_seconds > 0 && (
                  <p className="text-xs text-amber-400/60 mt-1">
                    Opponent within {risk.closest_gap_seconds.toFixed(1)}s
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* All Events - Sorted Analysis */}
      <div className="glass-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-white/80 uppercase tracking-wider">
            All Events
          </h4>
          <div className="flex items-center gap-1">
            <span className="text-xs text-white/40 mr-2">Sort:</span>
            {(
              [
                { key: 'swing_potential', label: 'Swing' },
                { key: 'closest_gap_seconds', label: 'Gap' },
                { key: 'point_differential', label: 'Diff' },
              ] as { key: SortField; label: string }[]
            ).map((opt) => (
              <button
                key={opt.key}
                onClick={() => setSortBy(opt.key)}
                className={`
                  text-xs px-2 py-1 rounded transition-colors
                  ${sortBy === opt.key
                    ? 'bg-[#D4AF37]/20 text-[#D4AF37]'
                    : 'text-white/40 hover:text-white/60'
                  }
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-1">
          {sortedAnalysis.map((ev) => {
            const isExpanded = expandedEvent === ev.event;

            return (
              <div key={ev.event}>
                <button
                  onClick={() =>
                    setExpandedEvent(isExpanded ? null : ev.event)
                  }
                  className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-white/[0.04] transition-colors text-left"
                >
                  {/* Expand indicator */}
                  <svg
                    className={`w-3.5 h-3.5 text-white/30 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 5l7 7-7 7"
                    />
                  </svg>

                  {/* Event name */}
                  <span className="text-sm text-white font-medium flex-1 min-w-0 truncate">
                    {ev.event}
                  </span>

                  {/* Score */}
                  <span className="text-xs text-white/40 flex-shrink-0">
                    <span className="text-[#D4AF37]">{ev.seton_points}</span>
                    <span className="mx-1">-</span>
                    <span className="text-[#7C8B9A]">{ev.opponent_points}</span>
                  </span>

                  {/* Point differential */}
                  <span
                    className={`
                      text-xs font-semibold flex-shrink-0 w-12 text-right
                      ${ev.point_differential > 0
                        ? 'text-green-400'
                        : ev.point_differential < 0
                          ? 'text-red-400'
                          : 'text-white/30'
                      }
                    `}
                  >
                    {ev.point_differential > 0 ? '+' : ''}
                    {ev.point_differential}
                  </span>

                  {/* Risk badge */}
                  <span
                    className={`
                      w-2 h-2 rounded-full flex-shrink-0
                      ${ev.risk_level === 'high'
                        ? 'bg-red-400'
                        : ev.risk_level === 'medium'
                          ? 'bg-amber-400'
                          : 'bg-green-400'
                      }
                    `}
                  />
                </button>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="ml-7 mr-3 mb-2 p-3 bg-[#0C2340]/50 rounded-lg animate-fade-in">
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-white/40">Swing Potential:</span>
                        <span className="ml-2 text-[#D4AF37] font-medium">
                          +{ev.swing_potential} pts
                        </span>
                      </div>
                      <div>
                        <span className="text-white/40">Closest Gap:</span>
                        <span className="ml-2 text-white/70 font-medium">
                          {ev.closest_gap_seconds.toFixed(1)}s
                        </span>
                      </div>
                      <div>
                        <span className="text-white/40">Risk Level:</span>
                        <span
                          className={`ml-2 font-medium ${riskColorMap[ev.risk_level] ?? riskColorMap.medium}`}
                        >
                          {ev.risk_level.charAt(0).toUpperCase() +
                            ev.risk_level.slice(1)}
                        </span>
                      </div>
                      <div>
                        <span className="text-white/40">Differential:</span>
                        <span
                          className={`ml-2 font-medium ${ev.point_differential >= 0 ? 'text-green-400' : 'text-red-400'}`}
                        >
                          {ev.point_differential > 0 ? '+' : ''}
                          {ev.point_differential}
                        </span>
                      </div>
                    </div>
                    {ev.recommendation && (
                      <p className="text-xs text-white/50 mt-2 border-t border-white/5 pt-2">
                        {ev.recommendation}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Focus Recommendations */}
      {coachingSummary.focus_recommendations.length > 0 && (
        <div className="glass-card rounded-xl p-5">
          <h4 className="text-sm font-semibold text-[#D4AF37] uppercase tracking-wider mb-3 flex items-center gap-2">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
              />
            </svg>
            Focus Recommendations
          </h4>
          <ul className="space-y-2">
            {coachingSummary.focus_recommendations.map((rec, idx) => (
              <li
                key={idx}
                className="flex items-start gap-2 text-sm text-white/70"
              >
                <span className="text-[#D4AF37] mt-0.5 flex-shrink-0">
                  &#8226;
                </span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
