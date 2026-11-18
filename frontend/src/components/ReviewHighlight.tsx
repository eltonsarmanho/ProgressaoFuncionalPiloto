import type { ScoringGroup } from "../api/types";
import { formatDecimal, roman } from "../labels";

/** ADMUI-03: the criteria of a version, with those carrying a `review_note` highlighted and explained. */
export function ReviewHighlight({ groups }: { groups: ScoringGroup[] }) {
  const marked = groups.flatMap((g) => g.criteria).filter((c) => c.review_note).length;
  return (
    <>
      {marked > 0 && (
        <p className="review-summary">
          {marked === 1
            ? "1 critério marcado para revisão humana."
            : `${marked} critérios marcados para revisão humana.`}
        </p>
      )}
      <table className="scoring-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Descrição</th>
            <th>Modo</th>
            <th>Pontos</th>
            <th>Limite</th>
          </tr>
        </thead>
        <tbody>
          {groups.flatMap((group) => [
            <tr className="group-head" key={`g${group.number}`}>
              <th colSpan={5}>
                Grupo {roman(group.number)} · {group.name}
                {group.counts_in_total ? "" : " (não conta no total)"}
              </th>
            </tr>,
            ...group.criteria.map((c) => (
              <tr key={`${c.group_number}.${c.item_number}`} className={c.review_note ? "review" : undefined}>
                <td data-label="Item">
                  {roman(c.group_number)}.{c.item_number}
                </td>
                <td data-label="Descrição">
                  {c.description}
                  {c.review_note && (
                    <p className="review-note">
                      <mark>Revisar</mark> {c.review_note}
                    </p>
                  )}
                </td>
                <td data-label="Modo">{c.mode}</td>
                <td data-label="Pontos">{formatDecimal(c.unit_points)}</td>
                <td data-label="Limite">{formatDecimal(c.max_points)}</td>
              </tr>
            )),
          ])}
        </tbody>
      </table>
    </>
  );
}
