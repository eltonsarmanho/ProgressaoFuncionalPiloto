import { useEffect, useId, useState } from "react";
import { errorMessage, request } from "../api/client";
import type { ScoringTableInfo, ScoringVersionSummary, Unit } from "../api/types";
import { FieldError } from "./FieldError";
import {
  HISTORY_ACTION_LABELS,
  HISTORY_ENTITY_LABELS,
  SET_DEFAULT_LABELS,
  TABLE_STATUS_LABELS,
  blockReasonText,
  formatDate,
  formatDateTime,
  historyChangeLabel,
  historyValueText,
} from "../labels";
import { Alert, Field, FormProblem, conflictCode, useSubmit } from "./formKit";
import { Modal } from "./Modal";

type DialogProps = {
  /** The dialog finished its write: the page closes it, reloads the list and announces the sentence. */
  onDone: (message: string) => void;
  onClose: () => void;
};

/** GTAB-11, GTAB-14: the units as check boxes in a named group; the error of the field sits next to it. */
function UnitChecklist({
  units,
  checked,
  onToggle,
  error,
  idBase,
}: {
  units: Unit[];
  checked: ReadonlySet<string>;
  onToggle: (unitId: string) => void;
  error?: string;
  idBase: string;
}) {
  const errorId = `${idBase}-error`;
  return (
    <fieldset
      className="tbl-check-group"
      aria-invalid={error ? true : undefined}
      aria-describedby={error ? errorId : undefined}
    >
      <legend>Unidades associadas</legend>
      {units.map((unit) => (
        <label key={unit.id} className="tbl-check">
          <input type="checkbox" checked={checked.has(unit.id)} onChange={() => onToggle(unit.id)} />
          {unit.archived ? `${unit.acronym} (arquivada)` : unit.acronym}
        </label>
      ))}
      <FieldError id={errorId} message={error} />
    </fieldset>
  );
}

/** The set with the unit added, or removed when it was there. */
function toggled(set: ReadonlySet<string>, unitId: string): Set<string> {
  const next = new Set(set);
  if (next.has(unitId)) next.delete(unitId);
  else next.add(unitId);
  return next;
}

