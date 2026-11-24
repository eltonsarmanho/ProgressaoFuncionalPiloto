import { useEffect, useState } from "react";
import { ApiError, errorMessage, request } from "../api/client";
import { blockReasonText } from "../labels";
import { Modal } from "./Modal";

/** What the dialog deletes: a version or a whole table (GTAB-27, GTAB-29). */
export type DeleteTarget = { kind: "version" | "table"; id: string; name: string };

type Blocker = { code: string; message: string; count: number | null; acronyms: string[] };
type Preview = {
  name: string;
  /** Only the table preview counts its versions and lists its units. */
  versions?: number;
  criteria: number;
  units?: { id: string; acronym: string }[];
  blocked: Blocker[];
};

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

const TEXT = {
  version: {
    title: "Excluir versão",
    ask: (name: string) =>
      `Excluir a versão "${name}"? A exclusão é definitiva e não pode ser desfeita. Saem a versão, os grupos e os critérios; a auditoria fica.`,
    previewPath: (id: string) => `/api/scoring-versions/${id}/delete-preview`,
    deletePath: (id: string) => `/api/scoring-versions/${id}`,
    done: (name: string) => `Versão "${name}" excluída.`,
    gone: (name: string) => `A versão "${name}" já tinha sido excluída.`,
  },
  table: {
    title: "Excluir tabela",
    ask: (name: string) =>
      `Excluir a tabela "${name}"? A exclusão é definitiva e não pode ser desfeita. Saem a tabela, as versões, os critérios e as associações de unidade; a auditoria fica.`,
    previewPath: (id: string) => `/api/scoring-tables/${id}/delete-preview`,
    deletePath: (id: string) => `/api/scoring-tables/${id}`,
    done: (name: string) => `Tabela "${name}" excluída.`,
    gone: (name: string) => `A tabela "${name}" já tinha sido excluída.`,
  },
} as const;

/**
 * GTAB-30, GTAB-16, GTAB-35: one dialog for a version and for a table. It loads the preview, shows what goes away
 * (or why it cannot go), says the deletion is final and asks once. A 404 means it is already gone.
 */
export function DeleteScoringDialog({
  target,
  onDeleted,
  onClose,
}: {
  target: DeleteTarget;
  /** The deletion happened (or had already happened): the page closes the dialog, reloads and announces. */
  onDeleted: (message: string) => void;
  onClose: () => void;
}) {
  const text = TEXT[target.kind];
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    request<Preview>("GET", text.previewPath(target.id))
      .then((value) => live && setPreview(value))
      .catch((err) => live && setError(errorMessage(err)));
    return () => {
      live = false;
    };
  }, [target.id, text]);

  async function confirm() {
    setError(null);
    setBusy(true);
    try {
      await request<void>("DELETE", text.deletePath(target.id));
      onDeleted(text.done(target.name));
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        onDeleted(text.gone(target.name));
        return;
      }
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  const blocked = preview !== null && preview.blocked.length > 0;
  return (
    <Modal title={text.title} onClose={onClose}>
      <p>{text.ask(target.name)}</p>
      {preview ? (
        <ul aria-label="O que será apagado">
          <li>
            {target.kind === "version" ? "Versão" : "Tabela"}: {preview.name}
          </li>
          {preview.versions !== undefined && <li>{count(preview.versions, "versão", "versões")}</li>}
          <li>{count(preview.criteria, "critério", "critérios")}</li>
          {preview.units !== undefined && (
            <li>
              {preview.units.length > 0
                ? `Unidades associadas: ${preview.units
                    .map((u) => u.acronym)
                    .sort()
                    .join(", ")}`
                : "Nenhuma unidade associada"}
            </li>
          )}
        </ul>
      ) : (
        !error && <p className="muted">Carregando…</p>
      )}
      {blocked && (
        <ul aria-label="Por que não pode ser excluída" className="error">
          {preview.blocked.map((b) => (
            <li key={b.code}>{blockReasonText(b.code, { processCount: b.count ?? undefined, acronyms: b.acronyms })}</li>
          ))}
        </ul>
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
          disabled={busy || preview === null || blocked}
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
