import { ApiError, errorMessage } from "./api/client";
import type { GenerationCode } from "./api/generated";
import { GENERATION_CODE_LABELS } from "./labels";

/** The `code` of a refusal: at the top of a 409 body, or in the first coded item of a 422 or 410 `detail`. */
export function errorCode(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null;
  const body = error.body as { code?: unknown } | undefined;
  if (typeof body?.code === "string") return body.code;
  if (Array.isArray(error.detail)) {
    for (const item of error.detail as { code?: unknown }[]) {
      if (item && typeof item.code === "string") return item.code;
    }
  }
  return null;
}

/** A 409 of a save: someone else changed the draft or the arrangement since it was read. */
export function isConflict(error: unknown): boolean {
  return error instanceof ApiError && error.status === 409;
}

/** A 409 or 410 with a known code shows its label; a coded 422 keeps the message the server wrote (it names the activity or document). */
export function generationErrorMessage(error: unknown): string {
  const code = errorCode(error);
  if (code && code in GENERATION_CODE_LABELS && error instanceof ApiError && [409, 410].includes(error.status)) {
    return GENERATION_CODE_LABELS[code as GenerationCode];
  }
  return errorMessage(error);
}