/** GTAB-11, GTAB-16, GTAB-35: creates a table with its first version; the API errors show next to the field. */
export function CreateTableDialog({
  units,
  tables,
  onDone,
  onClose,
}: DialogProps & { units: Unit[]; tables: ScoringTableInfo[] }) {
  const id = useId();
  const [name, setName] = useState("");
  const [unitIds, setUnitIds] = useState<ReadonlySet<string>>(new Set());
  const [status, setStatus] = useState("PENDENTE_VALIDACAO");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [reference, setReference] = useState("");
  const [versionName, setVersionName] = useState("");
  const [baseVersionId, setBaseVersionId] = useState("");
  const active = units.filter((u) => !u.archived);
  const bases = tables.flatMap((t) =>
    t.versions.filter((v) => v.superseded_by_id == null).map((v) => ({ id: v.id, text: `${t.name} · ${v.name}` })),
  );

  const { submit, errors, error, busy } = useSubmit(
    async () => {
      await request("POST", "/api/scoring-tables", {
        name: name.trim(),
        unit_ids: active.filter((u) => unitIds.has(u.id)).map((u) => u.id),
        status,
        valid_from: validFrom,
        ...(validTo ? { valid_to: validTo } : {}),
        norm_reference: reference.trim(),
        ...(versionName.trim() ? { version_name: versionName.trim() } : {}),
        ...(baseVersionId ? { base_version_id: baseVersionId } : {}),
      });
    },
    () => onDone(`Tabela "${name.trim()}" criada.`),
  );

  return (
    <Modal title="Nova tabela" onClose={onClose}>
      <form onSubmit={submit} noValidate aria-label="Nova tabela">
        <Field id={`${id}-name`} label="Nome da tabela" error={errors.name}>
          {(p) => <input {...p} value={name} onChange={(e) => setName(e.target.value)} />}
        </Field>
        <UnitChecklist
          units={active}
          checked={unitIds}
          onToggle={(unitId) => setUnitIds((set) => toggled(set, unitId))}
          error={errors.unit_ids}
          idBase={`${id}-units`}
        />
        <Field id={`${id}-status`} label="Situação" error={errors.status}>
          {(p) => (
            <select {...p} value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="PENDENTE_VALIDACAO">Pendente de validação</option>
              <option value="OFICIAL">Oficial</option>
            </select>
          )}
        </Field>
        <Field id={`${id}-valid_from`} label="Início da vigência" error={errors.valid_from}>
          {(p) => <input {...p} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />}
        </Field>
        <Field id={`${id}-valid_to`} label="Fim da vigência (opcional)" error={errors.valid_to}>
          {(p) => <input {...p} type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />}
        </Field>
        <Field id={`${id}-norm_reference`} label="Referência normativa" error={errors.norm_reference}>
          {(p) => <input {...p} value={reference} onChange={(e) => setReference(e.target.value)} />}
        </Field>
        <Field id={`${id}-version_name`} label="Nome da versão (opcional)" error={errors.version_name}>
          {(p) => <input {...p} value={versionName} onChange={(e) => setVersionName(e.target.value)} />}
        </Field>
        <Field id={`${id}-base`} label="Copiar critérios de (opcional)" error={errors.base_version_id}>
          {(p) => (
            <select {...p} value={baseVersionId} onChange={(e) => setBaseVersionId(e.target.value)}>
              <option value="">Não copiar</option>
              {bases.map((base) => (
                <option key={base.id} value={base.id}>
                  {base.text}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Alert message={error} />
        <div className="btn-row">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Criar tabela
          </button>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** GTAB-14, GTAB-16, GTAB-43: the units of a table; an archived unit it already has stays checked and marked. */
export function UnitsDialog({
  table,
  units,
  onDone,
  onClose,
}: DialogProps & { table: ScoringTableInfo; units: Unit[] }) {
  const id = useId();
  const offered = units.filter((u) => !u.archived || table.unit_ids.includes(u.id));
  const [unitIds, setUnitIds] = useState<ReadonlySet<string>>(new Set(table.unit_ids));
  // the units that have a version of this table in use: the ones the server refuses to take out (GTAB-43)
  const markedIds = new Set(table.versions.flatMap((v) => v.default_for_unit_ids));

  const { submit, error, busy } = useSubmit(
    async () => {
      const kept = offered.filter((u) => unitIds.has(u.id)).map((u) => u.id);
      const unknown = table.unit_ids.filter((unitId) => unitIds.has(unitId) && !kept.includes(unitId));
      await request("PUT", `/api/scoring-tables/${table.id}/units`, { unit_ids: [...kept, ...unknown] });
    },
    () => onDone(`Unidades da tabela "${table.name}" atualizadas.`),
    (err) => {
      if (conflictCode(err) !== "UNIDADE_COM_VERSAO_EM_USO") return null;
      const acronyms = offered.filter((u) => table.unit_ids.includes(u.id) && !unitIds.has(u.id) && markedIds.has(u.id));
      // without the acronyms the server's sentence is the one that names the units
      return acronyms.length > 0
        ? blockReasonText("UNIDADE_COM_VERSAO_EM_USO", { acronyms: acronyms.map((u) => u.acronym) })
        : null;
    },
  );

  return (
    <Modal title={`Unidades da tabela ${table.name}`} onClose={onClose}>
      <form onSubmit={submit} noValidate aria-label="Unidades da tabela">
        <UnitChecklist
          units={offered}
          checked={unitIds}
          onToggle={(unitId) => setUnitIds((set) => toggled(set, unitId))}
          idBase={`${id}-units`}
        />
        <Alert message={error} />
        <div className="btn-row">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Salvar unidades
          </button>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

/** GTAB-02, GTAB-16, GTAB-35: asks which unit of the table gets this version as the one in use. */
export function SetDefaultDialog({
  table,
  version,
  units,
  onDone,
  onClose,
}: DialogProps & { table: ScoringTableInfo; version: ScoringVersionSummary; units: Unit[] }) {
  const id = useId();
  const [unitId, setUnitId] = useState("");
  const offered = units.filter((u) => table.unit_ids.includes(u.id));

  const { submit, errors, error, busy } = useSubmit(
    async () => {
      if (!unitId) throw new FormProblem("unit_id", SET_DEFAULT_LABELS.chooseUnit);
      await request("PUT", `/api/scoring-units/${unitId}/default-version`, { version_id: version.id });
    },
    () => {
      const acronym = offered.find((u) => u.id === unitId)?.acronym ?? "";
      onDone(SET_DEFAULT_LABELS.done(version.name, acronym));
    },
  );

  return (
    <Modal title={`Definir ${version.name} como em uso`} onClose={onClose}>
      <form onSubmit={submit} noValidate aria-label="Definir como em uso">
        <fieldset
          className="tbl-check-group"
          aria-invalid={errors.unit_id ? true : undefined}
          aria-describedby={errors.unit_id ? `${id}-unit-error` : undefined}
        >
          <legend>Unidade</legend>
          {offered.map((unit) => {
            const already = version.default_for_unit_ids.includes(unit.id);
            return (
              <label key={unit.id} className="tbl-check">
                <input
                  type="radio"
                  name={`${id}-unit`}
                  checked={unitId === unit.id}
                  disabled={already}
                  onChange={() => setUnitId(unit.id)}
                />
                {already ? `${unit.acronym} (${SET_DEFAULT_LABELS.alreadyInUseUnit})` : unit.acronym}
              </label>
            );
          })}
          <FieldError id={`${id}-unit-error`} message={errors.unit_id} />
        </fieldset>
        <Alert message={error} />
        <div className="btn-row">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Definir como em uso
          </button>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}

type HistoryEvent = {
  id: number;
  occurred_at: string;
  user_id: string | null;
  entity: string;
  entity_id: string;
  action: string;
  changes: Record<string, { before?: unknown; after?: unknown }>;
  justification: string | null;
};
type History = { versions: ScoringVersionSummary[]; events: HistoryEvent[] };
type UserRef = { id: string; name: string };

/** GTAB-17, GTAB-35: the versions and the audit events of a table, with names instead of ids. */
export function HistoryDialog({
  table,
  units,
  onClose,
}: {
  table: ScoringTableInfo;
  units: Unit[];
  onClose: () => void;
}) {
  const [data, setData] = useState<{ history: History; users: UserRef[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    Promise.all([
      request<History>("GET", `/api/scoring-tables/${table.id}/history`),
      request<UserRef[]>("GET", "/api/users"),
    ])
      .then(([history, users]) => live && setData({ history, users }))
      .catch((err) => live && setError(errorMessage(err)));
    return () => {
      live = false;
    };
  }, [table.id, attempt]);

  function retry() {
    setError(null);
    setAttempt((n) => n + 1);
  }

  const versionNames = new Map<string, string>([
    ...table.versions.map((v) => [v.id, v.name] as [string, string]),
    ...(data?.history.versions ?? []).map((v) => [v.id, v.name] as [string, string]),
  ]);
  const names = (id: string): string | null =>
    units.find((u) => u.id === id)?.acronym ?? versionNames.get(id) ?? (id === table.id ? table.name : null);
  const authorOf = (event: HistoryEvent): string =>
    event.user_id === null
      ? "Sistema"
      : (data?.users.find((u) => u.id === event.user_id)?.name ?? "Usuário removido");
  const subjectOf = (event: HistoryEvent): string =>
    event.entity === "scoring_version"
      ? `Versão "${versionNames.get(event.entity_id) ?? "removida"}"`
      : (HISTORY_ENTITY_LABELS[event.entity] ?? event.entity);

  return (
    <Modal title={`Histórico de ${table.name}`} onClose={onClose}>
      {error && (
        <div role="alert" className="error">
          <p>{error}</p>
          <button type="button" className="btn btn-secondary" onClick={retry}>
            Tentar de novo
          </button>
        </div>
      )}
      {!data && !error && <p className="muted">Carregando…</p>}
      {data && (
        <>
          <h3>Versões</h3>
          <ul aria-label="Versões da tabela" className="tbl-versions">
            {data.history.versions.map((v) => (
              <li key={v.id} className="tbl-version">
                <p className="tbl-version-name">{v.name}</p>
                <p className="tbl-meta">
                  Vigência: {formatDate(v.valid_from)} a {v.valid_to ? formatDate(v.valid_to) : "em aberto"} ·{" "}
                  {TABLE_STATUS_LABELS[v.status] ?? v.status}
                </p>
                <p className="tbl-meta">Referência normativa: {v.norm_reference}</p>
              </li>
            ))}
          </ul>
          <h3>Eventos</h3>
          {data.history.events.length === 0 ? (
            <p className="muted">Nenhum evento registrado.</p>
          ) : (
            <ul aria-label="Eventos de auditoria" className="tbl-versions">
              {data.history.events.map((event) => (
                <li key={event.id} className="tbl-version">
                  <p className="tbl-version-name">
                    {formatDateTime(event.occurred_at)} · {authorOf(event)}
                  </p>
                  <p className="tbl-meta">
                    {HISTORY_ACTION_LABELS[event.action] ?? event.action} · {subjectOf(event)}
                  </p>
                  {Object.entries(event.changes).map(([key, change]) => (
                    <p className="tbl-meta" key={key}>
                      {historyChangeLabel(key)}: {historyValueText(key, change.before, names)} →{" "}
                      {historyValueText(key, change.after, names)}
                    </p>
                  ))}
                  {event.justification && <p className="tbl-meta">Referência: {event.justification}</p>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </Modal>
  );
}
