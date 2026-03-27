import { describe, it, expect } from "vitest";
import {
  mainNavigation,
  championshipNavigation,
  secondaryNavigation,
  allNavigation,
} from "@/config/navigation";

describe("Navigation Config", () => {
  it("has 7 main navigation items", () => {
    expect(mainNavigation).toHaveLength(7);
  });

  it("all nav items have required fields", () => {
    for (const item of [...mainNavigation, ...championshipNavigation, ...secondaryNavigation]) {
      expect(item.id).toBeTruthy();
      expect(item.label).toBeTruthy();
      expect(item.icon).toBeDefined();
      expect(item.href).toMatch(/^\//);
    }
  });

  it("all nav items have unique IDs", () => {
    const ids = allNavigation.map((n) => n.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("all nav items have unique hrefs", () => {
    const hrefs = allNavigation.map((n) => n.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });

  it("championship nav has live tracking", () => {
    expect(championshipNavigation.some((n) => n.id === "live")).toBe(true);
  });

  it("icons are Lucide components, not emoji strings", () => {
    for (const item of mainNavigation) {
      // Lucide icons are ForwardRef components (objects with $$typeof)
      expect(typeof item.icon).not.toBe("string");
      expect(item.icon).toBeDefined();
    }
  });
});
