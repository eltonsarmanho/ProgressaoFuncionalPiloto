import { useState, type FormEvent } from "react";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, DocumentSummary } from "../api/types";
import { FieldError, errorProps } from "./FieldError";
import { Modal } from "./Modal";

/**
 * VINC / UIM-16: links a document and a page to an activity in a dialog, with no justification.
 * A document outside the interstice is not offered (FORA-03); the API refuses the link anyway (409).
 */
export function ActivityLinkForm({
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
            {/* FORA-03: a document outside the interstice takes no part in Etapa 3; the API refuses the link (409). */}
            {documents
              .filter((d) => d.outside_interstice !== true)
              .map((d) => (
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
