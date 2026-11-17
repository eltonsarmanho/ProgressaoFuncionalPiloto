import type { ScoringResult } from "../api/types";
import { GROUP_NAMES, MINIMUM_LABELS, formatDecimal, roman } from "../labels";

/**
 * TELA-03: subtotals, totals, Group I percentage, minimum comparison and counters.
 * TELA-02: when group I is in PIT hours (official table) the total is labelled "Grupos II a VIII"
 * and the hours per period and in total are shown apart, never as points.
 */
export function ScoringSummary({
  result,
  groupNames = GROUP_NAMES,
  group1InHours,
}: {
  result: ScoringResult;
  groupNames?: Record<number, string>;
  /** Group I is outside the total (known from the chosen version); inferred from the result when omitted. */
  group1InHours?: boolean;
}) {
  const { minimum, counters } = result;
  const inHours =
    group1InHours ?? (result.rows.some((r) => r.pit_hours != null) || Number(result.group1_total_hours) > 0);
  const periods = Object.entries(result.group1_hours_by_period).sort(([a], [b]) => a.localeCompare(b));
  const minimumText =
    MINIMUM_LABELS[minimum.status] + (minimum.minimum != null ? ` (${formatDecimal(minimum.minimum)})` : "");
  return (
    <>
      <dl className="totals">
        {[...result.subtotals]
          .filter((s) => !(inHours && s.group_number === 1))
          .sort((a, b) => a.group_number - b.group_number)
          .map((s) => (
            <div key={s.group_number}>
              <dt>{`Grupo ${roman(s.group_number)} · ${groupNames[s.group_number] ?? GROUP_NAMES[s.group_number] ?? ""}`}</dt>
              <dd>{formatDecimal(s.subtotal)}</dd>
            </div>
          ))}
        <div>
          <dt>{inHours ? "Total geral (Grupos II a VIII)" : "Total geral"}</dt>
          <dd>{formatDecimal(result.total)}</dd>
        </div>
        <div>
          <dt>Pontuação potencial</dt>
          <dd>{formatDecimal(result.potential_total)}</dd>
        </div>
        <div>
          <dt>Potencial com data no interstício</dt>
          <dd>{formatDecimal(result.potential_dated)}</dd>
        </div>
        <div>
          <dt>Potencial sem data — aguardando revisão</dt>
          <dd>{formatDecimal(result.potential_undated)}</dd>
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
      {inHours && (
        <div role="group" aria-label="Horas de PIT do Grupo I">
          <dl className="totals">
            {periods.map(([period, hours]) => (
              <div key={period}>
                <dt>{`PIT ${period}`}</dt>
                <dd>{`${formatDecimal(hours)} horas`}</dd>
              </div>
            ))}
            <div>
              <dt>Total de horas de PIT</dt>
              <dd>{`${formatDecimal(result.group1_total_hours)} horas`}</dd>
            </div>
          </dl>
        </div>
      )}
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
