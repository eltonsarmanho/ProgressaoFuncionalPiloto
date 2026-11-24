import type { Criterion, ScoringGroup } from "../api/types";
import { SCORING_MODE_LABELS, formatDecimal, roman } from "../labels";

/**
 * ADMUI-03: the criteria of a version, with those carrying a `review_note` highlighted and explained.
 * GTAB-22: with `onEdit` each row gets an "Editar" button (only an ADMIN on an editable version passes it).
 */
export function ReviewHighlight({
  groups,
  onEdit,
}: {
  groups: ScoringGroup[];
  onEdit?: (criterion: Criterion) => void;
}) {
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
            <th>Carga mínima (h)</th>
            <th>Limite</th>
            {onEdit && <th>Ações</th>}
          </tr>
        </thead>
        <tbody>
          {groups.flatMap((group) => [
            <tr className="group-head" key={`g${group.number}`}>
              <th colSpan={onEdit ? 7 : 6}>
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
                <td data-label="Modo">{SCORING_MODE_LABELS[c.mode]}</td>
                <td data-label="Pontos">{formatDecimal(c.unit_points)}</td>
                <td data-label="Carga mínima (h)">{formatDecimal(c.min_hours)}</td>
                <td data-label="Limite">{formatDecimal(c.max_points)}</td>
                {onEdit && (
                  <td data-label="Ações">
                    <button
                      type="button"
                      className="btn btn-secondary tbl-edit"
                      aria-label={`Editar critério ${roman(c.group_number)}.${c.item_number}`}
                      onClick={() => onEdit(c)}
                    >
                      Editar
                    </button>
                  </td>
                )}
              </tr>
            )),
          ])}
        </tbody>
      </table>
    </>
  );
}
