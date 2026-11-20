import { useEffect, useId, useRef, useState } from "react";
import { PAGE_SIZE, countGroups, countSituations, filterActivities, groupsOf, validityOf } from "../activityList";
import { errorMessage, request } from "../api/client";
import type { Activity, BulkValidateResult, DocumentSummary, ScoringGroup, ScoringRow, SkippedActivity } from "../api/types";
import { INVALID_REASON_LABELS, needsCategoryMessage } from "../labels";
import { isConfidentSuggestion } from "../trust";
import { ActivityFilters, DEFAULT_FILTERS, type ActivityFilterState } from "./ActivityFilters";
import { ActivityLinkForm } from "./ActivityLinkForm";
import { ActivityRow, type RowFeedback } from "./ActivityRow";

type Notice = { tone: "error" | "ok"; text: string; skipped?: string[] };

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** VAL-04: "12 validadas; 3 ficaram sem categoria" (and the ones that are not valid, apart). */
function batchSummary(validated: number, skipped: SkippedActivity[]): string {
  const noCategory = skipped.filter((s) => s.reason === "SEM_CATEGORIA").length;
  const notValid = skipped.length - noCategory;
  const parts = [plural(validated, "validada", "validadas")];
  if (noCategory > 0) parts.push(`${noCategory} ${noCategory === 1 ? "ficou" : "ficaram"} sem categoria`);
  if (notValid > 0) parts.push(`${notValid} ${notValid === 1 ? "não é válida" : "não são válidas"}`);
  return parts.join("; ");
}

const skippedReason = (s: SkippedActivity) => (s.reason === "SEM_CATEGORIA" ? "sem categoria" : INVALID_REASON_LABELS[s.reason]);

/**
 * SEC-02, SEC-03, SEC-05, SEC-11, VAL-04: "Atividades válidas": the filters, 25 rows at a time,
 * the selection, the batch validation (the selected ones and the trusted ones) and the link of a
 * document. It gets only the valid activities; the filters and the search run here, in memory,
 * over the whole list. Every write reloads through `onChanged`; "Editar" is the parent's panel.
 */
