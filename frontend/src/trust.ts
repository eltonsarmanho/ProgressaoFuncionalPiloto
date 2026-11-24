import type { Activity, DocumentSummary, ScoringRow } from "./api/types";
import { LOW_CONFIDENCE } from "./labels";

/**
 * UIM-12: an AI suggestion the user may validate in bulk. The API keeps no confidence per
 * activity, so the confidence is the one of the documents it cites (all at 0.70 or more, read
 * without failure); a suggestion with candidate items, without an item, without a document or
 * with a scoring alert or a not-scored row still needs a human look and stays out.
 */
export function isConfidentSuggestion(
  activity: Activity,
  row: ScoringRow | undefined,
  documents: DocumentSummary[],
): boolean {
  if (activity.source !== "SUGERIDA_IA" || activity.status !== "AGUARDANDO_REVISAO") return false;
  if (activity.group_number == null || activity.candidates.length > 0) return false;
  if (!row || row.status !== "POTENCIAL" || row.alerts.length > 0) return false;
  const cited = activity.evidences ?? [];
  if (cited.length === 0) return false;
  return cited.every((evidence) => {
    const doc = documents.find((d) => d.id === evidence.document_id);
    return doc != null && doc.status === "PROCESSADO" && doc.confidence != null && Number(doc.confidence) >= LOW_CONFIDENCE;
  });
}
