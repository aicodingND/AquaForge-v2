'use client';

import { useState } from 'react';
import { SwimmerEntry } from '@/lib/api';

interface MobileRosterCardProps {
  swimmer: string;
  entries: SwimmerEntry[];
  gender: string;
  isExpanded: boolean;
  onToggle: () => void;
  onIncludeToggle: (swimmer: string, included: boolean) => void;
  onTimeEdit: (swimmer: string, event: string, newTime: string) => void;
  onLockToggle: (swimmer: string, event: string, locked: boolean) => void;
  isExcluded: boolean;
  lockedEvents: string[];
  showLockControls?: boolean;
  canAddLock?: boolean;
}

export default function MobileRosterCard({
  swimmer,
  entries,
  gender,
  isExpanded,
  onToggle,
  onIncludeToggle,
  onTimeEdit,
  onLockToggle,
  isExcluded,
  lockedEvents,
  showLockControls = true,
  canAddLock = true,
}: MobileRosterCardProps) {
  const [editingTime, setEditingTime] = useState<{ event: string; time: string } | null>(null);

  const handleTimeSave = (event: string, newTime: string) => {
    onTimeEdit(swimmer, event, newTime);
    setEditingTime(null);
  };

  const getEventCardColor = (event: string) => {
    const isLocked = lockedEvents.includes(event);
    if (isLocked) return 'border-[var(--gold-500)] bg-[var(--gold-500)]/10';

    // Color by event type for better visual distinction
    if (event.toLowerCase().includes('free')) return 'border-blue-400/30 bg-blue-500/5';
    if (event.toLowerCase().includes('back')) return 'border-green-400/30 bg-green-500/5';
    if (event.toLowerCase().includes('breast')) return 'border-purple-400/30 bg-purple-500/5';
    if (event.toLowerCase().includes('fly')) return 'border-orange-400/30 bg-orange-500/5';
    if (event.toLowerCase().includes('im')) return 'border-red-400/30 bg-red-500/5';

    return 'border-[var(--navy-600)] bg-[var(--navy-800)]/30';
  };

  const formatEventName = (event: string) => {
    // Shorten event names for mobile display
    return event
      .replace(' Yard', '')
      .replace(' Meter', '')
      .replace(' Freestyle', ' Free')
      .replace(' Backstroke', ' Back')
      .replace(' Breaststroke', ' Breast')
      .replace(' Butterfly', ' Fly')
      .replace(' Individual Medley', ' IM')
      .replace(' Medley Relay', ' MR')
      .replace(' Freestyle Relay', ' FR');
  };

  return (
    <div className={`glass-card mb-3 overflow-hidden ${isExcluded ? 'opacity-60' : ''}`}>
      {/* Header */}
      <div
        className="p-4 flex items-center justify-between cursor-pointer active:scale-[0.98] transition-transform"
        onClick={onToggle}
      >
        <div className="flex items-center gap-3">
          {/* Include/Exclude Toggle */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onIncludeToggle(swimmer, !isExcluded);
            }}
            className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
              isExcluded
                ? 'border-[var(--navy-500)] bg-transparent'
                : 'border-[var(--gold-500)] bg-[var(--gold-500)] shadow-md'
            }`}
          >
            {!isExcluded && (
              <span className="text-[var(--navy-900)] text-sm font-bold">✓</span>
            )}
          </button>

          {/* Swimmer Info */}
          <div className="flex-1">
            <h3 className="font-semibold text-white text-base">{swimmer}</h3>
            <div className="flex items-center gap-2 mt-1">
              {/* Gender Badge */}
              {gender && gender !== 'U' && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  gender === 'M'
                    ? 'bg-blue-500/20 text-blue-300'
                    : 'bg-pink-500/20 text-pink-300'
                }`}>
                  {gender}
                </span>
              )}

              {/* Stats */}
              <span className="text-xs text-white/50">
                {entries.length} events
              </span>

              {/* Lock Status */}
              {lockedEvents.length > 0 && (
                <span className="text-xs text-[var(--gold-400)] font-medium">
                  🔒 {lockedEvents.length} locked
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Expand Icon */}
        <div className={`transform transition-transform duration-200 ${
          isExpanded ? 'rotate-180' : ''
        }`}>
          <svg className="w-5 h-5 text-white/60" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-[var(--navy-600)] p-4 space-y-3">
          <div className="grid grid-cols-1 gap-3">
            {entries.map((entry, index) => {
              const isLocked = lockedEvents.includes(entry.event);
              const isEditing = editingTime?.event === entry.event;

              return (
                <div
                  key={`${entry.event}-${index}`}
                  className={`p-3 rounded-lg border transition-all ${getEventCardColor(entry.event)}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="font-medium text-white text-sm">
                          {formatEventName(entry.event)}
                        </h4>
                        {isLocked && (
                          <span className="text-[var(--gold-400)] text-xs">🔒</span>
                        )}
                      </div>

                      {/* Time Display/Edit */}
                      <div className="flex items-center gap-2">
                        {isEditing ? (
                          <div className="flex items-center gap-2 flex-1">
                            <input
                              type="text"
                              value={editingTime.time}
                              onChange={(e) => setEditingTime({ ...editingTime, time: e.target.value })}
                              className="flex-1 px-2 py-1 bg-[var(--navy-700)] border border-[var(--navy-500)] rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-[var(--gold-500)]"
                              autoFocus
                            />
                            <button
                              onClick={() => handleTimeSave(entry.event, editingTime.time)}
                              className="px-2 py-1 bg-green-500 text-white rounded text-xs font-medium hover:bg-green-600"
                            >
                              Save
                            </button>
                            <button
                              onClick={() => setEditingTime(null)}
                              className="px-2 py-1 bg-[var(--navy-600)] text-white rounded text-xs font-medium hover:bg-[var(--navy-500)]"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-3">
                            <span className="text-lg font-mono font-bold text-white">
                              {Number(entry.time).toFixed(2)}
                            </span>
                            <button
                              onClick={() => setEditingTime({ event: entry.event, time: entry.time.toString() })}
                              className="text-xs text-white/50 hover:text-white/80 transition-colors underline"
                            >
                              Edit
                            </button>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Lock Control */}
                    {showLockControls && (
                      <button
                        onClick={() => {
                          if (isLocked || canAddLock) {
                            onLockToggle(swimmer, entry.event, !isLocked);
                          }
                        }}
                        disabled={!isLocked && !canAddLock}
                        className={`w-8 h-8 rounded-full border-2 flex items-center justify-center transition-all ${
                          isLocked
                            ? 'border-[var(--gold-500)] bg-[var(--gold-500)]'
                            : canAddLock
                            ? 'border-[var(--navy-500)] bg-transparent hover:border-[var(--gold-400)]'
                            : 'border-[var(--navy-600)] bg-[var(--navy-700)] opacity-50 cursor-not-allowed'
                        }`}
                        title={isLocked ? 'Unlock swimmer' : !canAddLock ? 'No locks remaining' : 'Lock swimmer'}
                      >
                        {isLocked && (
                          <span className="text-[var(--navy-900)] text-xs font-bold">🔒</span>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 pt-3 border-t border-[var(--navy-600)]">
            <button
              onClick={() => onIncludeToggle(swimmer, !isExcluded)}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isExcluded
                  ? 'bg-green-500/20 text-green-300 hover:bg-green-500/30'
                  : 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
              }`}
            >
              {isExcluded ? '✓ Include in Optimization' : '✗ Exclude from Optimization'}
            </button>

            {showLockControls && canAddLock && (
              <button
                className="px-3 py-2 bg-[var(--gold-500)]/20 text-[var(--gold-300)] rounded-lg text-sm font-medium hover:bg-[var(--gold-500)]/30 transition-colors"
                onClick={() => {
                  // Lock first unlocked event
                  const firstUnlocked = entries.find(e => !lockedEvents.includes(e.event));
                  if (firstUnlocked) {
                    onLockToggle(swimmer, firstUnlocked.event, true);
                  }
                }}
              >
                🔒 Quick Lock
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
