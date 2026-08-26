/** Formatting helpers shared across screens. */

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const rest = Math.round(seconds % 60);
  if (minutes < 60) return rest ? `${minutes}m ${rest}s` : `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

/** mm:ss, for a running clock. */
export function formatClock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
  return `${minutes}:${String(safe % 60).padStart(2, "0")}`;
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  return new Date(value).toLocaleDateString("en-PK", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return `${Math.round(value * 10) / 10}%`;
}

/** Service brand tokens, matching the accent stored on the service row. */
export const SERVICE_THEME: Record<string, { bg: string; text: string; ring: string; soft: string }> = {
  army: { bg: "bg-army-500", text: "text-army-600", ring: "ring-army-500", soft: "bg-army-50" },
  air_force: { bg: "bg-paf-500", text: "text-paf-600", ring: "ring-paf-500", soft: "bg-paf-50" },
  navy: { bg: "bg-navy-500", text: "text-navy-600", ring: "ring-navy-500", soft: "bg-navy-50" },
  common: { bg: "bg-ink-600", text: "text-ink-700", ring: "ring-ink-500", soft: "bg-ink-100" },
};

export function serviceTheme(code: string | null | undefined) {
  return SERVICE_THEME[code ?? "common"] ?? SERVICE_THEME.common;
}

export function serviceName(code: string | null | undefined): string {
  return (
    { army: "Pakistan Army", air_force: "Pakistan Air Force", navy: "Pakistan Navy", common: "Common" }[
      code ?? "common"
    ] ?? "Common"
  );
}
