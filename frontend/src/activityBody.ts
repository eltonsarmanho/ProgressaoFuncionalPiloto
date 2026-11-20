import type { Activity } from "./api/types";

const TEXT = ["title", "description", "event_date", "period_start", "period_end", "evidence_note", "academic_period", "level"] as const;
const NUMBER = ["group_number", "item_number", "quantidade", "horas", "course_hours", "informed_points", "points_override"] as const;

/** What a PUT must resend so that an edit of one field leaves the others as they were. */
export function activityBody(activity: Activity): Record<string, unknown> {
  const body: Record<string, unknown> = { title: activity.title, description: activity.description ?? "" };
  for (const field of TEXT) {
    const value = activity[field];
    if (value != null && value !== "") body[field] = value;
  }
  for (const field of NUMBER) {
    const value = activity[field];
    if (value != null) body[field] = Number(value);
  }
  return { ...body, ...preservedFields(activity) };
}

/** Fields without an input in the activity form that an edit must not lose. */
export function preservedFields(activity: Activity): Record<string, unknown> {
  const kept: Record<string, unknown> = {};
  if (activity.unit_points_override != null) kept.unit_points_override = Number(activity.unit_points_override);
  if (activity.candidates.length > 0) kept.candidates = activity.candidates;
  return kept;
}
