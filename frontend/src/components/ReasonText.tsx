import type { Validity } from "../api/types";
import { invalidReasonText } from "../labels";

/** SEC-07: the reason an activity is not valid, written from `validity.params`; nothing when it is valid. */
export function ReasonText({ validity }: { validity: Validity }) {
  if (validity.state === "VALIDA" || validity.reason == null) return null;
  return <span className="reason-text">{invalidReasonText(validity)}</span>;
}
