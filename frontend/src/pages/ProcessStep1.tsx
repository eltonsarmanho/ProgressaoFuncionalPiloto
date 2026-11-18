import { useEffect, useState, type FormEvent } from "react";
import { useLocation, useNavigate, useParams } from "react-router";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Process, Professor, Unit } from "../api/types";
import { AlertList } from "../components/AlertList";
import { FieldError, errorProps } from "../components/FieldError";
import { StepNav } from "../components/StepNav";
import { STATUS_LABELS } from "../labels";

const FIELDS = [
  "professor_id",
  "unit_id",
  "modality",
  "current_class",
  "current_denomination",
  "current_level",
  "target_class",
  "target_denomination",
  "target_level",
  "start_date",
  "end_date",
  "opening_date",
  "notes",
  "resp_name",
  "resp_position",
  "resp_appointment",
  "resp_admin_unit",
] as const;
type Field = (typeof FIELDS)[number];
type Form = Record<Field, string>;

const NUMERIC: Field[] = ["current_level", "target_level"];
const OPTIONAL: Field[] = ["notes", "resp_name", "resp_position", "resp_appointment", "resp_admin_unit"];
const EMPTY = Object.fromEntries(FIELDS.map((f) => [f, ""])) as Form;

function toForm(p: Process): Form {
  return Object.fromEntries(FIELDS.map((f) => [f, p[f] == null ? "" : String(p[f])])) as Form;
}

function toPayload(form: Form): Record<string, unknown> {
  return Object.fromEntries(
    FIELDS.map((f) => {
      const value = form[f].trim();
      if (NUMERIC.includes(f)) return [f, value === "" ? null : Number(value)];
      if (OPTIONAL.includes(f)) return [f, value === "" ? null : value];
      return [f, value];
    }),
  );
}

export function ProcessStep1() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const passed = (location.state as { process?: Process } | null)?.process;

  const [form, setForm] = useState<Form>(EMPTY);
  const [process, setProcess] = useState<Process | null>(null);
  const [justificativa, setJustificativa] = useState("");
  const [professors, setProfessors] = useState<Professor[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const fail = (err: unknown) => setError(errorMessage(err));
    request<Professor[]>("GET", "/api/professors")
      .then((all) => setProfessors(all.filter((p) => !p.archived)))
      .catch(fail);
    request<Unit[]>("GET", "/api/units")
      .then((all) => setUnits(all.filter((u) => !u.archived)))
      .catch(fail);
  }, []);

  useEffect(() => {
    if (!id) return;
    const show = (p: Process) => {
      setProcess(p);
      setForm(toForm(p));
    };
    if (passed?.id === id) show(passed);
    else request<Process>("GET", `/api/processes/${id}`).then(show).catch((err) => setError(errorMessage(err)));
  }, [id, passed]);

  function set(field: Field, value: string) {
    setForm((f) => {
      const next = { ...f, [field]: value };
      if (field === "professor_id") {
        const prof = professors.find((p) => p.id === value);
        if (prof) next.unit_id = prof.unit_id;
      }
      return next;
    });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setError(null);
    try {
      if (process) {
        const fields = toPayload(form);
        delete fields.professor_id;
        delete fields.unit_id;
        const saved = await request<Process>("PUT", `/api/processes/${process.id}`, {
          ...fields,
          expected_version: process.version,
          justificativa: justificativa.trim() || null,
        });
        setProcess(saved);
        setForm(toForm(saved));
        setJustificativa("");
      } else {
        const saved = await request<Process>("POST", "/api/processes", toPayload(form));
        navigate(`/processos/${saved.id}`, { replace: true, state: { process: saved } });
      }
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const input = (field: Field, label: string, type = "text") => (
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

  const select = (field: Field, label: string, options: [string, string][], disabled = false) => (
    <div className="field">
      <label htmlFor={field}>{label}</label>
      <select
        id={field}
        value={form[field]}
        disabled={disabled}
        onChange={(e) => set(field, e.target.value)}
        {...errorProps(field, errors)}
      >
        <option value="">Selecione…</option>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
      <FieldError id={`${field}-error`} message={errors[field]} />
    </div>
  );

  return (
    <>
      <StepNav />
      <form className="card" onSubmit={onSubmit} noValidate>
        <h1>Etapa 1 · Processo e interstício</h1>
        {process && <p className="badge">{STATUS_LABELS[process.status]}</p>}

        <fieldset>
          <legend>Docente</legend>
          {select(
            "professor_id",
            "Docente",
            professors.map((p) => [p.id, `${p.full_name} (SIAPE ${p.siape})`]),
            Boolean(process),
          )}
          {select(
            "unit_id",
            "Unidade acadêmica",
            units.map((u) => [u.id, `${u.acronym} — ${u.name}`]),
            Boolean(process),
          )}
          {select("modality", "Modalidade", [
            ["PROGRESSAO", "Progressão"],
            ["PROMOCAO", "Promoção"],
          ])}
        </fieldset>

        <fieldset className="grid">
          <legend>Situação funcional</legend>
          {input("current_class", "Classe atual")}
          {input("current_denomination", "Denominação atual")}
          {input("current_level", "Nível atual", "number")}
          {input("target_class", "Classe pretendida")}
          {input("target_denomination", "Denominação pretendida")}
          {input("target_level", "Nível pretendido", "number")}
        </fieldset>

        <fieldset className="grid">
          <legend>Interstício</legend>
          {input("start_date", "Data inicial do interstício", "date")}
          {input("end_date", "Data final do interstício", "date")}
          {input("opening_date", "Data de abertura", "date")}
        </fieldset>

        <fieldset>
          <legend>Dados institucionais e observações</legend>
          {input("resp_name", "Nome do responsável")}
          {input("resp_position", "Cargo do responsável")}
          {input("resp_appointment", "Portaria de designação do responsável")}
          {input("resp_admin_unit", "Unidade administrativa responsável")}
          <div className="field">
            <label htmlFor="notes">Observações</label>
            <textarea
              id="notes"
              rows={3}
              value={form.notes}
              onChange={(e) => set("notes", e.target.value)}
              {...errorProps("notes", errors)}
            />
            <FieldError id="notes-error" message={errors.notes} />
          </div>
        </fieldset>

        {process && (
          <div className="field">
            <label htmlFor="justificativa">Justificativa da alteração</label>
            <textarea
              id="justificativa"
              rows={2}
              value={justificativa}
              onChange={(e) => setJustificativa(e.target.value)}
              {...errorProps("justificativa", errors)}
            />
            <FieldError id="justificativa-error" message={errors.justificativa} />
          </div>
        )}

        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button type="submit" disabled={busy}>
          Salvar
        </button>
      </form>

      {process && (
        <section className="card" aria-labelledby="result-title">
          <h2 id="result-title">Resultado da verificação</h2>
          <p>
            Duração do interstício: {process.interstice.months} meses e {process.interstice.days} dias
          </p>
          <AlertList alerts={process.alerts} />
        </section>
      )}
    </>
  );
}
