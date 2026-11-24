import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
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
import { countUnscored } from "../unscored";
import { ActivityForm } from "../components/ActivityForm";
import { AlertList } from "../components/AlertList";
import { Modal } from "../components/Modal";
import { ScoreEditor } from "../components/ScoreEditor";
import { ScoringPanel } from "../components/ScoringPanel";
import { ScoringTable } from "../components/ScoringTable";
import { STEP_BLOCKED_ID, StepNav } from "../components/StepNav";
import { TablePicker } from "../components/TablePicker";

type Pending = { kind: "new" } | { kind: "edit" | "points"; activity: Activity; pit?: boolean; outsideTotal?: boolean };

const MANUAL_CODE = "VALOR_UNITARIO_MANUAL";

/** A rejected activity has no scoring row: it stays in the table as a shaded row, to be reopened. */
function rejectedRow(a: Activity): ScoringRow {
  return {
    activity_id: a.id,
    title: a.title,
    activity_status: "REJEITADA",
    evidence_note: a.evidence_note,
    group_number: a.group_number,
    item_number: a.item_number,
    unit_points: null,
    effective_quantity: null,
    formula_text: null,
    points: "0.00",
    pit_hours: null,
    outside_total: false,
    academic_period: a.academic_period,
    level: a.level,
    status: "REJEITADA",
    reasons: [],
    alerts: [],
  };
}

/** The way to Etapa 5 stays closed while an activity of the table is not scored. */
function unscoredMessage(count: number): string {
  return count === 1
    ? "Há 1 atividade não pontuada. Valide ou rejeite a atividade destacada para seguir para a Etapa 5."
    : `Há ${count} atividades não pontuadas. Valide ou rejeite as atividades destacadas para seguir para a Etapa 5.`;
}

/** Etapa 4: loads the table choice, the result and the criteria; reloads after every change. */
export function ProcessScoring() {
  const { id = "" } = useParams();
  const [choice, setChoice] = useState<TableChoice | null>(null);
  const [result, setResult] = useState<ScoringResult | null>(null);
  const [version, setVersion] = useState<ScoringVersion | null>(null);
  const [tables, setTables] = useState<ScoringTableInfo[]>([]);
  const [rejected, setRejected] = useState<Activity[]>([]);
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
      // The rejected ones are an extra of the page: without them the table still works.
      const all = await request<Activity[]>("GET", `/api/processes/${id}/activities`).catch(() => [] as Activity[]);
      return { table, scoring, criteria, all };
    })()
      .then(({ table, scoring, criteria, all }) => {
        if (cancelled) return;
        setChoice(table);
        setResult(scoring);
        setVersion(criteria);
        setRejected(all.filter((a) => a.status === "REJEITADA"));
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
      setPending({ kind, activity, pit: row.pit_hours != null, outsideTotal: row.outside_total });
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
  async function act(kind: "validate" | "reject" | "reopen" | "distinct", row: ScoringRow) {
    setError(null);
    try {
      const activity = await request<Activity>("GET", `/api/activities/${row.activity_id}`);
      if (kind === "distinct") {
        await request("POST", `/api/activities/${activity.id}/distinct`, { expected_version: activity.version });
      } else {
        await request("POST", `/api/activities/${activity.id}/status`, {
          status: kind === "validate" ? "VALIDADA" : kind === "reject" ? "REJEITADA" : "AGUARDANDO_REVISAO",
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

  const scored = result?.rows ?? [];
  const unscored = countUnscored(scored);
  const blocked = unscored > 0 ? { step: 4, message: unscoredMessage(unscored) } : undefined;
  const tableRows = [...scored, ...rejected.map(rejectedRow)];

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
      <StepNav current={4} processId={id} blocked={blocked} />
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
            {unscored > 0 && (
              <p className="unscored-note">
                {unscored === 1 ? "1 atividade não pontuada, em destaque na tabela." : `${unscored} atividades não pontuadas, em destaque na tabela.`}{" "}
                Em cada uma, edite a pontuação e clique em Validar; se ela não vale pontos, clique em Rejeitar.
              </p>
            )}
            <ScoringTable
              rows={tableRows}
              subtotals={result.subtotals}
              groupNames={groupNames}
              group1TotalHours={result.group1_total_hours}
              actions={(row) =>
                row.status === "REJEITADA" ? (
                  <div className="row-actions">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      aria-label={`Reabrir ${row.title}`}
                      title={`Reabrir ${row.title}`}
                      onClick={() => void act("reopen", row)}
                    >
                      Reabrir
                    </button>
                  </div>
                ) : (
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
                  {row.activity_status !== "VALIDADA" && (
                    <button
                      type="button"
                      className="btn btn-primary"
                      aria-label={`Validar ${row.title}`}
                      title={`Validar ${row.title}`}
                      onClick={() => void act("validate", row)}
                    >
                      Validar
                    </button>
                  )}
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
                )
              }
            />
            <div className="btn-row">
              <button type="button" className="btn btn-primary" onClick={() => setPending({ kind: "new" })}>
                Nova atividade
              </button>
            </div>
          </section>

          <p>
            {unscored > 0 ? (
              <span aria-disabled="true" aria-describedby={STEP_BLOCKED_ID} className="muted">
                Ir para a Etapa 5 · Documentos gerados
              </span>
            ) : (
              <Link to={`/processos/${id}/gerados`}>Ir para a Etapa 5 · Documentos gerados</Link>
            )}
          </p>

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
            outsideTotal={pending.outsideTotal ?? false}
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
