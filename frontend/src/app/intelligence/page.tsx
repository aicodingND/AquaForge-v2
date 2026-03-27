"use client";

import { useState } from "react";
import Link from "next/link";
import { getApiBase } from "@/lib/api";

interface TrajectoryData {
  swimmer: string;
  event: string;
  trend: string;
  improvement_rate: number;
  has_plateaued: boolean;
  data_points: { date: string; time: number; is_predicted: boolean }[];
  predicted_times: { date: string; time: number; confidence: number }[];
}

interface PsychProfile {
  swimmer: string;
  clutch_factor: number;
  consistency: number;
  rivalry_boost: number;
  home_advantage: number;
  strong_opponents: string[];
  weak_opponents: string[];
  best_meet_types: string[];
  avoid_pressure_events: boolean;
  sample_size: number;
  confidence: number;
}

interface CoachTendencyData {
  coach_name: string;
  team_name: string;
  rests_stars_in_relays: number;
  front_loads_lineup: number;
  predictable_star_placement: number;
  adapts_to_opponent: number;
  uses_exhibition_strategically: number;
  favorite_events_for_stars: string[];
  avoided_events: string[];
  sample_size: number;
  confidence: number;
}

type Tab = "trajectory" | "psychological" | "coach";

const API_BASE = getApiBase();

