"use client";

import { useState } from "react";
import { SwimmerEntry } from "@/lib/api";
import BulkOperations from "./BulkOperations";
import MobileRosterCard from "./MobileRosterCard";
import RosterHeader from "./roster/RosterHeader";
import RosterRow from "./roster/RosterRow";

interface RosterTableProps {
  data: SwimmerEntry[];
  teamName: string;
  onSwimmerToggle?: (swimmerId: string, included: boolean) => void;
  onTimeEdit?: (swimmerId: string, event: string, newTime: string) => void;
  onLockSwimmer?: (swimmerId: string, event: string, locked: boolean) => void;
  onBulkSelect?: (swimmerIds: string[], selected: boolean) => void;
  onBulkExclude?: (swimmerIds: string[]) => void;
  onBulkLock?: (swimmerIds: string[], events: string[]) => void;
  onBulkUnlock?: (swimmerIds: string[]) => void;
  lockedSwimmers?: Map<string, string[]>; // swimmerId -> events[]
  excludedSwimmers?: Set<string>;
  showLockControls?: boolean;
  showBulkControls?: boolean;
  maxLocks?: number;
  className?: string;
}

export default function RosterTable({
  data,
  teamName,
  onSwimmerToggle,
  onTimeEdit,
  onLockSwimmer,
  onBulkSelect,
  onBulkExclude,
  onBulkLock,
  onBulkUnlock,
  lockedSwimmers = new Map(),
  excludedSwimmers = new Set(),
  showLockControls = true,
  showBulkControls = true,
  maxLocks = 3,
  className = "",
}: RosterTableProps) {
  const [expandedSwimmer, setExpandedSwimmer] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"ALL" | "M" | "F">("ALL");
  const [selectedSwimmers, setSelectedSwimmers] = useState<Set<string>>(
    new Set(),
  );
  const [selectAll, setSelectAll] = useState(false);

  // Group entries by swimmer and identify gender
  const swimmerMap = new Map<
    string,
    { entries: SwimmerEntry[]; gender: string }
  >();
  data.forEach((entry) => {
    const existing = swimmerMap.get(entry.swimmer) || {
      entries: [],
      gender: "U",
    };
    existing.entries.push(entry);
    // Attempt to determine gender from entry if not already set (or if 'U')
    if (existing.gender === "U" && entry.gender) {
      existing.gender = entry.gender;
    }
    // Also try to guess from event name if gender missing (e.g., "Boys 50 Free")
    if (existing.gender === "U" && entry.event) {
      if (entry.event.toLowerCase().includes("boys")) existing.gender = "M";
      if (entry.event.toLowerCase().includes("girls")) existing.gender = "F";
    }
    swimmerMap.set(entry.swimmer, existing);
  });

  // Calculate counts
  const counts = {
    ALL: swimmerMap.size,
    M: Array.from(swimmerMap.values()).filter((s) => s.gender === "M").length,
    F: Array.from(swimmerMap.values()).filter((s) => s.gender === "F").length,
  };

  // Filter and sort
  const swimmers = Array.from(swimmerMap.keys())
    .filter((name) => {
      const info = swimmerMap.get(name);
      if (activeTab !== "ALL" && info?.gender !== activeTab) return false;
      return name.toLowerCase().includes(searchQuery.toLowerCase());
    })
    .sort((a, b) => a.localeCompare(b));

  const currentLockCount = Array.from(lockedSwimmers.values()).reduce(
    (acc, events) => acc + events.length,
    0,
  );

  const isSwimmerLocked = (swimmer: string, event: string): boolean => {
    const events = lockedSwimmers.get(swimmer);
    return events ? events.includes(event) : false;
  };

  const canAddLock = currentLockCount < maxLocks;

  const handleLockToggle = (swimmer: string, event: string) => {
    if (!onLockSwimmer) return;
    const isLocked = isSwimmerLocked(swimmer, event);
    if (!isLocked && !canAddLock) return; // Can't add more locks
    onLockSwimmer(swimmer, event, !isLocked);
  };

  // Bulk selection handlers
  const handleSwimmerSelect = (swimmerId: string, selected: boolean) => {
    const newSelection = new Set(selectedSwimmers);
    if (selected) {
      newSelection.add(swimmerId);
    } else {
      newSelection.delete(swimmerId);
    }
    setSelectedSwimmers(newSelection);
    onBulkSelect?.([swimmerId], selected);
  };

  const handleSelectAllSwimmers = () => {
    const allSwimmerIds = swimmers;
    const newSelectAll = !selectAll;
    setSelectAll(newSelectAll);
    setSelectedSwimmers(new Set(newSelectAll ? allSwimmerIds : []));
    onBulkSelect?.(allSwimmerIds, newSelectAll);
  };

  // Get available events for bulk operations
  const availableEvents = Array.from(
    new Set(data.flatMap((entry) => entry.event)),
  ).sort();

  // Bulk operation handlers
  const handleBulkExclude = (swimmerIds: string[]) => {
    swimmerIds.forEach((swimmerId) => {
      onSwimmerToggle?.(swimmerId, false);
    });
    setSelectedSwimmers(new Set());
    setSelectAll(false);
  };

  const handleBulkLock = (swimmerIds: string[], events: string[]) => {
    swimmerIds.forEach((swimmerId) => {
      events.forEach((event) => {
        onLockSwimmer?.(swimmerId, event, true);
      });
    });
    setSelectedSwimmers(new Set());
    setSelectAll(false);
  };

  const handleBulkUnlock = (swimmerIds: string[]) => {
    swimmerIds.forEach((swimmerId) => {
      const lockedEvents = lockedSwimmers.get(swimmerId) || [];
      lockedEvents.forEach((event) => {
        onLockSwimmer?.(swimmerId, event, false);
      });
    });
    setSelectedSwimmers(new Set());
    setSelectAll(false);
  };

  return (
    <div className={`glass-card overflow-hidden ${className}`}>
      {/* Header */}
      <RosterHeader
        teamName={teamName}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        counts={counts}
        showLockControls={showLockControls}
        currentLockCount={currentLockCount}
        maxLocks={maxLocks}
        showBulkControls={showBulkControls}
        selectAll={selectAll}
        onSelectAll={handleSelectAllSwimmers}
        selectedCount={selectedSwimmers.size}
      />

      {/* Bulk Operations Panel */}
      {showBulkControls && selectedSwimmers.size > 0 && (
        <BulkOperations
          selectedSwimmers={selectedSwimmers}
          onBulkSelect={
            onBulkSelect ||
            ((ids, selected) =>
              ids.forEach((id) => handleSwimmerSelect(id, selected)))
          }
          onBulkExclude={handleBulkExclude}
          onBulkLock={handleBulkLock}
          onBulkUnlock={handleBulkUnlock}
          availableEvents={availableEvents}
          maxLocks={maxLocks}
          currentLockCount={currentLockCount}
          className="border-b border-[var(--navy-600)]"
        />
      )}

      {/* Roster List */}
      <div className="max-h-[400px] overflow-y-auto">
        {swimmers.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-white/40">No swimmers found</p>
          </div>
        ) : (
          swimmers.map((swimmer) => {
            const info = swimmerMap.get(swimmer);
            const entries = info?.entries || [];
            const isExpanded = expandedSwimmer === swimmer;
            const isExcluded = excludedSwimmers.has(swimmer);
            const swimmerLocks = lockedSwimmers.get(swimmer) || [];
            const hasLock = swimmerLocks.length > 0;

            return (
              <>
                {/* Mobile Card View */}
                <div className="sm:hidden">
                  <MobileRosterCard
                    swimmer={swimmer}
                    entries={entries}
                    gender={info?.gender || "U"}
                    isExpanded={isExpanded}
                    onToggle={() =>
                      setExpandedSwimmer(isExpanded ? null : swimmer)
                    }
                    onIncludeToggle={(swimId, included) =>
                      onSwimmerToggle?.(swimId, included)
                    }
                    onTimeEdit={(swimId, evt, time) =>
                      onTimeEdit?.(swimId, evt, time)
                    }
                    onLockToggle={(event, locked) =>
                      onLockSwimmer?.(swimmer, event, Boolean(locked))
                    }
                    isExcluded={isExcluded}
                    lockedEvents={swimmerLocks}
                    showLockControls={showLockControls}
                    canAddLock={canAddLock}
                  />
                </div>

                {/* Desktop Table View */}
                <RosterRow
                  swimmer={swimmer}
                  entries={entries}
                  gender={info?.gender || "U"}
                  isExpanded={isExpanded}
                  isExcluded={isExcluded}
                  lockedEvents={swimmerLocks}
                  canAddLock={canAddLock}
                  showLockControls={showLockControls}
                  showBulkControls={showBulkControls}
                  onToggleExpand={() =>
                    setExpandedSwimmer(isExpanded ? null : swimmer)
                  }
                  onSwimmerToggle={onSwimmerToggle}
                  onTimeEdit={onTimeEdit}
                  onLockToggle={handleLockToggle}
                />
              </>
            );
          })
        )}
      </div>
    </div>
  );
}
