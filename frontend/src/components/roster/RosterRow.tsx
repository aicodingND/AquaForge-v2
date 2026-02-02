"use client";

import { useState } from "react";
import { SwimmerEntry } from "@/lib/api";

interface RosterRowProps {
  swimmer: string;
  entries: SwimmerEntry[];
  gender: string;
  isExpanded: boolean;
  isExcluded: boolean;
  lockedEvents: string[];
  canAddLock: boolean;
  showLockControls: boolean;
  showBulkControls: boolean;
  onToggleExpand: () => void;
  onSwimmerToggle?: (swimmer: string, included: boolean) => void;
  onTimeEdit?: (swimmer: string, event: string, newTime: string) => void;
  onLockToggle: (swimmer: string, event: string) => void;
}

export default function RosterRow({
  swimmer,
  entries,
  gender,
  isExpanded,
  isExcluded,
  lockedEvents,
  canAddLock,
  showLockControls,
  showBulkControls,
  onToggleExpand,
  onSwimmerToggle,
  onTimeEdit,
  onLockToggle,
}: RosterRowProps) {
  const [editingEntry, setEditingEntry] = useState<{
    swimmer: string;
    event: string;
  } | null>(null);

  const hasLock = lockedEvents.length > 0;
  const isSwimmerLocked = (event: string): boolean => {
    return lockedEvents.includes(event);
  };

  return (
    <div
      className={`hidden sm:block border-b border-[var(--navy-600)] last:border-b-0 ${
        isExcluded ? "opacity-50" : ""
      }`}
    >
      <div
        className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-[var(--navy-800)] ${
          showBulkControls ? "cursor-pointer" : ""
        }`}
        role="button"
        tabIndex={0}
        onClick={onToggleExpand}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onToggleExpand();
        }}
      >
        {/* Include/Exclude Toggle */}
        {onSwimmerToggle && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onSwimmerToggle(swimmer, isExcluded);
            }}
            className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
              isExcluded
                ? "border-[var(--navy-500)] bg-transparent"
                : "border-[var(--gold-500)] bg-[var(--gold-500)]"
            }`}
          >
            {!isExcluded && (
              <span className="text-[var(--navy-900)] text-xs">✓</span>
            )}
          </button>
        )}

        {/* Lock Icon */}
        {hasLock && (
          <span
            className="text-[var(--gold-400)]"
            title={`Locked: ${lockedEvents.join(", ")}`}
          >
            🔒
          </span>
        )}

        {/* Swimmer Name */}
        <span
          className={`flex-1 font-medium ${hasLock ? "text-[var(--gold-400)]" : "text-white"}`}
        >
          {swimmer}
        </span>

        {/* Gender Badge */}
        {gender && gender !== "U" && (
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              gender === "M"
                ? "bg-blue-500/20 text-blue-300"
                : "bg-pink-500/20 text-pink-300"
            }`}
          >
            {gender}
          </span>
        )}

        {/* Event count */}
        <span className="text-white/40 text-sm">{entries.length} events</span>

        {/* Expand Arrow */}
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

      {/* Expanded Events */}
      {isExpanded && (
        <div className="px-4 pb-3 space-y-2 bg-[var(--navy-800)]/50 animate-fade-in">
          {entries.map((entry, idx) => {
            const isLocked = isSwimmerLocked(entry.event);
            const isEditing =
              editingEntry?.swimmer === swimmer &&
              editingEntry?.event === entry.event;

            return (
              <div
                key={idx}
                className={`flex items-center gap-3 p-2 rounded-lg ${
                  isLocked
                    ? "bg-[var(--gold-muted)] border border-[var(--gold-500)]/30"
                    : "bg-[var(--navy-700)]"
                }`}
              >
                {/* Lock Toggle */}
                {showLockControls && (
                  <button
                    type="button"
                    onClick={() => onLockToggle(swimmer, entry.event)}
                    disabled={!isLocked && !canAddLock}
                    className={`p-1 rounded transition-colors ${
                      isLocked
                        ? "text-[var(--gold-400)] hover:text-[var(--gold-300)]"
                        : canAddLock
                          ? "text-white/40 hover:text-white"
                          : "text-white/20 cursor-not-allowed"
                    }`}
                    title={
                      isLocked
                        ? "Unlock event"
                        : canAddLock
                          ? "Lock event (coach assigned)"
                          : "Max locks reached"
                    }
                  >
                    {isLocked ? "🔒" : "🔓"}
                  </button>
                )}

                {/* Event Name */}
                <span className="flex-1 text-sm text-white">
                  {entry.event}
                </span>

                {/* Time (editable) */}
                {isEditing && onTimeEdit ? (
                  <input
                    type="text"
                    defaultValue={String(entry.time)}
                    autoFocus
                    aria-label={`Edit time for ${entry.event}`}
                    placeholder="Time"
                    className="input py-1 px-2 w-24 text-sm font-mono text-center"
                    onBlur={(e) => {
                      onTimeEdit(swimmer, entry.event, e.target.value);
                      setEditingEntry(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        onTimeEdit(
                          swimmer,
                          entry.event,
                          (e.target as HTMLInputElement).value,
                        );
                        setEditingEntry(null);
                      }
                      if (e.key === "Escape") {
                        setEditingEntry(null);
                      }
                    }}
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() =>
                      onTimeEdit &&
                      setEditingEntry({
                        swimmer,
                        event: entry.event,
                      })
                    }
                    className="font-mono text-sm text-white/70 hover:text-[var(--gold-400)] transition-colors px-2 py-1 rounded hover:bg-white/5"
                    title="Click to edit time"
                  >
                    {entry.time}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
