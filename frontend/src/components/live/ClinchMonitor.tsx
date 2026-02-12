"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";

interface ClinchScenario {
  position: number;
  points_ahead: number;
  points_behind: number;
  can_clinch: boolean;
  requirements: string[]; // "Win 400 Free Relay"
  can_be_caught: boolean;
  dangers: string[]; // "Lose if Team B wins Relay"
}

interface ClinchData {
  target_team: string;
  current_position: number;
  scenarios: ClinchScenario[];
}

export default function ClinchMonitor({
  meetName,
  targetTeam,
}: {
  meetName: string;
  targetTeam: string;
}) {
  const [data, setData] = useState<ClinchData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchScenarios = async () => {
    setLoading(true);
    try {
      const resp = await api.getClinchScenarios(meetName, targetTeam);
      setData(resp);
    } catch (error) {
      console.error("Failed to load clinch scenarios:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, [meetName, targetTeam]);

  if (!data)
    return <div className="text-white/50 text-sm">Loading scenarios...</div>;

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          Clinch Monitor:{" "}
          <span className="text-[var(--gold-400)]">{targetTeam}</span>
        </h3>
        <button
          onClick={fetchScenarios}
          className={`btn btn-sm btn-outline ${loading ? "animate-spin" : ""}`}
        >
          ↻
        </button>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between text-sm glass-card bg-white/5 p-3">
          <span className="text-white/70">Current Position</span>
          <span className="text-xl font-bold text-white">
            #{data.current_position}
          </span>
        </div>

        {data.scenarios.map((s) => (
          <div key={s.position} className="border-t border-white/10 pt-4">
            <h4 className="font-medium text-white mb-2 flex items-center justify-between">
              <span>Goal: Finish #{s.position}</span>
              {s.can_clinch ? (
                <span className="badge badge-success">Clinchable</span>
              ) : (
                <span className="badge badge-error">Out of Reach</span>
              )}
            </h4>

            {s.can_clinch ? (
              <div className="space-y-2">
                <p className="text-green-400 text-xs font-semibold">
                  TO LOCK IT UP:
                </p>
                <ul className="text-xs text-white/80 list-disc list-inside space-y-1">
                  {s.requirements.length > 0 ? (
                    s.requirements.map((r, i) => <li key={i}>{r}</li>)
                  ) : (
                    <li>Already Clinched!</li>
                  )}
                </ul>
              </div>
            ) : (
              <p className="text-xs text-white/50">
                Cannot mathematically clinch this spot yet.
              </p>
            )}

            {s.can_be_caught && (
              <div className="mt-3">
                <p className="text-red-400 text-xs font-semibold">
                  DANGER ZONES:
                </p>
                <ul className="text-xs text-white/80 list-disc list-inside space-y-1">
                  {s.dangers.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
