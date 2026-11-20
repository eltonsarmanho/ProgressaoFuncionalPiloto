import { useEffect, useState } from "react";
import { Link } from "react-router";
import { errorMessage, request } from "../api/client";
import type { ProcessStatus, ProcessSummary } from "../api/types";
import { ArchiveProcessDialog, DeleteProcessDialog, StartProcessDialog } from "../components/ProcessDialogs";
import { MODALITY_LABELS, SEVERITIES, SEVERITY_LABELS, STATUS_LABELS, formatDate } from "../labels";

const STATUSES = Object.keys(STATUS_LABELS) as ProcessStatus[];

export function Dashboard() {
  const [processes, setProcesses] = useState<ProcessSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState<ProcessSummary | null>(null);
  const [deleting, setDeleting] = useState<ProcessSummary | null>(null);
  const [starting, setStarting] = useState<ProcessSummary | null>(null);

  function load() {
    return request<ProcessSummary[]>("GET", "/api/processes")
      .then(setProcesses)
      .catch((err) => setError(errorMessage(err)));
  }

  useEffect(() => {
    void load();
  }, []);

  function archived(id: string, status: ProcessStatus, version: number) {
    setProcesses((list) => list?.map((p) => (p.id === id ? { ...p, status, version } : p)) ?? null);
    setArchiving(null);
  }

  function started(id: string, status: ProcessStatus, version: number) {
    setProcesses((list) => list?.map((p) => (p.id === id ? { ...p, status, version } : p)) ?? null);
    setStarting(null);
  }

  function deleted(id: string, alreadyGone: boolean) {
    setProcesses((list) => list?.filter((p) => p.id !== id) ?? null);
    setDeleting(null);
    if (alreadyGone) void load();
  }

  if (error) return <p role="alert" className="error">{error}</p>;
  if (!processes) return <p className="muted">Carregando…</p>;

  return (
    <>
      <div className="page-head">
        <h1>Painel</h1>
        <div className="actions">
          <Link to="/professores/novo">Cadastrar docente</Link>
          <Link to="/processos/novo">Novo processo</Link>
        </div>
      </div>

      <section aria-label="Totais">
        <dl className="totals">
          <div className="card">
            <dt>Total de processos</dt>
            <dd>{processes.length}</dd>
          </div>
          {STATUSES.map((status) => (
            <div className="card" key={status}>
              <dt>{STATUS_LABELS[status]}</dt>
              <dd>{processes.filter((p) => p.status === status).length}</dd>
            </div>
          ))}
        </dl>
      </section>

      <h2>Processos</h2>
      {processes.length === 0 ? (
        <p className="muted">Nenhum processo cadastrado.</p>
      ) : (
        <ul className="process-list">
          {processes.map((p) => (
            <li key={p.id} className="card" aria-label={p.professor_name}>
              <Link to={`/processos/${p.id}`}>{p.professor_name}</Link>
              <p>
                <span className="badge">{STATUS_LABELS[p.status]}</span>{" "}
                {MODALITY_LABELS[p.modality]} · {formatDate(p.start_date)} a{" "}
                {formatDate(p.end_date)} ({p.interstice.months} meses)
              </p>
              <ul className="counts">
                {SEVERITIES.map((s) => (
                  <li key={s} className={`sev-${s}`}>
                    {SEVERITY_LABELS[s]}: {p.alert_counts[s]}
                  </li>
                ))}
              </ul>
              <div className="btn-row">
                {p.status === "RASCUNHO" && (
                  <button
                    type="button"
                    className="btn btn-primary"
                    aria-label={`Iniciar processo de ${p.professor_name}`}
                    title={`Iniciar processo de ${p.professor_name}`}
                    onClick={() => setStarting(p)}
                  >
                    Iniciar
                  </button>
                )}
                {p.status !== "ARQUIVADO" && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    aria-label={`Arquivar processo de ${p.professor_name}`}
                    title={`Arquivar processo de ${p.professor_name}`}
                    onClick={() => setArchiving(p)}
                  >
                    Arquivar
                  </button>
                )}
                <button
                  type="button"
                  className="btn btn-danger"
                  aria-label={`Excluir processo de ${p.professor_name}`}
                  title={`Excluir processo de ${p.professor_name}`}
                  onClick={() => setDeleting(p)}
                >
                  Excluir
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {starting && (
        <StartProcessDialog
          processId={starting.id}
          version={starting.version}
          onStarted={(status, version) => started(starting.id, status, version)}
          onStale={() => void load()}
          onClose={() => setStarting(null)}
        />
      )}
      {archiving && (
        <ArchiveProcessDialog
          process={archiving}
          onArchived={(status, version) => archived(archiving.id, status, version)}
          onStale={() => void load()}
          onClose={() => setArchiving(null)}
        />
      )}
      {deleting && (
        <DeleteProcessDialog
          process={deleting}
          onDeleted={(alreadyGone) => deleted(deleting.id, alreadyGone)}
          onClose={() => setDeleting(null)}
        />
      )}
    </>
  );
}
