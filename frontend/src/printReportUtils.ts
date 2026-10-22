export type PrintMode = "summary" | "full";

const QUICK_MODE_WARNING =
  "Quick mode caps variant and drug enrichment at 25 genes; results are incomplete.";

export function normalizeRunWarning(warning: string) {
  return warning.toLowerCase().includes("quick mode") && warning.toLowerCase().includes("incomplete")
    ? QUICK_MODE_WARNING
    : warning;
}
