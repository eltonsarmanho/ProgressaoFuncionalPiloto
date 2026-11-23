import { useId, useState } from "react";
import { request } from "../api/client";
import type { ScoringTableInfo, Unit } from "../api/types";
import { FieldError } from "./FieldError";
import { blockReasonText } from "../labels";
import { Alert, Field, conflictCode, useSubmit } from "./formKit";
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
