import { useEffect, useState } from "react";
import { useParams } from "react-router";
import { errorMessage, request } from "../api/client";
import type {
  Activity,
  Alert,
  ScoringRow,
  ScoringResult,
  ScoringTableInfo,
  ScoringVersion,
  TableChoice,
} from "../api/types";
import { activityBody } from "../activityBody";
import { ActivityForm } from "../components/ActivityForm";
import { AlertList } from "../components/AlertList";
import { Modal } from "../components/Modal";
import { ScoreEditor } from "../components/ScoreEditor";
import { ScoringPanel } from "../components/ScoringPanel";
import { ScoringTable } from "../components/ScoringTable";
import { StepNav } from "../components/StepNav";
import { TablePicker } from "../components/TablePicker";

type Pending = { kind: "new" } | { kind: "edit" | "points"; activity: Activity; pit?: boolean };

const MANUAL_CODE = "VALOR_UNITARIO_MANUAL";

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

  /** Loads the activity (the row has no version) before the edit form or the points editor. */
  async function edit(kind: "edit" | "points", row: ScoringRow) {
    try {
      const activity = await request<Activity>("GET", `/api/activities/${row.activity_id}`);
      setPending({ kind, activity, pit: row.pit_hours != null });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  /** UIM-23: back to the table's unit value. */
  async function clearManualValue(row: ScoringRow) {
    setError(null);
    try {
      const activity = await request<Activity>("GET", `/api/activities/${row.activity_id}`);
      await request("PUT", `/api/activities/${activity.id}`, {
        ...activityBody(activity),
        unit_points_override: null,
        expected_version: activity.version,
      });
      done();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  /** UIM-20: validate, reject and keep-as-distinct act at once; no justification, no panel. */
  async function act(kind: "validate" | "reject" | "distinct", row: ScoringRow) {
    setError(null);
    try {
      const activity = await request<Activity>("GET", `/api/activities/${row.activity_id}`);
      if (kind === "distinct") {
        await request("POST", `/api/activities/${activity.id}/distinct`, { expected_version: activity.version });
      } else {
        await request("POST", `/api/activities/${activity.id}/status`, {
          status: kind === "validate" ? "VALIDADA" : "REJEITADA",
          expected_version: activity.version,
        });
      }
      done();
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
  // The PIT hours exist where group I has a weekly-load criterion; group I is outside the total only
  // in the old version (it does not count in the total).
  const group1Load = groupOne ? groupOne.criteria.some((c) => c.mode === "CARGA_SEMANAL") : undefined;
  const group1OutsideTotal = groupOne ? !groupOne.counts_in_total && group1Load === true : undefined;

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
            <ScoringPanel result={result} groupNames={groupNames} group1OutsideTotal={group1OutsideTotal} group1Load={group1Load} />
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
                  <button
                    type="button"
                    className="btn btn-secondary"
                    aria-label={`Editar ${row.title}`}
                    title={`Editar ${row.title}`}
                    onClick={() => void edit("edit", row)}
                  >
                    Editar
                  </button>
                  {(row.status === "PONTUADA" || row.status === "POTENCIAL") && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      aria-label={`Editar pontuação de ${row.title}`}
                      title={`Editar pontuação de ${row.title}`}
                      onClick={() => void edit("points", row)}
                    >
                      Editar pontuação
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn-primary"
                    aria-label={`Validar ${row.title}`}
                    title={`Validar ${row.title}`}
                    onClick={() => void act("validate", row)}
                  >
                    Validar
                  </button>
                  <button
                    type="button"
                    className="btn btn-danger"
                    aria-label={`Rejeitar ${row.title}`}
                    title={`Rejeitar ${row.title}`}
                    onClick={() => void act("reject", row)}
                  >
                    Rejeitar
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    aria-label={`Marcar como distinta ${row.title}`}
                    title={`Marcar como distinta ${row.title}`}
                    onClick={() => void act("distinct", row)}
                  >
                    Manter como distinta
                  </button>
                  {row.alerts.some((a) => a.code === MANUAL_CODE) && (
                    <>
                      <span className="badge badge-pending">Manual</span>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        aria-label={`Usar valor da tabela em ${row.title}`}
                        title={`Usar valor da tabela em ${row.title}`}
                        onClick={() => void clearManualValue(row)}
                      >
                        Usar valor da tabela
                      </button>
                    </>
                  )}
                </div>
              )}
            />
            <div className="btn-row">
              <button type="button" className="btn btn-primary" onClick={() => setPending({ kind: "new" })}>
                Nova atividade
              </button>
            </div>
          </section>

          <section className="card" aria-labelledby="alerts-title">
            <h2 id="alerts-title">Alertas da pontuação</h2>
            <AlertList alerts={alerts} />
          </section>
        </>
      )}

      {pending?.kind === "new" && (
        <Modal title="Nova atividade" onClose={() => setPending(null)}>
          <ActivityForm processId={id} groups={version?.groups ?? []} onSaved={done} onCancel={() => setPending(null)} />
        </Modal>
      )}
      {pending?.kind === "points" && (
        <Modal title="Editar pontuação" onClose={() => setPending(null)}>
          <ScoreEditor
            key={pending.activity.id}
            activity={pending.activity}
            criterion={version?.groups
              .find((g) => g.number === pending.activity.group_number)
              ?.criteria.find((c) => c.item_number === pending.activity.item_number)}
            pit={pending.pit ?? false}
            onSaved={done}
            onCancel={() => setPending(null)}
          />
        </Modal>
      )}
      {pending?.kind === "edit" && (
        <Modal title="Editar atividade" onClose={() => setPending(null)}>
          <ActivityForm
            key={pending.activity.id}
            processId={id}
            groups={version?.groups ?? []}
            activity={pending.activity}
            onSaved={done}
            onCancel={() => setPending(null)}
          />
        </Modal>
      )}
    </>
  );
}
