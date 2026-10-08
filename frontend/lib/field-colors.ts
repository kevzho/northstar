/**
 * One colour per field, shared by every surface that draws a field.
 *
 * Lived only inside app/map/page.tsx, so the profile's field map and the
 * orbital map could have disagreed about what biology looks like. A colour
 * that means something must mean it everywhere or it means nothing.
 *
 * Tuned to read against both grounds — the bistre night and the manila paper —
 * which is why none of them is fully saturated.
 */
import type { OpportunityField } from "@/lib/types";

export const FIELD_COLORS: Record<OpportunityField, string> = {
  cs: "#6c9ef8",
  biology: "#56d394",
  math: "#c08bf5",
  physics: "#f09a62",
  engineering: "#55c7de",
  interdisciplinary: "#e7c868",
  design: "#f08bc9",
  business: "#a8d96c",
  humanities: "#dab07f",
  health: "#f07d7d",
};

export function fieldColor(field: string): string {
  return FIELD_COLORS[field as OpportunityField] ?? "#9e9e9e";
}
