/**
 * AquaForge State Store
 * Zustand-like state management using React Context
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { SwimmerEntry, OptimizationResult, StrategyInfo } from "./api";

interface TeamData {
  name: string;
  filename: string;
  data: SwimmerEntry[];
  swimmerCount: number;
  entryCount: number;
  events: string[];
  teams?: string[]; // Team codes for championship meets
}

// Serializable versions for persistence
interface CoachLockEntry {
  swimmer: string;
  events: string[];
}

interface EventBreakdown {
  event: string;
  entries: { swimmer: string; team: string; time: number; place: number; points: number }[];
  team_points: Record<string, number>;
}

interface SwingEvent {
  swimmer: string;
  event: string;
  point_gain: number;
  current_place: number;
  target_place: number;
}

interface AppState {
  // Team data
  setonTeam: TeamData | null;
  opponentTeam: TeamData | null;

  // Meet configuration
  meetMode: "dual" | "championship";
  selectedMeetId: string | null;
  selectedOpponentId: string | null;

  // Coach Locks (up to 3 swimmer-event pairs)
  coachLockedEvents: CoachLockEntry[];
  excludedSwimmers: string[];
  swimmerTimeOverrides: { swimmer: string; event: string; time: string }[];

  // Optimization state
  isOptimizing: boolean;
  optimizationResults: OptimizationResult[] | null;
  setonScore: number;
  opponentScore: number;

  // Championship-specific
  championshipStandings:
    | { rank: number; team: string; points: number }[]
    | null;
  eventBreakdowns: Record<string, EventBreakdown> | null;
  swingEvents: SwingEvent[] | null;

  // Advanced Settings
  enforceFatigue: boolean;
  robustMode: boolean;
  scoringType:
    | "visaa_top7"
    | "standard_top5"
    | "vcac_championship"
    | "visaa_state";

  // Championship Strategy
  selectedStrategy: string;
  availableStrategies: StrategyInfo[];

  // Optimizer Backend (aqua, gurobi, highs, etc.)
  selectedBackend: string;

  // UI state
  activeTab: "upload" | "optimize" | "results";
  logs: string[];

  // Actions
  setSetonTeam: (team: TeamData | null) => void;
  setOpponentTeam: (team: TeamData | null) => void;
  setMeetMode: (mode: "dual" | "championship") => void;
  setSelectedMeet: (meetId: string | null) => void;
  setSelectedOpponent: (teamId: string | null) => void;

  // Coach Lock Actions
  lockSwimmerEvent: (swimmer: string, event: string) => void;
  unlockSwimmerEvent: (swimmer: string, event: string) => void;
  clearAllLocks: () => void;
  toggleSwimmerExcluded: (swimmer: string) => void;
  updateSwimmerTime: (swimmer: string, event: string, newTime: string) => void;

  setOptimizing: (isOptimizing: boolean) => void;
  setOptimizerSettings: (settings: {
    backend?: string;
    fatigue?: boolean;
    robust?: boolean;
    scoring?:
      | "visaa_top7"
      | "standard_top5"
      | "vcac_championship"
      | "visaa_state";
  }) => void;
  setResults: (
    results: OptimizationResult[],
    setonScore: number,
    opponentScore: number,
    championshipData?: {
      standings?: { rank: number; team: string; points: number }[];
      eventBreakdowns?: Record<string, EventBreakdown>;
      swingEvents?: SwingEvent[];
    },
  ) => void;
  setChampionshipStrategy: (strategyId: string) => void;
  setAvailableStrategies: (strategies: StrategyInfo[]) => void;
  setSelectedBackend: (backend: string) => void;
  setActiveTab: (tab: "upload" | "optimize" | "results") => void;
  addLog: (message: string) => void;
}

const STORAGE_VERSION = 2; // Increment when state shape changes significantly

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial State
      setonTeam: null,
      opponentTeam: null,

      meetMode: "dual",
      selectedMeetId: null,
      selectedOpponentId: null,

      coachLockedEvents: [],
      excludedSwimmers: [],
      swimmerTimeOverrides: [],

      isOptimizing: false,
      optimizationResults: null,
      setonScore: 0,
      opponentScore: 0,

      championshipStandings: null,
      eventBreakdowns: null,
      swingEvents: null,

      enforceFatigue: true,
      robustMode: false,
      scoringType: "visaa_top7",

      selectedStrategy: "maximize_individual",
      availableStrategies: [],
      selectedBackend: "aqua",

      activeTab: "upload",
      logs: [],

      // Actions
      setSetonTeam: (team) =>
        set((state) => ({
          setonTeam: team,
          setonScore: 0,
          opponentScore: 0,
          optimizationResults: null,
          logs: [...state.logs, `Loaded team: ${team?.name || "Unknown"}`],
        })),

      setOpponentTeam: (team) =>
        set((state) => ({
          opponentTeam: team,
          setonScore: 0,
          opponentScore: 0,
          optimizationResults: null,
          logs: [
            ...state.logs,
            team ? `Loaded opponent: ${team.name}` : "Cleared opponent data",
          ],
        })),

      setMeetMode: (mode) =>
        set((state) => ({
          meetMode: mode,
          // Auto-configure scoring system for the selected mode
          scoringType:
            mode === "championship"
              ? "vcac_championship"
              : "visaa_top7",
          logs: [
            ...state.logs,
            `Switched to ${mode === "dual" ? "Dual Meet" : "Championship"} mode`,
          ],
        })),

      setSelectedMeet: (meetId) => set({ selectedMeetId: meetId }),
      setSelectedOpponent: (teamId) => set({ selectedOpponentId: teamId }),

      lockSwimmerEvent: (swimmer, event) =>
        set((state) => {
          // Limit to 3 locks
          if (state.coachLockedEvents.length >= 3) {
            return {
              logs: [...state.logs, "Cannot lock more than 3 events"],
            };
          }
          // Check if already locked
          const exists = state.coachLockedEvents.some(
            (l) => l.swimmer === swimmer && l.events.includes(event),
          );
          if (exists) return state;

          // Add lock
          return {
            coachLockedEvents: [
              ...state.coachLockedEvents,
              { swimmer, events: [event] },
            ],
            logs: [...state.logs, `Locked ${swimmer} in ${event}`],
          };
        }),

      unlockSwimmerEvent: (swimmer, event) =>
        set((state) => ({
          coachLockedEvents: state.coachLockedEvents
            .map((lock) =>
              lock.swimmer === swimmer
                ? {
                    ...lock,
                    events: lock.events.filter((e) => e !== event),
                  }
                : lock,
            )
            .filter((lock) => lock.events.length > 0),
          logs: [...state.logs, `Unlocked ${swimmer} in ${event}`],
        })),

      clearAllLocks: () =>
        set((state) => ({
          coachLockedEvents: [],
          logs: [...state.logs, "Cleared all coach locks"],
        })),

      toggleSwimmerExcluded: (swimmer) =>
        set((state) => {
          const isExcluded = state.excludedSwimmers.includes(swimmer);
          return {
            excludedSwimmers: isExcluded
              ? state.excludedSwimmers.filter((s) => s !== swimmer)
              : [...state.excludedSwimmers, swimmer],
            logs: [
              ...state.logs,
              isExcluded ? `Included ${swimmer}` : `Excluded ${swimmer}`,
            ],
          };
        }),

      updateSwimmerTime: (swimmer, event, time) =>
        set((state) => {
          const existing = state.swimmerTimeOverrides.findIndex(
            (o) => o.swimmer === swimmer && o.event === event,
          );

          const newOverrides = [...state.swimmerTimeOverrides];
          if (existing >= 0) {
            newOverrides[existing] = { swimmer, event, time };
          } else {
            newOverrides.push({ swimmer, event, time });
          }

          return {
            swimmerTimeOverrides: newOverrides,
            logs: [...state.logs, `Set override for ${swimmer}: ${time}`],
          };
        }),

      setOptimizing: (isOptimizing) => set({ isOptimizing }),

      setOptimizerSettings: (settings) =>
        set((state) => ({
          selectedBackend: settings.backend ?? state.selectedBackend,
          enforceFatigue: settings.fatigue ?? state.enforceFatigue,
          robustMode: settings.robust ?? state.robustMode,
          scoringType: settings.scoring ?? state.scoringType,
          logs: [...state.logs, "Updated optimization settings"],
        })),

      setResults: (results, setonScore, opponentScore, championshipData) =>
        set((state) => ({
          optimizationResults: results,
          setonScore,
          opponentScore,
          championshipStandings: championshipData?.standings || null,
          eventBreakdowns: championshipData?.eventBreakdowns || null,
          swingEvents: championshipData?.swingEvents || null,
          isOptimizing: false,
          logs: [
            ...state.logs,
            `Optimization complete. Score: ${setonScore}-${opponentScore}`,
          ],
        })),

      setChampionshipStrategy: (strategyId) =>
        set((state) => ({
          selectedStrategy: strategyId,
          logs: [...state.logs, `Strategy changed to: ${strategyId}`],
        })),

      setAvailableStrategies: (strategies) =>
        set({ availableStrategies: strategies }),

      setSelectedBackend: (backend) =>
        set((state) => ({
          selectedBackend: backend,
          logs: [...state.logs, `Backend changed to: ${backend}`],
        })),

      setActiveTab: (tab) => set({ activeTab: tab }),

      addLog: (message) =>
        set((state) => ({
          logs: [...state.logs.slice(-49), message].filter(Boolean) as string[],
        })),
    }),
    {
      name: "aquaforge-storage",
      storage: createJSONStorage(() => localStorage),
      version: STORAGE_VERSION,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      migrate: (persistedState: any, version: number) => {
        // Handle migration from older versions
        console.log(
          `[Store] Migrating from version ${version} to ${STORAGE_VERSION}`,
        );

        // Ensure all required fields exist
        const migratedState = {
          ...persistedState,
          championshipStandings: persistedState.championshipStandings || null,
          eventBreakdowns: persistedState.eventBreakdowns || null,
          swingEvents: persistedState.swingEvents || null,
          enforceFatigue: persistedState.enforceFatigue ?? true,
          robustMode: persistedState.robustMode ?? false,
          selectedStrategy:
            persistedState.selectedStrategy || "maximize_individual",
          availableStrategies: persistedState.availableStrategies || [],
          selectedBackend: persistedState.selectedBackend || "aqua",
          activeTab: persistedState.activeTab || "upload",
          logs: Array.isArray(persistedState.logs)
            ? persistedState.logs.slice(-20)
            : [],
        };

        return migratedState;
      },
      onRehydrateStorage: () => (state) => {
        console.log(
          "[Store] Rehydration complete",
          state ? "success" : "failed",
        );

        // Add rehydration log
        if (state) {
          state.addLog("Application state restored from local storage");
        }
      },
      partialize: (state) => ({
        setonTeam: state.setonTeam,
        opponentTeam: state.opponentTeam,
        meetMode: state.meetMode,
        selectedMeetId: state.selectedMeetId,
        selectedOpponentId: state.selectedOpponentId,
        coachLockedEvents: state.coachLockedEvents,
        excludedSwimmers: state.excludedSwimmers,
        swimmerTimeOverrides: state.swimmerTimeOverrides,
        optimizationResults: state.optimizationResults,
        setonScore: state.setonScore,
        opponentScore: state.opponentScore,
        championshipStandings: state.championshipStandings,
        eventBreakdowns: state.eventBreakdowns,
        swingEvents: state.swingEvents,
        enforceFatigue: state.enforceFatigue,
        robustMode: state.robustMode,
        scoringType: state.scoringType,
        selectedStrategy: state.selectedStrategy,
        availableStrategies: state.availableStrategies,
        selectedBackend: state.selectedBackend,
        activeTab: state.activeTab,
        logs: state.logs.slice(-20), // Keep only last 20 logs to avoid storage limits
      }),
    },
  ),
);
