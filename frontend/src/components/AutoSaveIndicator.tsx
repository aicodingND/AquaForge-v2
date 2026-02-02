"use client";

import { useState } from "react";
import { PersistenceStatus, useAutoPersistence } from "@/hooks/usePersistence";
import { useAppStore } from "@/lib/store";

interface AutoSaveIndicatorProps {
  className?: string;
}

export default function AutoSaveIndicator({
  className = "",
}: AutoSaveIndicatorProps) {
  const [lastSaved, setLastSaved] = useState<string | null>(null);
  const [showRestorePrompt, setShowRestorePrompt] = useState(false);
  const store = useAppStore();

  // Set up auto-persistence for the app store
  const { forceSave, clearData, getCurrentData, isSaving } = useAutoPersistence(
    store,
    {
      key: "aquaforge-app-state",
      debounceMs: 2000, // 2 seconds debounce
      onSave: (data) => {
        console.log("💾 Auto-saved app state");
        setLastSaved(data.lastSaved);
      },
      onLoad: (data) => {
        console.log("📂 Loaded persisted app state");

        // Restore data to store if we don't already have data
        if (!store.setonTeam && data.setonTeam) {
          store.setSetonTeam(data.setonTeam);
        }
        if (!store.opponentTeam && data.opponentTeam) {
          store.setOpponentTeam(data.opponentTeam);
        }
        if (!store.optimizationResults && data.optimizationResults) {
          store.setResults(
            data.optimizationResults,
            data.setonScore || 0,
            data.opponentScore || 0,
          );
        }
        if (data.meetMode && store.meetMode !== data.meetMode) {
          store.setMeetMode(data.meetMode);
        }

        setLastSaved(data.lastSaved);

        // Show restore prompt if we have meaningful data
        const hasData =
          (data.setonTeam?.data?.length ?? 0) > 0 ||
          (data.opponentTeam?.data?.length ?? 0) > 0;
        if (hasData) {
          setShowRestorePrompt(true);
        }
      },
      onError: (error) => {
        console.error("❌ Persistence error:", error);
      },
    },
  );

  // Handle data restoration
  const handleRestoreData = () => {
    const data = getCurrentData();
    if (data) {
      store.setSetonTeam(data.setonTeam || null);
      store.setOpponentTeam(data.opponentTeam || null);
      if (data.optimizationResults) {
        store.setResults(
          data.optimizationResults,
          data.setonScore || 0,
          data.opponentScore || 0,
        );
      }
      if (data.meetMode) {
        store.setMeetMode(data.meetMode);
      }
      store.addLog("Previous session data restored");
    }
    setShowRestorePrompt(false);
  };

  const handleClearData = () => {
    clearData();
    setLastSaved(null);
    store.addLog("Saved data cleared");
    setShowRestorePrompt(false);
  };

  const handleForceSave = () => {
    forceSave({
      setonTeam: store.setonTeam,
      opponentTeam: store.opponentTeam,
      optimizationResults: store.optimizationResults,
      meetMode: store.meetMode,
    });
    store.addLog("Manual save triggered");
  };

  return (
    <>
      {/* Restore Prompt */}
      {showRestorePrompt && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-white mb-3">
              Restore Previous Session?
            </h3>
            <p className="text-white/70 text-sm mb-6">
              We found saved data from your last session. Would you like to
              restore it?
            </p>
            <div className="flex gap-3">
              <button
                onClick={handleRestoreData}
                className="flex-1 px-4 py-2 bg-[var(--gold-500)] text-[var(--navy-900)] rounded-lg font-medium hover:bg-[var(--gold-400)] transition-colors"
              >
                Restore Data
              </button>
              <button
                onClick={() => setShowRestorePrompt(false)}
                className="flex-1 px-4 py-2 bg-[var(--navy-700)] text-white rounded-lg font-medium hover:bg-[var(--navy-600)] transition-colors"
              >
                Start Fresh
              </button>
            </div>
            <button
              onClick={handleClearData}
              className="w-full mt-3 text-xs text-white/40 hover:text-white/60 transition-colors underline"
            >
              Clear saved data
            </button>
          </div>
        </div>
      )}

      {/* Auto-save Indicator */}
      <div
        className={`fixed bottom-4 left-4 glass-card px-3 py-2 text-xs ${className}`}
      >
        <PersistenceStatus
          isSaving={isSaving}
          lastSaved={lastSaved ?? undefined}
          onClear={handleClearData}
        />

        {/* Manual Save Button */}
        <button
          onClick={handleForceSave}
          className="mt-2 w-full px-2 py-1 bg-[var(--navy-700)] hover:bg-[var(--navy-600)] text-white/60 hover:text-white/80 rounded transition-colors text-xs"
          title="Force save current state"
        >
          💾 Save Now
        </button>
      </div>
    </>
  );
}
