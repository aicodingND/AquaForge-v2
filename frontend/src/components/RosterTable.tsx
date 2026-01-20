'use client';

import { useState } from 'react';
import { SwimmerEntry } from '@/lib/api';

interface RosterTableProps {
  data: SwimmerEntry[];
  teamName: string;
  onSwimmerToggle?: (swimmerId: string, included: boolean) => void;
  onTimeEdit?: (swimmerId: string, event: string, newTime: string) => void;
  onLockSwimmer?: (swimmerId: string, event: string, locked: boolean) => void;
  lockedSwimmers?: Map<string, string[]>;  // swimmerId -> events[]
  excludedSwimmers?: Set<string>;
  showLockControls?: boolean;
  maxLocks?: number;
  className?: string;
}

export default function RosterTable({
  data,
  teamName,
  onSwimmerToggle,
  onTimeEdit,
  onLockSwimmer,
  lockedSwimmers = new Map(),
  excludedSwimmers = new Set(),
  showLockControls = true,
  maxLocks = 3,
  className = '',
}: RosterTableProps) {
  const [expandedSwimmer, setExpandedSwimmer] = useState<string | null>(null);
  const [editingEntry, setEditingEntry] = useState<{ swimmer: string; event: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'swimmer' | 'event' | 'time'>('swimmer');

  // Group entries by swimmer
  const swimmerMap = new Map<string, SwimmerEntry[]>();
  data.forEach((entry) => {
    const existing = swimmerMap.get(entry.swimmer) || [];
    existing.push(entry);
    swimmerMap.set(entry.swimmer, existing);
  });

  // Filter and sort
  const swimmers = Array.from(swimmerMap.keys())
    .filter((name) => name.toLowerCase().includes(searchQuery.toLowerCase()))
    .sort((a, b) => a.localeCompare(b));

  const currentLockCount = Array.from(lockedSwimmers.values()).reduce((acc, events) => acc + events.length, 0);

  const isSwimmerLocked = (swimmer: string, event: string): boolean => {
    const events = lockedSwimmers.get(swimmer);
    return events ? events.includes(event) : false;
  };

  const canAddLock = currentLockCount < maxLocks;

  const handleLockToggle = (swimmer: string, event: string) => {
    if (!onLockSwimmer) return;
    const isLocked = isSwimmerLocked(swimmer, event);
    if (!isLocked && !canAddLock) return; // Can't add more locks
    onLockSwimmer(swimmer, event, !isLocked);
  };

  return (
    <div className={`glass-card overflow-hidden ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-[var(--navy-500)] flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-white">{teamName}</h3>
          <span className="badge badge-info text-xs">{swimmers.length} swimmers</span>
        </div>
        
        {showLockControls && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-white/50">Coach Locks:</span>
            <span className={`font-mono ${currentLockCount >= maxLocks ? 'text-[var(--warning)]' : 'text-white'}`}>
              {currentLockCount}/{maxLocks}
            </span>
          </div>
        )}
      </div>

      {/* Search & Sort */}
      <div className="p-3 border-b border-[var(--navy-600)] flex gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder="Search swimmers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input w-full pl-9 py-2 text-sm"
          />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40">🔍</span>
        </div>
        
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'swimmer' | 'event' | 'time')}
          aria-label="Sort roster by"
          className="input py-2 px-3 text-sm w-32"
        >
          <option value="swimmer">By Name</option>
          <option value="event">By Event</option>
          <option value="time">By Time</option>
        </select>
      </div>

      {/* Roster List */}
      <div className="max-h-[400px] overflow-y-auto">
        {swimmers.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-white/40">No swimmers found</p>
          </div>
        ) : (
          swimmers.map((swimmer) => {
            const entries = swimmerMap.get(swimmer) || [];
            const isExpanded = expandedSwimmer === swimmer;
            const isExcluded = excludedSwimmers.has(swimmer);
            const swimmerLocks = lockedSwimmers.get(swimmer) || [];
            const hasLock = swimmerLocks.length > 0;

            return (
              <div
                key={swimmer}
                className={`border-b border-[var(--navy-600)] last:border-b-0 ${
                  isExcluded ? 'opacity-50' : ''
                }`}
              >
                {/* Swimmer Row */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => setExpandedSwimmer(isExpanded ? null : swimmer)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setExpandedSwimmer(isExpanded ? null : swimmer); }}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors cursor-pointer"
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
                          ? 'border-[var(--navy-500)] bg-transparent'
                          : 'border-[var(--gold-500)] bg-[var(--gold-500)]'
                      }`}
                    >
                      {!isExcluded && <span className="text-[var(--navy-900)] text-xs">✓</span>}
                    </button>
                  )}

                  {/* Lock Icon */}
                  {hasLock && (
                    <span className="text-[var(--gold-400)]" title={`Locked: ${swimmerLocks.join(', ')}`}>
                      🔒
                    </span>
                  )}

                  {/* Swimmer Name */}
                  <span className={`flex-1 font-medium ${hasLock ? 'text-[var(--gold-400)]' : 'text-white'}`}>
                    {swimmer}
                  </span>

                  {/* Event count */}
                  <span className="text-white/40 text-sm">{entries.length} events</span>

                  {/* Expand Arrow */}
                  <svg
                    className={`w-4 h-4 text-white/40 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>

                {/* Expanded Events */}
                {isExpanded && (
                  <div className="px-4 pb-3 space-y-2 bg-[var(--navy-800)]/50 animate-fade-in">
                    {entries.map((entry, idx) => {
                      const isLocked = isSwimmerLocked(swimmer, entry.event);
                      const isEditing = editingEntry?.swimmer === swimmer && editingEntry?.event === entry.event;

                      return (
                        <div
                          key={idx}
                          className={`flex items-center gap-3 p-2 rounded-lg ${
                            isLocked ? 'bg-[var(--gold-muted)] border border-[var(--gold-500)]/30' : 'bg-[var(--navy-700)]'
                          }`}
                        >
                          {/* Lock Toggle */}
                          {showLockControls && (
                            <button
                              type="button"
                              onClick={() => handleLockToggle(swimmer, entry.event)}
                              disabled={!isLocked && !canAddLock}
                              className={`p-1 rounded transition-colors ${
                                isLocked
                                  ? 'text-[var(--gold-400)] hover:text-[var(--gold-300)]'
                                  : canAddLock
                                  ? 'text-white/40 hover:text-white'
                                  : 'text-white/20 cursor-not-allowed'
                              }`}
                              title={isLocked ? 'Unlock event' : canAddLock ? 'Lock event (coach assigned)' : `Max ${maxLocks} locks reached`}
                            >
                              {isLocked ? '🔒' : '🔓'}
                            </button>
                          )}

                          {/* Event Name */}
                          <span className="flex-1 text-sm text-white">{entry.event}</span>

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
                                if (e.key === 'Enter') {
                                  onTimeEdit(swimmer, entry.event, (e.target as HTMLInputElement).value);
                                  setEditingEntry(null);
                                }
                                if (e.key === 'Escape') {
                                  setEditingEntry(null);
                                }
                              }}
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => onTimeEdit && setEditingEntry({ swimmer, event: entry.event })}
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
          })
        )}
      </div>
    </div>
  );
}
