"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { API_BASE } from "@/lib/config";

interface SwimmerBest {
  event_name: string;
  best_time: number;
  mean_time: number | null;
  sample_size: number;
}

interface SwimmerProfile {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  gender: string | null;
  seasons: { season_name: string; team_name: string; grade: number | null }[];
  bests: SwimmerBest[];
  total_entries: number;
}

interface TimeRecord {
  time: number;
  seed_time: number | null;
  place: number | null;
  points: number;
  event: string;
  meet: string;
  meet_date: string;
  meet_type: string;
}

function formatTime(seconds: number): string {
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins}:${secs.padStart(5, "0")}`;
  }
  return seconds.toFixed(2);
}

function SwimmerDetailContent() {
  const searchParams = useSearchParams();
  const swimmerId = searchParams.get("id");

  const [profile, setProfile] = useState<SwimmerProfile | null>(null);
  const [times, setTimes] = useState<TimeRecord[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!swimmerId) return;
    const load = async () => {
      try {
        setLoading(true);
        const [profileRes, timesRes] = await Promise.all([
          fetch(`${API_BASE}/historical/swimmers/${swimmerId}`),
          fetch(`${API_BASE}/historical/swimmers/${swimmerId}/times`),
        ]);
        if (!profileRes.ok) throw new Error("Swimmer not found");
        setProfile(await profileRes.json());
        if (timesRes.ok) setTimes(await timesRes.json());
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load swimmer");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [swimmerId]);

  if (!swimmerId) {
    return (
      <div className="p-6 lg:p-8">
        <p className="text-white/50">No swimmer ID provided.</p>
        <Link href="/history" className="text-[var(--gold-400)] hover:underline">
          &larr; Back to History
        </Link>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-6 lg:p-8">
        <div className="animate-pulse text-white/50">Loading swimmer profile...</div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="p-6 lg:p-8">
        <p className="text-red-400">{error || "Swimmer not found"}</p>
        <Link href="/history" className="text-[var(--gold-400)] hover:underline mt-2 inline-block">
          &larr; Back to History
        </Link>
      </div>
    );
  }

  // Group times by event for chart-style display
  const eventTimes: Record<string, TimeRecord[]> = {};
  for (const t of times) {
    if (!eventTimes[t.event]) eventTimes[t.event] = [];
    eventTimes[t.event].push(t);
  }
  // Sort each event's times by date
  for (const evts of Object.values(eventTimes)) {
    evts.sort((a, b) => a.meet_date.localeCompare(b.meet_date));
  }

  const eventNames = Object.keys(eventTimes).sort();
  const displayEvent = selectedEvent || eventNames[0] || null;
  const displayTimes = displayEvent ? eventTimes[displayEvent] || [] : [];

  // Simple ASCII time progression chart
  const renderProgressionChart = (records: TimeRecord[]) => {
    if (records.length === 0) return null;
    const minTime = Math.min(...records.map((r) => r.time));
    const maxTime = Math.max(...records.map((r) => r.time));
    const range = maxTime - minTime || 1;
    const barWidth = 30;

    return (
      <div className="font-mono text-xs space-y-1">
        {records.map((r, i) => {
          const pct = (maxTime - r.time) / range;
          const filled = Math.round(pct * barWidth);
          return (
            <div key={i} className="flex items-center gap-2">
              <span className="text-white/40 w-20 text-right shrink-0">
                {r.meet_date.slice(5)}
              </span>
              <span className="text-[var(--gold-400)] w-16 text-right shrink-0">
                {formatTime(r.time)}
              </span>
              <span className="text-[var(--gold-400)]">
                {"#".repeat(filled)}
              </span>
              <span className="text-[var(--navy-500)]">
                {".".repeat(Math.max(0, barWidth - filled))}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="p-6 lg:p-8 space-y-6">
      <Link href="/history" className="text-[var(--gold-400)] hover:underline text-sm">
        &larr; Back to History
      </Link>

      {/* Swimmer Header */}
      <div className="glass-card p-6">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[var(--gold-400)] to-[var(--gold-500)] flex items-center justify-center text-[var(--navy-900)] font-bold text-xl">
            {profile.first_name[0]}
            {profile.last_name[0]}
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">{profile.full_name}</h1>
            <p className="text-white/50 text-sm">
              {profile.gender === "M" ? "Male" : profile.gender === "F" ? "Female" : "—"} &middot;{" "}
              {profile.total_entries} total entries
            </p>
          </div>
        </div>

        {/* Seasons */}
        {profile.seasons.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {profile.seasons.map((s, i) => (
              <span
                key={i}
                className="px-3 py-1 rounded-full bg-[var(--navy-700)] text-white/70 text-xs"
              >
                {s.season_name} &middot; {s.team_name}
                {s.grade != null && ` (Gr. ${s.grade})`}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Best Times */}
      {profile.bests.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-[var(--navy-500)]">
            <h2 className="font-semibold text-white">Best Times</h2>
          </div>
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--navy-600)]">
                <th className="px-4 py-2 text-left text-white/60 text-sm">Event</th>
                <th className="px-4 py-2 text-right text-white/60 text-sm">Best</th>
                <th className="px-4 py-2 text-right text-white/60 text-sm">Average</th>
                <th className="px-4 py-2 text-right text-white/60 text-sm">Swims</th>
              </tr>
            </thead>
            <tbody>
              {profile.bests.map((b) => (
                <tr
                  key={b.event_name}
                  className="border-b border-[var(--navy-700)] hover:bg-[var(--navy-700)]/50 cursor-pointer"
                  onClick={() => setSelectedEvent(b.event_name)}
                >
                  <td className="px-4 py-2 text-white font-medium">{b.event_name}</td>
                  <td className="px-4 py-2 text-right text-[var(--gold-400)] font-mono">
                    {formatTime(b.best_time)}
                  </td>
                  <td className="px-4 py-2 text-right text-white/60 font-mono">
                    {b.mean_time ? formatTime(b.mean_time) : "—"}
                  </td>
                  <td className="px-4 py-2 text-right text-white/60">{b.sample_size}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Time Progression */}
      {eventNames.length > 0 && (
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-white">Time Progression</h2>
            <select
              value={displayEvent || ""}
              onChange={(e) => setSelectedEvent(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-[var(--navy-700)] border border-[var(--navy-500)] text-white text-sm focus:outline-none focus:border-[var(--gold-400)]"
            >
              {eventNames.map((e) => (
                <option key={e} value={e}>
                  {e}
                </option>
              ))}
            </select>
          </div>

          {displayTimes.length > 0 ? (
            <>
              {renderProgressionChart(displayTimes)}
              <div className="mt-4 text-white/30 text-xs">
                Showing {displayTimes.length} swims for {displayEvent}. Best:{" "}
                {formatTime(Math.min(...displayTimes.map((t) => t.time)))}
              </div>
            </>
          ) : (
            <p className="text-white/30 text-sm">No time data for this event.</p>
          )}
        </div>
      )}

      {/* Full Time Log */}
      {times.length > 0 && (
        <div className="glass-card overflow-hidden">
          <div className="p-4 border-b border-[var(--navy-500)]">
            <h2 className="font-semibold text-white">All Times ({times.length})</h2>
          </div>
          <div className="max-h-96 overflow-y-auto">
            <table className="w-full">
              <thead className="sticky top-0 bg-[var(--navy-800)]">
                <tr className="border-b border-[var(--navy-600)]">
                  <th className="px-4 py-2 text-left text-white/60 text-xs">Date</th>
                  <th className="px-4 py-2 text-left text-white/60 text-xs">Meet</th>
                  <th className="px-4 py-2 text-left text-white/60 text-xs">Event</th>
                  <th className="px-4 py-2 text-right text-white/60 text-xs">Time</th>
                  <th className="px-4 py-2 text-right text-white/60 text-xs">Place</th>
                  <th className="px-4 py-2 text-right text-white/60 text-xs">Points</th>
                </tr>
              </thead>
              <tbody>
                {times
                  .sort((a, b) => b.meet_date.localeCompare(a.meet_date))
                  .map((t, i) => (
                    <tr
                      key={i}
                      className="border-b border-[var(--navy-700)] hover:bg-[var(--navy-700)]/50"
                    >
                      <td className="px-4 py-2 text-white/60 text-sm">{t.meet_date}</td>
                      <td className="px-4 py-2 text-white text-sm truncate max-w-[200px]">
                        {t.meet}
                      </td>
                      <td className="px-4 py-2 text-white/80 text-sm">{t.event}</td>
                      <td className="px-4 py-2 text-right text-[var(--gold-400)] font-mono text-sm">
                        {formatTime(t.time)}
                      </td>
                      <td className="px-4 py-2 text-right text-white/60 text-sm">
                        {t.place || "—"}
                      </td>
                      <td className="px-4 py-2 text-right text-white/60 text-sm">
                        {t.points || "—"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SwimmerDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="p-6 lg:p-8">
          <div className="animate-pulse text-white/50">Loading...</div>
        </div>
      }
    >
      <SwimmerDetailContent />
    </Suspense>
  );
}
