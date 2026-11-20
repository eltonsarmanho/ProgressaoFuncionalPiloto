import { useId, useState, type ReactNode } from "react";
import type { ScoringResult } from "../api/types";
import { PANEL_LABELS, formatDecimal } from "../labels";
import { GroupBars } from "./GroupBars";
import { PanelHeadline } from "./PanelHeadline";
import { PotentialCards } from "./PotentialCards";
import { TeachingBlock } from "./TeachingBlock";

type Props = {
  result: ScoringResult;
  /** Names from the table version (a fallback for groups the short names do not cover). */
  groupNames?: Record<number, string>;
  /** Group I is outside the total (the old version); inferred from the rows when omitted. */
  group1OutsideTotal?: boolean;
  /** The table version has a weekly-load criterion in group I (the PIT hours); inferred from the rows when omitted. */
  group1Load?: boolean;
};

function Block({ title, children }: { title: string; children: ReactNode }) {
  const id = useId();
  return (
    <section className="panel-block" aria-labelledby={id}>
      <h3 id={id}>{title}</h3>
      {children}
    </section>
  );
}

/**
 * GRES-01..09: the scoring result of Etapa 4 as blocks (total, points by group, teaching, potential,
 * counters). It has no control, so it takes no focus; a live region says the new total only when it
 * changes after the first load (a validation, a rejection, another table).
 */
export function ScoringPanel({ result, groupNames, group1OutsideTotal, group1Load }: Props) {
  const outside = group1OutsideTotal ?? result.rows.some((r) => r.outside_total);
  const withTeaching = group1Load ?? result.rows.some((r) => r.pit_hours != null);
  const { counters } = result;

  const [seenTotal, setSeenTotal] = useState(result.total);
  const [announcement, setAnnouncement] = useState("");
  if (result.total !== seenTotal) {
    setSeenTotal(result.total);
    setAnnouncement(`Total geral atualizado: ${formatDecimal(result.total)} pontos`);
  }

  return (
    <div className="scoring-panel">
      <div role="status" className="visually-hidden">
        {announcement}
      </div>
      <Block title="Resultado">
        <PanelHeadline result={result} group1OutsideTotal={outside} />
      </Block>
      <Block title="Pontos por grupo">
        <GroupBars subtotals={result.subtotals} total={result.total} group1OutsideTotal={outside} groupNames={groupNames} />
      </Block>
      {withTeaching && (
        <Block title={PANEL_LABELS.teaching}>
          <TeachingBlock
            rows={result.rows}
            hoursByPeriod={result.group1_hours_by_period}
            totalHours={result.group1_total_hours}
            group1OutsideTotal={outside}
          />
        </Block>
      )}
      {Number(result.potential_total) > 0 && (
        <Block title="Potencial">
          <PotentialCards
            potentialTotal={result.potential_total}
            potentialDated={result.potential_dated}
            potentialUndated={result.potential_undated}
          />
        </Block>
      )}
      <Block title="Contadores">
        <ul className="counts" aria-label="Contadores">
          <li>Atividades: {counters.activities}</li>
          <li>Com comprovante: {counters.with_evidence}</li>
          <li>Pendentes: {counters.pending}</li>
          <li>Não pontuadas: {counters.not_scored}</li>
          <li>Com divergências: {counters.with_alerts}</li>
        </ul>
      </Block>
    </div>
  );
}
