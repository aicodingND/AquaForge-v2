/**
 * VCAC Team Mappings
 * Maps team codes to full names and metadata
 */

export interface TeamInfo {
  code: string;
  name: string;
  shortName: string;
  colors: {
    primary: string;
    secondary: string;
  };
  location?: string;
}

// VCAC Conference Teams
export const VCAC_TEAMS: Record<string, TeamInfo> = {
  SST: {
    code: "SST",
    name: "Seton School",
    shortName: "Seton",
    colors: { primary: "#1a365d", secondary: "#c5a83c" },
    location: "Manassas, VA",
  },
  ICS: {
    code: "ICS",
    name: "Immanuel Christian School",
    shortName: "Immanuel",
    colors: { primary: "#002868", secondary: "#bf0a30" },
    location: "Springfield, VA",
  },
  TCS: {
    code: "TCS",
    name: "Trinity Christian School",
    shortName: "Trinity",
    colors: { primary: "#006400", secondary: "#FFD700" },
    location: "Fairfax, VA",
  },
  FCS: {
    code: "FCS",
    name: "Faith Christian School",
    shortName: "Faith",
    colors: { primary: "#800020", secondary: "#FFFFFF" },
    location: "Roanoke, VA",
  },
  DJO: {
    code: "DJO",
    name: "St. John Paul the Great Catholic HS",
    shortName: "JP the Great",
    colors: { primary: "#003366", secondary: "#FFD700" },
    location: "Dumfries, VA",
  },
  OAK: {
    code: "OAK",
    name: "Oakcrest School",
    shortName: "Oakcrest",
    colors: { primary: "#006341", secondary: "#FFFFFF" },
    location: "Vienna, VA",
  },
  BI: {
    code: "BI",
    name: "Bishop Ireton High School",
    shortName: "Ireton",
    colors: { primary: "#8B0000", secondary: "#000000" },
    location: "Alexandria, VA",
  },
  // Add more teams as needed
};

/**
 * Get full team info from code
 */
export function getTeamInfo(code: string): TeamInfo {
  return (
    VCAC_TEAMS[code] || {
      code,
      name: code,
      shortName: code,
      colors: { primary: "#4a5568", secondary: "#a0aec0" },
    }
  );
}

/**
 * Get team name from code
 */
export function getTeamName(code: string): string {
  return VCAC_TEAMS[code]?.name || code;
}

/**
 * Get team short name from code
 */
export function getTeamShortName(code: string): string {
  return VCAC_TEAMS[code]?.shortName || code;
}

/**
 * Get all VCAC team codes
 */
export function getVCACTeamCodes(): string[] {
  return Object.keys(VCAC_TEAMS);
}

/**
 * Sort teams with Seton first
 */
export function sortTeamsSetonFirst(teams: string[]): string[] {
  return [...teams].sort((a, b) => {
    if (a === "SST") return -1;
    if (b === "SST") return 1;
    return a.localeCompare(b);
  });
}
