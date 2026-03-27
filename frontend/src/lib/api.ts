/**
 * AquaForge API Client
 * Communicates with the FastAPI backend
 */

export const getApiBase = () => {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;

  // In browser, use the same host but backend port 8001
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    return `http://${host}:8001/api/v1`;
  }

  return "http://localhost:8001/api/v1";
};

const API_BASE = getApiBase();

// Types
export interface SwimmerEntry {
  swimmer: string;
  event: string;
  time: string | number;
  team?: string;
  grade?: string | number;
  gender?: string;
}

export interface OptimizeRequest {
  seton_data: SwimmerEntry[];
  opponent_data: SwimmerEntry[];
  optimizer_backend: string;
  enforce_fatigue: boolean;
  robust_mode: boolean;
  scoring_type:
    | "visaa_top7"
    | "standard_top5"
    | "vcac_championship"
    | "visaa_state";
  strategy?: string;
  championship_strategy?: string;
  use_championship_factors?: boolean | null;
  locked_assignments?: { swimmer: string; event: string }[];
  excluded_swimmers?: string[];
  time_overrides?: { swimmer: string; event: string; time: string }[];
}

export interface OptimizeResponse {
  success: boolean;
  seton_score: number;
  opponent_score: number;
  score_margin: number;
  results: OptimizationResult[];
  statistics: Record<string, unknown>;
  warnings: string[];
  optimization_time_ms: number;
  // Championship-specific fields
  championship_standings?: { rank: number; team: string; points: number }[];
  event_breakdowns?: Record<string, { event: string; entries: { swimmer: string; team: string; time: number; place: number; points: number }[]; team_points: Record<string, number> }>;
  swing_events?: { swimmer: string; event: string; point_gain: number; current_place: number; target_place: number }[];
  sensitivity?: EventSensitivity[];
  relay_assignments?: RelayAssignment[];
}

export interface OptimizationResult {
  event: string;
  event_number: number;
  seton_swimmers: string[];
  opponent_swimmers: string[];
  seton_times: string[];
  opponent_times: string[];
  projected_score: { seton: number; opponent: number };
}

export interface EventSensitivity {
  event: string;
  swimmer: string;
  placement: number;
  points_earned: number;
  gap_to_next_place: number | null;
  gap_to_better_place: number | null;
  risk_level: "safe" | "competitive" | "at_risk";
  next_best_swimmer: string | null;
  score_impact_if_swapped: number | null;
}

export interface RelayAssignment {
  relay_event: string;
  team: string; // "A" or "B"
  legs: string[];
  predicted_time: number;
}

export interface UploadResponse {
  success: boolean;
  team_name: string;
  swimmer_count: number;
  entry_count: number;
  events: string[];
  data: SwimmerEntry[];
  message?: string;
  teams?: string[]; // Team codes for championship meets
}

// Championship Strategy Types
export interface StrategyInfo {
  key: string;
  name: string;
  description: string;
  when_to_use: string;
  example_scenario: string;
  pros: string[];
  cons: string[];
  recommended_for: string[];
  is_implemented: boolean;
  status: "available" | "coming_soon";
}

export interface StrategiesResponse {
  strategies: StrategyInfo[];
  summary: { total: number; implemented: number; coming_soon: number };
  default_strategy: string;
  recommendation: string;
  implemented_strategies: string[];
  coming_soon_strategies: string[];
}

