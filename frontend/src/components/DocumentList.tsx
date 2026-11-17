import { useRef, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { ApiError, errorMessage, fieldErrors, request } from "../api/client";
import type { DocumentSummary } from "../api/types";
import {
  ACTIVE_DOCUMENT_STATUSES,
  DOCUMENT_CODE_LABELS,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
  LOW_CONFIDENCE,
  NO_ITEM_CODE,
  TAXONOMY_LABELS,
  formatDecimal,
  formatSize,
} from "../labels";
import { FieldError, errorProps } from "./FieldError";

type Panel = { kind: "delete" | "classify"; doc: DocumentSummary };
type Notice = { tone: "error" | "ok"; text: string; existingId?: string };

const COLUMNS = ["Nome", "Tipo", "Tamanho", "Status", "Categoria sugerida", "Confiança", "Ações"] as const;

function labelOf(table: Record<string, string>, code: string | null): string {
  return code ? (table[code] ?? code) : "—";
}

/** The warning each document status carries; the AI-unavailable one points to manual entry (TELA-07). */
function StatusNote({ doc, onCreateActivity }: { doc: DocumentSummary; onCreateActivity: () => void }) {
  if (doc.status === "EXTRAIDO_SEM_IA") {
    return (
      <p className="doc-warning sev-ALERTA">
        A IA ficou indisponível para este documento ({labelOf(DOCUMENT_CODE_LABELS, doc.status_code)}). O texto foi
        extraído, mas nenhuma atividade foi sugerida: cadastre a atividade manualmente.{" "}
        <button type="button" className="link" onClick={onCreateActivity}>
          Criar atividade deste documento
        </button>
      </p>
    );
  }
  if (doc.suggested_category === NO_ITEM_CODE) {
    return (
      <p className="doc-warning sev-ALERTA">
        {DOCUMENT_CODE_LABELS[NO_ITEM_CODE]}: nenhuma atividade foi criada a partir deste documento.{" "}
        <button type="button" className="link" onClick={onCreateActivity}>
          Criar atividade deste documento
        </button>
      </p>
    );
  }
  if ((doc.status === "FALHOU" || doc.status === "REQUER_REVISAO") && doc.status_code) {
    return <p className="doc-warning sev-ALERTA">{labelOf(DOCUMENT_CODE_LABELS, doc.status_code)}</p>;
  }
  return null;
}

function Confidence({ doc }: { doc: DocumentSummary }) {
  if (doc.confidence == null) return <>—</>;
  const low = Number(doc.confidence) < LOW_CONFIDENCE;
  return (
    <>
      {formatDecimal(doc.confidence)}
      {low && <span className="doc-warning sev-ALERTA"> Baixa confiança: confira os dados</span>}
    </>
  );
}

function DeleteForm({ doc, onDone, onCancel }: { doc: DocumentSummary; onDone: () => void; onCancel: () => void }) {
  const [justificativa, setJustificativa] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (justificativa.trim() === "") {
      setErrors({ justificativa: "Informe a justificativa da exclusão." });
      return;
    }
    setErrors({});
    try {
      await request("DELETE", `/api/documents/${doc.id}?justificativa=${encodeURIComponent(justificativa.trim())}`);
      onDone();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    }
  }

  return (
    <form className="card" onSubmit={submit} noValidate aria-label="Excluir documento">
      <h3>Excluir documento: {doc.original_name}</h3>
      <p className="muted">
        O arquivo, o texto extraído e os vínculos são apagados. As atividades continuam, mas perdem este comprovante.
      </p>
      <div className="field">
        <label htmlFor="delete-justificativa">Justificativa da exclusão</label>
        <textarea
          id="delete-justificativa"
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
      <button type="submit">Confirmar exclusão</button>
      <button type="button" className="link" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}

function ClassifyForm({ doc, onDone, onCancel }: { doc: DocumentSummary; onDone: () => void; onCancel: () => void }) {
  const [tipo, setTipo] = useState(doc.manual_type ?? doc.suggested_type ?? "");
  const [categoria, setCategoria] = useState(
    doc.manual_category ?? (doc.suggested_category && doc.suggested_category !== NO_ITEM_CODE ? doc.suggested_category : ""),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setErrors({});
    try {
      await request("PUT", `/api/documents/${doc.id}/classification`, {
        tipo,
        categoria,
        expected_version: doc.version,
      });
      onDone();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    }
  }

  return (
    <form className="card" onSubmit={submit} noValidate aria-label="Classificar documento">
      <h3>Classificar documento: {doc.original_name}</h3>
      <p className="muted">Sua classificação é guardada ao lado da sugestão da IA, que não é alterada.</p>
      <div className="field">
        <label htmlFor="classify-tipo">Tipo do documento</label>
        <select id="classify-tipo" value={tipo} onChange={(e) => setTipo(e.target.value)} {...errorProps("tipo", errors)}>
          <option value="">Selecione…</option>
          {Object.entries(DOCUMENT_TYPE_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
        <FieldError id="tipo-error" message={errors.tipo} />
      </div>
      <div className="field">
        <label htmlFor="classify-categoria">Categoria da atividade</label>
        <select
          id="classify-categoria"
          value={categoria}
          onChange={(e) => setCategoria(e.target.value)}
          {...errorProps("categoria", errors)}
        >
          <option value="">Selecione…</option>
          {Object.entries(TAXONOMY_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
        <FieldError id="categoria-error" message={errors.categoria} />
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button type="submit">Salvar classificação</button>
      <button type="button" className="link" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}

/**
 * TELA-02 / 04 / 07 / 09: one row per document (cards at 360 px), with every action of the step.
 * `onChanged` reloads the list after replace, delete, reprocess and classify.
 */
export function DocumentList({
  documents,
  processId,
  onView,
  onCreateActivity,
  onChanged,
}: {
  documents: DocumentSummary[];
  processId: string;
  onView: (doc: DocumentSummary) => void;
  onCreateActivity: (doc: DocumentSummary) => void;
  onChanged: () => void;
}) {
  const [panel, setPanel] = useState<Panel | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const replaceTarget = useRef<DocumentSummary | null>(null);
  const replaceInput = useRef<HTMLInputElement>(null);

  const done = () => {
    setPanel(null);
    setNotice(null);
    onChanged();
  };

  async function reprocess(doc: DocumentSummary) {
    setNotice(null);
    try {
      await request("POST", `/api/documents/${doc.id}/reprocess`);
      setNotice({ tone: "ok", text: `${doc.original_name}: reprocessamento solicitado.` });
      onChanged();
    } catch (err) {
      setNotice({ tone: "error", text: `${doc.original_name}: ${errorMessage(err)}` });
    }
  }

  async function replace(file: File | undefined) {
    const doc = replaceTarget.current;
    if (replaceInput.current) replaceInput.current.value = "";
    if (!doc || !file) return;
    setNotice(null);
    const form = new FormData();
    form.append("file", file);
    form.append("expected_version", String(doc.version));
    try {
      await request("PUT", `/api/documents/${doc.id}/file`, form);
      setNotice({ tone: "ok", text: `${doc.original_name}: arquivo substituído; o documento será processado de novo.` });
      onChanged();
    } catch (err) {
      const existing = err instanceof ApiError && err.status === 409 ? duplicateId(err) : undefined;
      const issues = fieldErrors(err);
      setNotice({
        tone: "error",
        text: `${doc.original_name}: ${issues.arquivo ?? errorMessage(err)}`,
        existingId: existing,
      });
    }
  }

  return (
    <section className="card" aria-labelledby="documents-title">
      <h2 id="documents-title">Documentos enviados</h2>
      <p className="muted">
        Tudo que a IA sugere precisa da sua revisão. Reprocessar um documento rejeita os rascunhos da leitura anterior
        que você ainda não editou.
      </p>
      <input
        ref={replaceInput}
        type="file"
        className="visually-hidden"
        tabIndex={-1}
        aria-label="Arquivo substituto"
        accept=".pdf,.jpg,.jpeg,.png"
        onChange={(e) => void replace(e.target.files?.[0])}
      />
      <div aria-live="polite">
        {notice && (
          <p role={notice.tone === "error" ? "alert" : "status"} className={notice.tone === "error" ? "error" : undefined}>
            {notice.text}
            {notice.existingId && (
              <>
                {" "}
                <Link to={`/processos/${processId}/documentos?documento=${notice.existingId}`}>
                  Ver o documento já enviado
                </Link>
              </>
            )}
          </p>
        )}
      </div>
      {documents.length === 0 ? (
        <p>Nenhum documento enviado neste processo.</p>
      ) : (
        <table className="scoring-table doc-table">
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
            {documents.map((doc) => {
              const type = doc.manual_type ?? doc.suggested_type;
              const category = doc.manual_category ?? doc.suggested_category;
              const busy = ACTIVE_DOCUMENT_STATUSES.includes(doc.status);
              return (
                <tr key={doc.id}>
                  <td data-label="Nome">{doc.original_name}</td>
                  <td data-label="Tipo">
                    {labelOf(DOCUMENT_TYPE_LABELS, type)}
                    {doc.manual_type && <small className="muted"> (informado por você)</small>}
                    {!doc.manual_type && doc.suggested_type && <small className="muted"> (sugerido pela IA)</small>}
                  </td>
                  <td data-label="Tamanho">{formatSize(doc.size_bytes)}</td>
                  <td data-label="Status">
                    <span className={`status status-${doc.status}`}>{DOCUMENT_STATUS_LABELS[doc.status]}</span>
                    <StatusNote doc={doc} onCreateActivity={() => onCreateActivity(doc)} />
                  </td>
                  <td data-label="Categoria sugerida">
                    {category === NO_ITEM_CODE ? "Sem item de pontuação" : labelOf(TAXONOMY_LABELS, category)}
                    {doc.manual_category ? (
                      <small className="muted"> (informada por você)</small>
                    ) : (
                      category &&
                      category !== NO_ITEM_CODE && <small className="muted"> (sugerida pela IA)</small>
                    )}
                  </td>
                  <td data-label="Confiança">
                    <Confidence doc={doc} />
                  </td>
                  <td data-label="Ações">
                    <div className="row-actions">
                      <button type="button" className="link" onClick={() => onView(doc)}>
                        Visualizar {doc.original_name}
                      </button>
                      <a href={`/api/documents/${doc.id}/file?download=1`}>Baixar {doc.original_name}</a>
                      <button
                        type="button"
                        className="link"
                        onClick={() => {
                          replaceTarget.current = doc;
                          replaceInput.current?.click();
                        }}
                      >
                        Substituir {doc.original_name}
                      </button>
                      <button type="button" className="link" onClick={() => setPanel({ kind: "delete", doc })}>
                        Excluir {doc.original_name}
                      </button>
                      <button type="button" className="link" disabled={busy} onClick={() => void reprocess(doc)}>
                        Reprocessar {doc.original_name}
                      </button>
                      <button type="button" className="link" onClick={() => setPanel({ kind: "classify", doc })}>
                        Classificar {doc.original_name}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {panel?.kind === "delete" && (
        <DeleteForm key={panel.doc.id} doc={panel.doc} onDone={done} onCancel={() => setPanel(null)} />
      )}
      {panel?.kind === "classify" && (
        <ClassifyForm key={panel.doc.id} doc={panel.doc} onDone={done} onCancel={() => setPanel(null)} />
      )}
    </section>
  );
}

/** The 409 of a replacement carries the id of the document that already has the file. */
function duplicateId(error: ApiError): string | undefined {
  const body = error.body as { existing_document_id?: unknown } | undefined;
  return body?.existing_document_id ? String(body.existing_document_id) : undefined;
}
