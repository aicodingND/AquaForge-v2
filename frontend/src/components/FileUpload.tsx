"use client";

import { useCallback, useState } from "react";
import { api } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import ErrorDisplay, { getErrorContext } from "./ErrorDisplay";

interface FileUploadProps {
  teamType: "seton" | "opponent";
  label: string;
}

export default function FileUpload({ teamType, label }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { setSetonTeam, setOpponentTeam, addLog } = useAppStore();

  const handleFile = useCallback(
    async (file: File) => {
      console.log(
        "[FileUpload] Starting handleFile for:",
        file.name,
        "teamType:",
        teamType,
      );

      if (
        !file.name.endsWith(".xlsx") &&
        !file.name.endsWith(".csv") &&
        !file.name.endsWith(".json")
      ) {
        setError("Please upload an Excel (.xlsx), CSV, or JSON file");
        return;
      }

      setIsUploading(true);
      setError(null);

      try {
        addLog(`Uploading ${file.name}...`);
        console.log("[FileUpload] Calling api.uploadFile...");
        const response = await api.uploadFile(file, teamType);
        console.log(
          "[FileUpload] Response received:",
          JSON.stringify(response, null, 2),
        );

        if (response.success) {
          console.log("[FileUpload] SUCCESS - Creating teamData");
          const teamData = {
            name: response.team_name,
            filename: file.name,
            data: response.data,
            swimmerCount: response.swimmer_count,
            entryCount: response.entry_count,
            events: response.events,
            teams: response.teams, // Include teams for championship files
          };
          console.log(
            "[FileUpload] teamData:",
            JSON.stringify(teamData, null, 2),
          );

          if (teamType === "seton") {
            console.log("[FileUpload] Setting SETON team");
            setSetonTeam(teamData);
          } else {
            console.log("[FileUpload] Setting OPPONENT team");
            setOpponentTeam(teamData);
          }

          // Enhanced log message for championship files
          const teamsInfo = response.teams
            ? ` (${response.teams.length} teams: ${response.teams.join(", ")})`
            : "";
          addLog(
            `✓ Loaded ${response.swimmer_count} swimmers from ${file.name}${teamsInfo}`,
          );
        } else {
          console.log("[FileUpload] FAILED - response.success is false");
          setError(response.message || "Upload failed");
          addLog(`✗ Failed to load ${file.name}`);
        }
      } catch (err) {
        console.error("[FileUpload] ERROR:", err);
        const message = err instanceof Error ? err.message : "Upload failed";
        setError(message);
        addLog(`✗ Error: ${message}`);
      } finally {
        setIsUploading(false);
      }
    },
    [teamType, setSetonTeam, setOpponentTeam, addLog],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-[#D4AF37] mb-2">
        {label}
      </label>

      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`
          relative border-2 border-dashed rounded-xl p-8
          flex flex-col items-center justify-center gap-3
          transition-all duration-200 cursor-pointer
          ${
            isDragging
              ? "border-[#D4AF37] bg-[#C99700]/10"
              : "border-[#1a3a5c] hover:border-[#C99700]/50 bg-[#0C2340]/50"
          }
          ${isUploading ? "pointer-events-none opacity-60" : ""}
        `}
      >
        <input
          type="file"
          accept=".xlsx,.csv,.json"
          onChange={handleInputChange}
          aria-label="Upload team roster file"
          title="Upload Excel, CSV, or JSON file"
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
        />

        {isUploading ? (
          <>
            <div className="w-8 h-8 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin" />
            <p className="text-white/60">Uploading...</p>
          </>
        ) : (
          <>
            <svg
              className="w-10 h-10 text-[#C99700]/60"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-white/60 text-center">
              <span className="text-[#D4AF37] font-medium">
                Click to upload
              </span>{" "}
              or drag and drop
              <br />
              <span className="text-sm text-white/40">
                Excel, CSV, or JSON files
              </span>
            </p>
          </>
        )}
      </div>

      {error && (
        <ErrorDisplay
          error={error}
          onDismiss={() => setError(null)}
        />
      )}
    </div>
  );
}
