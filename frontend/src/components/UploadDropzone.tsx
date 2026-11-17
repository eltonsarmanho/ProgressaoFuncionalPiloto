import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router";
import { errorMessage, request } from "../api/client";
import type { UploadResult } from "../api/types";

const ACCEPT = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

const CREATED = 201;
const DUPLICATE = 409;
const RATE_LIMITED = 429;

function reason(result: UploadResult): string {
  if (result.status_code === CREATED) return "Enviado. Aguardando processamento.";
  if (result.status_code === DUPLICATE) return result.message ?? "Este arquivo já foi enviado neste processo.";
  if (result.status_code === RATE_LIMITED) {
    return result.message ?? "Muitos envios em pouco tempo. Aguarde um minuto e envie de novo.";
  }
  return result.message ?? "Arquivo recusado.";
}

/**
 * TELA-02 / TELA-05: drag and drop or file picker, several files per request. The outcome of each
 * file (201, 409, 422, 429) is shown beside its name and never blocks the others.
 */
export function UploadDropzone({ processId, onUploaded }: { processId: string; onUploaded: () => void }) {
  const [results, setResults] = useState<UploadResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const picker = useRef<HTMLInputElement>(null);

  async function send(files: File[]) {
    if (files.length === 0) return;
    const form = new FormData();
    files.forEach((file) => form.append("file", file));
    setBusy(true);
    setError(null);
    try {
      const outcome = await request<UploadResult[]>("POST", `/api/processes/${processId}/documents`, form);
      setResults(outcome);
      if (outcome.some((r) => r.status_code === CREATED)) onUploaded();
    } catch (err) {
      setResults([]);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    void send(Array.from(event.dataTransfer.files));
  }

  return (
    <section className="card" aria-labelledby="upload-title">
      <h2 id="upload-title">Enviar documentos</h2>
      <div
        className={`dropzone${dragging ? " dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        data-testid="dropzone"
      >
        <p>Arraste os arquivos até aqui ou escolha-os no computador.</p>
        <label htmlFor="upload-files">Selecionar arquivos (PDF, JPG ou PNG)</label>
        <input
          ref={picker}
          id="upload-files"
          type="file"
          multiple
          accept={ACCEPT}
          disabled={busy}
          onChange={(e) => {
            const chosen = Array.from(e.target.files ?? []);
            if (picker.current) picker.current.value = "";
            void send(chosen);
          }}
        />
        <p className="muted">Até 20 MB por arquivo. Cada arquivo é conferido separadamente.</p>
      </div>
      <div aria-live="polite">
        {busy && <p>Enviando…</p>}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        {results.length > 0 && (
          <ul className="upload-results" aria-label="Resultado do envio">
            {results.map((result, i) => (
              <li key={`${result.original_name}-${i}`} className={result.status_code === CREATED ? "ok" : "refused"}>
                <strong>{result.original_name}</strong>: {reason(result)}
                {result.status_code === DUPLICATE && result.existing_document_id && (
                  <>
                    {" "}
                    <Link to={`/processos/${processId}/documentos?documento=${result.existing_document_id}`}>
                      Ver o documento já enviado
                    </Link>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
