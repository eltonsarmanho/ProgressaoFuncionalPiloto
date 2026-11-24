import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { getBoard, type BoardView, type Opinion, type Ordinance } from "../api/board";
import { errorMessage, request } from "../api/client";
import type { Process } from "../api/types";
import { GeneratedBlock } from "../components/GeneratedBlock";
import { OpinionForm } from "../components/OpinionForm";
import { OrdinanceForm } from "../components/OrdinanceForm";
import { StepNav } from "../components/StepNav";
import { usePolling } from "../hooks/usePolling";
import { GENERATION_CODE_LABELS, STATUS_LABELS } from "../labels";

/**
 * Etapa 6: the ordinance of the board, the fields of the Parecer and the generated Parecer. While the
 * reading of the ordinance is queued or running the page asks the server every 3 s until it ends
 * (PORT-02, PORT-07). A concluded or archived process is read only: the buttons are off with the
 * reason, and the versions already generated can still be downloaded (BNAV-02).
 */
export function ProcessBoard() {
  const { id = "" } = useParams();
  const [process, setProcess] = useState<Process | null>(null);
  const [board, setBoard] = useState<BoardView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const reload = () => setReloads((n) => n + 1);

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
  }, [id]);

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
  }, [id, reloads]);

  const state = board?.ordinance.reading_state;
  usePolling(reload, state === "PENDENTE" || state === "LENDO");

  const readOnly = process !== null && (process.status === "CONCLUIDO" || process.status === "ARQUIVADO");
  const readOnlyReason = readOnly ? GENERATION_CODE_LABELS.PROCESSO_SOMENTE_LEITURA : undefined;
  const setOrdinance = (ordinance: Ordinance) => setBoard((all) => (all ? { ...all, ordinance } : all));
  const setOpinion = (opinion: Opinion) => setBoard((all) => (all ? { ...all, opinion } : all));

  return (
    <>
      <StepNav current={6} processId={id} />
      <h1>Etapa 6 · Banca e Parecer</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {process && readOnly && (
        <p className="review-summary">
          Processo {STATUS_LABELS[process.status].toLowerCase()}: a portaria e a minuta do Parecer só podem ser lidas.
        </p>
      )}
      {process && board && (
        <>
          <section className="card" aria-labelledby="board-ordinance-title">
            <h2 id="board-ordinance-title">Portaria da banca</h2>
            <OrdinanceForm
              processId={id}
              ordinance={board.ordinance}
              readOnly={readOnly}
              readOnlyReason={readOnlyReason}
              onChanged={setOrdinance}
              onStale={reload}
            />
          </section>
          <section className="card" aria-labelledby="board-opinion-title">
            <h2 id="board-opinion-title">Minuta do Parecer</h2>
            <OpinionForm
              processId={id}
              opinion={board.opinion}
              readOnly={readOnly}
              readOnlyReason={readOnlyReason}
              onChanged={setOpinion}
              onStale={reload}
            />
          </section>
          <GeneratedBlock processId={id} kind="PARECER" disabledReason={readOnlyReason} />
        </>
      )}
    </>
  );
}
