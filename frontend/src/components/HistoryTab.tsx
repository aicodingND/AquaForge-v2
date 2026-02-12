'use client';

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query'; // TODO: port dependency — requires `@tanstack/react-query` package (added to package.json)

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';

// ---------------------------------------------------------------------------
// Types mirroring the backend response models
// ---------------------------------------------------------------------------

interface TeamSummary {
  id: number;
  name: string;
  short_name: string | null;
  conference: string | null;
  is_user_team: boolean;
}

interface SeasonSummary {
  id: number;
  name: string;
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
  season_id: number | null;
  season_name: string | null;
  meet_type: string;
  location: string | null;
  pool_course: string;
  teams: MeetTeamScore[];
}

interface EntryResult {
  swimmer_id: number | null;
  swimmer_name: string | null;
  team_name: string | null;
  seed_time: number | null;
  finals_time: number | null;
  place: number | null;
  points: number;
  is_dq: boolean;
  is_exhibition: boolean;
}

interface EventResult {
  event_id: number;
  event_name: string;
  event_number: number | null;
  gender: string | null;
  is_relay: boolean;
  event_category: string | null;
  entries: EntryResult[];
}

interface MeetDetail extends MeetSummary {
  events: EventResult[];
  entry_count: number;
}

interface MeetsResponse {
  items: MeetSummary[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTime(seconds: number): string {
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins}:${secs.padStart(5, '0')}`;
  }
  return seconds.toFixed(2);
}

function meetTypeBadge(type: string): string {
  switch (type) {
    case 'dual':
      return 'Dual';
    case 'championship':
      return 'Champ';
    case 'invitational':
      return 'Invite';
    case 'time_trial':
      return 'TT';
    default:
      return type;
  }
}

function meetTypeColor(type: string): string {
  switch (type) {
    case 'dual':
      return 'bg-blue-500/20 text-blue-300';
    case 'championship':
      return 'bg-[#D4AF37]/20 text-[#D4AF37]';
    case 'invitational':
      return 'bg-purple-500/20 text-purple-300';
    case 'time_trial':
      return 'bg-gray-500/20 text-gray-300';
    default:
      return 'bg-white/10 text-white/60';
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatsBar({ stats }: { stats: DbStats | undefined }) {
  if (!stats) return null;
  const items = [
    { label: 'Teams', value: stats.total_teams },
    { label: 'Meets', value: stats.total_meets },
    { label: 'Swimmers', value: stats.total_swimmers },
    { label: 'Entries', value: stats.total_entries.toLocaleString() },
  ];
  return (
    <div className="grid grid-cols-4 gap-3 mb-5">
      {items.map((item) => (
        <div key={item.label} className="bg-[#0C2340]/60 rounded-lg p-3 text-center">
          <div className="text-lg font-bold text-[#D4AF37]">{item.value}</div>
          <div className="text-xs text-white/50">{item.label}</div>
        </div>
      ))}
    </div>
  );
}

function Selector({
  label,
  value,
  onChange,
  options,
  loading,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  loading?: boolean;
}) {
  return (
    <div>
      <label className="block text-xs text-white/50 mb-1">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="w-full bg-[#0C2340] border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-[#D4AF37]/50 disabled:opacity-50"
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function MeetCard({
  meet,
  isSelected,
  onClick,
}: {
  meet: MeetSummary;
  isSelected: boolean;
  onClick: () => void;
}) {
  // Sort teams by score descending (winner first)
  const sortedTeams = useMemo(
    () =>
      [...meet.teams].sort(
        (a, b) => (b.final_score ?? 0) - (a.final_score ?? 0)
      ),
    [meet.teams]
  );

  return (
    <button
      onClick={onClick}
      className={`w-full text-left rounded-lg p-3 transition-all border ${
        isSelected
          ? 'bg-[#D4AF37]/10 border-[#D4AF37]/30'
          : 'bg-[#0C2340]/40 border-white/5 hover:border-white/15 hover:bg-[#0C2340]/60'
      }`}
    >
      <div className="flex items-start justify-between mb-1.5">
        <h4 className="text-sm font-medium text-white leading-tight pr-2 truncate max-w-[75%]">
          {meet.name}
        </h4>
        <span
          className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full shrink-0 ${meetTypeColor(
            meet.meet_type
          )}`}
        >
          {meetTypeBadge(meet.meet_type)}
        </span>
      </div>
      <div className="text-xs text-white/40 mb-2">
        {new Date(meet.meet_date).toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}
        {meet.location && ` \u2022 ${meet.location}`}
      </div>
      {sortedTeams.length > 0 && (
        <div className="space-y-0.5">
          {sortedTeams.slice(0, 4).map((t, i) => (
            <div key={t.team_id} className="flex justify-between text-xs">
              <span
                className={
                  i === 0 && t.final_score != null
                    ? 'text-[#D4AF37] font-medium'
                    : 'text-white/60'
                }
              >
                {t.team_name}
              </span>
              <span
                className={
                  i === 0 && t.final_score != null
                    ? 'text-[#D4AF37] font-medium'
                    : 'text-white/50'
                }
              >
                {t.final_score != null ? t.final_score : '--'}
              </span>
            </div>
          ))}
          {sortedTeams.length > 4 && (
            <div className="text-[10px] text-white/30 text-right">
              +{sortedTeams.length - 4} more
            </div>
          )}
        </div>
      )}
    </button>
  );
}

