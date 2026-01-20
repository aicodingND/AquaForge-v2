'use client';

import { useState, useEffect } from 'react';

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
  colors: {
    primary: string;
    secondary: string;
    accent?: string;
  };
  rosterSource: 'hytek' | 'swimcloud' | 'manual';
  division: string;
  conference?: string;
  location?: string;
  isUserTeam?: boolean;
}

interface TeamSelectorProps {
  label?: string;
  value: string | null;
  onChange: (teamId: string) => void;
  excludeTeams?: string[];
  showAddNew?: boolean;
  className?: string;
}

export default function TeamSelector({
  label = 'Select Team',
  value,
  onChange,
  excludeTeams = [],
  showAddNew = false,
  className = '',
}: TeamSelectorProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // In production, this would fetch from API
    // For now, hardcode VCAC teams
    const loadTeams = async () => {
      const vcacTeams: Team[] = [
        {
          id: 'seton',
          name: 'Seton School Conquistadors',
          abbreviation: 'SET',
          colors: { primary: '#0C2340', secondary: '#D4AF37' },
          rosterSource: 'hytek',
          division: 'VISAA_DII',
          conference: 'VCAC',
          isUserTeam: true,
        },
        {
          id: 'trinity_christian',
          name: 'Trinity Christian School',
          abbreviation: 'TCS',
          colors: { primary: '#00205B', secondary: '#C8102E' },
          rosterSource: 'swimcloud',
          division: 'VISAA_DII',
          conference: 'VCAC',
        },
        {
          id: 'oakcrest',
          name: 'Oakcrest School',
          abbreviation: 'OAK',
          colors: { primary: '#003366', secondary: '#FFD700' },
          rosterSource: 'swimcloud',
          division: 'VISAA_DII',
          conference: 'VCAC',
        },
        {
          id: 'fredericksburg_christian',
          name: 'Fredericksburg Christian',
          abbreviation: 'FCS',
          colors: { primary: '#1C4587', secondary: '#FFFFFF' },
          rosterSource: 'swimcloud',
          division: 'VISAA_DII',
          conference: 'VCAC',
        },
        {
          id: 'immanuel_christian',
          name: 'Immanuel Christian',
          abbreviation: 'ICS',
          colors: { primary: '#002D62', secondary: '#FFFFFF' },
          rosterSource: 'swimcloud',
          division: 'VISAA_DII',
          conference: 'VCAC',
        },
        {
          id: 'st_john_paul',
          name: 'St. John Paul the Great',
          abbreviation: 'DJP',
          colors: { primary: '#1E3A5F', secondary: '#B8860B' },
          rosterSource: 'swimcloud',
          division: 'VISAA_DII',
          conference: 'VCAC',
        },
        {
          id: 'paul_vi',
          name: 'Paul VI Catholic',
          abbreviation: 'PVI',
          colors: { primary: '#003087', secondary: '#FFD700' },
          rosterSource: 'manual',
          division: 'VISAA_DII',
          conference: 'VCAC',
        },
      ];
      setTeams(vcacTeams.filter((t) => !excludeTeams.includes(t.id)));
    };
    loadTeams();
  }, [excludeTeams]);

  const selectedTeam = teams.find((t) => t.id === value);

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
        {selectedTeam ? (
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 rounded-full border-2"
              style={{
                backgroundColor: selectedTeam.colors.primary,
                borderColor: selectedTeam.colors.secondary,
              }}
            />
            <span className="text-white font-medium">{selectedTeam.name}</span>
            <span className="text-white/40 text-sm">({selectedTeam.abbreviation})</span>
          </div>
        ) : (
          <span className="text-white/40">Choose a team...</span>
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
          <div className="max-h-64 overflow-y-auto">
            {teams.map((team) => (
              <button
                key={team.id}
                type="button"
                onClick={() => {
                  onChange(team.id);
                  setIsOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors ${
                  team.id === value ? 'bg-[var(--gold-muted)]' : ''
                }`}
              >
                <div
                  className="w-4 h-4 rounded-full border-2"
                  style={{
                    backgroundColor: team.colors.primary,
                    borderColor: team.colors.secondary,
                  }}
                />
                <div className="flex-1">
                  <p className={`font-medium ${team.id === value ? 'text-[var(--gold-400)]' : 'text-white'}`}>
                    {team.name}
                  </p>
                  <p className="text-xs text-white/40">{team.location || team.conference}</p>
                </div>
                {team.isUserTeam && (
                  <span className="badge badge-gold text-[10px]">Your Team</span>
                )}
              </button>
            ))}
          </div>
          
          {showAddNew && (
            <button
              type="button"
              onClick={() => {
                // TODO: Open add team modal
                setIsOpen(false);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 border-t border-[var(--navy-600)] text-white/60 hover:text-[var(--gold-400)] hover:bg-white/5 transition-colors"
            >
              <span className="text-lg">+</span>
              <span className="text-sm">Add New Team</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}
