"use client";

interface RosterHeaderProps {
  teamName: string;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  activeTab: "ALL" | "M" | "F";
  onTabChange: (tab: "ALL" | "M" | "F") => void;
  counts: { ALL: number; M: number; F: number };
  showLockControls: boolean;
  currentLockCount: number;
  maxLocks: number;
  showBulkControls: boolean;
  selectAll: boolean;
  onSelectAll: () => void;
  selectedCount: number;
}

export default function RosterHeader({
  teamName,
  searchQuery,
  onSearchChange,
  activeTab,
  onTabChange,
  counts,
  showLockControls,
  currentLockCount,
  maxLocks,
  showBulkControls,
  selectAll,
  onSelectAll,
  selectedCount,
}: RosterHeaderProps) {
  return (
    <div className="p-4 border-b border-[var(--navy-500)]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-white">{teamName}</h3>
        </div>

        {showLockControls && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-white/50">Coach Locks:</span>
            <span
              className={`font-mono ${currentLockCount >= maxLocks ? "text-[var(--warning)]" : "text-white"}`}
            >
              {currentLockCount}/{maxLocks}
            </span>
          </div>
        )}
      </div>

      {/* Search and Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search swimmers..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full px-3 py-2 bg-[var(--navy-800)] border border-[var(--navy-600)] rounded-lg text-white placeholder-white/40 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--gold-500)] focus:border-transparent"
          />
        </div>

        {showBulkControls && (
          <div className="flex items-center gap-2">
            <button
              onClick={onSelectAll}
              className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                selectAll
                  ? "bg-[var(--gold-500)] text-[var(--navy-900)]"
                  : "bg-[var(--navy-800)] text-white/60 hover:text-white hover:bg-[var(--navy-700)]"
              }`}
            >
              {selectAll ? "Deselect All" : "Select All"}
            </button>

            {selectedCount > 0 && (
              <span className="px-2 py-1 bg-[var(--gold-500)]/20 text-[var(--gold-300)] rounded text-xs font-medium">
                {selectedCount} selected
              </span>
            )}
          </div>
        )}
      </div>

      {/* Gender Tabs */}
      <div className="flex p-1 bg-[var(--navy-900)]/50 rounded-lg">
        {(["ALL", "M", "F"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-all ${
              activeTab === tab
                ? "bg-[var(--navy-600)] text-white shadow-sm"
                : "text-white/50 hover:text-white/70"
            }`}
          >
            {tab === "ALL" ? "All Swimmers" : tab === "M" ? "Boys" : "Girls"}
            <span
              className={`ml-2 text-[10px] ${activeTab === tab ? "text-white/80" : "text-white/30"}`}
            >
              {counts[tab]}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