// API Client
class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    const apiKey = process.env.NEXT_PUBLIC_API_KEY;
    return apiKey ? { "X-API-Key": apiKey } : {};
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      headers: {
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health check
  async health(): Promise<{ status: string; timestamp: string }> {
    return this.request("/health");
  }

  // Upload team file
  async uploadFile(
    file: File,
    teamType: "seton" | "opponent",
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("team_type", teamType);

    return this.request("/data/upload", {
      method: "POST",
      body: formData,
    });
  }

  // Submit team data directly
  async submitTeamData(
    teamType: "seton" | "opponent",
    teamName: string,
    data: SwimmerEntry[],
  ): Promise<{ success: boolean; message: string }> {
    return this.request("/data/team", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team_type: teamType, team_name: teamName, data }),
    });
  }

  // Get available events
  async getEvents(): Promise<{ events: string[] }> {
    return this.request("/data/events");
  }

  // Run optimization
  async optimize(request: OptimizeRequest): Promise<OptimizeResponse> {
    console.log(
      "[API] optimize called with:",
      JSON.stringify(request, null, 2),
    );
    const response = await this.request<OptimizeResponse>("/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    console.log("[API] optimize response:", JSON.stringify(response, null, 2));
    return response;
  }

  // Preview optimization
  async previewOptimization(request: OptimizeRequest): Promise<{
    valid: boolean;
    seton: { swimmer_count: number; entry_count: number; events: string[] };
    opponent: { swimmer_count: number; entry_count: number; events: string[] };
    common_events: string[];
  }> {
    return this.request("/optimize/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  }

  // List optimization backends
  async listBackends(): Promise<{
    backends: Record<string, { available: boolean; description: string }>;
    default: string;
  }> {
    return this.request("/optimize/backends");
  }

  // Export results
  // Export results
  async exportResults(
    format: "csv" | "html" | "pdf" | "xlsx",
    results: OptimizationResult[],
    scores: { seton: number; opponent: number },
  ): Promise<Blob> {
    // Transform to backend expected format
    const payload = {
      format: format,
      optimization_results: {
        results: results, // Pass the array of results
        lineup: [], // Optional but good to have context
      },
      seton_score: scores.seton,
      opponent_score: scores.opponent,
    };

    const response = await fetch(`${this.baseUrl}/export`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...this.getAuthHeaders() },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("Export failed");
    }

    return response.blob();
  }

  // List available data sources
  async listDataSources(): Promise<{ sources: { id: string; name: string; description: string; type: string; teams?: number; entries?: number; available?: boolean }[] }> {
    return this.request("/data/sources");
  }

  // Load a specific data source
  async loadDataSource(sourceId: string, teamType: string): Promise<{
    success: boolean;
    team_name?: string;
    data?: SwimmerEntry[];
    swimmer_count?: number;
    entry_count?: number;
    events?: string[];
    teams?: string[];
    message?: string;
  }> {
    return this.request(`/data/load-source?source=${encodeURIComponent(sourceId)}&team_type=${encodeURIComponent(teamType)}`);
  }

  // Get optimization history for comparison
  async getHistory(
    opponent?: string,
    limit: number = 5,
  ): Promise<{
    runs: { opponent: string; our_score: number; opponent_score: number; date: string }[];
    count: number;
  }> {
    const params = new URLSearchParams();
    if (opponent) params.set("opponent", opponent);
    params.set("limit", String(limit));
    return this.request(`/optimize/history?${params.toString()}`);
  }

  // Get strategies...
  async getStrategies(): Promise<StrategiesResponse> {
    const v2Base = this.baseUrl.replace("/api/v1", "/api/v2");
    const response = await fetch(`${v2Base}/championship/strategies`, {
      headers: this.getAuthHeaders(),
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch strategies: HTTP ${response.status}`);
    }
    return response.json();
  }

  // ============================================================================
  // Live Tracker API
  // ============================================================================

  async initializeLiveMeet(
    meetName: string,
    entries: SwimmerEntry[],
    targetTeam: string = "SST",
    meetProfile: string = "vcac_championship",
  ): Promise<any> {
    return this.request("/live/initialize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        meet_name: meetName,
        meet_profile: meetProfile,
        target_team: targetTeam,
        entries: entries,
      }),
    });
  }

  async recordLiveResult(
    meetName: string,
    event: string,
    place: number,
    swimmer: string,
    team: string,
    time: number,
    isOfficial: boolean = true,
  ): Promise<any> {
    return this.request("/live/result", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        meet_name: meetName,
        event: event,
        place: place,
        swimmer: swimmer,
        team: team,
        time: time,
        is_official: isOfficial,
      }),
    });
  }

  async getLiveStandings(meetName: string): Promise<any> {
    return this.request(`/live/standings/${encodeURIComponent(meetName)}`);
  }

  async getClinchScenarios(meetName: string, targetTeam: string): Promise<any> {
    return this.request(
      `/live/clinch/${encodeURIComponent(meetName)}/${encodeURIComponent(
        targetTeam,
      )}`,
    );
  }

  async getLiveStatus(meetName: string): Promise<any> {
    return this.request(`/live/status/${encodeURIComponent(meetName)}`);
  }

  async getSwingEvents(
    meetName: string,
    targetTeam: string = "SST",
  ): Promise<any> {
    return this.request(
      `/live/swing/${encodeURIComponent(meetName)}?target_team=${encodeURIComponent(targetTeam)}`,
    );
  }

  async getCoachSummary(
    meetName: string,
    targetTeam: string = "SST",
  ): Promise<any> {
    return this.request(
      `/live/summary/${encodeURIComponent(meetName)}?target_team=${encodeURIComponent(targetTeam)}`,
    );
  }

  async getRemainingPoints(meetName: string): Promise<any> {
    return this.request(
      `/live/remaining/${encodeURIComponent(meetName)}`,
    );
  }
}

// Export singleton instance
export const api = new ApiClient();
export default api;
