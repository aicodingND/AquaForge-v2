import { describe, it, expect, beforeEach } from "vitest";
import { useAppStore } from "@/lib/store";

describe("AppStore", () => {
  beforeEach(() => {
    // Reset store between tests
    useAppStore.setState({
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
      sensitivity: null,
      relayAssignments: null,
      enforceFatigue: true,
      robustMode: false,
      scoringType: "visaa_top7",
      selectedStrategy: "maximize_individual",
      availableStrategies: [],
      selectedBackend: "aqua",
      logs: [],
    });
  });

  describe("initial state", () => {
    it("starts with dual meet mode", () => {
      const state = useAppStore.getState();
      expect(state.meetMode).toBe("dual");
    });

    it("starts with no teams loaded", () => {
      const state = useAppStore.getState();
      expect(state.setonTeam).toBeNull();
      expect(state.opponentTeam).toBeNull();
    });

    it("starts with aqua backend selected", () => {
      const state = useAppStore.getState();
      expect(state.selectedBackend).toBe("aqua");
    });

    it("starts with fatigue enforcement enabled", () => {
      const state = useAppStore.getState();
      expect(state.enforceFatigue).toBe(true);
    });
  });

  describe("meet mode switching", () => {
    it("switches to championship mode and auto-sets scoring", () => {
      useAppStore.getState().setMeetMode("championship");
      const state = useAppStore.getState();
      expect(state.meetMode).toBe("championship");
      expect(state.scoringType).toBe("vcac_championship");
    });

    it("switches back to dual mode and restores scoring", () => {
      useAppStore.getState().setMeetMode("championship");
      useAppStore.getState().setMeetMode("dual");
      const state = useAppStore.getState();
      expect(state.meetMode).toBe("dual");
      expect(state.scoringType).toBe("visaa_top7");
    });
  });

  describe("team loading", () => {
    const mockTeam = {
      name: "Seton",
      filename: "seton.csv",
      data: [{ swimmer: "John Doe", event: "50 Freestyle", time: "25.00" }],
      swimmerCount: 1,
      entryCount: 1,
      events: ["50 Freestyle"],
    };

    it("loads seton team and resets scores", () => {
      // Set some existing scores first
      useAppStore.setState({ setonScore: 100, opponentScore: 50 });

      useAppStore.getState().setSetonTeam(mockTeam);
      const state = useAppStore.getState();
      expect(state.setonTeam?.name).toBe("Seton");
      expect(state.setonScore).toBe(0);
      expect(state.opponentScore).toBe(0);
      expect(state.optimizationResults).toBeNull();
    });

    it("clears opponent team", () => {
      useAppStore.getState().setOpponentTeam(mockTeam);
      expect(useAppStore.getState().opponentTeam).not.toBeNull();

      useAppStore.getState().setOpponentTeam(null);
      expect(useAppStore.getState().opponentTeam).toBeNull();
    });
  });

  describe("coach locks", () => {
    it("locks a swimmer-event pair", () => {
      useAppStore.getState().lockSwimmerEvent("Jane Doe", "100 Butterfly");
      const state = useAppStore.getState();
      expect(state.coachLockedEvents).toHaveLength(1);
      expect(state.coachLockedEvents[0].swimmer).toBe("Jane Doe");
    });

    it("enforces max 3 locks", () => {
      const lock = useAppStore.getState().lockSwimmerEvent;
      lock("A", "Event 1");
      lock("B", "Event 2");
      lock("C", "Event 3");
      lock("D", "Event 4"); // should be rejected

      const state = useAppStore.getState();
      expect(state.coachLockedEvents).toHaveLength(3);
    });

    it("unlocks a swimmer-event pair", () => {
      useAppStore.getState().lockSwimmerEvent("Jane Doe", "100 Butterfly");
      useAppStore.getState().unlockSwimmerEvent("Jane Doe", "100 Butterfly");
      expect(useAppStore.getState().coachLockedEvents).toHaveLength(0);
    });

    it("clears all locks", () => {
      useAppStore.getState().lockSwimmerEvent("A", "Event 1");
      useAppStore.getState().lockSwimmerEvent("B", "Event 2");
      useAppStore.getState().clearAllLocks();
      expect(useAppStore.getState().coachLockedEvents).toHaveLength(0);
    });
  });

  describe("swimmer exclusions", () => {
    it("toggles swimmer exclusion on", () => {
      useAppStore.getState().toggleSwimmerExcluded("John Smith");
      expect(useAppStore.getState().excludedSwimmers).toContain("John Smith");
    });

    it("toggles swimmer exclusion off", () => {
      useAppStore.getState().toggleSwimmerExcluded("John Smith");
      useAppStore.getState().toggleSwimmerExcluded("John Smith");
      expect(useAppStore.getState().excludedSwimmers).not.toContain("John Smith");
    });
  });

  describe("optimizer settings", () => {
    it("updates backend selection", () => {
      useAppStore.getState().setSelectedBackend("gurobi");
      expect(useAppStore.getState().selectedBackend).toBe("gurobi");
    });

    it("updates multiple settings at once", () => {
      useAppStore.getState().setOptimizerSettings({
        backend: "highs",
        fatigue: false,
        robust: true,
      });
      const state = useAppStore.getState();
      expect(state.selectedBackend).toBe("highs");
      expect(state.enforceFatigue).toBe(false);
      expect(state.robustMode).toBe(true);
    });

    it("preserves unspecified settings", () => {
      useAppStore.getState().setOptimizerSettings({ backend: "gurobi" });
      const state = useAppStore.getState();
      expect(state.selectedBackend).toBe("gurobi");
      expect(state.enforceFatigue).toBe(true); // default preserved
    });
  });

  describe("results", () => {
    it("stores optimization results and clears optimizing flag", () => {
      useAppStore.setState({ isOptimizing: true });

      useAppStore.getState().setResults(
        [{ event: "50 Free", event_number: 4, seton_swimmers: [], opponent_swimmers: [], seton_times: [], opponent_times: [], projected_score: { seton: 20, opponent: 9 } }],
        130,
        102,
      );

      const state = useAppStore.getState();
      expect(state.optimizationResults).toHaveLength(1);
      expect(state.setonScore).toBe(130);
      expect(state.opponentScore).toBe(102);
      expect(state.isOptimizing).toBe(false);
    });
  });

  describe("logs", () => {
    it("caps logs at 50 entries", () => {
      const addLog = useAppStore.getState().addLog;
      for (let i = 0; i < 60; i++) {
        addLog(`Log entry ${i}`);
      }
      expect(useAppStore.getState().logs.length).toBeLessThanOrEqual(50);
    });
  });
});
