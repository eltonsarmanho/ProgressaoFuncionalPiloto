import type { ReactNode } from "react";
import type { ScoringRow } from "../api/types";
import { GROUP_NAMES, REASON_LABELS, ROW_STATUS_LABELS, formatDecimal, roman } from "../labels";

/** Short names so no header breaks into two lines; the full name of the abbreviated ones is the `title`. */
const COLUMNS = ["Grupo", "Item", "Atividade", "Qtde.", "Pts. unit.", "Total", "Status"] as const;
const COLUMN_TITLES: Partial<Record<(typeof COLUMNS)[number], string>> = {
  "Qtde.": "Quantidade",
  "Pts. unit.": "Pontuação unitária",
};

const PIT_LABEL = "horas (PIT)";
const POINT_PER_PIT_HOUR = "1.00";
const VALUE_COLUMN = 5;
const TITLE_COLUMN = 2;

type Props = {
  rows: ScoringRow[];
  subtotals: { group_number: number; subtotal: string }[];
  groupNames?: Record<number, string>;
  /** Total PIT hours of group I; shown in the group header instead of a points subtotal. */
  group1TotalHours?: string;
  actions?: (row: ScoringRow) => ReactNode;
};

/**
 * TELA-02 / TELA-08: rows grouped I..VIII; stacked cards on narrow screens (CSS).
 * A group I row of a version that keeps the group outside the total (`outside_total`) shows hours, never points.
 * GI-01: with the group counted in the total, the row shows the PIT hours as the quantity, 1,00 per hour and the points.
 */
export function ScoringTable({ rows, subtotals, groupNames = GROUP_NAMES, group1TotalHours, actions }: Props) {
  const numbers = [...new Set([...subtotals.map((s) => s.group_number), ...rows.flatMap((r) => (r.group_number ? [r.group_number] : []))])].sort(
    (a, b) => a - b,
  );
  const unassigned = rows.filter((r) => r.group_number == null);

  const renderRow = (r: ScoringRow) => {
    const inHours = r.outside_total;
    const countedPit = !inHours && r.pit_hours != null;
    const rejected = r.status === "REJEITADA";
    const cells = rejected
      ? [r.group_number ? roman(r.group_number) : "—", r.item_number ?? "—", r.title, "—", "—", "—"]
      : [
      r.group_number ? roman(r.group_number) : "—",
      r.item_number ?? "—",
      r.title,
      formatDecimal(countedPit ? r.pit_hours : r.effective_quantity),
      inHours ? "—" : formatDecimal(countedPit ? POINT_PER_PIT_HOUR : r.unit_points),
      inHours ? `${formatDecimal(r.pit_hours)} ${PIT_LABEL}` : formatDecimal(r.points),
    ];
    // Not scored (valid, waiting for "Validar" or without points) is highlighted; rejected is shaded.
    const rowClass = rejected ? "row-rejected" : r.status === "PONTUADA" ? undefined : "row-unscored";
    return (
      <tr key={r.activity_id} className={rowClass}>
        {cells.map((value, i) => (
          <td
            key={COLUMNS[i]}
            data-label={inHours && i === VALUE_COLUMN ? PIT_LABEL : (COLUMN_TITLES[COLUMNS[i]] ?? COLUMNS[i])}
            className={i === TITLE_COLUMN ? "text-block" : undefined}
          >
            {value}
          </td>
        ))}
        <td data-label="Status">
          <span className={`status status-${r.status}`}>{ROW_STATUS_LABELS[r.status] ?? r.status}</span>
          {r.reasons.length > 0 && (
            <ul className="reasons">
              {r.reasons.map((reason) => (
                <li key={reason}>{REASON_LABELS[reason] ?? reason}</li>
              ))}
            </ul>
          )}
          {actions?.(r)}
        </td>
      </tr>
    );
  };

  const head = (title: string, subtotal?: string, hours?: string) => (
    <tr className="group-head">
      <th colSpan={COLUMNS.length} scope="rowgroup">
        {title}
        {hours != null ? (
          <span className="subtotal"> · Total de {PIT_LABEL}: {formatDecimal(hours)}</span>
        ) : (
          subtotal != null && <span className="subtotal"> · Subtotal: {formatDecimal(subtotal)}</span>
        )}
      </th>
    </tr>
  );

  return (
    <table className="scoring-table wide-table score-table">
      <thead>
        <tr>
          {COLUMNS.map((c) => (
            <th key={c} scope="col" title={COLUMN_TITLES[c]}>
              {c}
            </th>
          ))}
        </tr>
      </thead>
      {numbers.map((n) => {
        const groupRows = rows.filter((r) => r.group_number === n);
        const subtotal = subtotals.find((s) => s.group_number === n)?.subtotal;
        const name = groupNames[n] ?? GROUP_NAMES[n];
        const inHours = groupRows.some((r) => r.outside_total);
        return (
          <tbody key={n}>
            {head(
              `Grupo ${roman(n)}${name ? ` · ${name}` : ""}`,
              inHours ? undefined : subtotal,
              inHours ? group1TotalHours : undefined,
            )}
            {groupRows.map(renderRow)}
          </tbody>
        );
      })}
      {unassigned.length > 0 && (
        <tbody>
          {head("Sem enquadramento")}
          {unassigned.map(renderRow)}
        </tbody>
      )}
    </table>
  );
}
