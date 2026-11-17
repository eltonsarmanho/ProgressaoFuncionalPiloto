import type { ReactNode } from "react";
import type { ScoringRow } from "../api/types";
import { GROUP_NAMES, REASON_LABELS, ROW_STATUS_LABELS, formatDecimal, roman } from "../labels";

const COLUMNS = [
  "Grupo",
  "Item",
  "Atividade",
  "Quantidade",
  "Pontuação unitária",
  "Total",
  "Comprovante",
  "Status",
] as const;

const PIT_LABEL = "horas (PIT)";
const VALUE_COLUMN = 5;

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
 * TELA-01: a row carrying `pit_hours` (group I of the official table) shows hours, never points.
 */
export function ScoringTable({ rows, subtotals, groupNames = GROUP_NAMES, group1TotalHours, actions }: Props) {
  const numbers = [...new Set([...subtotals.map((s) => s.group_number), ...rows.flatMap((r) => (r.group_number ? [r.group_number] : []))])].sort(
    (a, b) => a - b,
  );
  const unassigned = rows.filter((r) => r.group_number == null);

  const renderRow = (r: ScoringRow) => {
    const inHours = r.pit_hours != null;
    const cells = [
      r.group_number ? roman(r.group_number) : "—",
      r.item_number ?? "—",
      r.title,
      formatDecimal(r.effective_quantity),
      inHours ? "—" : formatDecimal(r.unit_points),
      inHours ? `${formatDecimal(r.pit_hours)} ${PIT_LABEL}` : formatDecimal(r.points),
      r.evidence_note || "Sem comprovante",
    ];
    return (
      <tr key={r.activity_id}>
        {cells.map((value, i) => (
          <td key={COLUMNS[i]} data-label={inHours && i === VALUE_COLUMN ? PIT_LABEL : COLUMNS[i]}>
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
    <table className="scoring-table">
      <thead>
        <tr>
          {COLUMNS.map((c) => (
            <th key={c} scope="col">
              {c}
            </th>
          ))}
        </tr>
      </thead>
      {numbers.map((n) => {
        const groupRows = rows.filter((r) => r.group_number === n);
        const subtotal = subtotals.find((s) => s.group_number === n)?.subtotal;
        const name = groupNames[n] ?? GROUP_NAMES[n];
        const inHours = groupRows.some((r) => r.pit_hours != null);
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
