import { ApiError, fieldErrors } from "./api/client";
import { errorCode, generationErrorMessage } from "./generationErrors";
import { GENERATION_CODE_LABELS } from "./labels";

/** PORT-12, PAR-13: what a save of the Etapas 6 and 7 says when someone else changed the data first. */
export const STALE_MESSAGE = "Os dados foram alterados por outra pessoa; recarregue";

export type BoardFailure = {
  /** A 422 that names fields: the message of each one, shown next to it. */
  fields: Record<string, string>;
  /** Any other failure, shown as an alert; null when `fields` has the answer. */
  message: string | null;
  /** A 409 for a version that is not the stored one: the page should read the data again. */
  stale: boolean;
};

/** The answer of the screens of the board to a failed call: by field (422), stale version (409) or one message. */
export function boardFailure(error: unknown): BoardFailure {
  const fields = fieldErrors(error);
  if (Object.keys(fields).length > 0) return { fields, message: null, stale: false };
  if (error instanceof ApiError && error.status === 409) {
    const code = errorCode(error);
    if (code === "PORTARIA_EXISTENTE" || code === "PROCESSO_SOMENTE_LEITURA") {
      return { fields: {}, message: GENERATION_CODE_LABELS[code], stale: false };
    }
    return { fields: {}, message: STALE_MESSAGE, stale: true };
  }
  return { fields: {}, message: generationErrorMessage(error), stale: false };
}
