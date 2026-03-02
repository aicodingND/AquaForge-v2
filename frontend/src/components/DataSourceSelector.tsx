"use client";

/**
 * DataSourceSelector Component
 * Quick-load buttons for pre-aggregated data, mode-aware
 */

import { useAppStore, useTeamActions } from "@/lib/store";
import { api } from "@/lib/api";
import { useState, useEffect } from "react";

interface DataSource {
  id: string;
  name: string;
  description: string;
  type: "championship" | "dual" | "team";
  teams?: number;
  entries?: number;
  available?: boolean;
}

interface DataSourceSelectorProps {
  mode: "championship" | "dual";
  teamType?: "seton" | "opponent";
}

export default function DataSourceSelector({
  mode,
  teamType = "seton",
}: DataSourceSelectorProps) {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fetching, setFetching] = useState(true);

  const { setSetonTeam, setOpponentTeam, addLog } = useTeamActions();
  const setMeetMode = useAppStore(s => s.setMeetMode);

  // Fetch available sources on mount
  useEffect(() => {
    api.listDataSources()
      .then((data) => {
        setSources((data.sources || []) as DataSource[]);
        setFetching(false);
      })
      .catch(() => {
        setFetching(false);
      });
  }, []);

  // Filter sources by mode
  const filteredSources = sources.filter((source) => {
    if (mode === "championship") {
      return source.type === "championship";
    } else {
      // Dual mode: show team rosters
      return source.type === "dual" || source.type === "team";
    }
  });

  const handleLoadSource = async (source: DataSource) => {
    setLoading(source.id);
    setError(null);

    try {
      const data = await api.loadDataSource(source.id, teamType);

      if (data.success) {
        const teamData = {
          name: data.team_name || source.name,
          filename: `${source.id}.json`,
          data: data.data || [],
          swimmerCount: data.swimmer_count || 0,
          entryCount: data.entry_count || 0,
          events: data.events || [],
          teams: data.teams,
        };

        // Set appropriate team based on teamType
        if (teamType === "seton") {
          setMeetMode(source.type === "championship" ? "championship" : "dual");
          setSetonTeam(teamData);
        } else {
          setOpponentTeam(teamData);
        }

        addLog(`Loaded ${source.name}: ${data.swimmer_count} swimmers`);
      } else {
        throw new Error(data.message || "Load failed");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load";
      setError(message);
      addLog(`Error: ${message}`);
    } finally {
      setLoading(null);
    }
  };

  if (fetching) {
    return (
      <div className="text-center py-4">
        <div className="w-5 h-5 border-2 border-(--gold-500) border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  if (filteredSources.length === 0) {
    return (
      <div className="text-center py-4 text-white/40 text-sm">
        No pre-loaded data available for {mode} mode
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-(--gold-400)">
          {mode === "championship"
            ? "Championship Data"
            : `${teamType === "seton" ? "Seton" : "Opponent"} Rosters`}
        </h4>
        <span className="text-xs text-white/40">Quick load</span>
      </div>

      <div className="space-y-2">
        {filteredSources.map((source) => (
          <button
            key={source.id}
            onClick={() => handleLoadSource(source)}
            disabled={loading !== null || !source.available}
            className={`w-full p-3 rounded-lg text-left transition-all ${
              !source.available
                ? "bg-(--navy-800) opacity-50 cursor-not-allowed"
                : loading === source.id
                  ? "bg-(--gold-muted) border border-(--gold-500)"
                  : "bg-(--navy-700) hover:bg-(--navy-600) border border-transparent hover:border-(--navy-400)"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium text-white text-sm">{source.name}</p>
                <p className="text-xs text-white/50">{source.description}</p>
              </div>
              {loading === source.id ? (
                <div className="w-5 h-5 border-2 border-(--gold-500) border-t-transparent rounded-full animate-spin" />
              ) : source.available ? (
                <div className="flex items-center gap-2">
                  {source.teams && source.teams > 1 && (
                    <span className="text-xs bg-(--navy-600) px-2 py-0.5 rounded">
                      {source.teams} teams
                    </span>
                  )}
                  <span className="text-(--gold-400)">&rarr;</span>
                </div>
              ) : (
                <span className="text-xs text-white/30">Unavailable</span>
              )}
            </div>
          </button>
        ))}
      </div>

      {error && <p className="text-xs text-red-400 text-center">{error}</p>}
    </div>
  );
}
