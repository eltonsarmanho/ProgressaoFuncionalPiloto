import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { DocumentKind, GeneratedDocument } from "../api/generated";
import { generationErrorMessage, isConflict } from "../generationErrors";
import { usePolling } from "../hooks/usePolling";
import { DOCUMENT_KIND_LABELS, GENERATION_CODE_LABELS, GENERATION_STATE_LABELS, alertText, formatDay, formatSize } from "../labels";

/**
 * UIG-01, UIG-04, UIG-05, UIG-06, VER-09: the block of one generated document. The warning of the
 * activities that stay out comes before the button; while a generation runs the block asks the
 * server every 3 s until it is PRONTO or FALHOU; every ready version stays in the history with a link
 * and the size of each format.
 *
 * `leftOut` is the number of activities that will not enter the document; `disabledReason` turns the
 * button off with the reason shown (a concluded process cannot generate the Comprovante).
 */
export function GeneratedBlock({
  processId,
  kind,
  leftOut = 0,
  disabledReason,
}: {
  processId: string;
  kind: DocumentKind;
  leftOut?: number;
  disabledReason?: string;
}) {
  const [rows, setRows] = useState<GeneratedDocument[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const reload = () => setReloads((n) => n + 1);

  useEffect(() => {
    let cancelled = false;
    request<GeneratedDocument[]>("GET", `/api/processes/${processId}/generated-documents?kind=${kind}`)
      .then((found) => {
        if (!cancelled) setRows(found);
      })
      .catch((err) => {
        if (!cancelled) setError(generationErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [processId, kind, reloads]);

  const running = rows?.some((r) => r.state === "GERANDO") ?? false;
  usePolling(reload, running);

  async function generate() {
    setError(null);
    try {
      await request("POST", `/api/processes/${processId}/generated-documents`, { kind });
    } catch (err) {
      setError(generationErrorMessage(err));
      if (!isConflict(err)) return;
    }
    reload();
  }

  const label = DOCUMENT_KIND_LABELS[kind];
  const latest = rows?.[0];
  const ready = (rows ?? []).filter((r) => r.state === "PRONTO");
  const headingId = `generated-${kind}`;

  return (
    <section className="card generated-block" aria-labelledby={headingId}>
      <h2 id={headingId}>{label}</h2>
      {leftOut > 0 && (
        <p className="doc-warning sev-ALERTA">
          {leftOut === 1 ? "1 atividade fica" : `${leftOut} atividades ficam`} de fora: só entram as validadas, com grupo e
          item.
        </p>
      )}
      <div className="btn-row">
        <button
          type="button"
          className="btn btn-primary"
          aria-label={latest?.state === "FALHOU" ? `Tentar de novo gerar ${label}` : `Gerar ${label}`}
          disabled={running || Boolean(disabledReason) || rows === null}
          onClick={() => void generate()}
        >
          {latest?.state === "FALHOU" ? "Tentar de novo" : "Gerar"}
        </button>
      </div>
      {disabledReason && <p className="muted">{disabledReason}</p>}
      {running && <p role="status">{GENERATION_STATE_LABELS.GERANDO}…</p>}
      {latest?.state === "FALHOU" && (
        <p role="alert" className="error">
          A geração falhou: {(latest.error_code && GENERATION_CODE_LABELS[latest.error_code]) ?? "tente de novo."}
        </p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {ready[0] && ready[0].alerts.length > 0 && (
        <ul aria-label="Alertas da geração" className="generation-alerts">
          {ready[0].alerts.map((alert, i) => (
            <li key={`${alert.code}-${i}`} className="sev-ALERTA">
              {alertText(alert)}
              {alert.message && alert.code !== "REDACAO_REJEITADA" && <small className="muted">{`: ${alert.message}`}</small>}
            </li>
          ))}
        </ul>
      )}
      {rows !== null && ready.length === 0 && !running && <p className="muted">Nenhuma versão gerada ainda.</p>}
      {ready.length > 0 && (
        <ul aria-label="Versões geradas" className="generation-history">
          {ready.map((row) => (
            <li key={row.id}>
              <strong>Versão {row.version_number}</strong>
              {row.finished_at && <small className="muted">{` · ${formatDay(row.finished_at)}`}</small>}
              <span className="row-actions">
                {row.files.map((file) => (
                  <a
                    key={file.format}
                    href={`/api/generated-documents/${row.id}/files/${file.format.toLowerCase()}`}
                    aria-label={`Baixar ${label} versão ${row.version_number} em ${file.format}`}
                  >
                    {`${file.format} (${formatSize(file.size_bytes)})`}
                  </a>
                ))}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
