"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Scoreboard from "@/components/live/Scoreboard";
import ResultEntry from "@/components/live/ResultEntry";
import ClinchMonitor from "@/components/live/ClinchMonitor";
import api from "@/lib/api";

export default function LiveDashboard() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-white/50 animate-pulse">
          Loading Live Dashboard...
        </div>
      }
    >
      <LiveDashboardContent />
    </Suspense>
  );
}

interface EventStatusData {
  completed: string[];
  in_progress: string[];
  upcoming: string[];
  progress: { completed: number; total: number; percent: number };
}

function LiveDashboardContent() {
  const searchParams = useSearchParams();
  const [meetName, setMeetName] = useState(
    searchParams.get("meet") || "vcac_2026",
  );

  // Dashboard state
  const [loading, setLoading] = useState(true);
  const [standings, setStandings] = useState<any>(null);
  const [teams, setTeams] = useState<string[]>([]);
  const [eventStatus, setEventStatus] = useState<EventStatusData | null>(null);
  const [swingData, setSwingData] = useState<any>(null);

  const loadData = useCallback(async () => {
    try {
      const [s, status] = await Promise.all([
        api.getLiveStandings(meetName).catch(() => null),
        api.getLiveStatus(meetName).catch(() => null),
      ]);

      if (s) {
        setStandings(s);
        if (s.team_totals) {
          setTeams(Object.keys(s.team_totals));
        }
      }
      if (status) {
        setEventStatus(status);
      }

      // Load swing data (non-blocking — OK if it fails)
      api
        .getSwingEvents(meetName, "SST")
        .then(setSwingData)
        .catch(() => {});
    } catch (err) {
      console.error("Failed to load live data", err);
    } finally {
      setLoading(false);
    }
  }, [meetName]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRefresh = () => {
    setLoading(true);
    loadData();
  };

  if (loading && !standings) {
    return (
      <div className="p-8 text-center text-white/50 animate-pulse">
        Loading Live Dashboard...
      </div>
    );
  }

  // Meet not initialized — show setup prompt
  if (!standings && !loading) {
    return <MeetSetup meetName={meetName} onMeetNameChange={setMeetName} />;
  }

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <span className="text-red-500 animate-pulse">●</span> Live
            Dashboard
          </h1>
          <p className="text-white/50 text-sm mt-1">
            Real-time tracking for {meetName}
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={meetName}
            onChange={(e) => setMeetName(e.target.value)}
            className="input py-1 px-3 text-sm w-32"
            placeholder="Meet ID"
          />
          <button onClick={handleRefresh} className="btn btn-sm btn-outline">
            Refresh
          </button>
        </div>
      </div>

      {/* Scoreboard */}
      <Scoreboard
        scores={standings.team_totals || {}}
        projected={standings.projected_remaining || {}}
        currentEvent={standings.events_completed || 0}
        totalEvents={
          (standings.events_completed || 0) + (standings.events_remaining || 0)
        }
      />

      {/* Event Status Bar */}
      {eventStatus && <EventStatusPanel status={eventStatus} />}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Data Entry + Swing Events */}
        <div className="space-y-6">
          <ResultEntry
            meetName={meetName}
            teams={teams}
            onResultRecorded={loadData}
          />

          {/* Swing Events Summary */}
          {swingData?.swing_events && swingData.swing_events.length > 0 && (
            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-white mb-3">
                High-Value Events
              </h3>
              <div className="space-y-2">
                {swingData.swing_events.slice(0, 5).map((ev: any) => (
                  <div
                    key={ev.event || ev.name}
                    className="flex items-center justify-between text-sm p-2 rounded bg-white/[0.03]"
                  >
                    <span className="text-white/80 truncate">
                      {ev.event || ev.name}
                    </span>
                    <span className="text-[var(--gold-400)] font-medium flex-shrink-0 ml-2">
                      +{Math.round(ev.swing_potential || ev.points || 0)} pts
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Analysis */}
        <div className="lg:col-span-2 space-y-6">
          <ClinchMonitor meetName={meetName} targetTeam="SST" />

          {/* Standings Detail Table */}
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold text-white mb-4">
              Standings Detail
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-white/50 border-b border-white/10">
                    <th className="text-left py-2">#</th>
                    <th className="text-left py-2">Team</th>
                    <th className="text-right py-2">Actual</th>
                    <th className="text-right py-2">Proj. Remaining</th>
                    <th className="text-right py-2">Total Proj.</th>
                  </tr>
                </thead>
                <tbody>
                  {standings.sorted_standings?.map(
                    (row: any, idx: number) => (
                      <tr
                        key={row.team}
                        className={`border-b border-white/5 text-white/80 ${
                          row.team === "SST" || row.team?.toLowerCase().includes("seton")
                            ? "bg-[var(--gold-500)]/5"
                            : ""
                        }`}
                      >
                        <td className="py-2 text-white/40">{idx + 1}</td>
                        <td className="py-2 font-medium">{row.team}</td>
                        <td className="text-right py-2">
                          {Math.round(row.actual)}
                        </td>
                        <td className="text-right py-2 text-white/50">
                          {Math.round(row.projected)}
                        </td>
                        <td className="text-right py-2 font-bold text-[var(--gold-400)]">
                          {Math.round(row.total)}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/** Event Status Panel — shows completed, in-progress, and upcoming events */
function EventStatusPanel({ status }: { status: EventStatusData }) {
  return (
    <div className="glass-card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          Event Progress
        </h3>
        <span className="text-xs text-white/50">
          {status.progress.completed}/{status.progress.total} events (
          {status.progress.percent}%)
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {status.completed.map((ev) => (
          <span
            key={ev}
            className="text-xs px-2 py-1 rounded bg-green-500/15 text-green-400 border border-green-500/20"
          >
            {ev}
          </span>
        ))}
        {status.in_progress.map((ev) => (
          <span
            key={ev}
            className="text-xs px-2 py-1 rounded bg-amber-500/15 text-amber-400 border border-amber-500/20 animate-pulse"
          >
            {ev}
          </span>
        ))}
        {status.upcoming.map((ev) => (
          <span
            key={ev}
            className="text-xs px-2 py-1 rounded bg-white/5 text-white/30 border border-white/10"
          >
            {ev}
          </span>
        ))}
      </div>
    </div>
  );
}

/** Meet Setup — shown when the meet hasn't been initialized yet */
function MeetSetup({
  meetName,
  onMeetNameChange,
}: {
  meetName: string;
  onMeetNameChange: (name: string) => void;
}) {
  return (
    <div className="p-8 max-w-lg mx-auto">
      <h2 className="text-xl text-white mb-4 text-center">
        Meet &quot;{meetName}&quot; Not Found
      </h2>
      <p className="text-white/50 mb-6 text-center">
        This meet hasn&apos;t been initialized for live tracking yet.
      </p>
      <div className="glass-card p-6 space-y-4">
        <div>
          <label className="block text-xs text-white/50 mb-1">
            Meet Name / ID
          </label>
          <input
            type="text"
            value={meetName}
            onChange={(e) => onMeetNameChange(e.target.value)}
            className="input w-full"
            placeholder="e.g. vcac_2026"
          />
        </div>
        <p className="text-sm text-white/40">
          Initialize the meet via the API first:
        </p>
        <pre className="text-xs bg-[var(--navy-900)] p-3 rounded text-white/60 overflow-x-auto">
          POST /api/v1/live/initialize{"\n"}
          {JSON.stringify(
            {
              meet_name: meetName,
              meet_profile: "vcac_championship",
              target_team: "SST",
              entries: ["...psych sheet data..."],
            },
            null,
            2,
          )}
        </pre>
      </div>
    </div>
  );
}
