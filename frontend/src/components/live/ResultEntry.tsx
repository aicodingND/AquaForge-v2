"use client";

import { useState } from "react";
import api from "@/lib/api";

export default function ResultEntry({
  meetName,
  teams,
  onResultRecorded,
}: {
  meetName: string;
  teams: string[];
  onResultRecorded: () => void;
}) {
  const [event, setEvent] = useState("");
  const [place, setPlace] = useState<number | "">("");
  const [swimmer, setSwimmer] = useState("");
  const [team, setTeam] = useState("");
  const [time, setTime] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!event || !place || !swimmer || !team) return;

    setIsSubmitting(true);
    try {
      await api.recordLiveResult(
        meetName,
        event,
        Number(place),
        swimmer,
        team,
        Number(time) || 0, // Time is optional or needs parsing, relying on backend specific logic but API expects number
      );
      // Reset some fields
      setPlace("");
      setSwimmer("");
      setTime("");
      onResultRecorded();
    } catch (error) {
      console.error("Failed to record result:", error);
      alert("Failed to record result");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="glass-card p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Record Result</h3>
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Event */}
        <div>
          <label className="block text-xs text-white/50 mb-1">Event</label>
          <input
            type="text"
            value={event}
            onChange={(e) => setEvent(e.target.value)}
            placeholder="e.g. Boys 50 Free"
            className="input-field w-full"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          {/* Place */}
          <div>
            <label className="block text-xs text-white/50 mb-1">Place</label>
            <input
              type="number"
              min="1"
              max="20"
              value={place}
              onChange={(e) => setPlace(Number(e.target.value))}
              placeholder="1"
              className="input-field w-full"
              required
            />
          </div>
          {/* Time */}
          <div>
            <label className="block text-xs text-white/50 mb-1">
              Time/Score
            </label>
            <input
              type="number"
              step="0.01"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              placeholder="22.50"
              className="input-field w-full"
            />
          </div>
        </div>

        {/* Swimmer */}
        <div>
          <label className="block text-xs text-white/50 mb-1">Swimmer</label>
          <input
            type="text"
            value={swimmer}
            onChange={(e) => setSwimmer(e.target.value)}
            placeholder="Name"
            className="input-field w-full"
            required
          />
        </div>

        {/* Team */}
        <div>
          <label className="block text-xs text-white/50 mb-1">Team</label>
          <select
            value={team}
            onChange={(e) => setTeam(e.target.value)}
            className="input-field w-full bg-[var(--navy-800)]"
            required
          >
            <option value="">Select Team</option>
            {teams.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn btn-gold w-full mt-4"
        >
          {isSubmitting ? "Recording..." : "Submit Result"}
        </button>
      </form>
    </div>
  );
}
