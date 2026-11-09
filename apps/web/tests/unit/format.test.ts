import { describe, expect, it } from "vitest";
import { formatBytes, formatDuration, formatNumber, formatPercent, formatRelative, orUnknown, parseIso } from "@/lib/format";

describe("formattering (nl-NL)", () => {
  it("bytes in binaire eenheden met komma", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1536)).toBe("1,5 KiB");
    expect(formatBytes(4_000_000_000_000)).toBe("3,6 TiB");
    expect(formatBytes(null)).toBe("onbekend");
    expect(formatBytes(-1)).toBe("onbekend");
  });

  it("relatieve tijd", () => {
    const now = new Date("2026-11-09T12:00:00Z");
    expect(formatRelative("2026-11-09T11:59:50Z", now)).toBe("zojuist");
    expect(formatRelative("2026-11-09T11:57:00Z", now)).toBe("3 min geleden");
    expect(formatRelative("2026-11-09T10:00:00Z", now)).toBe("2 uur geleden");
    expect(formatRelative("2026-11-08T12:00:00Z", now)).toBe("1 dag geleden");
    expect(formatRelative("2026-11-06T12:00:00Z", now)).toBe("3 dagen geleden");
    expect(formatRelative("2026-11-09T13:00:00Z", now)).toBe("over 1 uur");
    expect(formatRelative(null, now)).toBe("onbekend");
    expect(formatRelative("geen-datum", now)).toBe("onbekend");
  });

  it("percentage, getal, duur en onbekend", () => {
    expect(formatPercent(25)).toBe("25%");
    expect(formatPercent(undefined)).toBe("onbekend");
    expect(formatNumber(2.25)).toBe("2,3");
    expect(formatDuration(3600)).toBe("1 u 0 min");
    expect(formatDuration(90061)).toBe("1 d 1 u");
    expect(formatDuration(null)).toBe("onbekend");
    expect(orUnknown("")).toBe("onbekend");
    expect(orUnknown(0)).toBe("0");
    expect(parseIso("x")).toBeNull();
  });
});
