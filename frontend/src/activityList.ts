import type { Activity, Validity } from "./api/types";
import type { ActivityFilterState, SituationCounts, SituationFilter } from "./components/ActivityFilters";

/** SEC-02, SEC-06: how many activities a section shows at a time; "Mostrar mais" adds this many. */
export const PAGE_SIZE = 25;

/** An activity the list sent without `validity` (a stale answer) is read as a valid one. */
export function validityOf(activity: Activity): Validity {
  return (
    activity.validity ?? {
      state: "VALIDA",
      reason: null,
      needs_category: activity.group_number == null || activity.item_number == null,
      params: {},
    }
  );
}

export const isValid = (activity: Activity): boolean => validityOf(activity).state === "VALIDA";

/** The chip an activity of the valid section belongs to; "needs a category" comes first. */
export function situationOf(activity: Activity): Exclude<SituationFilter, "TODAS"> {
  if (validityOf(activity).needs_category) return "PRECISA_CATEGORIA";
  return activity.status === "VALIDADA" ? "VALIDADAS" : "AGUARDANDO";
}

/** SEC-03: the chips count the whole list, whatever the search and the group filter say. */
export function countSituations(activities: Activity[]): SituationCounts {
  const counts: SituationCounts = { TODAS: activities.length, AGUARDANDO: 0, VALIDADAS: 0, PRECISA_CATEGORIA: 0 };
  for (const activity of activities) counts[situationOf(activity)] += 1;
  return counts;
}

/** Case and accent do not matter in the search ("orientacao" finds "Orientação"). */
const fold = (text: string) => text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();

export function filterActivities(activities: Activity[], filters: ActivityFilterState): Activity[] {
  const query = fold(filters.query.trim());
  return activities.filter(
    (a) =>
      (query === "" || fold(a.title).includes(query)) &&
      (filters.situation === "TODAS" || situationOf(a) === filters.situation) &&
      (filters.group === null || a.group_number === filters.group),
  );
}

/** The group numbers the list has, for the group filter. */
export function groupsOf(activities: Activity[]): number[] {
  return [...new Set(activities.map((a) => a.group_number).filter((g): g is number => g != null))].sort((a, b) => a - b);
}
