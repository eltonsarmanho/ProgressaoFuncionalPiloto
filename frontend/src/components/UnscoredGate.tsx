import { useEffect, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router";
import { request } from "../api/client";
import type { Process, ScoringResult } from "../api/types";
import { countUnscored } from "../unscored";
import { STEP_BLOCKED_ID, StepNav } from "./StepNav";

function message(count: number): string {
  return count === 1
    ? "Há 1 atividade não pontuada na Etapa 4. Valide ou rejeite essa atividade para abrir esta etapa."
    : `Há ${count} atividades não pontuadas na Etapa 4. Valide ou rejeite essas atividades para abrir esta etapa.`;
}

/**
 * The Etapas 5 to 7 stay closed, even by the address, while the process has an activity that is not
 * scored. A concluded or archived process is read only and is never closed. When the check itself
 * fails the step opens: the server still refuses what cannot be generated.
 */
export function UnscoredGate({ step, title, children }: { step: number; title: string; children: ReactNode }) {
  const { id = "" } = useParams();
  const [state, setState] = useState<{ id: string; unscored: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const process = await request<Process>("GET", `/api/processes/${id}`);
      if (process.status === "CONCLUIDO" || process.status === "ARQUIVADO") return 0;
      const scoring = await request<ScoringResult>("GET", `/api/processes/${id}/scoring`);
      return countUnscored(scoring.rows);
    })()
      .catch(() => 0)
      .then((unscored) => {
        if (!cancelled) setState({ id, unscored });
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (state?.id !== id) return null;
  if (state.unscored === 0) return <>{children}</>;
  return (
    <>
      <StepNav current={step} processId={id} blocked={{ step: 4, message: message(state.unscored) }} />
      <h1>{`Etapa ${step} · ${title}`}</h1>
      <p role="alert" className="error" aria-describedby={STEP_BLOCKED_ID}>
        {message(state.unscored)}
      </p>
      <p>
        <Link to={`/processos/${id}/pontuacao`}>Voltar à Etapa 4 · Pontuação</Link>
      </p>
    </>
  );
}
