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

type Panel =
  | { kind: "validate" | "reject" | "edit" | "link"; activity: Activity }
  | { kind: "batch" };

const COLUMNS = ["Selecionar", "Atividade", "Origem", "Status", "Grupo e item", "Pontuação potencial", "Documentos", "Ações"] as const;

/** One justification, then `submit`; 422 on `justificativa` is shown at the field, anything else as an alert. */
function JustificationForm({
  title,
  confirmLabel,
  note,
  submit,
  onCancel,
}: {
  title: string;
  confirmLabel: string;
  note?: string;
  submit: (justificativa: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [justificativa, setJustificativa] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (justificativa.trim() === "") {
      setErrors({ justificativa: "Informe a justificativa." });
      return;
    }
    setErrors({});
    try {
      await submit(justificativa.trim());
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    }
  }

  return (
    <form className="card" onSubmit={onSubmit} noValidate aria-label={title}>
      <h3>{title}</h3>
      {note && <p className="muted">{note}</p>}
      <div className="field">
        <label htmlFor="review-justificativa">Justificativa</label>
        <textarea
          id="review-justificativa"
          rows={2}
          value={justificativa}
          onChange={(e) => setJustificativa(e.target.value)}
          {...errorProps("justificativa", errors)}
        />
        <FieldError id="justificativa-error" message={errors.justificativa} />
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button type="submit">{confirmLabel}</button>
      <button type="button" className="link" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}

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
  const [justificativa, setJustificativa] = useState("");
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
        ...(justificativa.trim() !== "" ? { justificativa: justificativa.trim() } : {}),
      });
      onDone();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    }
  }

  return (
    <form className="card" onSubmit={onSubmit} noValidate aria-label="Vincular documento">
      <h3>Vincular documento: {activity.title}</h3>
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
      <div className="field">
        <label htmlFor="link-justificativa">Justificativa (obrigatória se o documento já está ligado a outra atividade)</label>
        <textarea
          id="link-justificativa"
          rows={2}
          value={justificativa}
          onChange={(e) => setJustificativa(e.target.value)}
          {...errorProps("justificativa", errors)}
        />
        <FieldError id="justificativa-error" message={errors.justificativa} />
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button type="submit">Vincular</button>
      <button type="button" className="link" onClick={onCancel}>
        Cancelar
      </button>
    </form>
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
  const rowOf = new Map(rows.map((r) => [r.activity_id, r]));

  const done = () => {
    setPanel(null);
    setSelected([]);
    onChanged();
  };
  const toggle = (id: string) =>
    setSelected((current) => (current.includes(id) ? current.filter((x) => x !== id) : [...current, id]));

  const changeStatus = (activity: Activity, status: "VALIDADA" | "REJEITADA") => async (justificativa: string) => {
    await request("POST", `/api/activities/${activity.id}/status`, {
      status,
      expected_version: activity.version,
      justificativa,
    });
    done();
  };

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
      {activities.length === 0 ? (
        <p>Nenhuma atividade neste processo.</p>
      ) : (
        <>
          <button type="button" disabled={selected.length === 0} onClick={() => setPanel({ kind: "batch" })}>
            Validar as selecionadas ({selected.length})
          </button>
          <table className="scoring-table review-table">
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
                    <td data-label="Atividade">{a.title}</td>
                    <td data-label="Origem">{ACTIVITY_SOURCE_LABELS[a.source] ?? a.source}</td>
                    <td data-label="Status">
                      <span className={a.status === "AGUARDANDO_REVISAO" ? "badge badge-pending" : "badge"}>
                        {ACTIVITY_STATUS_LABELS[a.status] ?? a.status}
                      </span>
                    </td>
                    <td data-label="Grupo e item">
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
                        <button type="button" className="link" disabled={a.status === "VALIDADA"} onClick={() => setPanel({ kind: "validate", activity: a })}>
                          Validar {a.title}
                        </button>
                        <button type="button" className="link" disabled={a.status === "REJEITADA"} onClick={() => setPanel({ kind: "reject", activity: a })}>
                          Rejeitar {a.title}
                        </button>
                        <button type="button" className="link" onClick={() => setPanel({ kind: "edit", activity: a })}>
                          Editar {a.title}
                        </button>
                        <button type="button" className="link" onClick={() => setPanel({ kind: "link", activity: a })}>
                          Vincular documento a {a.title}
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

      {panel?.kind === "validate" && (
        <JustificationForm
          key={`validate-${panel.activity.id}`}
          title="Validar atividade"
          confirmLabel="Confirmar validação"
          note={`Você confirma que revisou os dados de “${panel.activity.title}”.`}
          submit={changeStatus(panel.activity, "VALIDADA")}
          onCancel={() => setPanel(null)}
        />
      )}
      {panel?.kind === "reject" && (
        <JustificationForm
          key={`reject-${panel.activity.id}`}
          title="Rejeitar atividade"
          confirmLabel="Confirmar rejeição"
          note={`A atividade “${panel.activity.title}” deixa de contar na pontuação.`}
          submit={changeStatus(panel.activity, "REJEITADA")}
          onCancel={() => setPanel(null)}
        />
      )}
      {panel?.kind === "batch" && (
        <JustificationForm
          title="Validar as atividades selecionadas"
          confirmLabel="Confirmar validação em lote"
          note={`A mesma justificativa vale para as ${selected.length} atividades selecionadas; cada uma gera o seu registro de auditoria.`}
          submit={async (justificativa) => {
            await request("POST", `/api/processes/${processId}/activities/validate-batch`, {
              activity_ids: selected,
              justificativa,
            });
            done();
          }}
          onCancel={() => setPanel(null)}
        />
      )}
      {panel?.kind === "edit" && (
        <ActivityForm
          key={`edit-${panel.activity.id}`}
          processId={processId}
          groups={groups}
          activity={panel.activity}
          onSaved={done}
          onCancel={() => setPanel(null)}
        />
      )}
      {panel?.kind === "link" && (
        <LinkForm key={`link-${panel.activity.id}`} activity={panel.activity} documents={documents} onDone={done} onCancel={() => setPanel(null)} />
      )}
    </section>
  );
}
