"use client";

import { useAppStore } from "@/lib/store";
import Toggle from "@/components/ui/Toggle";
import BackendSelector from "@/components/BackendSelector";

export default function SettingsPage() {
  const { scoringType, robustMode, enforceFatigue, setOptimizerSettings } =
    useAppStore();

  return (
    <div className="p-6 lg:p-8 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-white/50 text-sm mt-1">
          Configure optimization and scoring options
        </p>
      </div>

      {/* Settings Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scoring Settings */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="text-(--gold-400)">📊</span> Scoring Rules
          </h2>

          <div className="space-y-4">
            <div>
              <label
                htmlFor="scoring-type"
                className="block text-sm text-white/60 mb-2"
              >
                Scoring Type
              </label>
              <select
                id="scoring-type"
                title="Select scoring type"
                value={scoringType}
                onChange={(e) =>
                  setOptimizerSettings({
                    scoring: e.target.value as typeof scoringType,
                  })
                }
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-(--gold-500) focus:outline-none"
              >
                <option value="visaa_top7">VISAA Top 7 (6-4-3-2-1-0-0)</option>
                <option value="standard_top5">
                  Standard Top 5 (6-4-3-2-1)
                </option>
                <option value="vcac_championship">VCAC Championship</option>
                <option value="visaa_state">VISAA State</option>
              </select>
            </div>
          </div>
        </div>

        {/* Optimization Settings */}
        <div className="glass-card p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <span className="text-(--gold-400)">⚡</span> Optimization
          </h2>

          <div className="space-y-4">
            <Toggle
              enabled={robustMode}
              onChange={(enabled) => setOptimizerSettings({ robust: enabled })}
              label="Robust Mode"
              description="Maximize worst-case performance"
            />

            <Toggle
              enabled={enforceFatigue}
              onChange={(enabled) => setOptimizerSettings({ fatigue: enabled })}
              label="Fatigue Modeling"
              description="Account for swimmer fatigue"
            />
          </div>
        </div>

        {/* Engine Selection - Dynamic BackendSelector */}
        <BackendSelector />
      </div>

      {/* Info Card */}
      <div className="glass-card p-6 border-l-4 border-l-(--gold-500)">
        <h3 className="font-semibold text-white mb-2">💡 About AquaForge</h3>
        <p className="text-sm text-white/60">
          AquaForge uses advanced optimization algorithms including Nash
          Equilibrium, Beam Search, and Simulated Annealing to find optimal swim
          meet lineups.
        </p>
        <p className="text-xs text-white/40 mt-2">
          Version 1.0.0 • Built with ❤️ for Seton Swimming
        </p>
      </div>
    </div>
  );
}
