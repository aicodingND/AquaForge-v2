'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';

interface SwimmerSwapModalProps {
  show: boolean;
  onClose: () => void;
  eventName: string;
  currentSwimmer: string;
  availableSwimmers: { name: string; time: string }[];
  onSwap: (newSwimmer: string) => void;
}

export default function SwimmerSwapModal({
  show,
  onClose,
  eventName,
  currentSwimmer,
  availableSwimmers,
  onSwap,
}: SwimmerSwapModalProps) {
  const [selectedSwimmer, setSelectedSwimmer] = useState<string | null>(null);
  const [reason, setReason] = useState('');

  if (!show) return null;

  const handleConfirm = () => {
    if (selectedSwimmer) {
      onSwap(selectedSwimmer);
      onClose();
    }
  };

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-md mx-4 glass-card overflow-hidden shadow-2xl animate-scale-in"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-[var(--navy-500)] flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-white">Swap Swimmer</h3>
            <p className="text-sm text-white/50">{eventName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/5 text-white/50 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Current Assignment */}
        <div className="p-4 bg-[var(--navy-800)]/50 border-b border-[var(--navy-600)]">
          <p className="text-xs text-white/40 uppercase tracking-wider mb-2">Current</p>
          <div className="flex items-center gap-3">
            <span className="text-2xl">🏊</span>
            <div>
              <p className="font-medium text-white">{currentSwimmer}</p>
              <p className="text-xs text-white/50">Assigned by optimizer</p>
            </div>
          </div>
        </div>

        {/* Available Swimmers */}
        <div className="p-4 max-h-64 overflow-y-auto">
          <p className="text-xs text-white/40 uppercase tracking-wider mb-3">Available Swimmers</p>
          <div className="space-y-2">
            {availableSwimmers.map((swimmer) => (
              <button
                key={swimmer.name}
                onClick={() => setSelectedSwimmer(swimmer.name)}
                className={`w-full flex items-center justify-between p-3 rounded-lg border transition-all ${
                  selectedSwimmer === swimmer.name
                    ? 'border-[var(--gold-500)] bg-[var(--gold-muted)]'
                    : 'border-[var(--navy-500)] hover:border-white/30'
                }`}
              >
                <span className={`font-medium ${
                  selectedSwimmer === swimmer.name ? 'text-[var(--gold-400)]' : 'text-white'
                }`}>
                  {swimmer.name}
                </span>
                <span className="font-mono text-sm text-white/60">{swimmer.time}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Reason (optional) */}
        <div className="p-4 border-t border-[var(--navy-600)]">
          <label className="text-xs text-white/40 uppercase tracking-wider">
            Reason (optional)
          </label>
          <input
            type="text"
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="e.g., Coach preference, injury recovery..."
            className="input mt-2 text-sm"
          />
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-[var(--navy-500)] flex gap-3">
          <button onClick={onClose} className="btn btn-outline flex-1">
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedSwimmer}
            className="btn btn-gold flex-1"
          >
            Confirm Swap
          </button>
        </div>
      </div>
    </div>
  );
}
