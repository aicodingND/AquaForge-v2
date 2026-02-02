"use client";

import { useEffect, useRef, useCallback, useState } from "react";

export interface PersistenceData {
  setonTeam?: {
    name: string;
    filename: string;
    data: { swimmer: string; event: string; time: string | number; gender?: string }[];
    swimmerCount: number;
    entryCount: number;
    events: string[];
    teams?: string[];
  } | null;
  opponentTeam?: {
    name: string;
    filename: string;
    data: { swimmer: string; event: string; time: string | number; gender?: string }[];
    swimmerCount: number;
    entryCount: number;
    events: string[];
    teams?: string[];
  } | null;
  optimizationResults?: {
    event: string;
    event_number: number;
    seton_swimmers: string[];
    seton_times: string[];
    opponent_swimmers: string[];
    opponent_times: string[];
    projected_score: { seton: number; opponent: number };
  }[] | null;
  setonScore?: number;
  opponentScore?: number;
  meetMode?: "dual" | "championship";
  lastSaved: string;
}

interface UsePersistenceOptions {
  key?: string;
  debounceMs?: number;
  onSave?: (data: PersistenceData) => void;
  onLoad?: (data: PersistenceData) => void;
  onError?: (error: Error) => void;
}

export function usePersistence({
  key = "aquaforge-data",
  debounceMs = 1000,
  onSave,
  onLoad,
  onError,
}: UsePersistenceOptions = {}) {
  const [isSaving, setIsSaving] = useState(false);
  const saveTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const lastSaveRef = useRef<string>("");

  // Load data on mount
  useEffect(() => {
    try {
      const savedData = localStorage.getItem(key);
      if (savedData) {
        const parsed: PersistenceData = JSON.parse(savedData);

        // Validate data is recent (within 7 days)
        const saveTime = new Date(parsed.lastSaved);
        const now = new Date();
        const daysDiff =
          (now.getTime() - saveTime.getTime()) / (1000 * 60 * 60 * 24);

        if (daysDiff <= 7) {
          onLoad?.(parsed);
        } else {
          // Clear old data
          localStorage.removeItem(key);
        }
      }
    } catch (error) {
      console.warn("Failed to load persisted data:", error);
      onError?.(
        error instanceof Error ? error : new Error("Failed to load data"),
      );
    }
  }, [key, onLoad, onError]);

  // Save data with debouncing
  const saveData = useCallback(
    (data: Partial<PersistenceData>) => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      setIsSaving(true);

      saveTimeoutRef.current = setTimeout(() => {
        try {
          // Get current data from localStorage
          const currentDataStr = localStorage.getItem(key);
          const currentData: PersistenceData = currentDataStr
            ? JSON.parse(currentDataStr)
            : { lastSaved: new Date().toISOString() };

          // Merge with new data
          const mergedData: PersistenceData = {
            ...currentData,
            ...data,
            lastSaved: new Date().toISOString(),
          };

          // Only save if data actually changed
          const dataStr = JSON.stringify(mergedData);
          if (dataStr !== lastSaveRef.current) {
            localStorage.setItem(key, dataStr);
            lastSaveRef.current = dataStr;
            onSave?.(mergedData);
          }
        } catch (error) {
          console.error("Failed to save data:", error);
          onError?.(
            error instanceof Error ? error : new Error("Failed to save data"),
          );
        } finally {
          setIsSaving(false);
        }
      }, debounceMs);
    },
    [key, debounceMs, onSave, onError],
  );

  // Clear all persisted data
  const clearData = useCallback(() => {
    try {
      localStorage.removeItem(key);
      lastSaveRef.current = "";
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
        setIsSaving(false);
      }
    } catch (error) {
      console.error("Failed to clear data:", error);
      onError?.(
        error instanceof Error ? error : new Error("Failed to clear data"),
      );
    }
  }, [key, onError]);

  // Force immediate save (bypasses debouncing)
  const forceSave = useCallback(
    (data: Partial<PersistenceData>) => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }

      setIsSaving(true);

      try {
        const currentDataStr = localStorage.getItem(key);
        const currentData: PersistenceData = currentDataStr
          ? JSON.parse(currentDataStr)
          : { lastSaved: new Date().toISOString() };

        const mergedData: PersistenceData = {
          ...currentData,
          ...data,
          lastSaved: new Date().toISOString(),
        };

        const dataStr = JSON.stringify(mergedData);
        localStorage.setItem(key, dataStr);
        lastSaveRef.current = dataStr;
        onSave?.(mergedData);
      } catch (error) {
        console.error("Failed to force save data:", error);
        onError?.(
          error instanceof Error
            ? error
            : new Error("Failed to force save data"),
        );
      } finally {
        setIsSaving(false);
      }
    },
    [key, onSave, onError],
  );

  // Get current data without triggering save
  const getCurrentData = useCallback((): PersistenceData | null => {
    try {
      const dataStr = localStorage.getItem(key);
      return dataStr ? JSON.parse(dataStr) : null;
    } catch (error) {
      console.error("Failed to get current data:", error);
      return null;
    }
  }, [key]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  return {
    saveData,
    forceSave,
    clearData,
    getCurrentData,
    isSaving,
  };
}

