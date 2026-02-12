/**
 * AquaForge Frontend Configuration
 *
 * Centralized constants to avoid hardcoding values throughout the app.
 */

// API Configuration
export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
export const API_V2_BASE =
  process.env.NEXT_PUBLIC_API_URL_V2 || "http://localhost:8000/api/v2";

// App Metadata
export const APP_NAME = "AquaForge";
export const APP_VERSION = "1.0.0";

// Feature Flags
export const FEATURES = {
  championship_mode: true,
  robust_mode: true,
  fatigue_modeling: true,
  sample_data_button: process.env.NODE_ENV === "development",
} as const;

// UI Constants
export const MAX_COACH_LOCKS = 3;
export const DEFAULT_SCORING_TYPE = "visaa_top7";
export const DEFAULT_OPTIMIZER_ENGINE = "gurobi";
