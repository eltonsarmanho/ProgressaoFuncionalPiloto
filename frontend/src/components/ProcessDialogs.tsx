import { useEffect, useState } from "react";
import { ApiError, errorMessage, request } from "../api/client";
import { GENERATION_CODE_LABELS } from "../labels";
import type { ProcessStatus, ProcessSummary } from "../api/types";
import { Modal } from "./Modal";

/** GP-ARQ-02: the only question before archiving; no justification. */
export function ArchiveProcessDialog({
  process,
  onArchived,
  onStale,
  onClose,
}: {
  process: ProcessSummary;
  onArchived: (status: ProcessStatus, version: number) => void;
  /** The version moved on (409): the list must be loaded again. */
  onStale: () => void;
  onClose: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setError(null);
    setBusy(true);
    try {
      const updated = await request<{ status: ProcessStatus; version: number }>(
        "POST",
        `/api/processes/${process.id}/status`,
        { status: "ARQUIVADO", expected_version: process.version },
      );
      onArchived(updated.status, updated.version);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
      if (isConflict(err)) onStale();
    }
  }

  return (
    <Modal title="Arquivar processo" onClose={onClose}>
      <p>Arquivar o processo de {process.professor_name}? Ele fica somente leitura.</p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void confirm()}>
          Arquivar
        </button>
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </Modal>
  );
}

type DeletePreview = { documents: number; activities: number; generated_documents: number };

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** GP-DEL-02: says the deletion is final, lists what goes away, and asks once. */
export function DeleteProcessDialog({
  process,
  onDeleted,
  onClose,
}: {
  process: ProcessSummary;
  /** The process is gone (204) or was already gone (404): the list leaves it out. */
  onDeleted: (alreadyGone: boolean) => void;
  onClose: () => void;
}) {
  const [preview, setPreview] = useState<DeletePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    request<DeletePreview>("GET", `/api/processes/${process.id}/delete-preview`)
      .then((value) => live && setPreview(value))
      .catch((err) => live && setError(errorMessage(err)));
    return () => {
      live = false;
    };
  }, [process.id]);

  async function confirm() {
    setError(null);
    setBusy(true);
    try {
      await request<void>("DELETE", `/api/processes/${process.id}`);
      onDeleted(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        onDeleted(true);
        return;
      }
      setError(deleteMessage(err));
      setBusy(false);
    }
  }

  return (
    <Modal title="Excluir processo" onClose={onClose}>
      <p>
        Excluir o processo de {process.professor_name}? A exclusão é definitiva e não pode ser desfeita. O
        docente continua cadastrado; só o processo e o que depende dele saem.
      </p>
      {preview ? (
        <ul aria-label="O que será apagado">
          <li>{count(preview.documents, "documento de entrada", "documentos de entrada")}</li>
          <li>{count(preview.activities, "atividade", "atividades")}</li>
          <li>{count(preview.generated_documents, "documento gerado", "documentos gerados")}</li>
        </ul>
      ) : (
        !error && <p className="muted">Carregando…</p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="btn-row">
        <button
          type="button"
          className="btn btn-danger"
          disabled={busy || preview === null}
          onClick={() => void confirm()}
        >
          Excluir definitivamente
        </button>
        <button type="button" className="btn btn-secondary" onClick={onClose}>
          Cancelar
        </button>
      </div>
    </Modal>
  );
}

/** A busy process (409 `OPERACAO_EM_ANDAMENTO`) gets the readable text; the rest, the server's. */
function deleteMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    const code = (error.body as { code?: string } | undefined)?.code;
    if (code === "OPERACAO_EM_ANDAMENTO") return GENERATION_CODE_LABELS.OPERACAO_EM_ANDAMENTO;
  }
  return errorMessage(error);
}

function isConflict(error: unknown): boolean {
  return typeof error === "object" && error !== null && (error as { status?: number }).status === 409;
}
