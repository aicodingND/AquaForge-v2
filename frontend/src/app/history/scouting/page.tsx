"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getApiBase } from "@/lib/api";

const API_BASE = getApiBase();

function getHeaders(): Record<string, string> {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  return apiKey ? { "X-API-Key": apiKey } : {};
}

interface ScoutedTeam {
  id: number;
  name: string;
  short_name: string | null;
  swimmer_count: number;
  is_user_team: boolean;
}

interface OptimizerEntry {
  swimmer: string;
  event: string;
  time: number;
  team: string;
  grade: number;
  gender: string;
}

export default function ScoutingPage() {
  const [teams, setTeams] = useState<ScoutedTeam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Selected team detail
  const [selectedTeam, setSelectedTeam] = useState<ScoutedTeam | null>(null);
  const [roster, setRoster] = useState<OptimizerEntry[]>([]);
  const [rosterLoading, setRosterLoading] = useState(false);

  useEffect(() => {
    loadTeams();
  }, []);

  async function loadTeams() {
    try {
      const res = await fetch(`${API_BASE}/historical/scouted-teams`, {
        headers: getHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setTeams(data.teams || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load teams");
    } finally {
      setLoading(false);
    }
  }

  async function loadTeamRoster(team: ScoutedTeam) {
    setSelectedTeam(team);
    setRosterLoading(true);
    setRoster([]);
    try {
      const res = await fetch(
        `${API_BASE}/historical/scouting/${team.id}/optimizer-data`,
        { headers: getHeaders() }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRoster(data.data || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load roster");
    } finally {
      setRosterLoading(false);
    }
  }

  // Format seconds to MM:SS.ss
  function formatTime(seconds: number): string {
    if (seconds >= 60) {
      const min = Math.floor(seconds / 60);
      const sec = (seconds % 60).toFixed(2).padStart(5, "0");
      return `${min}:${sec}`;
    }
    return seconds.toFixed(2);
  }

  // Group roster by swimmer
  const swimmerMap = new Map<string, OptimizerEntry[]>();
  roster.forEach((entry) => {
    const existing = swimmerMap.get(entry.swimmer) || [];
    existing.push(entry);
    swimmerMap.set(entry.swimmer, existing);
  });

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Opponent Scouting</h1>
          <p className="text-white/50 text-sm mt-1">
            Browse scouted teams and load their data for optimization
          </p>
        </div>
        <Link
          href="/history"
          className="text-sm text-[var(--gold-400)] hover:underline"
        >
          Back to History
        </Link>
      </div>

      {/* Error */}
      {error && (
        <div className="glass-card p-4 border border-red-500/30 bg-red-500/10">
          <p className="text-red-400 text-sm">{error}</p>
          <button
            onClick={() => setError("")}
            className="text-xs text-red-300 mt-1 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="glass-card p-12 text-center">
          <p className="text-white/50">Loading scouted teams...</p>
        </div>
      )}

      {/* No teams */}
      {!loading && teams.length === 0 && (
        <div className="glass-card p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--navy-600)] flex items-center justify-center">
            <span className="text-3xl">🔍</span>
          </div>
          <h2 className="text-lg font-semibold text-white mb-2">
            No Scouted Teams
          </h2>
          <p className="text-white/50 mb-4 max-w-md mx-auto">
            Run the ingestion pipeline to load opponent data from scraped files.
          </p>
          <code className="text-xs text-white/40 bg-[var(--navy-600)] px-3 py-1 rounded">
            python scripts/refresh_opponent_data.py
          </code>
        </div>
      )}

      {/* Team Grid + Detail */}
      {!loading && teams.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Team List */}
          <div className="space-y-2">
            <h2 className="text-sm font-medium text-white/40 uppercase tracking-wider mb-3">
              Teams ({teams.length})
            </h2>
            {teams.map((team) => (
              <button
                key={team.id}
                onClick={() => loadTeamRoster(team)}
                className={`w-full text-left p-4 rounded-xl transition-colors ${
                  selectedTeam?.id === team.id
                    ? "bg-[var(--gold-500)]/20 border border-[var(--gold-500)]/30"
                    : "bg-[var(--navy-700)] hover:bg-[var(--navy-600)] border border-transparent"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p
                      className={`font-medium ${
                        selectedTeam?.id === team.id
                          ? "text-[var(--gold-400)]"
                          : "text-white"
                      }`}
                    >
                      {team.short_name || "—"}{" "}
                      <span className="text-white/50 font-normal">
                        {team.name}
                      </span>
                    </p>
                    <p className="text-xs text-white/40 mt-0.5">
                      {team.swimmer_count} swimmers
                      {team.is_user_team ? " (your team)" : ""}
                    </p>
                  </div>
                  <span className="text-white/20">→</span>
                </div>
              </button>
            ))}
          </div>

          {/* Roster Detail */}
          <div className="lg:col-span-2">
            {selectedTeam ? (
              <div className="glass-card overflow-hidden">
                <div className="p-4 border-b border-[var(--navy-500)] flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-white">
                      {selectedTeam.name}
                    </h3>
                    <p className="text-xs text-white/40">
                      {roster.length} entries across{" "}
                      {swimmerMap.size} swimmers
                    </p>
                  </div>
                  <Link
                    href="/meet"
                    className="text-xs text-[var(--gold-400)] hover:underline"
                  >
                    Use as Opponent →
                  </Link>
                </div>

                {rosterLoading ? (
                  <div className="p-8 text-center text-white/50">
                    Loading roster...
                  </div>
                ) : (
                  <div className="divide-y divide-[var(--navy-600)]">
                    {Array.from(swimmerMap.entries()).map(
                      ([swimmer, entries]) => (
                        <div key={swimmer} className="p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <p className="font-medium text-white">{swimmer}</p>
                            <span className="text-xs px-2 py-0.5 bg-[var(--navy-600)] text-white/40 rounded">
                              {entries[0]?.gender === "F" ? "Girls" : "Boys"} | Gr. {entries[0]?.grade}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {entries
                              .sort((a, b) => a.event.localeCompare(b.event))
                              .map((e, i) => (
                                <span
                                  key={i}
                                  className="text-xs bg-[var(--navy-600)] px-2 py-1 rounded text-white/70"
                                >
                                  {e.event}:{" "}
                                  <span className="font-mono text-white">
                                    {formatTime(e.time)}
                                  </span>
                                </span>
                              ))}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="glass-card p-12 text-center">
                <p className="text-white/40">
                  Select a team to view their scouting roster
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
