'use client';

import { useState } from 'react';
import { SwimmerEntry } from '@/lib/api';

interface BulkOperationsProps {
  selectedSwimmers: Set<string>;
  onBulkSelect: (swimmerIds: string[], selected: boolean) => void;
  onBulkExclude: (swimmerIds: string[]) => void;
  onBulkLock: (swimmerIds: string[], events: string[]) => void;
  onBulkUnlock: (swimmerIds: string[]) => void;
  availableEvents: string[];
  maxLocks: number;
  currentLockCount: number;
  className?: string;
}

export default function BulkOperations({
  selectedSwimmers,
  onBulkSelect,
  onBulkExclude,
  onBulkLock,
  onBulkUnlock,
  availableEvents,
  maxLocks,
  currentLockCount,
  className = '',
}: BulkOperationsProps) {
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [actionType, setActionType] = useState<'exclude' | 'lock' | 'unlock' | null>(null);

  const selectedSwimmerIds = Array.from(selectedSwimmers);
  const hasSelection = selectedSwimmerIds.length > 0;
  const canAddLocks = currentLockCount + selectedSwimmerIds.length <= maxLocks;

  const handleBulkAction = () => {
    if (!actionType || !hasSelection) return;

    switch (actionType) {
      case 'exclude':
        onBulkExclude(selectedSwimmerIds);
        break;
      case 'lock':
        if (selectedEvents.length > 0) {
          onBulkLock(selectedSwimmerIds, selectedEvents);
        }
        break;
      case 'unlock':
        onBulkUnlock(selectedSwimmerIds);
        break;
    }

    // Reset state
    setActionType(null);
    setSelectedEvents([]);
    setShowBulkActions(false);
  };

  const handleSelectAll = (swimmerIds: string[]) => {
    const allSelected = swimmerIds.every(id => selectedSwimmers.has(id));
    onBulkSelect(swimmerIds, !allSelected);
  };

  const getActionDescription = () => {
    switch (actionType) {
      case 'exclude':
        return `Exclude ${selectedSwimmerIds.length} swimmer(s) from optimization`;
      case 'lock':
        return `Lock ${selectedSwimmerIds.length} swimmer(s) in ${selectedEvents.length} event(s)`;
      case 'unlock':
        return `Unlock ${selectedSwimmerIds.length} swimmer(s)`;
      default:
        return '';
    }
  };

  const getActionButton = () => {
    const isDisabled = !actionType || (actionType === 'lock' && selectedEvents.length === 0);
    const isLockDisabled = actionType === 'lock' && !canAddLocks;

    return (
      <button
        onClick={handleBulkAction}
        disabled={isDisabled || isLockDisabled}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
          isDisabled || isLockDisabled
            ? 'bg-gray-600/30 text-gray-400 cursor-not-allowed'
            : 'bg-[var(--gold-500)] text-[var(--navy-900)] hover:bg-[var(--gold-400)] shadow-lg'
        }`}
      >
        {isLockDisabled
          ? `Not enough locks (${maxLocks - currentLockCount} remaining)`
          : `Apply to ${selectedSwimmerIds.length} swimmer(s)`
        }
      </button>
    );
  };

  if (!hasSelection) return null;

  return (
    <div className={`glass-card border border-[var(--gold-500)]/30 bg-[var(--gold-500)]/5 ${className}`}>
      {/* Selection Summary */}
      <div className="p-4 border-b border-[var(--navy-600)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[var(--gold-500)] text-[var(--navy-900)] flex items-center justify-center font-bold text-sm">
              {selectedSwimmerIds.length}
            </div>
            <div>
              <p className="text-sm font-medium text-white">
                {selectedSwimmerIds.length} swimmer(s) selected
              </p>
              <p className="text-xs text-white/60">
                Choose bulk action below
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowBulkActions(!showBulkActions)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              showBulkActions
                ? 'bg-[var(--navy-600)] text-white'
                : 'bg-white/10 text-white/80 hover:bg-white/20'
            }`}
          >
            {showBulkActions ? 'Hide Actions' : 'Show Actions'}
          </button>
        </div>
      </div>

      {/* Bulk Actions Panel */}
      {showBulkActions && (
        <div className="p-4 space-y-4">
          {/* Action Type Selection */}
          <div>
            <label className="block text-sm font-medium text-white mb-2">
              Action Type
            </label>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <button
                onClick={() => setActionType('exclude')}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  actionType === 'exclude'
                    ? 'border-red-400 bg-red-500/20 text-red-300'
                    : 'border-[var(--navy-600)] bg-[var(--navy-800)] text-white/60 hover:border-[var(--navy-500)] hover:text-white/80'
                }`}
              >
                <div className="font-medium text-sm">🚫 Exclude</div>
                <div className="text-xs opacity-70 mt-1">
                  Remove from optimization
                </div>
              </button>

              <button
                onClick={() => setActionType('lock')}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  actionType === 'lock'
                    ? 'border-blue-400 bg-blue-500/20 text-blue-300'
                    : 'border-[var(--navy-600)] bg-[var(--navy-800)] text-white/60 hover:border-[var(--navy-500)] hover:text-white/80'
                }`}
              >
                <div className="font-medium text-sm">🔒 Lock</div>
                <div className="text-xs opacity-70 mt-1">
                  Force into lineup
                </div>
              </button>

              <button
                onClick={() => setActionType('unlock')}
                className={`p-3 rounded-lg border text-left transition-colors ${
                  actionType === 'unlock'
                    ? 'border-green-400 bg-green-500/20 text-green-300'
                    : 'border-[var(--navy-600)] bg-[var(--navy-800)] text-white/60 hover:border-[var(--navy-500)] hover:text-white/80'
                }`}
              >
                <div className="font-medium text-sm">🔓 Unlock</div>
                <div className="text-xs opacity-70 mt-1">
                  Remove all locks
                </div>
              </button>
            </div>
          </div>

          {/* Event Selection for Lock Action */}
          {actionType === 'lock' && (
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Select Events to Lock
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-40 overflow-y-auto">
                {availableEvents.map((event) => (
                  <label
                    key={event}
                    className="flex items-center gap-2 p-2 rounded-lg bg-[var(--navy-800)] hover:bg-[var(--navy-700)] cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      checked={selectedEvents.includes(event)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedEvents([...selectedEvents, event]);
                        } else {
                          setSelectedEvents(selectedEvents.filter(e => e !== event));
                        }
                      }}
                      className="rounded border-[var(--navy-500)] bg-[var(--navy-700)] text-[var(--gold-500)] focus:ring-[var(--gold-500)] focus:ring-offset-[var(--navy-900)]"
                    />
                    <span className="text-xs text-white/80 truncate">{event}</span>
                  </label>
                ))}
              </div>
              {selectedEvents.length > 0 && (
                <p className="text-xs text-[var(--gold-400)] mt-2">
                  {selectedEvents.length} event(s) selected
                </p>
              )}
            </div>
          )}

          {/* Action Description */}
          {actionType && (
            <div className="p-3 bg-[var(--navy-800)] rounded-lg">
              <p className="text-sm text-white/80">
                {getActionDescription()}
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center justify-between pt-2 border-t border-[var(--navy-600)]">
            <button
              onClick={() => {
                setActionType(null);
                setSelectedEvents([]);
                setShowBulkActions(false);
              }}
              className="px-3 py-1.5 text-sm text-white/60 hover:text-white transition-colors"
            >
              Cancel
            </button>

            {getActionButton()}
          </div>
        </div>
      )}
    </div>
  );
}
