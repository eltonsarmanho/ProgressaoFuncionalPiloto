import { useEffect, useState, type FormEvent } from "react";
import { useParams } from "react-router";
import { errorMessage, fieldErrors, request } from "../api/client";
import type {
  Activity,
  Alert,
  ScoringRow,
  ScoringResult,
  ScoringTableInfo,
  ScoringVersion,
  TableChoice,
} from "../api/types";
import { ActivityForm } from "../components/ActivityForm";
import { AlertList } from "../components/AlertList";
import { FieldError, errorProps } from "../components/FieldError";
import { ScoringSummary } from "../components/ScoringSummary";
import { ScoringTable } from "../components/ScoringTable";
import { StepNav } from "../components/StepNav";
import { TablePicker } from "../components/TablePicker";

type Pending =
  | { kind: "new" }
  | { kind: "edit"; activity: Activity }
  | { kind: "validate" | "reject" | "distinct"; activity: Activity };

const ACTION_TITLES = {
  validate: "Validar atividade",
  reject: "Rejeitar atividade",
  distinct: "Marcar como distinta",
} as const;

function JustifiedAction({
  kind,
  activity,
  onDone,
  onCancel,
}: {
  kind: "validate" | "reject" | "distinct";
  activity: Activity;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [justificativa, setJustificativa] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (justificativa.trim() === "") {
      setErrors({ justificativa: "Informe a justificativa." });
      return;
    }
    setErrors({});
    const base = { expected_version: activity.version, justificativa: justificativa.trim() };
    try {
      if (kind === "distinct") {
        await request("POST", `/api/activities/${activity.id}/distinct`, base);
      } else {
        await request("POST", `/api/activities/${activity.id}/status`, {
          ...base,
          status: kind === "validate" ? "VALIDADA" : "REJEITADA",
        });
      }
      onDone();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    }
  }

  return (
    <form className="card" onSubmit={submit} noValidate aria-label={ACTION_TITLES[kind]}>
      <h2>
        {ACTION_TITLES[kind]}: {activity.title}
      </h2>
      <div className="field">
        <label htmlFor="action-justificativa">Justificativa</label>
        <textarea
          id="action-justificativa"
          rows={2}
          value={justificativa}
          onChange={(e) => setJustificativa(e.target.value)}
          {...errorProps("justificativa", errors)}
          aria-describedby={errors.justificativa ? "justificativa-error" : undefined}
        />
        <FieldError id="justificativa-error" message={errors.justificativa} />
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button type="submit">Confirmar</button>
      <button type="button" className="link" onClick={onCancel}>
        Cancelar
      </button>
    </form>
  );
}

/** Etapa 4: loads the table choice, the result and the criteria; reloads after every change. */
export function ProcessScoring() {
  const { id = "" } = useParams();
  const [choice, setChoice] = useState<TableChoice | null>(null);
  const [result, setResult] = useState<ScoringResult | null>(null);
  const [version, setVersion] = useState<ScoringVersion | null>(null);
  const [tables, setTables] = useState<ScoringTableInfo[]>([]);
  const [pending, setPending] = useState<Pending | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const table = await request<TableChoice>("GET", `/api/processes/${id}/scoring/table`);
      const scoring = await request<ScoringResult>("GET", `/api/processes/${id}/scoring`);
      const versionId = table.chosen?.version.id ?? table.suggested?.version.id;
      const criteria = versionId ? await request<ScoringVersion>("GET", `/api/scoring-versions/${versionId}`) : null;
      return { table, scoring, criteria };
    })()
      .then(({ table, scoring, criteria }) => {
        if (cancelled) return;
        setChoice(table);
        setResult(scoring);
        setVersion(criteria);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(errorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloads]);

  useEffect(() => {
    request<ScoringTableInfo[]>("GET", "/api/scoring-tables")
      .then((all) => setTables(all.filter((t) => !t.archived)))
      .catch(() => setTables([]));
  }, []);

  async function open(kind: "edit" | "validate" | "reject" | "distinct", row: ScoringRow) {
    try {
      const activity = await request<Activity>("GET", `/api/activities/${row.activity_id}`);
      setPending({ kind, activity });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const done = () => {
    setPending(null);
    setReloads((n) => n + 1);
  };

  const groupNames = version ? Object.fromEntries(version.groups.map((g) => [g.number, g.name])) : undefined;
  const groupOne = version?.groups.find((g) => g.number === 1);
  // PIT hours only where group I is outside the total and has a weekly-load criterion (PIT-02/03).
  const group1InHours = groupOne
    ? !groupOne.counts_in_total && groupOne.criteria.some((c) => c.mode === "CARGA_SEMANAL")
    : undefined;

  const alerts: Alert[] = [];
  const seen = new Set<string>();
  const add = (a: Alert, prefix = "") => {
    const message = prefix + a.message;
    const key = `${a.code}|${message}`;
    if (seen.has(key)) return;
    seen.add(key);
    alerts.push({ ...a, message });
  };
  choice?.alerts.forEach((a) => add(a));
  result?.alerts.forEach((a) => add(a));
  result?.rows.forEach((r) => r.alerts.forEach((a) => add(a, `${r.title}: `)));

  return (
    <>
      <StepNav current={4} processId={id} />
      <h1>Etapa 4 · Pontuação</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {choice && <TablePicker processId={id} choice={choice} tables={tables} onChanged={done} />}

      {result && (
        <>
          <section className="card" aria-labelledby="summary-title">
            <h2 id="summary-title">Resumo</h2>
            <ScoringSummary result={result} groupNames={groupNames} group1InHours={group1InHours} />
          </section>

          <section className="card" aria-labelledby="activities-title">
            <h2 id="activities-title">Atividades</h2>
            <ScoringTable
              rows={result.rows}
              subtotals={result.subtotals}
              groupNames={groupNames}
              group1TotalHours={result.group1_total_hours}
              actions={(row) => (
                <div className="row-actions">
                  <button type="button" className="link" onClick={() => void open("edit", row)}>
                    Editar {row.title}
                  </button>
                  <button type="button" className="link" onClick={() => void open("validate", row)}>
                    Validar {row.title}
                  </button>
                  <button type="button" className="link" onClick={() => void open("reject", row)}>
                    Rejeitar {row.title}
                  </button>
                  <button type="button" className="link" onClick={() => void open("distinct", row)}>
                    Marcar como distinta {row.title}
                  </button>
                </div>
              )}
            />
            {!pending && (
              <button type="button" onClick={() => setPending({ kind: "new" })}>
                Nova atividade
              </button>
            )}
          </section>

          <section className="card" aria-labelledby="alerts-title">
            <h2 id="alerts-title">Alertas da pontuação</h2>
            <AlertList alerts={alerts} />
          </section>
        </>
      )}

      {pending?.kind === "new" && (
        <ActivityForm processId={id} groups={version?.groups ?? []} onSaved={done} onCancel={() => setPending(null)} />
      )}
      {pending?.kind === "edit" && (
        <ActivityForm
          key={pending.activity.id}
          processId={id}
          groups={version?.groups ?? []}
          activity={pending.activity}
          onSaved={done}
          onCancel={() => setPending(null)}
        />
      )}
      {pending && pending.kind !== "new" && pending.kind !== "edit" && (
        <JustifiedAction
          key={`${pending.kind}-${pending.activity.id}`}
          kind={pending.kind}
          activity={pending.activity}
          onDone={done}
          onCancel={() => setPending(null)}
        />
      )}
    </>
  );
}
