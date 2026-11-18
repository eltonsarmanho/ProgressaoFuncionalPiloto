import { useState, type FormEvent } from "react";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, DocumentSummary, ScoringGroup, ScoringRow } from "../api/types";
import {
  ACTIVITY_SOURCE_LABELS,
  ACTIVITY_STATUS_LABELS,
  ROW_STATUS_LABELS,
  formatDecimal,
  itemLabel,
} from "../labels";
import { ActivityForm } from "./ActivityForm";
import { FieldError, errorProps } from "./FieldError";
import { Modal } from "./Modal";

type Panel = { kind: "edit" | "link"; activity: Activity };
type Notice = { tone: "error" | "ok"; text: string };

const COLUMNS = ["Selecionar", "Atividade", "Origem", "Status", "Grupo e item", "Pontuação potencial", "Documentos", "Ações"] as const;

function LinkForm({
  activity,
  documents,
  onDone,
  onCancel,
}: {
  activity: Activity;
  documents: DocumentSummary[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const [documentId, setDocumentId] = useState("");
  const [page, setPage] = useState("1");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (documentId === "") {
      setErrors({ document_id: "Escolha o documento." });
      return;
    }
    setErrors({});
    try {
      await request("POST", `/api/activities/${activity.id}/evidences`, {
        document_id: documentId,
        page: Number(page),
      });
      onDone();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    }
  }

  return (
    <Modal title="Vincular documento" onClose={onCancel}>
      <p>{activity.title}</p>
      <form onSubmit={onSubmit} noValidate>
        <div className="field">
          <label htmlFor="link-document">Documento</label>
          <select id="link-document" value={documentId} onChange={(e) => setDocumentId(e.target.value)} {...errorProps("document_id", errors)}>
            <option value="">Selecione…</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.original_name}
              </option>
            ))}
          </select>
          <FieldError id="document_id-error" message={errors.document_id} />
        </div>
        <div className="field">
          <label htmlFor="link-page">Página do documento</label>
          <input id="link-page" type="number" min={1} value={page} onChange={(e) => setPage(e.target.value)} {...errorProps("page", errors)} />
          <FieldError id="page-error" message={errors.page} />
        </div>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="btn-row">
          <button type="submit" className="btn btn-primary">
            Vincular
          </button>
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

/**
 * TELA-06 / REV-02..04: every activity with its origin, status, item, potential score and the
 * documents (name and page) it is linked to; validation is always a human action.
 * The potential score comes from the scoring result row of the activity.
 */
