import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { ConclusionPreview, ConclusionResult } from "../api/generated";
import { DOCUMENT_KINDS } from "../api/generated";
import { errorCode, generationErrorMessage } from "../generationErrors";
import { DOCUMENT_KIND_LABELS, GENERATION_ALERT_LABELS, formatSize } from "../labels";
import { Modal } from "./Modal";

const plural = (n: number, one: string, many: string) => (n === 1 ? `1 ${one}` : `${n} ${many}`);
const space = (bytes: number) => (bytes === 0 ? "0 KB" : formatSize(bytes));

/**
 * UIG-09, DEL-01, DEL-03, DEL-04, DEL-08: "Concluir e excluir documentos de entrada". The dialog reads the
 * preview, lists the generated documents that are still missing (the button stays off), says what is
 * deleted and that it cannot be undone, and only sends `confirmar: true` after the user ticks the
 * confirmation. A partial deletion keeps the process open and offers to try again. There is no
 * justification field. `onChanged` tells the page to reload the process (it concluded, or its version moved).
 */
export function ConcludeDialog({
  processId,
  processVersion,
  onChanged,
  onClose,
}: {
  processId: string;
  processVersion: number;
  onChanged: () => void;
  onClose: () => void;
}) {
  const [preview, setPreview] = useState<ConclusionPreview | null>(null);
  const [result, setResult] = useState<ConclusionResult | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let cancelled = false;
    request<ConclusionPreview>("GET", `/api/processes/${processId}/conclusion`)
      .then((found) => {
        if (!cancelled) setPreview(found);
      })
      .catch((err) => {
        if (!cancelled) setError(generationErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [processId, reloads]);

  const missing = preview ? DOCUMENT_KINDS.filter((kind) => !preview.artifacts[kind]) : [];
  const concluded = result?.status === "CONCLUIDO";
  const partial = result !== null && !concluded;

  async function conclude() {
    setError(null);
    setBusy(true);
    try {
      const done = await request<ConclusionResult>("POST", `/api/processes/${processId}/conclusion`, {
        expected_version: processVersion,
        confirmar: true,
      });
      setResult(done);
      if (done.status === "CONCLUIDO") onChanged();
      else setReloads((n) => n + 1);
    } catch (err) {
      setError(generationErrorMessage(err));
      if (errorCode(err) === "VERSAO_DESATUALIZADA") onChanged(); // the version of the process moved: reload it
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title="Concluir e excluir documentos de entrada" onClose={onClose}>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {concluded && result && (
        <>
          <p role="status">Processo concluído.</p>
          <p>
            {plural(result.arquivos_removidos, "arquivo excluído", "arquivos excluídos")}, {space(result.bytes_liberados)} liberados.
          </p>
          <p className="muted">O processo agora é somente leitura. Os documentos gerados e o histórico continuam disponíveis.</p>
          <div className="btn-row">
            <button type="button" className="btn btn-primary" onClick={onClose}>
              Fechar
            </button>
          </div>
        </>
      )}
      {!concluded && preview && (
        <>
          <p>
            Ao concluir, o processo vira somente leitura e os arquivos dos documentos de entrada saem do servidor,
            junto com o texto extraído de cada página. As atividades, a pontuação e os documentos gerados ficam.
          </p>
          <p>
            <strong>
              {preview.files === 1
                ? `1 arquivo, ${space(preview.bytes)} será excluído de forma irreversível.`
                : `${preview.files} arquivos, ${space(preview.bytes)} serão excluídos de forma irreversível.`}
            </strong>
          </p>
          {partial && result && (
            <>
              <p role="alert" className="error">
                {GENERATION_ALERT_LABELS.EXCLUSAO_PARCIAL}
              </p>
              <p>
                {plural(result.arquivos_removidos, "arquivo excluído", "arquivos excluídos")},{" "}
                {plural(result.arquivos_pendentes, "arquivo ainda por excluir", "arquivos ainda por excluir")}.
              </p>
            </>
          )}
          {missing.length > 0 && (
            <p className="doc-warning sev-ALERTA">
              Falta gerar: {missing.map((kind) => DOCUMENT_KIND_LABELS[kind]).join(", ")}.
            </p>
          )}
          <label className="check-head" htmlFor="conclude-confirm">
            <input
              id="conclude-confirm"
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            Confirmo a exclusão irreversível dos documentos de entrada
          </label>
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-danger"
              disabled={!confirmed || missing.length > 0 || busy}
              onClick={() => void conclude()}
            >
              {partial ? "Tentar de novo" : "Concluir e excluir"}
            </button>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancelar
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
