import type { ScoringRow } from "../api/types";
import { LEVEL_LABELS, PANEL_LABELS, formatDecimal } from "../labels";

type Props = {
  rows: ScoringRow[];
  /** PIT hours per academic period and in total, as the engine sums them (only validated offers). */
  hoursByPeriod: Record<string, string>;
  totalHours: string;
  /** Group I is outside the total (the old table version): the hours are not points. */
  group1OutsideTotal: boolean;
};

const NO_PERIOD = "";

/**
 * GRES-04, GRES-05, GRES-09: the group I offers by academic period, with the discipline, the level
 * and the PIT hours. The component sums nothing: the totals come from the API (D8). An offer still
 * awaiting validation is listed with a text label and stays out of the hours.
 */
export function TeachingBlock({ rows, hoursByPeriod, totalHours, group1OutsideTotal }: Props) {
  const offers = rows.filter((r) => r.pit_hours != null && (r.status === "PONTUADA" || r.status === "POTENCIAL"));
  if (offers.length === 0) return <p>{PANEL_LABELS.noOffers}</p>;

  const byPeriod = new Map<string, ScoringRow[]>();
  for (const offer of offers) {
    const key = offer.academic_period ?? NO_PERIOD;
    byPeriod.set(key, [...(byPeriod.get(key) ?? []), offer]);
  }
  const periods = [...byPeriod.keys()].sort((a, b) =>
    a === NO_PERIOD ? 1 : b === NO_PERIOD ? -1 : a.localeCompare(b),
  );

  return (
    <div className="teaching">
      {periods.map((period) => (
        <div key={period} className="teaching-period">
          <h4>{period === NO_PERIOD ? PANEL_LABELS.noAcademicPeriod : `Período letivo ${period}`}</h4>
          <ul className="teaching-offers">
            {byPeriod.get(period)!.map((offer) => (
              <li key={offer.activity_id}>
                <span className="teaching-title">{offer.title}</span>
                {offer.level && <span className="teaching-level">{LEVEL_LABELS[offer.level]}</span>}
                <span className="teaching-hours">{`${formatDecimal(offer.pit_hours)} h`}</span>
                {offer.status === "POTENCIAL" && <span className="badge badge-pending">{PANEL_LABELS.awaitingValidation}</span>}
              </li>
            ))}
          </ul>
          {period !== NO_PERIOD && (
            <p className="teaching-total">{`Total do período: ${formatDecimal(hoursByPeriod[period] ?? "0.00")} horas`}</p>
          )}
        </div>
      ))}
      <p className="teaching-total teaching-grand-total">
        {group1OutsideTotal
          ? `Total do Grupo I: ${formatDecimal(totalHours)} horas (fora do total)`
          : `Total do Grupo I: ${formatDecimal(totalHours)} horas = ${formatDecimal(totalHours)} pontos`}
      </p>
    </div>
  );
}