async function fetchIntelligence<T>(path: string): Promise<T> {
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  const headers: Record<string, string> = {};
  if (apiKey) headers["X-API-Key"] = apiKey;

  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function TrendBadge({ trend }: { trend: string }) {
  const colors: Record<string, string> = {
    improving: "bg-green-500/20 text-green-400 border-green-500/30",
    stable: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    declining: "bg-red-500/20 text-red-400 border-red-500/30",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs border ${colors[trend] || colors.stable}`}>
      {trend}
    </span>
  );
}

function PercentBar({ value, label, color = "gold" }: { value: number; label: string; color?: string }) {
  const pct = Math.round(value * 100);
  const barColor = color === "gold" ? "bg-[var(--gold-400)]" : "bg-blue-400";
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-white/60">{label}</span>
        <span className="text-white font-medium">{pct}%</span>
      </div>
      <div className="h-2 bg-[var(--navy-600)] rounded-full overflow-hidden">
        <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function IntelligencePage() {
  const [tab, setTab] = useState<Tab>("trajectory");
  const [swimmerId, setSwimmerId] = useState("");
  const [teamName, setTeamName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Results
  const [trajectories, setTrajectories] = useState<TrajectoryData[]>([]);
  const [trajectoryName, setTrajectoryName] = useState("");
  const [profile, setProfile] = useState<PsychProfile | null>(null);
  const [tendency, setTendency] = useState<CoachTendencyData | null>(null);
  const [tendencyMeetCount, setTendencyMeetCount] = useState(0);

  async function loadTrajectory() {
    if (!swimmerId) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchIntelligence<{
        swimmer_name: string;
        trajectories: TrajectoryData[];
      }>(`/intelligence/trajectory/${swimmerId}`);
      setTrajectories(data.trajectories);
      setTrajectoryName(data.swimmer_name);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load trajectory");
    } finally {
      setLoading(false);
    }
  }

  async function loadPsychological() {
    if (!swimmerId) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchIntelligence<{
        swimmer_name: string;
        profile: PsychProfile;
      }>(`/intelligence/psychological/${swimmerId}`);
      setProfile(data.profile);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  }

  async function loadCoachTendency() {
    if (!teamName) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchIntelligence<{
        tendency: CoachTendencyData;
        meet_count: number;
      }>(`/intelligence/coach-tendency/${encodeURIComponent(teamName)}`);
      setTendency(data.tendency);
      setTendencyMeetCount(data.meet_count);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load tendency");
    } finally {
      setLoading(false);
    }
  }

  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "trajectory", label: "Trajectory", icon: "📈" },
    { key: "psychological", label: "Psych Profile", icon: "🧠" },
    { key: "coach", label: "Coach Tendency", icon: "📋" },
  ];

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Intelligence</h1>
          <p className="text-white/50 text-sm mt-1">
            AI-powered analysis from historical meet data
          </p>
        </div>
        <Link href="/history" className="text-sm text-[var(--gold-400)] hover:underline">
          View Historical Data
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => { setTab(t.key); setError(""); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-[var(--gold-500)] text-[var(--navy-900)]"
                : "bg-[var(--navy-600)] text-white/60 hover:text-white"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="glass-card p-6">
        {tab === "coach" ? (
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-sm text-white/60 block mb-1">Team Name</label>
              <input
                type="text"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                placeholder="e.g. Collegiate, St Christopher's"
                className="w-full px-4 py-2 bg-[var(--navy-600)] border border-[var(--navy-500)] rounded-lg text-white placeholder:text-white/30 focus:outline-none focus:border-[var(--gold-400)]"
                onKeyDown={(e) => e.key === "Enter" && loadCoachTendency()}
              />
            </div>
            <button
              onClick={loadCoachTendency}
              disabled={loading || !teamName}
              className="btn btn-gold disabled:opacity-50"
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>
        ) : (
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-sm text-white/60 block mb-1">Swimmer ID</label>
              <input
                type="number"
                value={swimmerId}
                onChange={(e) => setSwimmerId(e.target.value)}
                placeholder="Enter swimmer database ID"
                className="w-full px-4 py-2 bg-[var(--navy-600)] border border-[var(--navy-500)] rounded-lg text-white placeholder:text-white/30 focus:outline-none focus:border-[var(--gold-400)]"
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    tab === "trajectory" ? loadTrajectory() : loadPsychological();
                  }
                }}
              />
            </div>
            <button
              onClick={tab === "trajectory" ? loadTrajectory : loadPsychological}
              disabled={loading || !swimmerId}
              className="btn btn-gold disabled:opacity-50"
            >
              {loading ? "Analyzing..." : "Analyze"}
            </button>
          </div>
        )}
        <p className="text-xs text-white/30 mt-2">
          {tab === "coach"
            ? "Search by team name or abbreviation. Requires historical meet data in database."
            : "Find swimmer IDs on the History page. Requires historical meet data in database."}
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="glass-card p-4 border border-red-500/30 bg-red-500/10">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Trajectory Results */}
      {tab === "trajectory" && trajectories.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white">
            {trajectoryName} — {trajectories.length} Event{trajectories.length !== 1 ? "s" : ""}
          </h2>
          {trajectories.map((t, i) => (
            <div key={i} className="glass-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-white">{t.event}</h3>
                <TrendBadge trend={t.trend} />
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <p className="text-white/50 text-xs">Data Points</p>
                  <p className="text-white font-bold">{t.data_points.length}</p>
                </div>
                <div>
                  <p className="text-white/50 text-xs">Improvement Rate</p>
                  <p className={`font-bold ${t.improvement_rate < 0 ? "text-green-400" : t.improvement_rate > 0 ? "text-red-400" : "text-white"}`}>
                    {t.improvement_rate < 0 ? "" : "+"}{t.improvement_rate.toFixed(3)} s/mo
                  </p>
                </div>
                <div>
                  <p className="text-white/50 text-xs">Plateaued</p>
                  <p className="text-white font-bold">{t.has_plateaued ? "Yes" : "No"}</p>
                </div>
                <div>
                  <p className="text-white/50 text-xs">Best Time</p>
                  <p className="text-white font-bold">
                    {t.data_points.length > 0
                      ? Math.min(...t.data_points.map((p) => p.time)).toFixed(2)
                      : "—"}
                  </p>
                </div>
              </div>

              {/* Simple time log */}
              {t.data_points.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-white/40 text-xs">
                        <th className="text-left py-1">Date</th>
                        <th className="text-right py-1">Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {t.data_points.slice(-8).map((dp, j) => (
                        <tr key={j} className="border-t border-[var(--navy-600)]">
                          <td className="py-1 text-white/60">{dp.date}</td>
                          <td className="py-1 text-right text-white font-mono">{dp.time.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Predictions */}
              {t.predicted_times.length > 0 && (
                <div className="mt-4 pt-4 border-t border-[var(--navy-500)]">
                  <p className="text-xs text-white/40 mb-2">Predicted Times</p>
                  <div className="flex gap-4">
                    {t.predicted_times.map((pt, j) => (
                      <div key={j} className="bg-[var(--navy-600)] rounded-lg px-3 py-2 text-center">
                        <p className="text-xs text-white/40">{pt.date}</p>
                        <p className="text-white font-mono font-bold">{pt.time.toFixed(2)}</p>
                        <p className="text-xs text-white/30">{Math.round(pt.confidence * 100)}% conf</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Psychological Profile Results */}
      {tab === "psychological" && profile && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">{profile.swimmer}</h2>
            <div className="text-xs text-white/40">
              {profile.sample_size} samples | {Math.round(profile.confidence * 100)}% confidence
            </div>
          </div>

          <div className="space-y-4 mb-6">
            <PercentBar value={profile.clutch_factor / 1.5} label={`Clutch Factor (${profile.clutch_factor.toFixed(2)})`} />
            <PercentBar value={profile.consistency} label="Consistency" color="blue" />
            <PercentBar value={profile.rivalry_boost / 1.3} label={`Rivalry Boost (${profile.rivalry_boost.toFixed(2)})`} />
            <PercentBar value={profile.home_advantage / 1.1} label={`Home Advantage (${profile.home_advantage.toFixed(2)})`} color="blue" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {profile.strong_opponents.length > 0 && (
              <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-4">
                <p className="text-xs text-green-400 font-medium mb-2">Performs Well Against</p>
                <div className="flex flex-wrap gap-1">
                  {profile.strong_opponents.map((o) => (
                    <span key={o} className="text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded">{o}</span>
                  ))}
                </div>
              </div>
            )}
            {profile.weak_opponents.length > 0 && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                <p className="text-xs text-red-400 font-medium mb-2">Struggles Against</p>
                <div className="flex flex-wrap gap-1">
                  {profile.weak_opponents.map((o) => (
                    <span key={o} className="text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded">{o}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {profile.avoid_pressure_events && (
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
              <p className="text-sm text-amber-400">
                This swimmer may struggle under pressure. Consider lower-stakes event assignments for championship meets.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Coach Tendency Results */}
      {tab === "coach" && tendency && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">{tendency.team_name}</h2>
              <p className="text-xs text-white/40">Coach: {tendency.coach_name}</p>
            </div>
            <div className="text-xs text-white/40">
              {tendencyMeetCount} meets analyzed | {Math.round(tendency.confidence * 100)}% confidence
            </div>
          </div>

          <div className="space-y-4 mb-6">
            <PercentBar value={tendency.predictable_star_placement} label="Predictability" />
            <PercentBar value={tendency.front_loads_lineup} label="Front-Loads Lineup" color="blue" />
            <PercentBar value={tendency.rests_stars_in_relays} label="Rests Stars in Relays" />
            <PercentBar value={tendency.adapts_to_opponent} label="Adapts to Opponent" color="blue" />
            <PercentBar value={tendency.uses_exhibition_strategically} label="Strategic Exhibition Use" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tendency.favorite_events_for_stars.length > 0 && (
              <div className="bg-[var(--navy-600)] rounded-lg p-4">
                <p className="text-xs text-[var(--gold-400)] font-medium mb-2">Star Swimmer Events</p>
                <div className="flex flex-wrap gap-1">
                  {tendency.favorite_events_for_stars.map((e) => (
                    <span key={e} className="text-xs bg-[var(--gold-500)]/20 text-[var(--gold-400)] px-2 py-0.5 rounded">{e}</span>
                  ))}
                </div>
              </div>
            )}
            {tendency.avoided_events.length > 0 && (
              <div className="bg-[var(--navy-600)] rounded-lg p-4">
                <p className="text-xs text-white/40 font-medium mb-2">Typically Conceded Events</p>
                <div className="flex flex-wrap gap-1">
                  {tendency.avoided_events.map((e) => (
                    <span key={e} className="text-xs bg-white/10 text-white/60 px-2 py-0.5 rounded">{e}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && !error &&
        ((tab === "trajectory" && trajectories.length === 0) ||
         (tab === "psychological" && !profile) ||
         (tab === "coach" && !tendency)) && (
        <div className="glass-card p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--navy-600)] flex items-center justify-center">
            <span className="text-3xl">{tabs.find((t) => t.key === tab)?.icon}</span>
          </div>
          <p className="text-white/50">
            {tab === "coach"
              ? "Enter a team name to analyze coaching patterns."
              : "Enter a swimmer ID to analyze performance."}
          </p>
          <p className="text-white/30 text-sm mt-2">
            Historical meet data must be imported via ETL pipeline first.
          </p>
        </div>
      )}
    </div>
  );
}
