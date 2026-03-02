'use client';

import { useState, useMemo, useCallback } from 'react';
import { useAppStore } from '@/lib/store';
import { SwimmerEntry } from '@/lib/api';

interface SwimmerInfo {
  name: string;
  grade: string;
  events: string[];
  available: boolean;
}

export default function SwimmerAvailability() {
  const setonTeam = useAppStore(s => s.setonTeam);
  const [search, setSearch] = useState('');
  const [availability, setAvailability] = useState<Record<string, boolean>>({});

  // Derive unique swimmers from Seton team data
  const swimmers = useMemo<SwimmerInfo[]>(() => {
    if (!setonTeam?.data) return [];

    const swimmerMap = new Map<
      string,
      { events: Set<string>; grade: string }
    >();

    for (const entry of setonTeam.data) {
      const name = entry.swimmer;
      if (!swimmerMap.has(name)) {
        swimmerMap.set(name, { events: new Set(), grade: '' });
      }
      const info = swimmerMap.get(name)!;
      info.events.add(entry.event);
      // Extract grade from team field if present (e.g. "10th", "SR", etc.)
      if (entry.team && !info.grade) {
        info.grade = entry.team;
      }
    }

    return Array.from(swimmerMap.entries())
      .map(([name, info]) => ({
        name,
        grade: info.grade,
        events: Array.from(info.events),
        available: availability[name] !== false, // default to available
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [setonTeam, availability]);

  // Filter swimmers by search query
  const filteredSwimmers = useMemo(() => {
    if (!search.trim()) return swimmers;
    const q = search.toLowerCase();
    return swimmers.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.grade.toLowerCase().includes(q) ||
        s.events.some((e) => e.toLowerCase().includes(q))
    );
  }, [swimmers, search]);

  const availableCount = swimmers.filter((s) => s.available).length;
  const unavailableCount = swimmers.length - availableCount;

  const toggleAvailability = useCallback((name: string) => {
    setAvailability((prev) => ({
      ...prev,
      [name]: prev[name] === false ? true : false,
    }));
  }, []);

  const markAllAvailable = useCallback(() => {
    setAvailability({});
  }, []);

  const markAllUnavailable = useCallback(() => {
    const all: Record<string, boolean> = {};
    swimmers.forEach((s) => {
      all[s.name] = false;
    });
    setAvailability(all);
  }, [swimmers]);

  // Empty state: no team loaded
  if (!setonTeam) {
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
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
        <p className="text-white/60">No team loaded</p>
        <p className="text-sm text-white/40">
          Upload a Seton team file to manage availability
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-5 pb-0">
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
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            Swimmer Availability
          </h3>
          <div className="flex items-center gap-2">
            <button
              onClick={markAllAvailable}
              className="text-xs px-2 py-1 rounded bg-green-500/10 text-green-400 hover:bg-green-500/20 transition-colors"
            >
              All Available
            </button>
            <button
              onClick={markAllUnavailable}
              className="text-xs px-2 py-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
            >
              All Unavailable
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-4">
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
            placeholder="Search swimmers, grades, events..."
            className="w-full bg-[#0C2340]/50 border border-white/10 rounded-lg py-2 pl-10 pr-4 text-sm text-white placeholder-white/30 focus:outline-none focus:border-[#D4AF37]/50 transition-colors"
          />
        </div>
      </div>

      {/* Swimmer list */}
      <div className="max-h-[400px] overflow-y-auto px-5">
        {filteredSwimmers.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-sm text-white/40">
              {search
                ? 'No swimmers match your search'
                : 'No swimmers found in team data'}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {filteredSwimmers.map((swimmer) => (
              <label
                key={swimmer.name}
                className={`
                  flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all
                  hover:bg-white/[0.04]
                  ${!swimmer.available ? 'opacity-60' : ''}
                `}
              >
                {/* Toggle switch */}
                <div className="relative flex-shrink-0">
                  <input
                    type="checkbox"
                    checked={swimmer.available}
                    onChange={() => toggleAvailability(swimmer.name)}
                    className="sr-only peer"
                    aria-label={`Toggle availability for ${swimmer.name}`}
                  />
                  <div
                    className={`
                      w-10 h-5 rounded-full transition-colors
                      ${swimmer.available ? 'bg-[#C99700]' : 'bg-[#1a3a5c]'}
                    `}
                    onClick={() => toggleAvailability(swimmer.name)}
                  >
                    <div
                      className={`
                        absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform
                        ${swimmer.available ? 'left-5' : 'left-0.5'}
                      `}
                    />
                  </div>
                </div>

                {/* Swimmer info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={`
                        text-sm font-medium
                        ${swimmer.available ? 'text-white' : 'text-white/40 line-through'}
                      `}
                    >
                      {swimmer.name}
                    </span>
                    {swimmer.grade && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[#1a3a5c] text-white/50">
                        {swimmer.grade}
                      </span>
                    )}
                  </div>
                </div>

                {/* Event count */}
                <div className="flex-shrink-0 text-right">
                  {swimmer.available ? (
                    <span className="text-xs text-white/40">
                      {swimmer.events.length}{' '}
                      {swimmer.events.length === 1 ? 'event' : 'events'}
                    </span>
                  ) : (
                    <span className="text-xs text-red-400/60">unavail</span>
                  )}
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Summary footer */}
      <div className="p-4 mt-2 border-t border-white/10 flex items-center justify-between">
        <div className="flex items-center gap-4 text-sm">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-400" />
            <span className="text-white/60">
              Available: <span className="text-white font-medium">{availableCount}</span>
            </span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span className="text-white/60">
              Unavailable: <span className="text-white font-medium">{unavailableCount}</span>
            </span>
          </span>
        </div>
        <span className="text-xs text-white/30">
          {swimmers.length} total
        </span>
      </div>
    </div>
  );
}
