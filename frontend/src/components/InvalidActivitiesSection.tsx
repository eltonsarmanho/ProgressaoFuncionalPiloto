import { useEffect, useId, useRef, useState } from "react";
import { PAGE_SIZE, validityOf } from "../activityList";
import type { Activity, InvalidReason, ScoringGroup } from "../api/types";
import { INVALID_REASON_LABELS } from "../labels";
import { ActivityRow, type RowFeedback } from "./ActivityRow";

const REASON_ORDER: InvalidReason[] = ["REJEITADA", "FORA_DO_INTERSTICIO", "CARGA_HORARIA_INSUFICIENTE", "GRUPO_NAO_CONTA", "DUPLICIDADE"];

/** "Fora do interstício: 6; Rejeitada por você: 1": only the reasons that occur. */
function reasonCounts(activities: Activity[]): string {
  const counts = new Map<InvalidReason, number>();
  for (const a of activities) {
    const reason = validityOf(a).reason;
    if (reason) counts.set(reason, (counts.get(reason) ?? 0) + 1);
  }
  return REASON_ORDER.filter((r) => counts.has(r))
    .map((r) => `${INVALID_REASON_LABELS[r]}: ${counts.get(r)}`)
    .join("; ");
}

/**
 * SEC-06, SEC-07, SEC-09..SEC-12: "Atividades não válidas", closed on opening. The title is a
 * button (`aria-expanded`) that carries the total and the count of each reason; each row shows its
 * reason in words with "Editar" (and "Reabrir" on a rejected one). It gets only the not valid
 * activities; fixing one makes the parent's list send it to the valid section.
 */
export function InvalidActivitiesSection({
  activities,
  groups,
  onEdit,
  onChanged,
  feedback,
}: {
  activities: Activity[];
  groups: ScoringGroup[];
  onEdit: (activity: Activity) => void;
  onChanged: () => void;
  feedback?: RowFeedback;
}) {
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState(PAGE_SIZE);
  const title = `Atividades não válidas (${activities.length})`;
  const list = useRef<HTMLUListElement>(null);
  const focusFrom = useRef<number | null>(null);

  // "Mostrar mais" removes the button that had the focus: the first new row takes it.
  useEffect(() => {
    if (focusFrom.current == null) return;
    list.current?.querySelectorAll<HTMLElement>("[data-activity-title]")[focusFrom.current]?.focus();
    focusFrom.current = null;
  }, [shown]);

  if (activities.length === 0) {
    return (
      <section className="activity-section" aria-labelledby="invalid-title">
        <h2 id="invalid-title" tabIndex={-1} data-focus-fallback>
          {title}
        </h2>
        <p>Nenhuma atividade não válida</p>
      </section>
    );
  }

  return (
    <section className="activity-section" aria-labelledby="invalid-title">
      <h2 id="invalid-title" className="section-heading">
        <button type="button" className="section-toggle" data-focus-fallback aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((o) => !o)}>
          <span className="section-toggle-title">{title}</span>
          <span className="section-toggle-counts">{reasonCounts(activities)}</span>
        </button>
      </h2>
      <div id={panelId} hidden={!open}>
        {open && (
          <>
            <ul className="activity-list" ref={list}>
              {activities.slice(0, shown).map((a) => (
                <ActivityRow
                  key={a.id}
                  activity={a}
                  groups={groups}
                  selected={false}
                  onEdit={() => onEdit(a)}
                  onLink={() => undefined}
                  onChanged={onChanged}
                  feedback={feedback}
                />
              ))}
            </ul>
            <p className="muted" aria-live="polite">{`Mostrando ${Math.min(shown, activities.length)} de ${activities.length}`}</p>
            {activities.length > shown && (
              <button type="button" className="btn btn-secondary" onClick={() => {
                  focusFrom.current = shown;
                  setShown((n) => n + PAGE_SIZE);
                }}
              >
                Mostrar mais
              </button>
            )}
          </>
        )}
      </div>
    </section>
  );
}
