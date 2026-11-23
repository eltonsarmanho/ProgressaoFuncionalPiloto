import { useId, useState } from "react";
import { request } from "../api/client";
import type { Criterion, ScoringMode } from "../api/types";
import { SCORING_MODE_LABELS, roman } from "../labels";
import { Alert, Field, useSubmit, type Errors } from "./formKit";
import { Modal } from "./Modal";

const DECIMAL_FIELDS = ["unit_points", "hours_per_block", "prep_ratio", "min_hours", "max_points"] as const;
const TEXT_FIELDS = ["description", "unit_label", "accepted_evidence", "rules", "review_note"] as const;
type Draft = Record<(typeof DECIMAL_FIELDS)[number] | (typeof TEXT_FIELDS)[number] | "weeks_per_semester" | "mode", string>;

const LABELS = {
  description: "Descrição",
  unit_label: "Unidade de medida",
  mode: "Modo de pontuação",
  unit_points: "Pontos por unidade",
  hours_per_block: "Horas por bloco",
  weeks_per_semester: "Semanas por semestre",
  prep_ratio: "Preparação",
  max_points: "Limite de pontos",
  min_hours: "Carga horária mínima",
  accepted_evidence: "Evidência aceita",
  rules: "Regras",
  review_note: "Nota de revisão",
} as const;
const LONG_TEXT = new Set<string>(["description", "accepted_evidence", "rules", "review_note"]);

const NOT_NEGATIVE = /^\d+([.,]\d+)?$/;
const POSITIVE_INTEGER = /^\d+$/;

/** "10,50" and "10.5" and "10" as one number: the text without a comma and without trailing zeros. */
function canonical(value: string): string {
  const dotted = value.trim().replace(",", ".");
  return dotted.includes(".") ? dotted.replace(/0+$/, "").replace(/\.$/, "") : dotted;
}

function draftOf(c: Criterion): Draft {
  return {
    description: c.description,
    unit_label: c.unit_label ?? "",
    mode: c.mode,
    unit_points: c.unit_points ?? "",
    hours_per_block: c.hours_per_block ?? "",
    weeks_per_semester: c.weeks_per_semester === null ? "" : String(c.weeks_per_semester),
    prep_ratio: c.prep_ratio ?? "",
    max_points: c.max_points ?? "",
    min_hours: c.min_hours ?? "",
    accepted_evidence: c.accepted_evidence ?? "",
    rules: c.rules ?? "",
    review_note: c.review_note ?? "",
  };
}

/**
 * The fields of the draft that differ from the criterion, in the types the API takes (decimals and the integer as
 * numbers, an emptied number as null), and the problems of the numbers that cannot be converted (GTAB-21).
 */
function diff(original: Criterion, draft: Draft): { changes: Record<string, unknown>; problems: Errors } {
  const before = draftOf(original);
  const changes: Record<string, unknown> = {};
  const problems: Errors = {};
  if (draft.mode !== before.mode) changes.mode = draft.mode;
  for (const field of TEXT_FIELDS) {
    if (draft[field].trim() !== before[field].trim()) changes[field] = draft[field].trim();
  }
  for (const field of DECIMAL_FIELDS) {
    const value = draft[field].trim();
    if (value === "") {
      if (before[field] !== "") changes[field] = null;
    } else if (!NOT_NEGATIVE.test(value)) {
      problems[field] = "Informe um número não negativo.";
    } else if (canonical(value) !== canonical(before[field])) {
      changes[field] = Number(value.replace(",", "."));
    }
  }
  const weeks = draft.weeks_per_semester.trim();
  if (weeks === "") {
    if (before.weeks_per_semester !== "") changes.weeks_per_semester = null;
  } else if (!POSITIVE_INTEGER.test(weeks) || Number(weeks) <= 0) {
    problems.weeks_per_semester = "Informe um número inteiro positivo.";
  } else if (weeks !== before.weeks_per_semester) {
    changes.weeks_per_semester = Number(weeks);
  }
  return { changes, problems };
}

/**
 * GTAB-18, GTAB-21: edits one criterion of a version no process uses. It sends only what changed, with the
 * normative reference of the change; the 422 of the API shows next to the field and the typed values stay.
 */
export function CriterionEditDialog({
  versionId,
  criterion,
  onSaved,
  onClose,
}: {
  versionId: string;
  criterion: Criterion;
  /** The API answered with the criterion as it is now: the list replaces the old one. */
  onSaved: (updated: Criterion) => void;
  onClose: () => void;
}) {
  const id = useId();
  const [draft, setDraft] = useState<Draft>(() => draftOf(criterion));
  const [reference, setReference] = useState("");
  const [local, setLocal] = useState<Errors>({});
  const item = `${roman(criterion.group_number)}.${criterion.item_number}`;
  const set = (field: keyof Draft) => (value: string) => setDraft((d) => ({ ...d, [field]: value }));

  const { submit, errors, error, busy } = useSubmit(
    async () => {
      const { changes } = diff(criterion, draft);
      const updated = await request<Criterion>(
        "PUT",
        `/api/scoring-versions/${versionId}/criteria/${criterion.group_number}/${criterion.item_number}`,
        { change_reference: reference.trim(), changes },
      );
      onSaved(updated);
    },
    () => undefined,
  );

  function send(event: React.FormEvent) {
    event.preventDefault();
    const { changes, problems } = diff(criterion, draft);
    const found: Errors = { ...problems };
    if (reference.trim() === "") found.change_reference = "Informe a referência normativa da alteração.";
    if (Object.keys(changes).length === 0 && Object.keys(problems).length === 0) found.changes = "Nenhuma alteração informada";
    setLocal(found);
    if (Object.keys(found).length === 0) void submit(event);
  }

  const shown = { ...errors, ...local };
  const input = (field: keyof Draft) => (props: Record<string, unknown>) =>
    LONG_TEXT.has(field) ? (
      <textarea {...props} rows={2} value={draft[field]} onChange={(e) => set(field)(e.target.value)} />
    ) : (
      <input {...props} value={draft[field]} onChange={(e) => set(field)(e.target.value)} />
    );
  const plain = (field: Exclude<keyof Draft, "mode">) => (
    <Field id={`${id}-${field}`} label={LABELS[field]} error={shown[field]}>
      {(p) => input(field)(p)}
    </Field>
  );

  return (
    <Modal title={`Editar critério ${item}`} onClose={onClose}>
      <form onSubmit={send} noValidate aria-label="Editar critério">
        {plain("description")}
        {plain("unit_label")}
        <Field id={`${id}-mode`} label={LABELS.mode} error={shown.mode}>
          {(p) => (
            <select {...p} value={draft.mode} onChange={(e) => set("mode")(e.target.value as ScoringMode)}>
              {(Object.keys(SCORING_MODE_LABELS) as ScoringMode[]).map((mode) => (
                <option key={mode} value={mode}>
                  {SCORING_MODE_LABELS[mode]}
                </option>
              ))}
            </select>
          )}
        </Field>
        {plain("unit_points")}
        {plain("hours_per_block")}
        {plain("weeks_per_semester")}
        {plain("prep_ratio")}
        {plain("max_points")}
        {plain("min_hours")}
        {plain("accepted_evidence")}
        {plain("rules")}
        {plain("review_note")}
        <Field id={`${id}-change_reference`} label="Referência normativa da alteração" error={shown.change_reference}>
          {(p) => <input {...p} value={reference} onChange={(e) => setReference(e.target.value)} />}
        </Field>
        <Alert message={shown.changes ?? error} />
        <div className="btn-row">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            Salvar critério
          </button>
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </form>
    </Modal>
  );
}
