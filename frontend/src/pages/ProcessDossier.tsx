import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { getBoard, saveCity, type BoardView, type RequestSettings } from "../api/board";
import { errorMessage, request } from "../api/client";
import type { Process } from "../api/types";
import { boardFailure } from "../boardErrors";
import { ConcludeDialog } from "../components/ConcludeDialog";
import { DossierChecklist } from "../components/DossierChecklist";
import { FieldError } from "../components/FieldError";
import { GeneratedBlock } from "../components/GeneratedBlock";
import { StepNav } from "../components/StepNav";
import { GENERATION_CODE_LABELS, STATUS_LABELS } from "../labels";

/** REQ-05, REQ-06: the city of the line "<cidade>, <data>." of the Requerimento; empty leaves the blank line. */
function CityField({
  processId,
  settings,
  readOnly,
  readOnlyReason,
  onChanged,
  onStale,
}: {
  processId: string;
  settings: RequestSettings;
  readOnly: boolean;
  readOnlyReason?: string;
  onChanged: (next: RequestSettings) => void;
  onStale: () => void;
}) {
  const [city, setCity] = useState(settings.city ?? "");
  const [seen, setSeen] = useState(settings.version);
  if (seen !== settings.version) {
    setSeen(settings.version);
    setCity(settings.city ?? "");
  }
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function save() {
    setErrors({});
    setMessage(null);
    setBusy(true);
    try {
      onChanged(await saveCity(processId, city.trim() || null, settings.version));
    } catch (err) {
      const failure = boardFailure(err);
      setErrors(failure.fields);
      setMessage(failure.message);
      if (failure.stale) onStale();
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-labelledby="dossier-city-title">
      <h2 id="dossier-city-title">Cidade do Requerimento</h2>
      <p className="muted">A cidade vai na linha de local e data do fim do Requerimento. Sem cidade, a linha fica em branco.</p>
      {readOnly && readOnlyReason && <p className="muted">{readOnlyReason}</p>}
      <div className="field">
        <label htmlFor="dossier-city">Cidade</label>
        <input
          id="dossier-city"
          type="text"
          value={city}
          disabled={readOnly || busy}
          aria-invalid={errors.city ? true : undefined}
          aria-describedby={errors.city ? "dossier-city-error" : undefined}
          onChange={(event) => setCity(event.target.value)}
        />
        <FieldError id="dossier-city-error" message={errors.city} />
      </div>
      {message && (
        <p role="alert" className="error">
          {message}
        </p>
      )}
      <div className="btn-row">
        <button type="button" className="btn btn-primary" disabled={readOnly || busy} onClick={() => void save()}>
          Salvar cidade
        </button>
      </div>
    </section>
  );
}

/**
 * Etapa 7: the city and the generated Requerimento, the checklist of the dossier and the conclusion of
 * the process (moved here from the Etapa 5). The checklist is read again when the Requerimento becomes
 * ready. A concluded or archived process is read only: the city, the generation and the marks are off
 * with the reason, and the versions already generated can still be downloaded (BNAV-02).
 */
export function ProcessDossier() {
  const { id = "" } = useParams();
  const [process, setProcess] = useState<Process | null>(null);
  const [board, setBoard] = useState<BoardView | null>(null);
  const [concluding, setConcluding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const [boardReloads, setBoardReloads] = useState(0);
  const [checklistKey, setChecklistKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    request<Process>("GET", `/api/processes/${id}`)
      .then((found) => {
        if (!cancelled) setProcess(found);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloads]);

  useEffect(() => {
    let cancelled = false;
    getBoard(id)
      .then((found) => {
        if (!cancelled) setBoard(found);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, boardReloads]);

  const readOnly = process !== null && (process.status === "CONCLUIDO" || process.status === "ARQUIVADO");
  const readOnlyReason = readOnly ? GENERATION_CODE_LABELS.PROCESSO_SOMENTE_LEITURA : undefined;

  return (
    <>
      <StepNav current={7} processId={id} />
      <h1>Etapa 7 · Requerimento e dossiê</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {process && readOnly && (
        <p className="review-summary">
          Processo {STATUS_LABELS[process.status].toLowerCase()}: a cidade, o Requerimento e as marcas do dossiê só podem ser
          lidos.
        </p>
      )}
      {process && (
        <>
          {board && (
            <CityField
              processId={id}
              settings={board.request_settings}
              readOnly={readOnly}
              readOnlyReason={readOnlyReason}
              onChanged={(request_settings) => setBoard((all) => (all ? { ...all, request_settings } : all))}
              onStale={() => setBoardReloads((n) => n + 1)}
            />
          )}
          <GeneratedBlock
            processId={id}
            kind="REQUERIMENTO"
            disabledReason={readOnlyReason}
            onReady={() => setChecklistKey((n) => n + 1)}
          />
          <DossierChecklist processId={id} readOnly={readOnly} readOnlyReason={readOnlyReason} refreshKey={checklistKey} />
          {process.status === "EM_ANDAMENTO" && (
            <section className="card" aria-labelledby="conclude-title">
              <h2 id="conclude-title">Concluir o processo</h2>
              <p className="muted">
                Depois de gerar a Tabela, o Relatório e o Comprovante, conclua o processo para excluir do servidor os
                documentos de entrada. Os documentos gerados e o histórico ficam.
              </p>
              <div className="btn-row">
                <button type="button" className="btn btn-danger" onClick={() => setConcluding(true)}>
                  Concluir e excluir documentos de entrada
                </button>
              </div>
            </section>
          )}
          {process.status === "RASCUNHO" && (
            <section className="card" aria-labelledby="conclude-title">
              <h2 id="conclude-title">Concluir o processo</h2>
              <p className="muted">Inicie o processo na Etapa 1 para poder concluir.</p>
              <div className="btn-row">
                <Link className="btn btn-secondary" to={`/processos/${id}`}>
                  Ir para a Etapa 1
                </Link>
              </div>
            </section>
          )}
          {concluding && (
            <ConcludeDialog
              processId={id}
              processVersion={process.version}
              onChanged={() => setReloads((n) => n + 1)}
              onClose={() => setConcluding(false)}
            />
          )}
        </>
      )}
    </>
  );
}
