"use client";

/**
 * ChampionshipTeamsGrid Component
 * Displays all teams in a championship meet with their swimmer counts and key stats
 */

import React, { useMemo } from "react";
import { useAppStore } from "@/lib/store";
import { getTeamInfo, sortTeamsSetonFirst, TeamInfo } from "@/lib/teamMappings";

interface TeamStats {
  code: string;
  info: TeamInfo;
  swimmerCount: number;
  entryCount: number;
  events: Set<string>;
  swimmers: string[];
}

export default function ChampionshipTeamsGrid() {
  const setonTeam = useAppStore((s) => s.setonTeam);

  // Calculate stats for each team from the championship data
  const teamStats = useMemo(() => {
    if (!setonTeam?.data || !setonTeam.teams) return [];

    const statsMap = new Map<string, TeamStats>();

    // Initialize all teams from the teams array
    for (const teamCode of setonTeam.teams) {
      statsMap.set(teamCode, {
        code: teamCode,
        info: getTeamInfo(teamCode),
        swimmerCount: 0,
        entryCount: 0,
        events: new Set(),
        swimmers: [],
      });
    }

    // Process all entries
    for (const entry of setonTeam.data) {
      const teamCode = entry.team || "Unknown";
      let stats = statsMap.get(teamCode);

      if (!stats) {
        stats = {
          code: teamCode,
          info: getTeamInfo(teamCode),
          swimmerCount: 0,
          entryCount: 0,
          events: new Set(),
          swimmers: [],
        };
        statsMap.set(teamCode, stats);
      }

      stats.entryCount++;
      stats.events.add(entry.event);

      if (!stats.swimmers.includes(entry.swimmer)) {
        stats.swimmers.push(entry.swimmer);
        stats.swimmerCount++;
      }
    }

    // Sort with Seton first
    const sortedCodes = sortTeamsSetonFirst(Array.from(statsMap.keys()));
    return sortedCodes.map((code) => statsMap.get(code)!);
  }, [setonTeam]);

  if (!setonTeam?.teams || teamStats.length === 0) {
    return (
      <div className="card bg-navy-800/50 p-6 text-center">
        <p className="text-white/60">
          Upload a championship psych sheet to view teams
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">
          Championship Teams ({teamStats.length})
        </h3>
        <span className="badge badge-gold">
          {setonTeam.swimmerCount} total swimmers
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {teamStats.map((team) => (
          <TeamCard key={team.code} team={team} isSeton={team.code === "SST"} />
        ))}
      </div>
    </div>
  );
}

interface TeamCardProps {
  team: TeamStats;
  isSeton?: boolean;
}

function TeamCard({ team, isSeton }: TeamCardProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <div
      className={`card overflow-hidden transition-all duration-200 ${
        isSeton
          ? "ring-2 ring-gold-500/50 bg-gradient-to-br from-navy-800 to-navy-900"
          : "bg-navy-800/60 hover:bg-navy-800/80"
      }`}
    >
      {/* Header with team colors */}
      <div
        className="h-2"
        style={{
          background: `linear-gradient(to right, ${team.info.colors.primary}, ${team.info.colors.secondary})`,
        }}
      />

      <div className="p-4">
        {/* Team Info */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-lg">
                {team.info.shortName}
              </span>
              {isSeton && (
                <span className="badge badge-gold text-[10px]">HOME</span>
              )}
            </div>
            <p className="text-xs text-white/50">{team.info.name}</p>
            {team.info.location && (
              <p className="text-xs text-white/40">{team.info.location}</p>
            )}
          </div>
          <span
            className="text-2xl font-bold"
            style={{ color: team.info.colors.primary }}
          >
            {team.code}
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <div className="text-center p-2 bg-navy-900/50 rounded">
            <div className="text-xl font-bold text-cyan-400">
              {team.swimmerCount}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Swimmers</div>
          </div>
          <div className="text-center p-2 bg-navy-900/50 rounded">
            <div className="text-xl font-bold text-gold-400">
              {team.entryCount}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Entries</div>
          </div>
          <div className="text-center p-2 bg-navy-900/50 rounded">
            <div className="text-xl font-bold text-green-400">
              {team.events.size}
            </div>
            <div className="text-[10px] text-white/50 uppercase">Events</div>
          </div>
        </div>

        {/* Expand/Collapse Swimmers */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full text-center py-1 text-xs text-white/60 hover:text-white/80 transition-colors"
        >
          {isExpanded ? "▲ Hide Swimmers" : "▼ Show Swimmers"}
        </button>

        {/* Swimmer List */}
        {isExpanded && (
          <div className="mt-2 max-h-40 overflow-y-auto">
            <div className="space-y-1">
              {team.swimmers.slice(0, 20).map((swimmer, idx) => (
                <div
                  key={idx}
                  className="text-xs text-white/70 py-1 px-2 bg-navy-900/30 rounded"
                >
                  {swimmer}
                </div>
              ))}
              {team.swimmers.length > 20 && (
                <div className="text-xs text-white/50 text-center py-1">
                  + {team.swimmers.length - 20} more
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