function MeetDetailPanel({ meetId }: { meetId: number }) {
  const { data: meet, isLoading, error } = useQuery<MeetDetail>({
    queryKey: ['historical-meet-detail', meetId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/historical/meets/${meetId}`);
      if (!res.ok) throw new Error('Failed to fetch meet detail');
      return res.json();
    },
  });

  if (isLoading) {
    return (
      <div className="space-y-3 animate-pulse">
        <div className="h-6 bg-white/10 rounded w-2/3" />
        <div className="h-4 bg-white/10 rounded w-1/2" />
        <div className="space-y-2 mt-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-white/5 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !meet) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400 text-sm">
          Failed to load meet details
        </p>
      </div>
    );
  }

  // Sort teams by score descending
  const sortedTeams = [...meet.teams].sort(
    (a, b) => (b.final_score ?? 0) - (a.final_score ?? 0)
  );

  // Sort events by event_number
  const sortedEvents = [...meet.events].sort(
    (a, b) => (a.event_number ?? 999) - (b.event_number ?? 999)
  );

  return (
    <div className="space-y-4">
      {/* Meet header */}
      <div>
        <h3 className="text-lg font-semibold text-white">{meet.name}</h3>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span className="text-xs text-white/50">
            {new Date(meet.meet_date).toLocaleDateString('en-US', {
              weekday: 'short',
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
          </span>
          <span
            className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${meetTypeColor(
              meet.meet_type
            )}`}
          >
            {meetTypeBadge(meet.meet_type)}
          </span>
          <span className="text-[10px] text-white/30">{meet.pool_course}</span>
          {meet.location && (
            <span className="text-[10px] text-white/30">{meet.location}</span>
          )}
        </div>
      </div>

      {/* Team scores */}
      {sortedTeams.length > 0 && (
        <div className="bg-[#0C2340]/60 rounded-lg p-3">
          <h4 className="text-xs font-medium text-white/50 uppercase tracking-wider mb-2">
            Final Scores
          </h4>
          <div className="space-y-1.5">
            {sortedTeams.map((t, i) => (
              <div
                key={t.team_id}
                className={`flex justify-between items-center px-2 py-1 rounded ${
                  i === 0 && t.final_score != null
                    ? 'bg-[#D4AF37]/10'
                    : ''
                }`}
              >
                <span
                  className={`text-sm ${
                    i === 0 && t.final_score != null
                      ? 'text-[#D4AF37] font-semibold'
                      : 'text-white/70'
                  }`}
                >
                  {i === 0 && t.final_score != null && (
                    <span className="mr-1.5">1st</span>
                  )}
                  {t.team_name}
                  {t.is_home && (
                    <span className="ml-1.5 text-[10px] text-white/30">
                      (H)
                    </span>
                  )}
                </span>
                <span
                  className={`text-sm font-mono ${
                    i === 0 && t.final_score != null
                      ? 'text-[#D4AF37] font-bold'
                      : 'text-white/50'
                  }`}
                >
                  {t.final_score != null ? t.final_score : '--'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Event results */}
      <div>
        <h4 className="text-xs font-medium text-white/50 uppercase tracking-wider mb-2">
          Events ({meet.entry_count} entries)
        </h4>
        {sortedEvents.length === 0 ? (
          <p className="text-sm text-white/40 text-center py-4">
            No event data available
          </p>
        ) : (
          <div className="space-y-2">
            {sortedEvents.map((ev) => (
              <EventCard key={ev.event_id} event={ev} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function EventCard({ event }: { event: EventResult }) {
  const [expanded, setExpanded] = useState(false);

  // Sort entries by place, then by finals_time
  const sortedEntries = useMemo(
    () =>
      [...event.entries].sort((a, b) => {
        if (a.place != null && b.place != null) return a.place - b.place;
        if (a.place != null) return -1;
        if (b.place != null) return 1;
        return (a.finals_time ?? 9999) - (b.finals_time ?? 9999);
      }),
    [event.entries]
  );

  const topEntries = expanded ? sortedEntries : sortedEntries.slice(0, 3);

  return (
    <div className="bg-[#0C2340]/40 rounded-lg border border-white/5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          {event.event_number != null && (
            <span className="text-[10px] text-white/30 font-mono w-5 text-right">
              #{event.event_number}
            </span>
          )}
          <span className="text-sm text-white font-medium">
            {event.event_name}
          </span>
          {event.is_relay && (
            <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded-full">
              Relay
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-white/30">
            {event.entries.length} entries
          </span>
          <svg
            className={`w-3.5 h-3.5 text-white/30 transition-transform ${
              expanded ? 'rotate-180' : ''
            }`}
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

      {(expanded || sortedEntries.length <= 3) && sortedEntries.length > 0 && (
        <div className="px-3 pb-2">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-white/30">
                <th className="text-left font-medium py-1 w-8">Pl</th>
                <th className="text-left font-medium py-1">Name</th>
                <th className="text-left font-medium py-1">Team</th>
                <th className="text-right font-medium py-1">Time</th>
                <th className="text-right font-medium py-1 w-10">Pts</th>
              </tr>
            </thead>
            <tbody>
              {topEntries.map((entry, idx) => (
                <tr
                  key={idx}
                  className={`border-t border-white/5 ${
                    entry.is_dq ? 'opacity-50' : ''
                  }`}
                >
                  <td className="py-1 text-white/40 font-mono">
                    {entry.is_dq ? 'DQ' : entry.place ?? '--'}
                  </td>
                  <td className="py-1 text-white/80">
                    {entry.swimmer_name ?? 'Unknown'}
                    {entry.is_exhibition && (
                      <span className="ml-1 text-[9px] text-white/30">EX</span>
                    )}
                  </td>
                  <td className="py-1 text-white/50">{entry.team_name ?? ''}</td>
                  <td className="py-1 text-right font-mono text-white/70">
                    {entry.finals_time != null
                      ? formatTime(entry.finals_time)
                      : entry.seed_time != null
                      ? formatTime(entry.seed_time)
                      : '--'}
                  </td>
                  <td className="py-1 text-right text-white/40 font-mono">
                    {entry.points > 0 ? entry.points : ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!expanded && sortedEntries.length > 3 && (
            <button
              onClick={() => setExpanded(true)}
              className="text-[10px] text-[#D4AF37]/70 hover:text-[#D4AF37] mt-1"
            >
              Show all {sortedEntries.length} entries
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function HistoryTabSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="grid grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-[#0C2340]/60 rounded-lg p-3">
            <div className="h-6 bg-white/10 rounded mb-1" />
            <div className="h-3 bg-white/10 rounded w-1/2 mx-auto" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-3">
          <div className="h-10 bg-white/5 rounded" />
          <div className="h-10 bg-white/5 rounded" />
        </div>
        <div className="col-span-2 space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-20 bg-white/5 rounded" />
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main HistoryTab component
// ---------------------------------------------------------------------------

export default function HistoryTab() {
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  const [selectedSeasonId, setSelectedSeasonId] = useState<string>('');
  const [selectedMeetId, setSelectedMeetId] = useState<number | null>(null);
  const [page, setPage] = useState(1);

  // ---- Data fetching ----

  const { data: stats } = useQuery<DbStats>({
    queryKey: ['historical-stats'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/historical/stats`);
      if (!res.ok) throw new Error('Failed to fetch stats');
      return res.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const { data: teams, isLoading: teamsLoading } = useQuery<TeamSummary[]>({
    queryKey: ['historical-teams'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/historical/teams`);
      if (!res.ok) throw new Error('Failed to fetch teams');
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
  });

  const { data: seasons, isLoading: seasonsLoading } = useQuery<
    SeasonSummary[]
  >({
    queryKey: ['historical-seasons'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/historical/seasons`);
      if (!res.ok) throw new Error('Failed to fetch seasons');
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: meetsData,
    isLoading: meetsLoading,
    error: meetsError,
  } = useQuery<MeetsResponse>({
    queryKey: [
      'historical-meets',
      selectedTeamId,
      selectedSeasonId,
      page,
    ],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (selectedTeamId) params.set('team_id', selectedTeamId);
      if (selectedSeasonId) params.set('season_id', selectedSeasonId);
      params.set('page', String(page));
      params.set('page_size', '20');
      const res = await fetch(
        `${API_BASE}/historical/meets?${params.toString()}`
      );
      if (!res.ok) throw new Error('Failed to fetch meets');
      return res.json();
    },
    staleTime: 2 * 60 * 1000,
  });

  // ---- Derived data ----

  const teamOptions = useMemo(
    () =>
      (teams ?? []).map((t) => ({
        value: String(t.id),
        label: t.name,
      })),
    [teams]
  );

  const seasonOptions = useMemo(
    () =>
      (seasons ?? []).map((s) => ({
        value: String(s.id),
        label: s.name,
      })),
    [seasons]
  );

  const meets = meetsData?.items ?? [];
  const totalMeets = meetsData?.total ?? 0;
  const hasMore = meetsData?.has_more ?? false;

  // Reset page when filters change
  const handleTeamChange = (v: string) => {
    setSelectedTeamId(v);
    setPage(1);
    setSelectedMeetId(null);
  };

  const handleSeasonChange = (v: string) => {
    setSelectedSeasonId(v);
    setPage(1);
    setSelectedMeetId(null);
  };

  // ---- Render ----

  const isInitialLoad = teamsLoading && seasonsLoading;
  if (isInitialLoad) return <HistoryTabSkeleton />;

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-1">
          Historical Data
        </h2>
        <p className="text-sm text-white/60">
          Browse meets, scores, and event results from the Hy-Tek database
        </p>
      </div>

      {/* Stats bar */}
      <StatsBar stats={stats} />

      {/* 3-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left sidebar: selectors */}
        <div className="lg:col-span-3 space-y-3">
          <div className="glass-card rounded-xl p-4 space-y-3">
            <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
              Filters
            </h3>
            <Selector
              label="Team"
              value={selectedTeamId}
              onChange={handleTeamChange}
              options={teamOptions}
              loading={teamsLoading}
            />
            <Selector
              label="Season"
              value={selectedSeasonId}
              onChange={handleSeasonChange}
              options={seasonOptions}
              loading={seasonsLoading}
            />
            {(selectedTeamId || selectedSeasonId) && (
              <button
                onClick={() => {
                  setSelectedTeamId('');
                  setSelectedSeasonId('');
                  setPage(1);
                  setSelectedMeetId(null);
                }}
                className="text-xs text-[#D4AF37]/70 hover:text-[#D4AF37] transition-colors"
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Quick summary below filters */}
          <div className="glass-card rounded-xl p-4">
            <div className="text-xs text-white/40">
              {totalMeets > 0
                ? `Showing ${meets.length} of ${totalMeets} meets`
                : 'No meets found'}
            </div>
          </div>
        </div>

        {/* Center: meet list */}
        <div className="lg:col-span-4 space-y-2">
          <div className="glass-card rounded-xl p-4">
            <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider mb-3">
              Meets
            </h3>

            {meetsLoading && (
              <div className="space-y-2 animate-pulse">
                {[1, 2, 3, 4, 5].map((i) => (
                  <div
                    key={i}
                    className="h-20 bg-white/5 rounded-lg"
                  />
                ))}
              </div>
            )}

            {meetsError && (
              <div className="text-center py-6">
                <p className="text-red-400 text-sm">
                  Failed to load meets
                </p>
                <p className="text-xs text-white/30 mt-1">
                  Make sure the API server is running
                </p>
              </div>
            )}

            {!meetsLoading && !meetsError && meets.length === 0 && (
              <div className="text-center py-8">
                <svg
                  className="w-10 h-10 mx-auto mb-2 text-white/15"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                  />
                </svg>
                <p className="text-sm text-white/40">No meets found</p>
                <p className="text-xs text-white/25 mt-1">
                  Try adjusting your filters
                </p>
              </div>
            )}

            {!meetsLoading && !meetsError && meets.length > 0 && (
              <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                {meets.map((meet) => (
                  <MeetCard
                    key={meet.id}
                    meet={meet}
                    isSelected={selectedMeetId === meet.id}
                    onClick={() => setSelectedMeetId(meet.id)}
                  />
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalMeets > 20 && (
              <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="text-xs px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/70 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <span className="text-xs text-white/40">
                  Page {page}
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!hasMore}
                  className="text-xs px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/70 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right: meet detail */}
        <div className="lg:col-span-5">
          <div className="glass-card rounded-xl p-4">
            {selectedMeetId ? (
              <MeetDetailPanel meetId={selectedMeetId} />
            ) : (
              <div className="text-center py-12">
                <svg
                  className="w-12 h-12 mx-auto mb-3 text-white/10"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                  />
                </svg>
                <p className="text-sm text-white/40">
                  Select a meet to view details
                </p>
                <p className="text-xs text-white/25 mt-1">
                  Event results, scores, and entries will appear here
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
