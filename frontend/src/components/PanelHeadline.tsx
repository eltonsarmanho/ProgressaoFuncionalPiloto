import type { ScoringResult } from "../api/types";
import { PANEL_LABELS, MINIMUM_LABELS, formatDecimal } from "../labels";

type Props = {
  result: Pick<ScoringResult, "total" | "minimum" | "group1_percent">;
  /** Group I is outside the total (the old table version). */
  group1OutsideTotal: boolean;
};

/**
 * GRES-01, GRES-02: the grand total with the groups it sums, the minimum in short text and the
 * Group I share (GI-08). A read-only block: the values come from the API as they are.
 */
export function PanelHeadline({ result, group1OutsideTotal }: Props) {
  const { minimum } = result;
  const defined = minimum.status !== "NAO_DEFINIDO";
  const minimumText = defined
    ? `${MINIMUM_LABELS[minimum.status]}${minimum.minimum != null ? ` (${formatDecimal(minimum.minimum)})` : ""}`
    : PANEL_LABELS.minimumUndefined;
  return (
    <dl className="panel-headline">
      <div>
        <dt>Total geral</dt>
        <dd>
          <span className="panel-value">{formatDecimal(result.total)}</span>{" "}
          <span className="panel-scope">
            {group1OutsideTotal ? PANEL_LABELS.totalWithoutGroup1 : PANEL_LABELS.totalWithGroup1}
          </span>
        </dd>
      </div>
      <div>
        <dt>Mínimo de referência</dt>
        <dd className={defined ? "panel-minimum" : undefined}>{minimumText}</dd>
      </div>
      <div>
        <dt>Percentual do Grupo I</dt>
        <dd>{result.group1_percent == null ? "—" : `${formatDecimal(result.group1_percent)}%`}</dd>
      </div>
    </dl>
  );
}
