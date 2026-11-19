import { useState, type FormEvent } from "react";
import { activityBody } from "../activityBody";
import { isYearlyUnit } from "../activityList";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Activity, ScoringGroup } from "../api/types";
import { CategoryPicker } from "./CategoryPicker";
import { FieldError } from "./FieldError";

type Form = {
  title: string;
  group_number: string;
  item_number: string;
  event_date: string;
  period_start: string;
  period_end: string;
  quantidade: string;
  horas: string;
  academic_period: string;
  level: string;
};

const str = (v: string | number | null | undefined) => (v == null ? "" : String(v));

function toForm(a?: Activity): Form {
  return {
    title: str(a?.title),
    group_number: str(a?.group_number),
    item_number: str(a?.item_number),
    event_date: str(a?.event_date),
    period_start: str(a?.period_start),
    period_end: str(a?.period_end),
    quantidade: str(a?.quantidade),
    horas: str(a?.horas),
    academic_period: str(a?.academic_period),
    level: str(a?.level),
  };
}

const number = (v: string): number | string => (Number.isNaN(Number(v)) ? v : Number(v));

/**
 * EDT-01, EDT-04..EDT-07: the short form of an activity. Editing asks for Título, Data (Início and
 * Fim in a category measured by year) and Categoria, plus Horas only when the category has a
 * minimum workload; a Grupo I offering shows only Título and Categoria, because its period and
 * hours come from the document. A new activity adds Quantidade. The PUT still sends the whole
 * body (`activityBody`), so what the form does not show is kept as it was. It acts at once: no
 * justification and no field for the proof text (the proof is linked in Etapa 3).
 */
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

  const isEdit = Boolean(activity);
  const group = groups.find((g) => String(g.number) === form.group_number);
  const criterion = group?.criteria.find((c) => String(c.item_number) === form.item_number);
  const groupOne = form.group_number === "1";
  /** EDT-05: an existing Grupo I offering; any other activity put in Grupo I has no document to bring its period. */
  const offering = groupOne && activity?.group_number === 1;
  const newGroupOne = groupOne && !offering;
  const yearly = isYearlyUnit(criterion?.unit_label);
  const showDates = !offering && !newGroupOne;
  const showHours = showDates && criterion?.min_hours != null;
  const showQuantity = !isEdit && !newGroupOne;
  /** The 422 field names that have an input right now; an error for any other is shown as a general alert. */
  const shown = [
    "title", "group_number", "item_number", "categoria",
    ...(showDates ? (yearly ? ["period_start", "period_end"] : ["event_date"]) : []),
    ...(showHours ? ["horas"] : []),
    ...(showQuantity ? ["quantidade"] : []),
    ...(newGroupOne ? ["academic_period", "level", "horas"] : []),
  ];

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const body: Record<string, unknown> = activity ? activityBody(activity) : {};
    const put = (field: string, value: unknown) => {
      if (value === "" || value == null) delete body[field];
      else body[field] = value;
    };

    put("title", form.title.trim());
    put("group_number", form.group_number === "" ? null : Number(form.group_number));
    // Grupo I takes its item from the level: an offering keeps the item it has, a new one sends none.
    if (newGroupOne) delete body.item_number;
    else put("item_number", form.item_number === "" ? null : Number(form.item_number));

    if (showDates) {
      const dateFields = yearly ? ["period_start", "period_end"] : ["event_date"];
      const otherFields = yearly ? ["event_date"] : ["period_start", "period_end"];
      for (const field of dateFields) put(field, form[field as keyof Form].trim());
      // A date or a period, not both: the one that is not shown goes only when the shown one was filled.
      if (dateFields.some((field) => form[field as keyof Form].trim() !== "")) for (const field of otherFields) delete body[field];
    }
    if (showHours) put("horas", form.horas.trim() === "" ? null : number(form.horas.trim()));
    if (showQuantity) put("quantidade", form.quantidade.trim() === "" ? null : number(form.quantidade.trim()));
    if (newGroupOne) {
      put("academic_period", form.academic_period.trim());
      put("level", form.level);
      put("horas", form.horas.trim() === "" ? null : number(form.horas.trim()));
    }

    setBusy(true);
    setErrors({});
    try {
      const saved = activity
        ? await request<Activity>("PUT", `/api/activities/${activity.id}`, { ...body, expected_version: activity.version })
        : await request<Activity>("POST", `/api/processes/${processId}/activities`, body);
      onSaved(saved);
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      const first = Object.keys(byField).find((field) => shown.includes(field));
      if (first) document.getElementById(first)?.focus();
      const hidden = Object.entries(byField).find(([field]) => !shown.includes(field));
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
      else if (hidden) setError(hidden[1]);
    } finally {
      setBusy(false);
    }
  }

  const describedBy = (field: string, hint?: string) => {
    const ids = [hint, errors[field] ? `${field}-error` : undefined].filter(Boolean);
    return ids.length > 0 ? ids.join(" ") : undefined;
  };

  const input = (field: keyof Form, label: string, type = "text", hint?: string) => (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <input
        id={field}
        type={type}
        value={form[field]}
        onChange={(e) => set(field, e.target.value)}
        aria-invalid={errors[field] ? true : undefined}
        aria-describedby={describedBy(field, hint ? `${field}-hint` : undefined)}
      />
      {hint && (
        <small id={`${field}-hint`} className="muted">
          {hint}
        </small>
      )}
      <FieldError id={`${field}-error`} message={errors[field]} />
    </div>
  );

  const DATE_HINT = "AAAA-MM-DD ou AAAA-MM";

  return (
    <form className="card" onSubmit={onSubmit} noValidate aria-label={isEdit ? "Editar atividade" : "Nova atividade"}>
      <h2>{isEdit ? "Editar atividade" : "Nova atividade"}</h2>
      {input("title", "Título")}

      <div className="field">
        <CategoryPicker
          groups={groups}
          value={{ group_number: form.group_number === "" ? null : Number(form.group_number), item_number: form.item_number === "" ? null : Number(form.item_number) }}
          label="Categoria"
          hideLabel={false}
          error={errors.categoria ?? errors.group_number ?? errors.item_number}
          onChange={(value) => setForm((f) => ({ ...f, group_number: String(value.group_number), item_number: String(value.item_number) }))}
        />
      </div>

      {offering && (
        <p className="muted">Oferta do Grupo I: o período letivo, o nível e as horas vêm do documento.</p>
      )}

      {showDates &&
        (yearly ? (
          <>
            {input("period_start", "Início", "text", DATE_HINT)}
            {input("period_end", "Fim", "text", DATE_HINT)}
          </>
        ) : (
          input("event_date", "Data", "text", DATE_HINT)
        ))}

      {showHours && input("horas", "Horas", "number")}
      {showQuantity && input("quantidade", "Quantidade", "number")}

      {newGroupOne && (
        <>
          {input("academic_period", "Período letivo (AAAA.N)")}
          <div className="field">
            <label htmlFor="level">Nível</label>
            <select
              id="level"
              value={form.level}
              onChange={(e) => set("level", e.target.value)}
              aria-invalid={errors.level ? true : undefined}
              aria-describedby={describedBy("level")}
            >
              <option value="">Selecione…</option>
              <option value="GRADUACAO">Graduação</option>
              <option value="POS_GRADUACAO">Pós-graduação</option>
            </select>
            <FieldError id="level-error" message={errors.level} />
          </div>
          {input("horas", "Horas semanais", "number")}
        </>
      )}

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
