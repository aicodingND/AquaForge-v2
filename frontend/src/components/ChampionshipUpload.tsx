'use client';

import { useState } from 'react';
import { useAppStore } from '@/lib/store';

interface Team {
  name: string;
  swimmer_count: number;
  entry_count: number;
  events: string[];
}

interface ChampionshipData {
  teams: Team[];
  selectedTeam: string | null;
  allData: any[];
  file_hash?: string;
}

/**
 * Championship file upload component (ported from Windows).
 * Uses local state for upload flow, then sets Seton team data
 * in the global store once a team is selected.
 */
export default function ChampionshipUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [championshipData, setChampionshipData] = useState<ChampionshipData | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/v1/data/championship/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();

      setChampionshipData({
        teams: data.teams || [],
        selectedTeam: null,
        allData: data.all_entries || [],
        file_hash: data.file_hash,
      });

    } catch (err: any) {
      setError(err.message || 'Failed to upload file');
    } finally {
      setIsUploading(false);
    }
  };

  const handleTeamSelect = (teamName: string) => {
    setSelectedTeam(teamName);

    if (championshipData?.allData) {
      const teamData = championshipData.allData.filter(
        (entry: any) => entry.team === teamName
      );

      useAppStore.getState().setSetonTeam({
        name: teamName,
        filename: `${teamName}_championship.xlsx`,
        data: teamData,
        swimmerCount: new Set(teamData.map((e: any) => e.swimmer)).size,
        entryCount: teamData.length,
        events: [...new Set(teamData.map((e: any) => e.event))] as string[],
      });
    }
  };

  const clearChampionshipData = () => {
    setChampionshipData(null);
    setSelectedTeam(null);
  };

  if (!championshipData) {
    return (
      <div className="glass-card rounded-xl p-8">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[#D4AF37]/10 mb-4">
            <svg className="w-8 h-8 text-[#D4AF37]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>

          <h3 className="text-xl font-bold text-white mb-2">
            Upload Championship Meet File
          </h3>
          <p className="text-sm text-white/60 max-w-md mx-auto mb-6">
            Upload a multi-team championship meet file. The file should include a &apos;team&apos; column to identify each swimmer&apos;s team.
          </p>

          <div className="bg-[#0C2340]/50 rounded-lg p-4 text-left max-w-md mx-auto mb-6">
            <p className="text-xs font-semibold text-[#D4AF37] mb-2">Required Columns:</p>
            <ul className="text-xs text-white/60 space-y-1">
              <li>* <span className="font-mono">team</span> - Team name</li>
              <li>* <span className="font-mono">swimmer</span> - Swimmer name</li>
              <li>* <span className="font-mono">event</span> - Event name</li>
              <li>* <span className="font-mono">time</span> - Best time</li>
              <li>* <span className="font-mono">grade</span> - Grade level (optional)</li>
            </ul>
          </div>
        </div>

        <label className="block">
          <input
            type="file"
            accept=".xlsx,.xls,.csv"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="hidden"
            id="championship-file-input"
          />
          <label
            htmlFor="championship-file-input"
            className={`
              flex items-center justify-center gap-2 w-full py-3 px-4 rounded-lg
              font-medium text-sm transition-all cursor-pointer
              ${isUploading
                ? 'bg-white/10 text-white/40 cursor-not-allowed'
                : 'bg-[#D4AF37] hover:bg-[#C99700] text-[#0C2340]'
              }
            `}
          >
            {isUploading ? (
              <>
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Uploading...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                Choose File
              </>
            )}
          </label>
        </label>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="glass-card rounded-xl p-5">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Championship Meet Data</h3>
            <p className="text-sm text-white/60 mt-1">
              {championshipData.teams.length} teams found - Select your team below
            </p>
          </div>
          <button
            onClick={clearChampionshipData}
            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 text-sm transition-colors"
          >
            Clear &amp; Re-upload
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {championshipData.teams.map((team: Team) => {
          const isSelected = team.name === selectedTeam;

          return (
            <button
              key={team.name}
              onClick={() => handleTeamSelect(team.name)}
              className={`
                glass-card rounded-xl p-5 text-left transition-all
                ${isSelected
                  ? 'ring-2 ring-[#D4AF37] bg-[#D4AF37]/5'
                  : 'hover:bg-white/[0.02]'
                }
              `}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h4 className="text-base font-semibold text-white truncate">
                    {team.name}
                  </h4>
                </div>

                {isSelected && (
                  <div className="flex-shrink-0 ml-2">
                    <div className="w-6 h-6 rounded-full bg-[#D4AF37] flex items-center justify-center">
                      <svg className="w-4 h-4 text-[#0C2340]" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#0C2340]/50 rounded-lg p-2">
                  <p className="text-xs text-white/50">Swimmers</p>
                  <p className="text-lg font-bold text-white">{team.swimmer_count}</p>
                </div>
                <div className="bg-[#0C2340]/50 rounded-lg p-2">
                  <p className="text-xs text-white/50">Entries</p>
                  <p className="text-lg font-bold text-white">{team.entry_count}</p>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-1">
                {team.events.slice(0, 3).map((event) => (
                  <span
                    key={event}
                    className="text-xs px-2 py-0.5 rounded bg-[#1a3a5c] text-white/60"
                  >
                    {event}
                  </span>
                ))}
                {team.events.length > 3 && (
                  <span className="text-xs px-2 py-0.5 rounded bg-[#1a3a5c] text-white/60">
                    +{team.events.length - 3} more
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {selectedTeam && (
        <div className="glass-card rounded-xl p-5 bg-[#D4AF37]/5 border border-[#D4AF37]/20">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-[#D4AF37]" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-semibold text-white">
                Team Selected: <span className="text-[#D4AF37]">{selectedTeam}</span>
              </p>
              <p className="text-xs text-white/60 mt-0.5">
                You can now optimize your lineup on the Optimize tab
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
