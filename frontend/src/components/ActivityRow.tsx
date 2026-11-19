import { useRef, useState } from "react";
import { activityBody } from "../activityBody";
import { validityOf } from "../activityList";
import { ApiError, errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, ActivityStatus, ScoringGroup } from "../api/types";
import {
  BADGE_AWAITING_VALIDATION,
  BADGE_NEEDS_CATEGORY,
  BADGE_VALIDATED,
  formatDecimal,
  formatDocumentDate,
  itemLabel,
} from "../labels";
import { CategoryPicker, type CategoryValue } from "./CategoryPicker";
import { MergedNote } from "./MergedNote";
import { ReasonText } from "./ReasonText";

function whenText(a: Activity): string {
  if (a.event_date) return formatDocumentDate(a.event_date, a.period_precision);
  if (a.period_start || a.period_end) {
    const start = a.period_start ? formatDocumentDate(a.period_start, a.period_precision) : "—";
    const end = a.period_end ? formatDocumentDate(a.period_end, a.period_precision) : "—";
    return `${start} a ${end}`;
  }
  return "Sem data";
}

/** What the workspace does with the result of a write of a row: announce it and keep the focus. */
export type RowFeedback = {
  /** The write succeeded; called before the list reloads, while the row is still on the page. */
  done: (activityId: string, message: string) => void;
};

/**
 * VAL-06, SEC-04, SEC-12: one activity of the Etapa 3 as a `<li>` that wraps at any width. It shows
 * the title, the date, the category, the predicted points, the seals (always with text) and the
 * actions; "Validar" is offered only to a valid activity that has a category. Validate, reject,
 * reopen and the choice of the category act at once and call `onChanged` so the parent reloads
 * the list; "Editar" and "Vincular" are the parent's panels.
 */
