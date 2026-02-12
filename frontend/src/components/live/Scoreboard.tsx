"use client";

interface ScoreboardProps {
  scores: Record<string, number>;
  projected: Record<string, number>;
  currentEvent: number;
  totalEvents: number;
}

export default function Scoreboard({
  scores,
  projected,
  currentEvent,
  totalEvents,
}: ScoreboardProps) {
  // Sort teams by total score descending
  const sortedTeams = Object.entries(scores)
    .map(([team, score]) => ({
      team,
      score,
      projected: projected[team] || 0,
      total: score + (projected[team] || 0),
    }))
    .sort((a, b) => b.total - a.total);

  // Get top 2 teams for hero display
  const [team1, team2] = sortedTeams;

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="flex items-center justify-between text-xs text-white/50 mb-1">
        <span>
          Event {currentEvent} of {totalEvents}
        </span>
        <span>{Math.round((currentEvent / totalEvents) * 100)}% Complete</span>
      </div>
      <div className="w-full bg-[var(--navy-800)] h-2 rounded-full overflow-hidden">
        <div
          className="bg-[var(--gold-500)] h-full transition-all duration-500"
          style={{ width: `${(currentEvent / totalEvents) * 100}%` }}
        />
      </div>

      {/* Main Score Display */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sortedTeams.slice(0, 4).map((t, idx) => (
          <div
            key={t.team}
            className={`glass-card p-4 flex items-center justify-between ${
              idx === 0 ? "border-l-4 border-l-[var(--gold-500)]" : ""
            }`}
          >
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-xl font-bold text-white">{t.team}</h3>
                {idx === 0 && <span className="text-xl">👑</span>}
              </div>
              <p className="text-xs text-white/50">
                Projected Final:{" "}
                <span className="text-white">{Math.round(t.total)}</span>
              </p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-white">
                {Math.round(t.score)}
              </p>
              <p className="text-xs text-[var(--gold-400)]">Current</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
