import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { errorMessage, request } from "../api/client";
import type { Activity, DocumentSummary, ScoringGroup, ScoringResult, ScoringVersion, TableChoice } from "../api/types";
import { ActivityReviewList } from "../components/ActivityReviewList";
import { StepNav } from "../components/StepNav";

type Loaded = {
  activities: Activity[];
  result: ScoringResult | null;
  documents: DocumentSummary[];
  groups: ScoringGroup[];
};

async function load(id: string): Promise<Loaded> {
  const [activities, documents, table] = await Promise.all([
    request<Activity[]>("GET", `/api/processes/${id}/activities`),
    request<DocumentSummary[]>("GET", `/api/processes/${id}/documents`),
    request<TableChoice>("GET", `/api/processes/${id}/scoring/table`),
  ]);
  // The potential score and the criteria are extras of the review: without them the list still works.
  const result = await request<ScoringResult>("GET", `/api/processes/${id}/scoring`).catch(() => null);
  const versionId = table.chosen?.version.id ?? table.suggested?.version.id;
  const version = versionId
    ? await request<ScoringVersion>("GET", `/api/scoring-versions/${versionId}`).catch(() => null)
    : null;
  return { activities, result, documents, groups: version?.groups ?? [] };
}

/** Etapa 3: review of the activities (human validation), their documents and the batch validation. */
export function ProcessActivities() {
  const { id = "" } = useParams();
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let cancelled = false;
    load(id)
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

  return (
    <>
      <StepNav current={3} processId={id} />
      <h1>Etapa 3 · Atividades</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {data && (
        <div className="card">
          <ActivityReviewList
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
        <Link to={`/processos/${id}/pontuacao`}>Ir para a Etapa 4 · Pontuação</Link>
      </p>
    </>
  );
}
