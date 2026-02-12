'use client';

import { useState, useMemo } from 'react';

interface SwimmerQualification {
  swimmer: string;
  grade: number;
  qualifications: {
    event: string;
    best_time: number;
    standard: number;
    status: 'qualified' | 'close' | 'needs_work';
    gap: number;
  }[];
}

interface QualifyingTrackerProps {
  swimmers: SwimmerQualification[];
}

type StatusFilter = 'all' | 'qualified' | 'close' | 'needs_work';

function formatTime(seconds: number): string {
  if (seconds >= 60) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, '0')}`;
  }
  return `${seconds.toFixed(1)}s`;
}

function gradeLabel(grade: number): string {
  switch (grade) {
    case 9:
      return '9th';
    case 10:
      return '10th';
    case 11:
      return '11th';
    case 12:
      return '12th';
    default:
      return `${grade}`;
  }
}

export default function QualifyingTracker({
  swimmers,
}: QualifyingTrackerProps) {
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [expandedSwimmer, setExpandedSwimmer] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  // Aggregate stats
  const stats = useMemo(() => {
    let qualified = 0;
    let close = 0;
    let needsWork = 0;

    swimmers.forEach((s) => {
      s.qualifications.forEach((q) => {
        switch (q.status) {
          case 'qualified':
            qualified++;
            break;
          case 'close':
            close++;
            break;
          case 'needs_work':
            needsWork++;
            break;
        }
      });
    });

    return { qualified, close, needsWork };
  }, [swimmers]);

  // Filtered and searched swimmers
  const filteredSwimmers = useMemo(() => {
    let result = swimmers;

    // Filter by status
    if (filter !== 'all') {
      result = result.filter((s) =>
        s.qualifications.some((q) => q.status === filter)
      );
    }

    // Filter by search
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (s) =>
          s.swimmer.toLowerCase().includes(q) ||
          s.qualifications.some((qual) =>
            qual.event.toLowerCase().includes(q)
          )
      );
    }

    return result;
  }, [swimmers, filter, search]);

  const statusIcon: Record<string, string> = {
    qualified: 'text-green-400',
    close: 'text-amber-400',
    needs_work: 'text-red-400',
  };

  const statusLabel: Record<string, string> = {
    qualified: 'Qualified',
    close: 'Close',
    needs_work: 'Needs Work',
  };

  // Empty state
  if (!swimmers || swimmers.length === 0) {
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
            d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
          />
        </svg>
        <p className="text-white/60">No qualifying data available</p>
        <p className="text-sm text-white/40">
          Upload swimmer data to track championship qualifying times
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with stats */}
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
                d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
              />
            </svg>
            Championship Qualifying Tracker
          </h3>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-[#0C2340]/50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-green-400">
              {stats.qualified}
            </p>
            <p className="text-xs text-white/50">Qualified</p>
          </div>
          <div className="bg-[#0C2340]/50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-amber-400">{stats.close}</p>
            <p className="text-xs text-white/50">Close</p>
          </div>
          <div className="bg-[#0C2340]/50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-400">
              {stats.needsWork}
            </p>
            <p className="text-xs text-white/50">Needs Work</p>
          </div>
        </div>
      </div>

      {/* Filters and search */}
      <div className="glass-card rounded-xl p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 w-full sm:w-auto">
            <svg
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search swimmers or events..."
              className="w-full bg-[#0C2340]/50 border border-white/10 rounded-lg py-2 pl-10 pr-4 text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#D4AF37]/50 transition-colors"
            />
          </div>

          {/* Status filter buttons */}
          <div className="flex gap-1">
            {(
              [
                { key: 'all', label: 'All' },
                { key: 'qualified', label: 'Qualified' },
                { key: 'close', label: 'Close' },
                { key: 'needs_work', label: 'Needs Work' },
              ] as { key: StatusFilter; label: string }[]
            ).map((opt) => (
              <button
                key={opt.key}
                onClick={() => setFilter(opt.key)}
                className={`
                  text-xs px-3 py-1.5 rounded-lg transition-colors font-medium
                  ${filter === opt.key
                    ? 'bg-[#D4AF37]/20 text-[#D4AF37]'
                    : 'text-white/40 hover:text-white/60 hover:bg-white/[0.04]'
                  }
                `}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Swimmer list */}
      {filteredSwimmers.length === 0 ? (
        <div className="glass-card rounded-xl p-6 text-center">
          <p className="text-sm text-white/40">
            No swimmers match the current filter
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredSwimmers.map((swimmer) => {
            const isExpanded = expandedSwimmer === swimmer.swimmer;
            const qualCount = swimmer.qualifications.filter(
              (q) => q.status === 'qualified'
            ).length;
            const totalCount = swimmer.qualifications.length;

            // Filter qualifications if a specific status filter is active
            const visibleQuals =
              filter === 'all'
                ? swimmer.qualifications
                : swimmer.qualifications.filter((q) => q.status === filter);

            return (
              <div
                key={swimmer.swimmer}
                className="glass-card rounded-xl overflow-hidden"
              >
                {/* Swimmer header (always visible) */}
                <button
                  onClick={() =>
                    setExpandedSwimmer(
                      isExpanded ? null : swimmer.swimmer
                    )
                  }
                  className="w-full flex items-center gap-3 p-4 hover:bg-white/[0.03] transition-colors text-left"
                >
                  {/* Expand arrow */}
                  <svg
                    className={`w-4 h-4 text-white/30 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
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

                  {/* Swimmer name and grade */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-white truncate">
                        {swimmer.swimmer}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[#1a3a5c] text-white/50">
                        {gradeLabel(swimmer.grade)}
                      </span>
                    </div>
                  </div>

                  {/* Qualification summary */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs text-white/40">
                      {qualCount}/{totalCount} qualified
                    </span>
                    {/* Mini progress bar */}
                    <div className="w-16 h-1.5 bg-[#1a3a5c] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#D4AF37] to-[#C99700] rounded-full transition-all"
                        style={{
                          width: `${totalCount > 0 ? (qualCount / totalCount) * 100 : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </button>

                {/* Expanded qualification details */}
                {isExpanded && (
                  <div className="px-4 pb-4 space-y-2 animate-fade-in">
                    {visibleQuals.map((qual) => {
                      // Compute progress percentage: how close they are to standard
                      // For "qualified" (gap <= 0): 100%
                      // For others: clamp between 0% and 99%
                      const progressPct =
                        qual.status === 'qualified'
                          ? 100
                          : qual.standard > 0
                            ? Math.max(
                                0,
                                Math.min(
                                  99,
                                  ((qual.standard - qual.gap) / qual.standard) * 100
                                )
                              )
                            : 0;

                      return (
                        <div
                          key={qual.event}
                          className="bg-[#0C2340]/50 rounded-lg p-3"
                        >
                          <div className="flex items-center gap-3 mb-2">
                            {/* Status dot */}
                            <span
                              className={`
                                w-2.5 h-2.5 rounded-full flex-shrink-0
                                ${qual.status === 'qualified'
                                  ? 'bg-green-400'
                                  : qual.status === 'close'
                                    ? 'bg-amber-400'
                                    : 'bg-red-400'
                                }
                              `}
                            />

                            {/* Event name */}
                            <span className="text-sm text-white font-medium flex-1">
                              {qual.event}
                            </span>

                            {/* Times */}
                            <span className="text-xs text-white/60">
                              {formatTime(qual.best_time)}
                            </span>
                            <span className="text-xs text-white/30">/</span>
                            <span className="text-xs text-white/40">
                              {formatTime(qual.standard)}
                            </span>

                            {/* Gap */}
                            <span
                              className={`
                                text-xs font-semibold min-w-[48px] text-right
                                ${statusIcon[qual.status]}
                              `}
                            >
                              {qual.gap <= 0 ? '' : '+'}
                              {qual.gap.toFixed(1)}s
                            </span>
                          </div>

                          {/* Progress bar */}
                          <div className="w-full h-1.5 bg-[#1a3a5c] rounded-full overflow-hidden">
                            <div
                              className={`
                                h-full rounded-full transition-all
                                ${qual.status === 'qualified'
                                  ? 'bg-green-400'
                                  : qual.status === 'close'
                                    ? 'bg-amber-400'
                                    : 'bg-red-400'
                                }
                              `}
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>

                          {/* Status label */}
                          <div className="flex justify-between mt-1">
                            <span
                              className={`text-xs ${statusIcon[qual.status]}`}
                            >
                              {statusLabel[qual.status]}
                            </span>
                            <span className="text-xs text-white/30">
                              {progressPct.toFixed(0)}%
                            </span>
                          </div>
                        </div>
                      );
                    })}

                    {visibleQuals.length === 0 && (
                      <p className="text-xs text-white/30 text-center py-2">
                        No events match the current filter
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
