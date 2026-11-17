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

type Props = {
  rows: ScoringRow[];
  subtotals: { group_number: number; subtotal: string }[];
  groupNames?: Record<number, string>;
};

/** TELA-02 / TELA-08: rows grouped I..VIII; stacked cards on narrow screens (CSS). */
export function ScoringTable({ rows, subtotals, groupNames = GROUP_NAMES }: Props) {
  const numbers = [...new Set([...subtotals.map((s) => s.group_number), ...rows.flatMap((r) => (r.group_number ? [r.group_number] : []))])].sort(
    (a, b) => a - b,
  );
  const unassigned = rows.filter((r) => r.group_number == null);

  const renderRow = (r: ScoringRow) => {
    const cells = [
      r.group_number ? roman(r.group_number) : "—",
      r.item_number ?? "—",
      r.title,
      formatDecimal(r.effective_quantity),
      formatDecimal(r.unit_points),
      formatDecimal(r.points),
      r.evidence_note || "Sem comprovante",
    ];
    return (
      <tr key={r.activity_id}>
        {cells.map((value, i) => (
          <td key={COLUMNS[i]} data-label={COLUMNS[i]}>
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
        </td>
      </tr>
    );
  };

  const head = (title: string, subtotal?: string) => (
    <tr className="group-head">
      <th colSpan={COLUMNS.length} scope="rowgroup">
        {title}
        {subtotal != null && <span className="subtotal"> · Subtotal: {formatDecimal(subtotal)}</span>}
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
        return (
          <tbody key={n}>
            {head(`Grupo ${roman(n)}${name ? ` · ${name}` : ""}`, subtotal)}
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