export function ActivityRow({
  activity,
  groups,
  selected,
  onToggleSelect,
  onEdit,
  onLink,
  onChanged,
  feedback,
}: {
  activity: Activity;
  groups: ScoringGroup[];
  selected: boolean;
  /** Offers the selection box of the batch validation; omit it where nothing is selectable. */
  onToggleSelect?: () => void;
  onEdit: () => void;
  onLink: () => void;
  onChanged: () => void;
  feedback?: RowFeedback;
}) {
  const [notice, setNotice] = useState<string | null>(null);
  const [categoryError, setCategoryError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const pickerRef = useRef<HTMLSelectElement>(null);
  const titleRef = useRef<HTMLParagraphElement>(null);

  const validity = validityOf(activity);
  const isValid = validity.state === "VALIDA";
  const rejected = activity.status === "REJEITADA";
  const awaiting = activity.status === "AGUARDANDO_REVISAO";
  const criterion = groups
    .find((g) => g.number === activity.group_number)
    ?.criteria.find((c) => c.item_number === activity.item_number);
  const category = criterion
    ? `${itemLabel(activity.group_number, activity.item_number)} · ${criterion.description}`
    : itemLabel(activity.group_number, activity.item_number);

  /** A write of this row: errors stay in the row; a stale list is reloaded (409, or 422 of status or category). */
  async function write(action: () => Promise<unknown>, success: string) {
    setNotice(null);
    setCategoryError(undefined);
    setBusy(true);
    try {
      await action();
      feedback?.done(activity.id, success);
      // The button or the select that had the focus goes away with the write: the title is the stable place.
      titleRef.current?.focus();
      onChanged();
    } catch (err) {
      const byField = fieldErrors(err);
      const message = Object.values(byField)[0] ?? errorMessage(err);
      setNotice(message);
      if (byField.categoria) {
        setCategoryError(byField.categoria);
        pickerRef.current?.focus();
      }
      const stale = err instanceof ApiError && (err.status === 409 || "status" in byField || "categoria" in byField);
      if (stale) onChanged();
    } finally {
      setBusy(false);
    }
  }

  const STATUS_RESULT: Partial<Record<ActivityStatus, string>> = {
    VALIDADA: "validada",
    REJEITADA: "rejeitada",
    AGUARDANDO_REVISAO: "reaberta",
  };
  const changeStatus = (status: ActivityStatus) =>
    write(
      () => request("POST", `/api/activities/${activity.id}/status`, { status, expected_version: activity.version }),
      `${activity.title} ${STATUS_RESULT[status] ?? "atualizada"}`,
    );
  const chooseCategory = (value: CategoryValue) =>
    write(
      () =>
        request("PUT", `/api/activities/${activity.id}`, {
          ...activityBody(activity),
          ...value,
          expected_version: activity.version,
        }),
      `Categoria definida em ${activity.title}`,
    );

  return (
    <li className="activity-row">
      <div className="activity-row-main">
        {onToggleSelect && isValid && awaiting && (
          <input
            type="checkbox"
            aria-label={`Selecionar ${activity.title}`}
            checked={selected}
            onChange={onToggleSelect}
          />
        )}
        <div className="activity-row-body">
          <p className="activity-title" ref={titleRef} tabIndex={-1} data-activity-title={activity.id}>
            {activity.title}
          </p>
          <p className="activity-meta">
            {isValid &&
              (validity.needs_category ? (
                <span className="badge badge-pending">{BADGE_NEEDS_CATEGORY}</span>
              ) : activity.status === "VALIDADA" ? (
                <span className="badge badge-ok">{BADGE_VALIDATED}</span>
              ) : (
                <span className="badge badge-pending">{BADGE_AWAITING_VALIDATION}</span>
              ))}
            <span className="activity-date">{whenText(activity)}</span>
            {!validity.needs_category && <span className="activity-category">{category}</span>}
            {isValid && activity.predicted_points != null && (
              <span className="activity-points">{`Pontos previstos: ${formatDecimal(activity.predicted_points)}`}</span>
            )}
          </p>
          {!isValid && (
            <p className="activity-reason">
              <ReasonText validity={validity} />
            </p>
          )}
          {isValid && validity.needs_category && (
            <CategoryPicker
              groups={groups}
              value={null}
              label={`Categoria de ${activity.title}`}
              error={categoryError}
              disabled={busy}
              selectRef={pickerRef}
              onChange={(value) => void chooseCategory(value)}
            />
          )}
          {activity.evidences && activity.evidences.length > 0 ? (
            <ul className="evidence-list">
              {activity.evidences.map((e) => (
                <li key={e.id}>
                  {e.document_name}, página {e.page}
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">Sem documento vinculado</p>
          )}
          <MergedNote merged={activity.merged ?? []} onSeparated={onChanged} />
          {notice && (
            <p role="alert" className="error">
              {notice}
            </p>
          )}
        </div>
      </div>
      <div className="row-actions">
        {isValid && awaiting && !validity.needs_category && (
          <button
            type="button"
            className="btn btn-primary"
            aria-label={`Validar ${activity.title}`}
            disabled={busy}
            onClick={() => void changeStatus("VALIDADA")}
          >
            Validar
          </button>
        )}
        {isValid && (
          <button
            type="button"
            className="btn btn-danger"
            aria-label={`Rejeitar ${activity.title}`}
            disabled={busy}
            onClick={() => void changeStatus("REJEITADA")}
          >
            Rejeitar
          </button>
        )}
        {rejected && (
          <button
            type="button"
            className="btn btn-secondary"
            aria-label={`Reabrir ${activity.title}`}
            disabled={busy}
            onClick={() => void changeStatus("AGUARDANDO_REVISAO")}
          >
            Reabrir
          </button>
        )}
        <button type="button" className="btn btn-secondary" aria-label={`Editar ${activity.title}`} onClick={onEdit}>
          Editar
        </button>
        {isValid && (
          <button
            type="button"
            className="btn btn-secondary"
            aria-label={`Vincular documento a ${activity.title}`}
            onClick={onLink}
          >
            Vincular
          </button>
        )}
      </div>
    </li>
  );
}
