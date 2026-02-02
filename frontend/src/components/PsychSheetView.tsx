"use client";

import { useState, useMemo } from "react";
import { SwimmerEntry } from "@/lib/api";

interface PsychSheetViewProps {
  data: SwimmerEntry[];
  userTeamName?: string;
  showPointProjections?: boolean;
  scoringTable?: number[];
  className?: string;
}

interface EventBreakdown {
  event: string;
  entries: {
    swimmer: string;
    team: string;
    time: string | number;
    place: number;
    points: number;
    isUserTeam: boolean;
  }[];
}

// VCAC 12-place individual scoring (relay = 2x these values)
const DEFAULT_SCORING = [16, 13, 12, 11, 10, 9, 7, 5, 4, 3, 2, 1];

export default function PsychSheetView({
  data,
  userTeamName = "Seton",
  showPointProjections = true,
  scoringTable = DEFAULT_SCORING,
  className = "",
}: PsychSheetViewProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  // Group by event and rank
  const eventBreakdowns = useMemo(() => {
    const eventMap = new Map<string, SwimmerEntry[]>();

    data.forEach((entry) => {
      const existing = eventMap.get(entry.event) || [];
      existing.push(entry);
      eventMap.set(entry.event, existing);
    });

    const breakdowns: EventBreakdown[] = [];

    eventMap.forEach((entries, event) => {
      // Sort by time (handle string times like "1:23.45")
      const sorted = entries.sort((a, b) => {
        const timeA = parseTime(a.time);
        const timeB = parseTime(b.time);
        return timeA - timeB;
      });

      breakdowns.push({
        event,
        entries: sorted.map((entry, idx) => ({
          swimmer: entry.swimmer,
          team: entry.team || "Unknown",
          time: entry.time,
          place: idx + 1,
          points: idx < scoringTable.length ? scoringTable[idx] : 0,
          isUserTeam: (entry.team || "")
            .toLowerCase()
            .includes(userTeamName.toLowerCase()),
        })),
      });
    });

    // Sort events by standard order
    const eventOrder = [
      "200 Medley Relay",
      "200 IM",
      "50 Free",
      "Diving",
      "100 Fly",
      "100 Free",
      "500 Free",
      "200 Free Relay",
      "100 Back",
      "100 Breast",
      "400 Free Relay",
    ];

    return breakdowns.sort((a, b) => {
      const aIdx = eventOrder.findIndex((e) => a.event.includes(e));
      const bIdx = eventOrder.findIndex((e) => b.event.includes(e));
      if (aIdx === -1 && bIdx === -1) return a.event.localeCompare(b.event);
      if (aIdx === -1) return 1;
      if (bIdx === -1) return -1;
      return aIdx - bIdx;
    });
  }, [data, scoringTable, userTeamName]);

  // Calculate user team total points
  const userTeamPoints = useMemo(() => {
    return eventBreakdowns.reduce((total, event) => {
      const userEntries = event.entries.filter((e) => e.isUserTeam);
      // Take top 4 scorers per event (typical championship rule)
      return (
        total + userEntries.slice(0, 4).reduce((sum, e) => sum + e.points, 0)
      );
    }, 0);
  }, [eventBreakdowns]);

  const toggleEvent = (event: string) => {
    const next = new Set(expandedEvents);
    if (next.has(event)) {
      next.delete(event);
    } else {
      next.add(event);
    }
    setExpandedEvents(next);
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-[var(--gold-400)]">📊</span>
          Psych Sheet Rankings
        </h3>

        {showPointProjections && (
          <div className="text-sm">
            <span className="text-white/50">
              Projected {userTeamName} Points:
            </span>
            <span className="text-[var(--gold-400)] font-bold ml-2">
              {userTeamPoints}
            </span>
          </div>
        )}
      </div>

      {/* Event List */}
      <div className="space-y-2">
        {eventBreakdowns.map((breakdown) => {
          const isExpanded = expandedEvents.has(breakdown.event);
          const userEntries = breakdown.entries.filter((e) => e.isUserTeam);
          const topUserPlace = userEntries[0]?.place;

          return (
            <div key={breakdown.event} className="glass-card overflow-hidden">
              {/* Event Header */}
              <button
                type="button"
                onClick={() => toggleEvent(breakdown.event)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className="text-white font-medium">
                    {breakdown.event}
                  </span>
                  <span className="text-xs text-white/40">
                    {breakdown.entries.length} entries
                  </span>
                </div>

                <div className="flex items-center gap-4">
                  {/* User team indicator */}
                  {userEntries.length > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-[var(--gold-400)]">
                        {userTeamName}: {userEntries.length} entries
                      </span>
                      {topUserPlace && topUserPlace <= 3 && (
                        <span className="badge badge-gold text-[10px] py-0">
                          {topUserPlace === 1
                            ? "🥇"
                            : topUserPlace === 2
                              ? "🥈"
                              : "🥉"}
                        </span>
                      )}
                    </div>
                  )}

                  <svg
                    className={`w-4 h-4 text-white/40 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </div>
              </button>

              {/* Expanded Rankings */}
              {isExpanded && (
                <div className="border-t border-[var(--navy-600)] bg-[var(--navy-800)]/50">
                  <table className="w-full">
                    <thead>
                      <tr className="text-xs text-white/50 uppercase tracking-wider">
                        <th className="px-4 py-2 text-left w-12">Place</th>
                        <th className="px-4 py-2 text-left">Swimmer</th>
                        <th className="px-4 py-2 text-left">Team</th>
                        <th className="px-4 py-2 text-right">Time</th>
                        {showPointProjections && (
                          <th className="px-4 py-2 text-right w-16">Pts</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {breakdown.entries.slice(0, 12).map((entry, idx) => (
                        <tr
                          key={idx}
                          className={`border-t border-[var(--navy-700)] ${
                            entry.isUserTeam ? "bg-[var(--gold-muted)]" : ""
                          }`}
                        >
                          <td className="px-4 py-2 text-sm">
                            {entry.place <= 3 ? (
                              <span className="font-bold text-[var(--gold-400)]">
                                {entry.place}
                              </span>
                            ) : (
                              <span className="text-white/60">
                                {entry.place}
                              </span>
                            )}
                          </td>
                          <td
                            className={`px-4 py-2 text-sm font-medium ${
                              entry.isUserTeam
                                ? "text-[var(--gold-400)]"
                                : "text-white"
                            }`}
                          >
                            {entry.swimmer}
                          </td>
                          <td className="px-4 py-2 text-sm text-white/60">
                            {entry.team}
                          </td>
                          <td className="px-4 py-2 text-sm text-right font-mono text-white/80">
                            {entry.time}
                          </td>
                          {showPointProjections && (
                            <td className="px-4 py-2 text-sm text-right font-medium">
                              {entry.points > 0 ? (
                                <span
                                  className={
                                    entry.isUserTeam
                                      ? "text-[var(--gold-400)]"
                                      : "text-white"
                                  }
                                >
                                  +{entry.points}
                                </span>
                              ) : (
                                <span className="text-white/30">—</span>
                              )}
                            </td>
                          )}
                        </tr>
                      ))}
                      {breakdown.entries.length > 12 && (
                        <tr className="border-t border-[var(--navy-700)]">
                          <td
                            colSpan={showPointProjections ? 5 : 4}
                            className="px-4 py-2 text-xs text-white/40 text-center"
                          >
                            +{breakdown.entries.length - 12} more entries
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Helper to parse swim times like "1:23.45" to seconds
function parseTime(time: string | number): number {
  if (typeof time === "number") return time;

  const parts = time.replace(/[^\d:.]/g, "").split(":");
  if (parts.length === 2) {
    // MM:SS.ss format
    return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
  }
  // Just seconds
  return parseFloat(parts[0]) || 999;
}
