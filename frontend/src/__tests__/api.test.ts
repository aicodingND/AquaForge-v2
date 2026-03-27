import { describe, it, expect, vi, beforeEach } from "vitest";
import { getApiBase } from "@/lib/api";

describe("API Client", () => {
  describe("getApiBase", () => {
    beforeEach(() => {
      vi.unstubAllEnvs();
    });

    it("uses NEXT_PUBLIC_API_URL when set", () => {
      vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.aquaforge.app/api/v1");
      expect(getApiBase()).toBe("https://api.aquaforge.app/api/v1");
    });

    it("falls back to localhost:8001 in SSR context", () => {
      // In test environment (no window manipulation needed), getApiBase
      // should return the localhost fallback when no env var is set
      vi.stubEnv("NEXT_PUBLIC_API_URL", "");
      const base = getApiBase();
      expect(base).toContain("8001");
      expect(base).toContain("/api/v1");
    });
  });

  describe("navigation config uses centralized API base", () => {
    it("config.ts API_BASE includes /api/v1", async () => {
      const { API_BASE } = await import("@/lib/config");
      expect(API_BASE).toContain("/api/v1");
    });

    it("config.ts API_V2_BASE includes /api/v2", async () => {
      const { API_V2_BASE } = await import("@/lib/config");
      expect(API_V2_BASE).toContain("/api/v2");
    });
  });
});
