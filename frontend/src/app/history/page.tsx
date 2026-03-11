"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API_BASE } from "@/lib/config";

interface DbStats {
  total_teams: number;
  total_swimmers: number;
  total_meets: number;
  total_entries: number;
  total_relay_entries: number;
  total_splits: number;
  total_seasons: number;
  total_imports: number;
}

interface TeamSummary {
  id: number;
  name: string;
  short_name: string | null;
  conference: string | null;
  is_user_team: boolean;
}

interface MeetTeamScore {
  team_id: number;
  team_name: string;
  final_score: number | null;
  is_home: boolean;
}

interface MeetSummary {
  id: number;
  name: string;
  meet_date: string;
  season_name: string | null;
  meet_type: string;
  teams: MeetTeamScore[];
}

interface SwimmerSummary {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  gender: string | null;
}

type Tab = "overview" | "teams" | "meets" | "swimmers";

export default function HistoryPage() {
  const [stats, setStats] = useState<DbStats | null>(null);
  const [teams, setTeams] = useState<TeamSummary[]>([]);
  const [meets, setMeets] = useState<MeetSummary[]>([]);
  const [swimmers, setSwimmers] = useState<SwimmerSummary[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [swimmerSearch, setSwimmerSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const [statsRes, teamsRes, meetsRes] = await Promise.all([
          fetch(`${API_BASE}/historical/stats`),
          fetch(`${API_BASE}/historical/teams`),
          fetch(`${API_BASE}/historical/meets?page_size=50`),
        ]);
        if (statsRes.ok) setStats(await statsRes.json());
        if (teamsRes.ok) setTeams(await teamsRes.json());
        if (meetsRes.ok) {
          const data = await meetsRes.json();
          setMeets(data.items || []);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load historical data");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const searchSwimmers = async () => {
    if (!swimmerSearch.trim()) return;
    try {
      const res = await fetch(
        `${API_BASE}/historical/swimmers?name=${encodeURIComponent(swimmerSearch)}&page_size=50`
      );
      if (res.ok) {
        const data = await res.json();
        setSwimmers(data.items || []);
        setTab("swimmers");
      }
    } catch {
      // Silently handle search errors
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-2xl font-bold text-white mb-4">Historical Data</h1>
        <div className="glass-card p-12 text-center">
          <div className="animate-pulse text-white/50">Loading database...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8">
        <h1 className="text-2xl font-bold text-white mb-4">Historical Data</h1>
        <div className="glass-card p-12 text-center">
          <p className="text-red-400 mb-2">Failed to connect to historical database</p>
          <p className="text-white/50 text-sm">{error}</p>
          <p className="text-white/30 text-xs mt-4">
            Run ETL pipeline first: python -m swim_ai_reflex.backend.etl.pipeline
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Historical Data</h1>
        <p className="text-white/50 text-sm mt-1">
          Browse imported HyTek meet data, teams, swimmers, and time progressions
        </p>
      </div>

      {/* Swimmer Search */}
      <div className="glass-card p-4">
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Search swimmers by name..."
            value={swimmerSearch}
            onChange={(e) => setSwimmerSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && searchSwimmers()}
            className="flex-1 px-4 py-2 rounded-lg bg-[var(--navy-700)] border border-[var(--navy-500)] text-white placeholder-white/30 focus:outline-none focus:border-[var(--gold-400)]"
          />
          <button
            onClick={searchSwimmers}
            className="btn btn-gold px-6"
          >
            Search
          </button>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 bg-[var(--navy-800)] p-1 rounded-lg w-fit">
        {(["overview", "teams", "meets", "swimmers"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              tab === t
                ? "bg-[var(--gold-400)] text-[var(--navy-900)]"
                : "text-white/60 hover:text-white"
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "overview" && stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Teams", value: stats.total_teams, icon: "🏫" },
            { label: "Swimmers", value: stats.total_swimmers, icon: "🏊" },
            { label: "Meets", value: stats.total_meets, icon: "📋" },
            { label: "Entries", value: stats.total_entries, icon: "⏱️" },
            { label: "Relay Entries", value: stats.total_relay_entries, icon: "🔄" },
            { label: "Splits", value: stats.total_splits, icon: "📊" },
            { label: "Seasons", value: stats.total_seasons, icon: "📅" },
            { label: "Imports", value: stats.total_imports, icon: "📥" },
          ].map((s) => (
            <div key={s.label} className="glass-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <span>{s.icon}</span>
                <span className="text-white/50 text-sm">{s.label}</span>
              </div>
              <p className="text-white font-bold text-2xl">
                {s.value.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      {tab === "teams" && (
        <div className="glass-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--navy-500)]">
                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium">Name</th>
                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium">Code</th>
                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium">Conference</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((t) => (
                <tr
                  key={t.id}
                  className="border-b border-[var(--navy-700)] hover:bg-[var(--navy-700)]/50"
                >
                  <td className="px-4 py-3 text-white font-medium">
                    {t.is_user_team && (
                      <span className="text-[var(--gold-400)] mr-1" title="Your team">
                        *
                      </span>
                    )}
                    {t.name}
                  </td>
                  <td className="px-4 py-3 text-white/60 font-mono text-sm">
                    {t.short_name || "—"}
                  </td>
                  <td className="px-4 py-3 text-white/60">{t.conference || "—"}</td>
                </tr>
              ))}
              {teams.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-white/30">
                    No teams found. Run ETL pipeline to import data.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === "meets" && (
        <div className="space-y-3">
          {meets.map((m) => (
            <div key={m.id} className="glass-card p-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-white">{m.name}</h3>
                  <p className="text-white/50 text-sm">
                    {new Date(m.meet_date).toLocaleDateString()} &middot;{" "}
                    {m.meet_type} &middot; {m.season_name || "Unknown season"}
                  </p>
                </div>
              </div>
              {m.teams.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-3">
                  {m.teams.map((t) => (
                    <span
                      key={t.team_id}
                      className="px-2 py-1 rounded bg-[var(--navy-700)] text-white/70 text-xs"
                    >
                      {t.team_name}
                      {t.final_score != null && (
                        <span className="ml-1 text-[var(--gold-400)]">
                          {t.final_score}
                        </span>
                      )}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {meets.length === 0 && (
            <div className="glass-card p-8 text-center text-white/30">
              No meets found. Run ETL pipeline to import data.
            </div>
          )}
        </div>
      )}

      {tab === "swimmers" && (
        <div className="glass-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--navy-500)]">
                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium">Name</th>
                <th className="px-4 py-3 text-left text-white/60 text-sm font-medium">Gender</th>
                <th className="px-4 py-3 text-right text-white/60 text-sm font-medium">Profile</th>
              </tr>
            </thead>
            <tbody>
              {swimmers.map((s) => (
                <tr
                  key={s.id}
                  className="border-b border-[var(--navy-700)] hover:bg-[var(--navy-700)]/50"
                >
                  <td className="px-4 py-3 text-white font-medium">{s.full_name}</td>
                  <td className="px-4 py-3 text-white/60">{s.gender || "—"}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/history/swimmer?id=${s.id}`}
                      className="text-[var(--gold-400)] hover:underline text-sm"
                    >
                      View Profile &rarr;
                    </Link>
                  </td>
                </tr>
              ))}
              {swimmers.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-white/30">
                    {swimmerSearch
                      ? "No swimmers found matching your search."
                      : "Search for a swimmer to see results."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
