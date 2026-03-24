"use client";

import { useState, useMemo } from "react";
import { useAppStore } from "@/lib/store";
import { useShallow } from "zustand/react/shallow";

type Tab = "lock" | "exclude" | "override";

/**
 * WhatIfPanel — Coach controls for lock/exclude/time-override before optimization.
 *
 * Reads swimmer roster from setonTeam.data, surfaces three tabs:
 *   1. Lock:     Pin a swimmer into an event (max 3 locks)
 *   2. Exclude:  Scratch a swimmer entirely
 *   3. Override: Change a seed time for a specific swimmer-event
 */
export default function WhatIfPanel() {
  const {
    setonTeam,
    coachLockedEvents,
    excludedSwimmers,
    swimmerTimeOverrides,
    lockSwimmerEvent,
    unlockSwimmerEvent,
    clearAllLocks,
    toggleSwimmerExcluded,
    updateSwimmerTime,
  } = useAppStore(
    useShallow((s) => ({
      setonTeam: s.setonTeam,
      coachLockedEvents: s.coachLockedEvents,
      excludedSwimmers: s.excludedSwimmers,
      swimmerTimeOverrides: s.swimmerTimeOverrides,
      lockSwimmerEvent: s.lockSwimmerEvent,
      unlockSwimmerEvent: s.unlockSwimmerEvent,
      clearAllLocks: s.clearAllLocks,
      toggleSwimmerExcluded: s.toggleSwimmerExcluded,
      updateSwimmerTime: s.updateSwimmerTime,
    })),
  );

  const [activeTab, setActiveTab] = useState<Tab>("lock");
  const [searchQuery, setSearchQuery] = useState("");
  const [overrideSwimmer, setOverrideSwimmer] = useState("");
  const [overrideEvent, setOverrideEvent] = useState("");
  const [overrideTime, setOverrideTime] = useState("");

  // Derive swimmers and their events from roster data
  const swimmerMap = useMemo(() => {
    if (!setonTeam?.data) return new Map<string, string[]>();
    const map = new Map<string, string[]>();
    for (const entry of setonTeam.data) {
      const existing = map.get(entry.swimmer) || [];
      if (!existing.includes(entry.event)) {
        existing.push(entry.event);
      }
      map.set(entry.swimmer, existing);
    }
    return map;
  }, [setonTeam?.data]);

  const swimmers = useMemo(() => {
    const all = Array.from(swimmerMap.keys()).sort();
    if (!searchQuery.trim()) return all;
    const q = searchQuery.toLowerCase();
    return all.filter((s) => s.toLowerCase().includes(q));
  }, [swimmerMap, searchQuery]);

  // Flatten locks for display
  const flatLocks = useMemo(
    () =>
      coachLockedEvents.flatMap((lock) =>
        lock.events.map((event) => ({ swimmer: lock.swimmer, event })),
      ),
    [coachLockedEvents],
  );

  const isLocked = (swimmer: string, event: string) =>
    flatLocks.some((l) => l.swimmer === swimmer && l.event === event);

  const totalModifications =
    flatLocks.length + excludedSwimmers.length + swimmerTimeOverrides.length;

  if (!setonTeam?.data || setonTeam.data.length === 0) {
    return null; // Don't render until roster is loaded
  }

  const handleAddOverride = () => {
    if (!overrideSwimmer || !overrideEvent || !overrideTime) return;
    updateSwimmerTime(overrideSwimmer, overrideEvent, overrideTime);
    setOverrideTime("");
  };

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "lock", label: "Lock", count: flatLocks.length },
    { key: "exclude", label: "Exclude", count: excludedSwimmers.length },
    {
      key: "override",
      label: "Override",
      count: swimmerTimeOverrides.length,
    },
  ];

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-[var(--navy-500)]">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">What-If Mode</h3>
          {totalModifications > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-[var(--gold-500)] text-[var(--navy-900)]">
              {totalModifications} active
            </span>
          )}
        </div>
        <p className="text-xs text-white/40 mt-1">
          Lock assignments, scratch swimmers, or override seed times
        </p>
      </div>

      {/* Active Modifications Chips */}
      {totalModifications > 0 && (
        <div className="px-4 pt-3 flex flex-wrap gap-1.5">
          {flatLocks.map((l) => (
            <button
              key={`lock-${l.swimmer}-${l.event}`}
              onClick={() => unlockSwimmerEvent(l.swimmer, l.event)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-blue-500/20 text-blue-300 border border-blue-400/30 hover:bg-blue-500/30 transition-colors"
              title={`Unlock ${l.swimmer} from ${l.event}`}
            >
              <svg
                className="w-3 h-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
              {l.swimmer.split(" ").pop()} → {l.event.replace(/^(Girls |Boys )/, "")}
              <span className="ml-0.5 text-blue-400/60">&times;</span>
            </button>
          ))}
          {excludedSwimmers.map((s) => (
            <button
              key={`excl-${s}`}
              onClick={() => toggleSwimmerExcluded(s)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-red-500/20 text-red-300 border border-red-400/30 hover:bg-red-500/30 transition-colors"
              title={`Include ${s}`}
            >
              <svg
                className="w-3 h-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                />
              </svg>
              {s}
              <span className="ml-0.5 text-red-400/60">&times;</span>
            </button>
          ))}
          {swimmerTimeOverrides.map((o) => (
            <button
              key={`ovr-${o.swimmer}-${o.event}`}
              onClick={() => updateSwimmerTime(o.swimmer, o.event, "")}
              className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs bg-amber-500/20 text-amber-300 border border-amber-400/30 hover:bg-amber-500/30 transition-colors"
              title={`Remove override for ${o.swimmer}`}
            >
              <svg
                className="w-3 h-3"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {o.swimmer.split(" ").pop()} {o.event.replace(/^(Girls |Boys )/, "")} → {o.time}
              <span className="ml-0.5 text-amber-400/60">&times;</span>
            </button>
          ))}
        </div>
      )}

      {/* Tab Bar */}
      <div className="flex border-b border-[var(--navy-600)] mx-4 mt-3">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? "border-[var(--gold-500)] text-white"
                : "border-transparent text-white/40 hover:text-white/60"
            }`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] bg-white/10">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {/* ── Lock Tab ── */}
        {activeTab === "lock" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs text-white/50">
                Pin a swimmer to an event (max 3). The optimizer will keep these
                assignments fixed.
              </p>
              {flatLocks.length > 0 && (
                <button
                  onClick={clearAllLocks}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  Clear all
                </button>
              )}
            </div>

            {flatLocks.length >= 3 && (
              <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                <p className="text-xs text-amber-300">
                  Maximum 3 locks reached. Remove one to add another.
                </p>
              </div>
            )}

            {/* Search */}
            <input
              type="text"
              placeholder="Search swimmers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--navy-800)] border border-[var(--navy-600)] text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[var(--gold-500)]/50"
            />

            {/* Swimmer List */}
            <div className="max-h-60 overflow-y-auto space-y-1 scrollbar-thin">
              {swimmers.map((swimmer) => {
                const events = swimmerMap.get(swimmer) || [];
                const isExcluded = excludedSwimmers.includes(swimmer);
                return (
                  <div
                    key={swimmer}
                    className={`rounded-lg border ${isExcluded ? "border-red-500/20 bg-red-500/5 opacity-50" : "border-[var(--navy-600)] bg-[var(--navy-800)]"}`}
                  >
                    <div className="px-3 py-2">
                      <p
                        className={`text-sm font-medium ${isExcluded ? "text-red-300 line-through" : "text-white"}`}
                      >
                        {swimmer}
                      </p>
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {events.map((event) => {
                          const locked = isLocked(swimmer, event);
                          return (
                            <button
                              key={event}
                              onClick={() =>
                                locked
                                  ? unlockSwimmerEvent(swimmer, event)
                                  : lockSwimmerEvent(swimmer, event)
                              }
                              disabled={
                                !locked &&
                                (flatLocks.length >= 3 || isExcluded)
                              }
                              className={`px-2 py-0.5 rounded text-xs transition-colors ${
                                locked
                                  ? "bg-blue-500/30 text-blue-200 border border-blue-400/40"
                                  : "bg-[var(--navy-700)] text-white/50 hover:text-white/70 hover:bg-[var(--navy-600)] disabled:opacity-30 disabled:cursor-not-allowed"
                              }`}
                              title={
                                locked
                                  ? `Unlock ${event}`
                                  : `Lock ${swimmer} into ${event}`
                              }
                            >
                              {locked && (
                                <span className="mr-1 text-blue-300">
                                  &#128274;
                                </span>
                              )}
                              {event.replace(/^(Girls |Boys )/, "")}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                );
              })}
              {swimmers.length === 0 && (
                <p className="text-sm text-white/30 text-center py-4">
                  {searchQuery ? "No swimmers match" : "No roster loaded"}
                </p>
              )}
            </div>
          </div>
        )}

        {/* ── Exclude Tab ── */}
        {activeTab === "exclude" && (
          <div className="space-y-3">
            <p className="text-xs text-white/50">
              Scratch swimmers from the lineup. They won&apos;t be assigned to
              any events.
            </p>

            {/* Search */}
            <input
              type="text"
              placeholder="Search swimmers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[var(--navy-800)] border border-[var(--navy-600)] text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[var(--gold-500)]/50"
            />

            <div className="max-h-60 overflow-y-auto space-y-1 scrollbar-thin">
              {swimmers.map((swimmer) => {
                const isExcluded = excludedSwimmers.includes(swimmer);
                const eventCount = (swimmerMap.get(swimmer) || []).length;
                return (
                  <button
                    key={swimmer}
                    onClick={() => toggleSwimmerExcluded(swimmer)}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-colors ${
                      isExcluded
                        ? "bg-red-500/15 border border-red-500/30 text-red-300"
                        : "bg-[var(--navy-800)] border border-[var(--navy-600)] text-white hover:bg-[var(--navy-700)]"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-4 h-4 rounded border flex items-center justify-center ${
                          isExcluded
                            ? "bg-red-500 border-red-400"
                            : "border-[var(--navy-500)]"
                        }`}
                      >
                        {isExcluded && (
                          <svg
                            className="w-3 h-3 text-white"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={3}
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        )}
                      </div>
                      <span
                        className={isExcluded ? "line-through" : ""}
                      >
                        {swimmer}
                      </span>
                    </div>
                    <span className="text-xs text-white/30">
                      {eventCount} event{eventCount !== 1 ? "s" : ""}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Override Tab ── */}
        {activeTab === "override" && (
          <div className="space-y-3">
            <p className="text-xs text-white/50">
              Override a seed time. Use this if a swimmer has a projected time
              different from the psych sheet (e.g., recent practice time, injury
              adjustment).
            </p>

            {/* Override Form */}
            <div className="space-y-2 p-3 rounded-lg bg-[var(--navy-800)] border border-[var(--navy-600)]">
              <select
                value={overrideSwimmer}
                onChange={(e) => {
                  setOverrideSwimmer(e.target.value);
                  setOverrideEvent("");
                }}
                className="w-full px-3 py-2 rounded-lg bg-[var(--navy-700)] border border-[var(--navy-600)] text-white text-sm focus:outline-none focus:border-[var(--gold-500)]/50"
              >
                <option value="">Select swimmer...</option>
                {Array.from(swimmerMap.keys())
                  .sort()
                  .map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
              </select>

              {overrideSwimmer && (
                <select
                  value={overrideEvent}
                  onChange={(e) => setOverrideEvent(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--navy-700)] border border-[var(--navy-600)] text-white text-sm focus:outline-none focus:border-[var(--gold-500)]/50"
                >
                  <option value="">Select event...</option>
                  {(swimmerMap.get(overrideSwimmer) || []).map((ev) => (
                    <option key={ev} value={ev}>
                      {ev}
                    </option>
                  ))}
                </select>
              )}

              {overrideSwimmer && overrideEvent && (
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="New time (e.g., 25.43 or 1:05.20)"
                    value={overrideTime}
                    onChange={(e) => setOverrideTime(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddOverride()}
                    className="flex-1 px-3 py-2 rounded-lg bg-[var(--navy-700)] border border-[var(--navy-600)] text-white text-sm placeholder:text-white/30 focus:outline-none focus:border-[var(--gold-500)]/50"
                  />
                  <button
                    onClick={handleAddOverride}
                    disabled={!overrideTime}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-[var(--gold-500)] text-[var(--navy-900)] hover:bg-[var(--gold-400)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Set
                  </button>
                </div>
              )}
            </div>

            {/* Active Overrides List */}
            {swimmerTimeOverrides.length > 0 && (
              <div className="space-y-1">
                <p className="text-xs text-white/40 font-medium">
                  Active overrides
                </p>
                {swimmerTimeOverrides.map((o) => (
                  <div
                    key={`${o.swimmer}-${o.event}`}
                    className="flex items-center justify-between px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20"
                  >
                    <div className="text-sm">
                      <span className="text-amber-200 font-medium">
                        {o.swimmer}
                      </span>
                      <span className="text-white/40 mx-1.5">in</span>
                      <span className="text-white/70">
                        {o.event.replace(/^(Girls |Boys )/, "")}
                      </span>
                      <span className="text-white/40 mx-1.5">&rarr;</span>
                      <span className="text-amber-300 font-mono font-bold">
                        {o.time}
                      </span>
                    </div>
                    <button
                      onClick={() =>
                        updateSwimmerTime(o.swimmer, o.event, "")
                      }
                      className="text-amber-400/60 hover:text-amber-300 text-lg leading-none"
                      title="Remove override"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