// Hook for auto-saving app store state
export function useAutoPersistence(
  store: {
    setonTeam: PersistenceData["setonTeam"];
    opponentTeam: PersistenceData["opponentTeam"];
    optimizationResults: PersistenceData["optimizationResults"];
    meetMode: PersistenceData["meetMode"];
  } | null,
  options: UsePersistenceOptions = {},
) {
  const { saveData, forceSave, clearData, getCurrentData, isSaving } =
    usePersistence(options);

  // Auto-save when relevant store data changes
  useEffect(() => {
    if (!store) return;

    const { setonTeam, opponentTeam, optimizationResults, meetMode } = store;

    // Only save if we have meaningful data
    const hasData =
      (setonTeam?.data?.length ?? 0) > 0 ||
      (opponentTeam?.data?.length ?? 0) > 0 ||
      optimizationResults;

    if (hasData) {
      saveData({
        setonTeam,
        opponentTeam,
        optimizationResults,
        meetMode,
      });
    }
  }, [
    store?.setonTeam,
    store?.opponentTeam,
    store?.optimizationResults,
    store?.meetMode,
    saveData,
  ]);

  return {
    saveData,
    forceSave,
    clearData,
    getCurrentData,
    isSaving,
  };
}

// Component for displaying persistence status
export function PersistenceStatus({
  isSaving,
  lastSaved,
  onClear,
}: {
  isSaving?: boolean;
  lastSaved?: string;
  onClear?: () => void;
}) {
  const getStatusText = () => {
    if (isSaving) return "Saving...";
    if (lastSaved) {
      const saved = new Date(lastSaved);
      const now = new Date();
      const minutes = Math.floor(
        (now.getTime() - saved.getTime()) / (1000 * 60),
      );

      if (minutes < 1) return "Just saved";
      if (minutes < 60) return `Saved ${minutes}m ago`;
      if (minutes < 1440) return `Saved ${Math.floor(minutes / 60)}h ago`;
      return `Saved ${Math.floor(minutes / 1440)}d ago`;
    }
    return "Not saved";
  };

  const getStatusColor = () => {
    if (isSaving) return "text-yellow-400";
    if (lastSaved) return "text-green-400";
    return "text-gray-400";
  };

  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={`flex items-center gap-1 ${getStatusColor()}`}>
        {isSaving ? (
          <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
        ) : (
          <div className="w-2 h-2 rounded-full bg-current" />
        )}
        <span>{getStatusText()}</span>
      </div>

      {lastSaved && onClear && (
        <button
          onClick={onClear}
          className="text-white/40 hover:text-white/60 transition-colors underline"
          title="Clear saved data"
        >
          Clear
        </button>
      )}
    </div>
  );
}
