import { useEffect, useState } from "react";
import { Link } from "react-router";
import { errorMessage, request } from "../api/client";
import type { ProcessStatus, ProcessSummary } from "../api/types";
import { MODALITY_LABELS, SEVERITIES, SEVERITY_LABELS, STATUS_LABELS, formatDate } from "../labels";

const STATUSES = Object.keys(STATUS_LABELS) as ProcessStatus[];

export function Dashboard() {
  const [processes, setProcesses] = useState<ProcessSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    request<ProcessSummary[]>("GET", "/api/processes")
      .then(setProcesses)
      .catch((err) => setError(errorMessage(err)));
  }, []);

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
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