export function ActivityReviewList({
  processId,
  activities,
  rows,
  groups,
  documents,
  onChanged,
}: {
  processId: string;
  activities: Activity[];
  rows: ScoringRow[];
  groups: ScoringGroup[];
  documents: DocumentSummary[];
  onChanged: () => void;
}) {
  const [panel, setPanel] = useState<Panel | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [busy, setBusy] = useState(false);
  const rowOf = new Map(rows.map((r) => [r.activity_id, r]));

  const done = () => {
    setPanel(null);
    setSelected([]);
    onChanged();
  };
  const toggle = (id: string) =>
    setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  /** UIM-13: validate and reject act at once; no justification, no panel. */
  async function changeStatus(activity: Activity, status: "VALIDADA" | "REJEITADA") {
    setNotice(null);
    setBusy(true);
    try {
      await request("POST", `/api/activities/${activity.id}/status`, {
        status,
        expected_version: activity.version,
      });
      done();
    } catch (err) {
      setNotice({ tone: "error", text: `${activity.title}: ${errorMessage(err)}` });
    } finally {
      setBusy(false);
    }
  }

  /** REV-04: the atomic batch endpoint; one request for all the ids. */
  async function validateBatch(ids: string[]) {
    setNotice(null);
    setBusy(true);
    try {
      await request("POST", `/api/processes/${processId}/activities/validate-batch`, { activity_ids: ids });
      done();
      setNotice({ tone: "ok", text: `${ids.length === 1 ? "1 atividade validada" : `${ids.length} atividades validadas`}.` });
    } catch (err) {
      setNotice({ tone: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  function potential(activity: Activity): string {
    const row = rowOf.get(activity.id);
    if (!row) return "—";
    const value = row.pit_hours != null ? `${formatDecimal(row.pit_hours)} horas (PIT)` : formatDecimal(row.points);
    return `${value} (${ROW_STATUS_LABELS[row.status] ?? row.status})`;
  }

  function isUndated(activity: Activity): boolean {
    return rowOf.get(activity.id)?.alerts.some((alert) => alert.code === "DATA_AUSENTE") ?? false;
  }

  return (
    <section aria-labelledby="review-title">
      <h2 id="review-title">Atividades</h2>
      <p className="review-note">
        Atividades sugeridas pela IA aguardam a sua revisão: nada é validado sem você.
      </p>
      <div aria-live="polite">
        {notice && (
          <p role={notice.tone === "error" ? "alert" : "status"} className={notice.tone === "error" ? "error" : undefined}>
            {notice.text}
          </p>
        )}
      </div>
      {activities.length === 0 ? (
        <p>Nenhuma atividade neste processo.</p>
      ) : (
        <>
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-primary"
              disabled={selected.length === 0 || busy}
              onClick={() => void validateBatch(selected)}
            >
              Validar as selecionadas ({selected.length})
            </button>
          </div>
          <table className="scoring-table wide-table review-table">
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th key={c} scope="col">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {activities.map((a) => {
                const criterion = groups.find((g) => g.number === a.group_number)?.criteria.find((c) => c.item_number === a.item_number);
                return (
                  <tr key={a.id}>
                    <td data-label="Selecionar">
                      <input
                        type="checkbox"
                        aria-label={`Selecionar ${a.title}`}
                        checked={selected.includes(a.id)}
                        onChange={() => toggle(a.id)}
                      />
                    </td>
                    <td data-label="Atividade" className="text-block">
                      {a.title}
                    </td>
                    <td data-label="Origem">{ACTIVITY_SOURCE_LABELS[a.source] ?? a.source}</td>
                    <td data-label="Status">
                      <span className={a.status === "AGUARDANDO_REVISAO" ? "badge badge-pending" : "badge"}>
                        {ACTIVITY_STATUS_LABELS[a.status] ?? a.status}
                      </span>
                    </td>
                    <td data-label="Grupo e item" className="text-block">
                      {itemLabel(a.group_number, a.item_number)}
                      {criterion && <small className="muted"> · {criterion.description}</small>}
                    </td>
                    <td data-label="Pontuação potencial">
                      {potential(a)}
                      {isUndated(a) && <small className="muted"> · sem data</small>}
                    </td>
                    <td data-label="Documentos">
                      {a.evidences && a.evidences.length > 0 ? (
                        <ul className="evidence-list">
                          {a.evidences.map((e) => (
                            <li key={e.id}>
                              {e.document_name}, página {e.page}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        "Sem documento vinculado"
                      )}
                    </td>
                    <td data-label="Ações">
                      <div className="row-actions">
                        <button
                          type="button"
                          className="btn btn-primary"
                          aria-label={`Validar ${a.title}`}
                          title={`Validar ${a.title}`}
                          disabled={a.status === "VALIDADA" || busy}
                          onClick={() => void changeStatus(a, "VALIDADA")}
                        >
                          Validar
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger"
                          aria-label={`Rejeitar ${a.title}`}
                          title={`Rejeitar ${a.title}`}
                          disabled={a.status === "REJEITADA" || busy}
                          onClick={() => void changeStatus(a, "REJEITADA")}
                        >
                          Rejeitar
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          aria-label={`Editar ${a.title}`}
                          title={`Editar ${a.title}`}
                          onClick={() => setPanel({ kind: "edit", activity: a })}
                        >
                          Editar
                        </button>
                        <button
                          type="button"
                          className="btn btn-secondary"
                          aria-label={`Vincular documento a ${a.title}`}
                          title={`Vincular documento a ${a.title}`}
                          onClick={() => setPanel({ kind: "link", activity: a })}
                        >
                          Vincular
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      {panel?.kind === "edit" && (
        <Modal title="Editar atividade" onClose={() => setPanel(null)}>
          <ActivityForm
            key={`edit-${panel.activity.id}`}
            processId={processId}
            groups={groups}
            activity={panel.activity}
            onSaved={done}
            onCancel={() => setPanel(null)}
          />
        </Modal>
      )}
      {panel?.kind === "link" && (
        <LinkForm key={`link-${panel.activity.id}`} activity={panel.activity} documents={documents} onDone={done} onCancel={() => setPanel(null)} />
      )}
    </section>
  );
}
