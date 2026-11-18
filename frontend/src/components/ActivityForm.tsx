import { useState, type FormEvent } from "react";
import { preservedFields } from "../activityBody";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, ScoringGroup, ScoringMode } from "../api/types";
import { GROUP_NAMES, roman } from "../labels";
import { FieldError, errorProps } from "./FieldError";

type Form = {
  title: string;
  description: string;
  group_number: string;
  item_number: string;
  event_date: string;
  period_start: string;
  period_end: string;
  evidence_note: string;
  quantidade: string;
  horas: string;
  academic_period: string;
  level: string;
  course_hours: string;
  points_override: string;
  informed_points: string;
};

const str = (v: string | number | null | undefined) => (v == null ? "" : String(v));

function toForm(a?: Activity): Form {
  return {
    title: str(a?.title),
    description: str(a?.description),
    group_number: str(a?.group_number),
    item_number: str(a?.item_number),
    event_date: str(a?.event_date),
    period_start: str(a?.period_start),
    period_end: str(a?.period_end),
    evidence_note: str(a?.evidence_note),
    quantidade: str(a?.quantidade),
    horas: str(a?.horas),
    academic_period: str(a?.academic_period),
    level: str(a?.level),
    course_hours: str(a?.course_hours),
    points_override: str(a?.points_override),
    informed_points: str(a?.informed_points),
  };
}

const NUMERIC = ["quantidade", "horas", "course_hours", "points_override", "informed_points"] as const;
const TEXT = [
  "title",
  "description",
  "event_date",
  "period_start",
  "period_end",
  "evidence_note",
  "academic_period",
  "level",
] as const;

/** TELA-04 / TELA-05: fields follow the criterion mode. No justification field (UIM-17). */
export function ActivityForm({
  processId,
  groups,
  activity,
  onSaved,
  onCancel,
}: {
  processId: string;
  groups: ScoringGroup[];
  activity?: Activity;
  onSaved: (saved: Activity) => void;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState<Form>(() => toForm(activity));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (field: keyof Form, value: string) => setForm((f) => ({ ...f, [field]: value }));

  const group = groups.find((g) => String(g.number) === form.group_number);
  const criterion = group?.criteria.find((c) => String(c.item_number) === form.item_number);
  const mode: ScoringMode | null =
    group?.number === 1 && (!criterion || criterion.mode === "CARGA_SEMANAL")
      ? "CARGA_SEMANAL"
      : (criterion?.mode ?? null);
  const isEdit = Boolean(activity);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const body: Record<string, unknown> = {};
    for (const f of TEXT) {
      const v = form[f].trim();
      if (v !== "") body[f] = v;
    }
    if (form.group_number !== "") body.group_number = Number(form.group_number);
    if (form.item_number !== "" && mode !== "CARGA_SEMANAL") body.item_number = Number(form.item_number);
    for (const f of NUMERIC) {
      const v = form[f].trim();
      if (v !== "") body[f] = Number.isNaN(Number(v)) ? v : Number(v);
    }

    setBusy(true);
    setErrors({});
    try {
      const saved = activity
        ? await request<Activity>("PUT", `/api/activities/${activity.id}`, {
            ...body,
            ...preservedFields(activity),
            expected_version: activity.version,
          })
        : await request<Activity>("POST", `/api/processes/${processId}/activities`, body);
      onSaved(saved);
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const input = (field: keyof Form, label: string, type = "text") => (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <input
        id={field}
        type={type}
        value={form[field]}
        onChange={(e) => set(field, e.target.value)}
        {...errorProps(field, errors)}
      />
      <FieldError id={`${field}-error`} message={errors[field]} />
    </div>
  );

  const textarea = (field: keyof Form, label: string) => (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <textarea
        id={field}
        rows={2}
        value={form[field]}
        onChange={(e) => set(field, e.target.value)}
        {...errorProps(field, errors)}
      />
      <FieldError id={`${field}-error`} message={errors[field]} />
    </div>
  );

  return (
    <form className="card" onSubmit={onSubmit} noValidate aria-label={isEdit ? "Editar atividade" : "Nova atividade"}>
      <h2>{isEdit ? "Editar atividade" : "Nova atividade"}</h2>
      {input("title", "Título")}
      {textarea("description", "Descrição")}

      <div className="field">
        <label htmlFor="group_number">Grupo</label>
        <select
          id="group_number"
          value={form.group_number}
          onChange={(e) => setForm((f) => ({ ...f, group_number: e.target.value, item_number: "" }))}
          {...errorProps("group_number", errors)}
        >
          <option value="">Sem enquadramento</option>
          {groups.map((g) => (
            <option key={g.number} value={g.number}>
              {`${roman(g.number)} · ${g.name || GROUP_NAMES[g.number]}`}
            </option>
          ))}
        </select>
        <FieldError id="group_number-error" message={errors.group_number} />
      </div>

      {group && (
        <div className="field">
          <label htmlFor="item_number">Item</label>
          <select
            id="item_number"
            value={form.item_number}
            onChange={(e) => set("item_number", e.target.value)}
            {...errorProps("item_number", errors)}
          >
            <option value="">{group.number === 1 ? "Pelo nível (I.1 ou I.2)" : "Selecione…"}</option>
            {group.criteria.map((c) => (
              <option key={c.item_number} value={c.item_number}>
                {`${roman(c.group_number)}.${c.item_number} · ${c.description}`}
              </option>
            ))}
          </select>
          <FieldError id="item_number-error" message={errors.item_number} />
        </div>
      )}

      {input("event_date", "Data do evento ou mês (AAAA-MM-DD ou AAAA-MM)")}
      {input("period_start", "Início do período (AAAA-MM-DD ou AAAA-MM)")}
      {input("period_end", "Fim do período (AAAA-MM-DD ou AAAA-MM)")}

      {mode === "POR_UNIDADE" && input("quantidade", "Quantidade", "number")}
      {mode === "POR_BLOCO_DE_HORAS" && input("horas", "Horas", "number")}
      {mode === "VALOR_INFORMADO" && input("informed_points", "Pontos informados", "number")}
      {mode === "CARGA_SEMANAL" && (
        <>
          {input("academic_period", "Período letivo (AAAA.N)")}
          <div className="field">
            <label htmlFor="level">Nível</label>
            <select
              id="level"
              value={form.level}
              onChange={(e) => set("level", e.target.value)}
              {...errorProps("level", errors)}
            >
              <option value="">Selecione…</option>
              <option value="GRADUACAO">Graduação</option>
              <option value="POS_GRADUACAO">Pós-graduação</option>
            </select>
            <FieldError id="level-error" message={errors.level} />
          </div>
          {input("horas", "Horas semanais", "number")}
          {input("course_hours", "Carga horária do curso (opcional)", "number")}
          {input("points_override", "Pontuação manual (substitui o cálculo)", "number")}
        </>
      )}

      {input("evidence_note", "Comprovante")}

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="btn-row">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          Salvar atividade
        </button>
        {onCancel && (
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  );
}
