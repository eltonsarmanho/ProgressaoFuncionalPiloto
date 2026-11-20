import { GROUP_NAMES, formatDecimal, roman } from "../labels";

type Props = {
  subtotals: { group_number: number; subtotal: string }[];
  total: string;
  /** Group I is outside the total (the old table version): it gets no bar. */
  group1OutsideTotal: boolean;
  /** Names from the table version; used only for a group `GROUP_NAMES` does not know. */
  groupNames?: Record<number, string>;
};

/** The width of a bar, in percent of the grand total; a total of 0 draws an empty bar. */
function widthOf(subtotal: string, total: string): string {
  const part = Number(subtotal);
  const whole = Number(total);
  if (!(whole > 0) || !(part > 0)) return "0%";
  return `${Math.round((part / whole) * 10000) / 100}%`;
}

/**
 * GRES-03: one line per group with its short name, the subtotal in text and a bar proportional to
 * the grand total. The bar is only a drawing: the value is always written beside it.
 */
export function GroupBars({ subtotals, total, group1OutsideTotal, groupNames }: Props) {
  const groups = [...subtotals]
    .filter((s) => !(group1OutsideTotal && s.group_number === 1))
    .sort((a, b) => a.group_number - b.group_number);
  return (
    <ul className="group-bars" aria-label="Pontos por grupo">
      {groups.map((s) => (
        <li key={s.group_number} className={Number(s.subtotal) === 0 ? "group-bar muted" : "group-bar"}>
          <span className="group-bar-name">
            {`${roman(s.group_number)} · ${GROUP_NAMES[s.group_number] ?? groupNames?.[s.group_number] ?? ""}`}
          </span>
          <span className="group-bar-value">{formatDecimal(s.subtotal)}</span>
          <div className="group-bar-track" aria-hidden="true">
            <div className="group-bar-fill" style={{ width: widthOf(s.subtotal, total) }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