export function ValidActivitiesSection({
  processId,
  activities,
  rows,
  groups,
  documents,
  onEdit,
  onChanged,
  feedback,
}: {
  processId: string;
  activities: Activity[];
  rows: ScoringRow[];
  groups: ScoringGroup[];
  documents: DocumentSummary[];
  onEdit: (activity: Activity) => void;
  onChanged: () => void;
  feedback?: RowFeedback;
}) {
  const [filters, setFilters] = useState<ActivityFilterState>(DEFAULT_FILTERS);
  const [shown, setShown] = useState(PAGE_SIZE);
  const [selection, setSelection] = useState<string[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const [linking, setLinking] = useState<Activity | null>(null);
  const beyondId = useId();
  const list = useRef<HTMLUListElement>(null);
  const focusFrom = useRef<number | null>(null);

  // "Mostrar mais" removes the button that had the focus: the first new row takes it.
  useEffect(() => {
    if (focusFrom.current == null) return;
    list.current?.querySelectorAll<HTMLElement>("[data-activity-title]")[focusFrom.current]?.focus();
    focusFrom.current = null;
  }, [shown]);

  const rowOf = new Map(rows.map((r) => [r.activity_id, r]));
  const filtered = filterActivities(activities, filters);
  const visible = filtered.slice(0, shown);
  const needsCategory = activities.filter((a) => validityOf(a).needs_category).length;

  // SEC-11: the selection is what the filters show and what can be validated now (a reload may have
  // validated some of it, and a filter hides the rest): the counter and the batch count only that.
  const validatable = filtered
    .filter((a) => a.status === "AGUARDANDO_REVISAO" && !validityOf(a).needs_category)
    .map((a) => a.id);
  const validatableSet = new Set(validatable);
  const picked = selection.filter((id) => validatableSet.has(id));
  const shownIds = new Set(visible.map((a) => a.id));
  const beyondAll = validatable.filter((id) => !shownIds.has(id)).length;
  const beyondPicked = picked.filter((id) => !shownIds.has(id)).length;
  const confident = activities
    .filter((a) => !validityOf(a).needs_category && isConfidentSuggestion(a, rowOf.get(a.id), documents))
    .map((a) => a.id);

  const changeFilters = (next: ActivityFilterState) => {
    setFilters(next);
    setShown(PAGE_SIZE);
    // What the new filters hide leaves the selection, and does not come back when they are cleared.
    const kept = new Set(filterActivities(activities, next).map((a) => a.id));
    setSelection((current) => current.filter((id) => kept.has(id)));
  };
  const toggle = (id: string) =>
    setSelection((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  /** VAL-04: one request for all the ids; the server validates what it can and lists the rest. */
  async function validateBatch(ids: string[], rest = "") {
    setNotice(null);
    setBusy(true);
    try {
      const result = await request<BulkValidateResult>("POST", `/api/processes/${processId}/activities/validate-batch`, {
        activity_ids: ids,
      });
      const titleOf = (id: string) => activities.find((a) => a.id === id)?.title ?? id;
      setSelection([]);
      setNotice({
        tone: "ok",
        text: `${batchSummary(result.activities.length, result.skipped)}.${rest}`,
        skipped: result.skipped.map((s) => `${titleOf(s.id)}: ${skippedReason(s)}`),
      });
      onChanged();
    } catch (err) {
      setNotice({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="activity-section" aria-labelledby="valid-title">
      <h2 id="valid-title" tabIndex={-1} data-focus-fallback>
        {`Atividades válidas (${activities.length})`}
      </h2>
      <p className="review-note">Atividades sugeridas pela IA aguardam a sua revisão: nada é validado sem você.</p>
      {needsCategory > 0 && (
        <p className="error" aria-live="polite">
          {needsCategoryMessage(needsCategory)}
        </p>
      )}
      <div aria-live="polite">
        {notice && (
          <div role={notice.tone === "error" ? "alert" : "status"} className={notice.tone === "error" ? "error" : undefined}>
            <p>{notice.text}</p>
            {notice.skipped && notice.skipped.length > 0 && (
              <ul className="skipped-list">
                {notice.skipped.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {activities.length === 0 ? (
        <p>Nenhuma atividade válida ainda</p>
      ) : (
        <>
          <ActivityFilters filters={filters} counts={countSituations(activities)} groups={groupsOf(activities)} groupCounts={countGroups(activities)} onChange={changeFilters} />
          <div className="btn-row activity-toolbar">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={validatable.length === 0}
              aria-describedby={beyondAll > 0 ? beyondId : undefined}
              onClick={() => setSelection(validatable)}
            >
              Selecionar todas ({validatable.length})
            </button>
            <button type="button" className="btn btn-secondary" disabled={picked.length === 0} onClick={() => setSelection([])}>
              Limpar seleção
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={picked.length === 0 || busy}
              onClick={() => void validateBatch(picked)}
            >
              Validar as selecionadas ({picked.length})
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={confident.length === 0 || busy}
              title="Só sugestões da IA sem candidatos, sem aviso e de documentos lidos com confiança a partir de 70%"
              onClick={() => void validateBatch(confident, " As demais continuam aguardando a sua revisão.")}
            >
              Validar as confiáveis ({confident.length})
            </button>
          </div>
          <p className="muted">{plural(confident.length, "atividade elegível", "atividades elegíveis")} para a validação por confiança.</p>
          {beyondAll > 0 && (
            <p id={beyondId} className="muted">
              {`Selecionar todas inclui as ${validatable.length} atividades dos filtros, ${beyondAll} além das ${visible.length} mostradas.`}
            </p>
          )}
          <p className="muted" aria-live="polite">
            {plural(picked.length, "atividade selecionada", "atividades selecionadas")}
            {beyondPicked > 0 ? ` (${beyondPicked} além das mostradas)` : ""}
          </p>

          {filtered.length === 0 ? (
            <p>Nenhuma atividade encontrada com estes filtros.</p>
          ) : (
            <>
              <ul className="activity-list" ref={list}>
                {visible.map((a) => (
                  <ActivityRow
                    key={a.id}
                    activity={a}
                    groups={groups}
                    selected={picked.includes(a.id)}
                    onToggleSelect={() => toggle(a.id)}
                    onEdit={() => onEdit(a)}
                    onLink={() => setLinking(a)}
                    onChanged={onChanged}
                    feedback={feedback}
                  />
                ))}
              </ul>
              <p className="muted" aria-live="polite">{`Mostrando ${visible.length} de ${filtered.length}`}</p>
              {filtered.length > shown && (
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
        </>
      )}

      {linking && (
        <ActivityLinkForm
          key={linking.id}
          activity={linking}
          documents={documents}
          onDone={() => {
            setLinking(null);
            onChanged();
          }}
          onCancel={() => setLinking(null)}
        />
      )}
    </section>
  );
}
