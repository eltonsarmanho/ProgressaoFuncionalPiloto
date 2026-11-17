import type { ScoringResult } from "../api/types";
import { GROUP_NAMES, MINIMUM_LABELS, formatDecimal, roman } from "../labels";

/** TELA-03: subtotals, totals, Group I percentage, minimum comparison and counters. */
export function ScoringSummary({
  result,
  groupNames = GROUP_NAMES,
}: {
  result: ScoringResult;
  groupNames?: Record<number, string>;
}) {
  const { minimum, counters } = result;
  const minimumText =
    MINIMUM_LABELS[minimum.status] + (minimum.minimum != null ? ` (${formatDecimal(minimum.minimum)})` : "");
  return (
    <>
      <dl className="totals">
        {[...result.subtotals]
          .sort((a, b) => a.group_number - b.group_number)
          .map((s) => (
            <div key={s.group_number}>
              <dt>{`Grupo ${roman(s.group_number)} · ${groupNames[s.group_number] ?? GROUP_NAMES[s.group_number] ?? ""}`}</dt>
              <dd>{formatDecimal(s.subtotal)}</dd>
            </div>
          ))}
        <div>
          <dt>Total geral</dt>
          <dd>{formatDecimal(result.total)}</dd>
        </div>
        <div>
          <dt>Pontuação potencial</dt>
          <dd>{formatDecimal(result.potential_total)}</dd>
        </div>
        <div>
          <dt>Percentual do Grupo I</dt>
          <dd>{result.group1_percent == null ? "—" : `${formatDecimal(result.group1_percent)}%`}</dd>
        </div>
        <div>
          <dt>Mínimo de referência</dt>
          <dd>{minimumText}</dd>
        </div>
      </dl>
      <ul className="counts" aria-label="Contadores">
        <li>Atividades: {counters.activities}</li>
        <li>Com comprovante: {counters.with_evidence}</li>
        <li>Pendentes: {counters.pending}</li>
        <li>Não pontuadas: {counters.not_scored}</li>
        <li>Com divergências: {counters.with_alerts}</li>
      </ul>
    </>
  );
}
