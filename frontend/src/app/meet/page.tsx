"use client";

import FileUpload from "@/components/FileUpload";
import MeetSelector from "@/components/MeetSelector";
import TeamSelector from "@/components/TeamSelector";
import RosterTable from "@/components/RosterTable";
import ChampionshipTeamsGrid from "@/components/ChampionshipTeamsGrid";
import DataSourceSelector from "@/components/DataSourceSelector";
import { useAppStore } from "@/lib/store";
import { useState, useMemo } from "react";
import Link from "next/link";

export default function MeetSetupPage() {
  const {
    setonTeam,
    opponentTeam,
    meetMode,
    selectedMeetId,
    selectedOpponentId,
    setSelectedMeet,
    setSelectedOpponent,
    coachLockedEvents,
    excludedSwimmers,
    lockSwimmerEvent,
    unlockSwimmerEvent,
    toggleSwimmerExcluded,
    updateSwimmerTime,
  } = useAppStore();

  const [activeSection, setActiveSection] = useState<
    "setup" | "upload" | "roster" | "teams"
  >("setup");

  const isDual = meetMode === "dual";
  const readyToOptimize = isDual
    ? setonTeam && opponentTeam
    : setonTeam != null;

  // Convert store format to Map for RosterTable
  const lockedSwimmersMap = useMemo(() => {
    const map = new Map<string, string[]>();
    coachLockedEvents.forEach((entry) => {
      map.set(entry.swimmer, entry.events);
    });
    return map;
  }, [coachLockedEvents]);

  const excludedSwimmersSet = useMemo(
    () => new Set(excludedSwimmers),
    [excludedSwimmers],
  );

  const handleLockSwimmer = (
    swimmer: string,
    event: string,
    locked: boolean,
  ) => {
    if (locked) {
      lockSwimmerEvent(swimmer, event);
    } else {
      unlockSwimmerEvent(swimmer, event);
    }
  };

  const handleSwimmerToggle = (swimmer: string) => {
    toggleSwimmerExcluded(swimmer);
  };

  const handleTimeEdit = (swimmer: string, event: string, newTime: string) => {
    updateSwimmerTime(swimmer, event, newTime);
  };

  return (
    <div className="p-6 lg:p-8 space-y-6 pb-32">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Meet Setup</h1>
          <p className="text-white/50 text-sm mt-1">
            {isDual
              ? "Configure dual meet matchup"
              : "Configure championship meet"}
          </p>
        </div>
        <div className="badge badge-gold uppercase">{meetMode} Mode</div>
      </div>

      {/* Debug panel removed - data flow verified working */}

      {/* Meet & Team Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <MeetSelector
          label="Select Meet"
          value={selectedMeetId}
          onChange={setSelectedMeet}
          showAddNew
        />

        {isDual && (
          <TeamSelector
            label="Opponent Team"
            value={selectedOpponentId}
            onChange={setSelectedOpponent}
            excludeTeams={["seton"]}
            showAddNew
          />
        )}

        <div className="flex items-end">
          <div
            className={`flex-1 p-3 rounded-lg ${readyToOptimize ? "bg-[var(--success-muted)]" : "bg-[var(--navy-700)]"}`}
          >
            <p className="text-xs text-white/50 uppercase tracking-wider mb-1">
              Status
            </p>
            <div className="flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${readyToOptimize ? "bg-[var(--success)]" : "bg-[var(--warning)]"}`}
              />
              <span
                className={
                  readyToOptimize ? "text-[var(--success)]" : "text-white/60"
                }
              >
                {readyToOptimize ? "Ready to Optimize" : "Data Needed"}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-[var(--navy-700)] rounded-lg p-1 w-fit">
        {(isDual
          ? (["setup", "upload", "roster"] as const)
          : (["setup", "upload", "roster", "teams"] as const)
        ).map((section) => (
          <button
            key={section}
            onClick={() =>
              setActiveSection(
                section as "setup" | "upload" | "roster" | "teams",
              )
            }
            className={`py-2 px-4 rounded-md text-sm font-medium transition-all capitalize ${
              activeSection === section
                ? "bg-gradient-to-r from-[var(--gold-400)] to-[var(--gold-500)] text-[var(--navy-900)]"
                : "text-white/60 hover:text-white"
            }`}
          >
            {section === "setup" && "⚙️ "}
            {section === "upload" && "📁 "}
            {section === "roster" && "👥 "}
            {section === "teams" && "🏆 "}
            {section}
          </button>
        ))}
      </div>

      {/* Setup Section */}
      {activeSection === "setup" && (
        <div className="glass-card p-6 space-y-6">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-[var(--gold-400)]">⚙️</span> Quick Setup
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Meet Summary */}
            <div className="p-4 bg-[var(--navy-800)] rounded-lg">
              <p className="text-white/50 text-sm mb-2">Selected Meet</p>
              {selectedMeetId ? (
                <div>
                  <p className="text-white font-medium">
                    {selectedMeetId === "vcac_championship_2026" &&
                      "VCAC Championship"}
                    {selectedMeetId === "visaa_state_2026" &&
                      "VISAA State Championships"}
                    {selectedMeetId === "dual_template" && "Dual Meet (Custom)"}
                  </p>
                  <p className="text-xs text-white/40 mt-1">
                    Mode: {meetMode} • Scoring auto-configured
                  </p>
                </div>
              ) : (
                <p className="text-white/40">Select a meet above</p>
              )}
            </div>

            {/* Coach Locks Summary */}
            <div className="p-4 bg-[var(--navy-800)] rounded-lg">
              <p className="text-white/50 text-sm mb-2">Coach Locked Events</p>
              {coachLockedEvents.length > 0 ? (
                <div className="space-y-1">
                  {coachLockedEvents.map((entry, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <span className="text-[var(--gold-400)]">🔒</span>
                      <span className="text-white">{entry.swimmer}</span>
                      <span className="text-white/40">
                        → {entry.events.join(", ")}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-white/40">No locked assignments</p>
              )}
              <p className="text-xs text-white/30 mt-2">
                Use the Roster tab to lock up to 3 swimmer-event assignments
              </p>
            </div>
          </div>

          {readyToOptimize && (
            <Link href="/optimize" className="btn btn-gold w-full py-4 text-lg">
              ⚡ Proceed to Optimization
            </Link>
          )}

          {/* DEV: Load Sample Data Button */}
          <button
            onClick={async () => {
              try {
                const res = await fetch("/fixtures/sample-teams.json");
                const data = await res.json();
                useAppStore.getState().setMeetMode("dual");
                useAppStore.getState().setSelectedMeet("dual_template");
                useAppStore.getState().setSetonTeam(data.seton);
                useAppStore.getState().setOpponentTeam(data.opponent);
              } catch (err) {
                console.error("Failed to load sample data:", err);
              }
            }}
            className="btn btn-outline w-full py-2 text-sm mt-4 border-dashed opacity-50 hover:opacity-100"
          >
            🛠️ DEV: Load Sample Data
          </button>
        </div>
      )}

      {/* Upload Section */}
      {activeSection === "upload" && (
        <div
          className={`grid grid-cols-1 ${isDual ? "lg:grid-cols-2" : ""} gap-6`}
        >
          {/* Seton / Championship Column */}
          <div className="space-y-4">
            {/* Quick Load Section */}
            <div className="glass-card p-4">
              <DataSourceSelector
                mode={isDual ? "dual" : "championship"}
                teamType="seton"
              />
            </div>

            <FileUpload
              teamType="seton"
              label={isDual ? "Seton Team File" : "Championship Psych Sheet"}
            />
            {setonTeam && (
              <div className="glass-card p-4 border-l-4 border-l-[var(--gold-500)] animate-fade-in">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-white">{setonTeam.name}</h3>
                  <span className="badge badge-success">Loaded</span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-white/50">Swimmers</p>
                    <p className="text-white font-medium text-lg">
                      {setonTeam.swimmerCount}
                    </p>
                  </div>
                  <div>
                    <p className="text-white/50">Entries</p>
                    <p className="text-white font-medium text-lg">
                      {setonTeam.entryCount}
                    </p>
                  </div>
                  {setonTeam.teams && setonTeam.teams.length > 1 && (
                    <div className="col-span-2">
                      <p className="text-white/50">Teams</p>
                      <p className="text-white font-medium">
                        {setonTeam.teams.length} teams:{" "}
                        {setonTeam.teams.slice(0, 4).join(", ")}
                        {setonTeam.teams.length > 4 && "..."}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Opponent Column (Dual Mode Only) */}
          {isDual && (
            <div className="space-y-4">
              {/* Quick Load for Opponents */}
              <div className="glass-card p-4">
                <DataSourceSelector mode="dual" teamType="opponent" />
              </div>

              <FileUpload teamType="opponent" label="Opponent Team File" />
              {opponentTeam && (
                <div className="glass-card p-4 border-l-4 border-l-white/30 animate-fade-in">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-white">
                      {opponentTeam.name}
                    </h3>
                    <span className="badge badge-success">Loaded</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-white/50">Swimmers</p>
                      <p className="text-white font-medium text-lg">
                        {opponentTeam.swimmerCount}
                      </p>
                    </div>
                    <div>
                      <p className="text-white/50">Entries</p>
                      <p className="text-white font-medium text-lg">
                        {opponentTeam.entryCount}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Roster Section */}
      {activeSection === "roster" && (
        <div
          className={`grid grid-cols-1 ${isDual ? "lg:grid-cols-2" : ""} gap-6`}
        >
          {setonTeam ? (
            <RosterTable
              data={setonTeam.data}
              teamName={setonTeam.name}
              lockedSwimmers={lockedSwimmersMap}
              excludedSwimmers={excludedSwimmersSet}
              onLockSwimmer={handleLockSwimmer}
              onSwimmerToggle={handleSwimmerToggle}
              onTimeEdit={handleTimeEdit}
              showLockControls={true}
              maxLocks={3}
            />
          ) : (
            <div className="glass-card p-8 text-center">
              <p className="text-white/40">
                Upload Seton team data to view roster
              </p>
            </div>
          )}

          {isDual &&
            (opponentTeam ? (
              <RosterTable
                data={opponentTeam.data}
                teamName={opponentTeam.name}
                showLockControls={false}
              />
            ) : (
              <div className="glass-card p-8 text-center">
                <p className="text-white/40">
                  Upload opponent data to view roster
                </p>
              </div>
            ))}
        </div>
      )}

      {/* Teams Section (Championship Mode Only) */}
      {activeSection === "teams" && !isDual && (
        <div className="space-y-4">
          <ChampionshipTeamsGrid />
        </div>
      )}

      {/* Optimization CTA - Fixed at bottom, always visible */}
      {activeSection !== "setup" && (
        <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-gradient-to-t from-[var(--navy-900)] via-[var(--navy-900)]/95 to-transparent">
          <div className="max-w-6xl mx-auto">
            <div
              className={`glass-card p-4 shadow-2xl ${readyToOptimize ? "border-[var(--gold-500)] shadow-[var(--gold-500)]/20" : "border-white/10"}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${readyToOptimize ? "bg-gradient-to-br from-[var(--gold-400)] to-[var(--gold-500)] animate-pulse" : "bg-white/10"}`}
                  >
                    <span className="text-xl">
                      {readyToOptimize ? "⚡" : "⏸"}
                    </span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">
                      {readyToOptimize
                        ? "Ready to Optimize!"
                        : "Upload Required"}
                    </h3>
                    <p className="text-white/50 text-sm">
                      {readyToOptimize
                        ? (isDual
                            ? "Both teams loaded"
                            : "Psych sheet loaded") +
                          (coachLockedEvents.length > 0
                            ? ` • ${coachLockedEvents.length} coach lock(s)`
                            : "")
                        : isDual
                          ? !setonTeam && !opponentTeam
                            ? "Upload both team files to continue"
                            : !setonTeam
                              ? "Upload Seton team file"
                              : "Upload opponent team file"
                          : "Upload championship psych sheet to continue"}
                    </p>
                  </div>
                </div>
                {readyToOptimize ? (
                  <Link href="/optimize" className="btn btn-gold">
                    Proceed →
                  </Link>
                ) : (
                  <button
                    disabled
                    className="btn btn-disabled opacity-50 cursor-not-allowed"
                    title={
                      isDual
                        ? !setonTeam && !opponentTeam
                          ? "Upload both teams first"
                          : !setonTeam
                            ? "Upload Seton team first"
                            : "Upload opponent team first"
                        : "Upload psych sheet first"
                    }
                  >
                    Proceed →
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
