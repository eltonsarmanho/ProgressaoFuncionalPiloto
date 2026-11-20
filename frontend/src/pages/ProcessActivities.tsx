import { useEffect, useRef, useState, type RefObject } from "react";
import { Link, useParams } from "react-router";
import { isValid, validityOf } from "../activityList";
import { errorMessage, request } from "../api/client";
import type { Activity, DocumentSummary, Process, ScoringGroup, ScoringResult, ScoringVersion, TableChoice } from "../api/types";
import { ActivityWorkspace } from "../components/ActivityWorkspace";
import { STEP_BLOCKED_ID, StepNav } from "../components/StepNav";
import { needsCategoryMessage } from "../labels";

type Loaded = {
  activities: Activity[];
  result: ScoringResult | null;
  documents: DocumentSummary[];
  groups: ScoringGroup[];
};

type Preparation = { id: string; done: Promise<void> };

/**
 * DUP-04: the merge of the duplicates runs once each time the page opens, before the first load of
 * the list, and never in a reload after a write. A read-only process is not merged; a failure of
 * the merge (or of reading the process) leaves the list as it is: the review still opens.
 */
function prepare(id: string, cache: RefObject<Preparation | null>): Promise<void> {
  if (cache.current?.id === id) return cache.current.done;
  const done = (async () => {
    const process = await request<Process>("GET", `/api/processes/${id}`).catch(() => null);
    if (process?.status === "CONCLUIDO" || process?.status === "ARQUIVADO") return;
    await request("POST", `/api/processes/${id}/activities/merge-duplicates`).catch(() => null);
  })();
  cache.current = { id, done };
  return done;
}

async function load(id: string): Promise<Loaded> {
  const [activities, documents, table] = await Promise.all([
    request<Activity[]>("GET", `/api/processes/${id}/activities`),
    request<DocumentSummary[]>("GET", `/api/processes/${id}/documents`),
    request<TableChoice>("GET", `/api/processes/${id}/scoring/table`),
  ]);
  // The scoring rows and the criteria are extras of the review: without them the list still works.
  const result = await request<ScoringResult>("GET", `/api/processes/${id}/scoring`).catch(() => null);
  const versionId = table.chosen?.version.id ?? table.suggested?.version.id;
  const version = versionId
    ? await request<ScoringVersion>("GET", `/api/scoring-versions/${versionId}`).catch(() => null)
    : null;
  return { activities, result, documents, groups: version?.groups ?? [] };
}

/**
 * Etapa 3: review of the activities in two sections (valid and not valid), with the batch
 * validation and the documents. The way to Etapa 4 stays closed while a valid activity lacks its
 * category (SEC-05), but only when there is a table to choose the category from: without one the
 * way stays open and the page tells the user to choose the table in Etapa 4, where it is chosen.
 */
export function ProcessActivities() {
  const { id = "" } = useParams();
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);
  const preparation = useRef<Preparation | null>(null);

  useEffect(() => {
    let cancelled = false;
    prepare(id, preparation)
      .then(() => load(id))
      .then((loaded) => {
        if (cancelled) return;
        setData(loaded);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloads]);

  const hasTable = data != null && data.groups.length > 0;
  const missing = hasTable ? data.activities.filter((a) => isValid(a) && validityOf(a).needs_category).length : 0;

  return (
    <>
      <StepNav
        current={3}
        processId={id}
        blocked={missing > 0 ? { step: 3, message: needsCategoryMessage(missing) } : undefined}
      />
      <h1>Etapa 3 · Atividades</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {data && !hasTable && (
        <p className="review-note">
          Nenhuma tabela de pontuação foi escolhida, por isso as categorias ainda não podem ser definidas.{" "}
          <Link to={`/processos/${id}/pontuacao`}>Escolher a tabela na Etapa 4</Link>
        </p>
      )}
      {data && (
        <div className="card">
          <ActivityWorkspace
            processId={id}
            activities={data.activities}
            rows={data.result?.rows ?? []}
            groups={data.groups}
            documents={data.documents}
            onChanged={() => setReloads((n) => n + 1)}
          />
        </div>
      )}
      <p>
        {missing > 0 ? (
          <span aria-disabled="true" aria-describedby={STEP_BLOCKED_ID} className="muted">
            Ir para a Etapa 4 · Pontuação
          </span>
        ) : (
          <Link to={`/processos/${id}/pontuacao`}>Ir para a Etapa 4 · Pontuação</Link>
        )}
      </p>
    </>
  );
}
