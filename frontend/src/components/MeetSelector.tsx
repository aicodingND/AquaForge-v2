'use client';

import { useState, useEffect } from 'react';
import { useAppStore } from '@/lib/store';
import { useShallow } from 'zustand/react/shallow';

export interface Meet {
  id: string;
  name: string;
  date: string | null;
  type: 'dual' | 'championship';
  meetMode: 'dual' | 'championship';
  scoringRules: string;
  teams: string[];
  venue?: string;
}

interface MeetSelectorProps {
  label?: string;
  value: string | null;
  onChange: (meetId: string) => void;
  showAddNew?: boolean;
  className?: string;
}

export default function MeetSelector({
  label = 'Select Meet',
  value,
  onChange,
  showAddNew = false,
  className = '',
}: MeetSelectorProps) {
  const [meets, setMeets] = useState<Meet[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const { meetMode, setMeetMode, setOptimizerSettings } = useAppStore(useShallow(s => ({ meetMode: s.meetMode, setMeetMode: s.setMeetMode, setOptimizerSettings: s.setOptimizerSettings })));

  useEffect(() => {
    // Load meets from data folder (mocked for now)
    const loadMeets = async () => {
      const scheduledMeets: Meet[] = [
        {
          id: 'vcac_championship_2026',
          name: 'VCAC Championship',
          date: '2026-02-07',
          type: 'championship',
          meetMode: 'championship',
          scoringRules: 'vcac_championship',
          teams: ['seton', 'trinity_christian', 'oakcrest', 'fredericksburg_christian', 'immanuel_christian', 'st_john_paul', 'paul_vi'],
          venue: 'Sport & Health - Fredericksburg',
        },
        {
          id: 'visaa_state_2026',
          name: 'VISAA State Championships',
          date: '2026-02-12',
          type: 'championship',
          meetMode: 'championship',
          scoringRules: 'visaa_state',
          teams: [],
          venue: 'SwimRVA, Richmond',
        },
        {
          id: 'dual_template',
          name: 'Dual Meet (Custom)',
          date: null,
          type: 'dual',
          meetMode: 'dual',
          scoringRules: 'visaa_top7',
          teams: ['seton'],
        },
      ];
      setMeets(scheduledMeets);
    };
    loadMeets();
  }, []);

  // Filter meets based on current mode
  const filteredMeets = meets.filter((m) => m.meetMode === meetMode);

  const selectedMeet = meets.find((m) => m.id === value);

  const handleSelectMeet = (meet: Meet) => {
    onChange(meet.id);

    // Auto-configure settings based on meet
    setMeetMode(meet.meetMode);

    // Map scoring rules
    const scoringMap: Record<string, 'visaa_top7' | 'standard_top5' | 'vcac_championship' | 'visaa_state'> = {
      'vcac_championship': 'vcac_championship',
      'visaa_state': 'visaa_state',
      'visaa_top7': 'visaa_top7',
      'standard_top5': 'standard_top5',
    };

    if (scoringMap[meet.scoringRules]) {
      setOptimizerSettings({ scoring: scoringMap[meet.scoringRules] });
    }

    setIsOpen(false);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'TBD';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getMeetTypeIcon = (type: string) => {
    return type === 'championship' ? '🏆' : '⚔️';
  };

  return (
    <div className={`relative ${className}`}>
      {label && (
        <label className="block text-sm text-white/60 mb-2">{label}</label>
      )}

      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 bg-[var(--navy-800)] border border-[var(--navy-500)] rounded-lg text-left hover:border-[var(--gold-500)] transition-colors"
      >
        {selectedMeet ? (
          <div className="flex items-center gap-3">
            <span className="text-xl">{getMeetTypeIcon(selectedMeet.type)}</span>
            <div>
              <span className="text-white font-medium">{selectedMeet.name}</span>
              <span className="text-white/40 text-sm ml-2">• {formatDate(selectedMeet.date)}</span>
            </div>
          </div>
        ) : (
          <span className="text-white/40">Choose a meet...</span>
        )}

        <svg
          className={`w-5 h-5 text-white/50 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-2 bg-[var(--navy-800)] border border-[var(--navy-500)] rounded-lg shadow-xl overflow-hidden animate-fade-in">
          {/* Scheduled Meets */}
          <div className="border-b border-[var(--navy-600)]">
            <p className="px-4 py-2 text-xs text-white/40 uppercase tracking-wider">Scheduled Meets</p>
          </div>

          <div className="max-h-64 overflow-y-auto">
            {filteredMeets.filter((m) => m.date).map((meet) => (
              <button
                key={meet.id}
                type="button"
                onClick={() => handleSelectMeet(meet)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors ${
                  meet.id === value ? 'bg-[var(--gold-muted)]' : ''
                }`}
              >
                <span className="text-xl">{getMeetTypeIcon(meet.type)}</span>
                <div className="flex-1">
                  <p className={`font-medium ${meet.id === value ? 'text-[var(--gold-400)]' : 'text-white'}`}>
                    {meet.name}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-white/40">
                    <span>{formatDate(meet.date)}</span>
                    <span>•</span>
                    <span>{meet.teams.length} teams</span>
                    {meet.venue && <span>• {meet.venue}</span>}
                  </div>
                </div>
                <span className={`badge ${meet.type === 'championship' ? 'badge-gold' : 'badge-info'} text-[10px]`}>
                  {meet.type === 'championship' ? 'Championship' : 'Dual'}
                </span>
              </button>
            ))}
          </div>

          {/* Quick Setup */}
          <div className="border-t border-[var(--navy-600)]">
            <p className="px-4 py-2 text-xs text-white/40 uppercase tracking-wider">Quick Setup</p>
          </div>

          {filteredMeets.filter((m) => !m.date).map((meet) => (
            <button
              key={meet.id}
              type="button"
              onClick={() => handleSelectMeet(meet)}
              className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors ${
                meet.id === value ? 'bg-[var(--gold-muted)]' : ''
              }`}
            >
              <span className="text-xl">{getMeetTypeIcon(meet.type)}</span>
              <div className="flex-1">
                <p className={`font-medium ${meet.id === value ? 'text-[var(--gold-400)]' : 'text-white'}`}>
                  {meet.name}
                </p>
                <p className="text-xs text-white/40">Configure opponent manually</p>
              </div>
            </button>
          ))}

          {showAddNew && (
            <button
              type="button"
              onClick={() => {
                // TODO: Open add meet modal
                setIsOpen(false);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 border-t border-[var(--navy-600)] text-white/60 hover:text-[var(--gold-400)] hover:bg-white/5 transition-colors"
            >
              <span className="text-lg">+</span>
              <span className="text-sm">Schedule New Meet</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
