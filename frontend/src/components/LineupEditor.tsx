'use client';

import { useState, useCallback, useMemo, useRef } from 'react';
import { useScores } from '@/lib/store';
import { api, getApiBase, OptimizationResult } from '@/lib/api';

interface SwimmerAssignment {
  swimmer: string;
  event: string;
  time: string;
  team: string;
  points: number;
}

interface ModifiedLineup {
  results: OptimizationResult[];
  setonScore: number;
  opponentScore: number;
}

export default function LineupEditor() {
  const { optimizationResults, setonScore, opponentScore } = useScores();

  const [modified, setModified] = useState<ModifiedLineup | null>(null);
  const [movingSwimmer, setMovingSwimmer] = useState<{
    swimmer: string;
    fromEvent: string;
    fromIndex: number;
  } | null>(null);
  const [isRescoring, setIsRescoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // PERFORMANCE FIX: Add debounce timer for rescore API calls
  const rescoreTimerRef = useRef<NodeJS.Timeout | null>(null);

  const currentResults = modified?.results ?? optimizationResults;
  const currentSetonScore = modified?.setonScore ?? setonScore;
  const currentOpponentScore = modified?.opponentScore ?? opponentScore;
  const scoreDiff = currentSetonScore - currentOpponentScore - (setonScore - opponentScore);
  const isModified = modified !== null;

  const handleMoveSwimmer = useCallback(
    (swimmer: string, fromEvent: string, fromIndex: number) => {
      setMovingSwimmer({ swimmer, fromEvent, fromIndex });
      setError(null);
    },
    []
  );

  const handleDropSwimmer = useCallback(
    async (toEvent: string) => {
      if (!movingSwimmer || !currentResults) return;
      if (movingSwimmer.fromEvent === toEvent) {
        setMovingSwimmer(null);
        return;
      }

      // Create a deep copy of results and perform the swap
      const newResults = currentResults.map((r) => ({
        ...r,
        seton_swimmers: [...r.seton_swimmers],
        seton_times: [...r.seton_times],
        projected_score: { ...r.projected_score },
      }));

      const fromResult = newResults.find(
        (r) => r.event === movingSwimmer.fromEvent
      );
      const toResult = newResults.find((r) => r.event === toEvent);

      if (!fromResult || !toResult) {
        setMovingSwimmer(null);
        return;
      }

      // Remove swimmer from source event
      const swimmerIdx = fromResult.seton_swimmers.indexOf(
        movingSwimmer.swimmer
      );
      if (swimmerIdx === -1) {
        setMovingSwimmer(null);
        return;
      }

      const [removedSwimmer] = fromResult.seton_swimmers.splice(swimmerIdx, 1);
      const [removedTime] = fromResult.seton_times.splice(swimmerIdx, 1);

      // Add swimmer to destination event
      toResult.seton_swimmers.push(removedSwimmer);
      toResult.seton_times.push(removedTime);

      setMovingSwimmer(null);
      setIsRescoring(true);
      setError(null);

      // PERFORMANCE FIX: Debounce rescore API calls by 500ms to prevent rapid fire requests
      if (rescoreTimerRef.current) {
        clearTimeout(rescoreTimerRef.current);
      }

      rescoreTimerRef.current = setTimeout(async () => {
        // Attempt to rescore via API
        try {
          const response = await fetch(
            `${getApiBase()}/rescore`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ results: newResults }),
            }
          );

          if (response.ok) {
            const data = await response.json();
            setModified({
              results: data.results ?? newResults,
              setonScore: data.seton_score ?? currentSetonScore,
              opponentScore: data.opponent_score ?? currentOpponentScore,
            });
          } else {
            // Rescore endpoint not available -- use local results as-is
            const localSetonScore = newResults.reduce(
              (sum, r) => sum + (r.projected_score?.seton ?? 0),
              0
            );
            const localOpponentScore = newResults.reduce(
              (sum, r) => sum + (r.projected_score?.opponent ?? 0),
              0
            );
            setModified({
              results: newResults,
              setonScore: localSetonScore,
              opponentScore: localOpponentScore,
            });
          }
        } catch {
          // Fallback: compute scores locally
          const localSetonScore = newResults.reduce(
            (sum, r) => sum + (r.projected_score?.seton ?? 0),
            0
          );
          const localOpponentScore = newResults.reduce(
            (sum, r) => sum + (r.projected_score?.opponent ?? 0),
            0
          );
          setModified({
            results: newResults,
            setonScore: localSetonScore,
            opponentScore: localOpponentScore,
          });
        } finally {
          setIsRescoring(false);
        }
      }, 500); // 500ms debounce delay
    },
    [movingSwimmer, currentResults, currentSetonScore, currentOpponentScore]
  );

  const handleCancelMove = useCallback(() => {
    setMovingSwimmer(null);
  }, []);

  const handleReset = useCallback(() => {
    setModified(null);
    setMovingSwimmer(null);
    setError(null);
  }, []);

  // Empty state
  if (!optimizationResults || optimizationResults.length === 0) {
    return (
      <div className="glass-card rounded-xl p-8 text-center">
        <span className="text-4xl mb-3 block">&#9998;</span>
        <p className="text-white/60">No lineup to edit</p>
        <p className="text-sm text-white/40">
          Run an optimization to edit the lineup
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with score comparison */}
      <div className="glass-card rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <svg
              className="w-5 h-5 text-[#D4AF37]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
              />
            </svg>
            Lineup Editor
          </h3>
          <div className="flex items-center gap-3">
            {isModified && (
              <span className="text-xs px-2 py-1 rounded-full bg-[#D4AF37]/20 text-[#D4AF37] font-medium">
                Modified
              </span>
            )}
            <button
              onClick={handleReset}
              disabled={!isModified}
              className={`
                px-3 py-1.5 rounded-lg text-sm font-medium transition-all
                ${isModified
                  ? 'bg-[#1a3a5c] text-white/80 hover:bg-[#1a3a5c]/80'
                  : 'bg-[#1a3a5c]/40 text-white/30 cursor-not-allowed'
                }
              `}
            >
              Reset
            </button>
          </div>
        </div>

        {/* Score comparison bar */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white/50">Original:</span>
            <span className="text-[#D4AF37] font-semibold">{setonScore}</span>
            <span className="text-white/30">-</span>
            <span className="text-[#7C8B9A] font-semibold">
              {opponentScore}
            </span>
          </div>
          {isModified && (
            <>
              <svg
                className="w-4 h-4 text-white/30"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-white/50">Modified:</span>
                <span className="text-[#D4AF37] font-semibold">
                  {currentSetonScore}
                </span>
                <span className="text-white/30">-</span>
                <span className="text-[#7C8B9A] font-semibold">
                  {currentOpponentScore}
                </span>
              </div>
              <span
                className={`
                  text-sm font-semibold px-2 py-0.5 rounded
                  ${scoreDiff > 0
                    ? 'text-green-400 bg-green-500/10'
                    : scoreDiff < 0
                      ? 'text-red-400 bg-red-500/10'
                      : 'text-white/50 bg-white/5'
                  }
                `}
              >
                {scoreDiff > 0 ? '+' : ''}
                {scoreDiff} pts
              </span>
            </>
          )}
        </div>

        {isRescoring && (
          <div className="mt-3 flex items-center gap-2 text-sm text-[#D4AF37]">
            <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            Re-scoring lineup...
          </div>
        )}

        {error && (
          <p className="mt-3 text-sm text-red-400">{error}</p>
        )}
      </div>

      {/* Move target banner */}
      {movingSwimmer && (
        <div className="rounded-xl bg-[#D4AF37]/10 border border-[#D4AF37]/30 p-4 flex items-center justify-between animate-fade-in">
          <p className="text-sm text-[#D4AF37]">
            Moving{' '}
            <span className="font-semibold">{movingSwimmer.swimmer}</span> from{' '}
            <span className="font-semibold">{movingSwimmer.fromEvent}</span>{' '}
            &mdash; select a destination event below
          </p>
          <button
            onClick={handleCancelMove}
            className="text-white/40 hover:text-red-400 transition-colors text-sm px-2 py-1"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Event sections */}
      <div className="space-y-3">
        {currentResults?.map((result, idx) => {
          const isTarget =
            movingSwimmer !== null &&
            movingSwimmer.fromEvent !== result.event;

          return (
            <div
              key={`${result.event}-${idx}`}
              className={`
                glass-card rounded-xl p-5 transition-all
                ${isTarget
                  ? 'ring-2 ring-[#D4AF37]/40 cursor-pointer hover:ring-[#D4AF37]/70'
                  : ''
                }
              `}
              onClick={isTarget ? () => handleDropSwimmer(result.event) : undefined}
            >
              {/* Event header */}
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <span className="text-white/40 text-xs">
                    #{result.event_number}
                  </span>
                  {result.event}
                </h4>
                <div className="text-xs text-white/40">
                  <span className="text-[#D4AF37]">
                    {result.projected_score?.seton ?? 0}
                  </span>
                  <span className="mx-1">-</span>
                  <span className="text-[#7C8B9A]">
                    {result.projected_score?.opponent ?? 0}
                  </span>
                </div>
              </div>

              {/* Seton swimmers */}
              <div className="flex flex-wrap gap-2">
                {result.seton_swimmers.map((swimmer, sIdx) => {
                  const isBeingMoved =
                    movingSwimmer?.swimmer === swimmer &&
                    movingSwimmer?.fromEvent === result.event;

                  return (
                    <div
                      key={`${swimmer}-${sIdx}`}
                      className={`
                        bg-white/[0.07] rounded-lg border border-white/10 p-3
                        flex items-center gap-3 min-w-[160px] transition-all
                        ${isBeingMoved ? 'opacity-40 scale-95' : ''}
                      `}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-white font-medium truncate">
                          {swimmer}
                        </p>
                        <p className="text-xs text-white/40">
                          {result.seton_times?.[sIdx] ?? '—'}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (movingSwimmer?.swimmer === swimmer) {
                            handleCancelMove();
                          } else {
                            handleMoveSwimmer(swimmer, result.event, sIdx);
                          }
                        }}
                        className={`
                          text-xs px-2 py-1 rounded transition-colors flex-shrink-0
                          ${movingSwimmer?.swimmer === swimmer
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-[#1a3a5c] text-white/60 hover:text-[#D4AF37] hover:bg-[#1a3a5c]/80'
                          }
                        `}
                        title={
                          movingSwimmer?.swimmer === swimmer
                            ? 'Cancel move'
                            : `Move ${swimmer} to another event`
                        }
                      >
                        {movingSwimmer?.swimmer === swimmer ? (
                          'Cancel'
                        ) : (
                          <svg
                            className="w-3.5 h-3.5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                            />
                          </svg>
                        )}
                      </button>
                    </div>
                  );
                })}

                {result.seton_swimmers.length === 0 && (
                  <p className="text-xs text-white/30 italic py-2">
                    No Seton swimmers assigned
                  </p>
                )}
              </div>

              {/* Drop target indicator */}
              {isTarget && (
                <div className="mt-3 border border-dashed border-[#D4AF37]/30 rounded-lg p-2 text-center">
                  <p className="text-xs text-[#D4AF37]/60">
                    Click to drop {movingSwimmer?.swimmer} here
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
