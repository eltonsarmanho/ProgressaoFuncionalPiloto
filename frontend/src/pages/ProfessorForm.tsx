import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { Professor, Unit } from "../api/types";
import { FieldError, errorProps } from "../components/FieldError";

type FormData = Pick<
  Professor,
  "full_name" | "siape" | "titration" | "position" | "unit_id" | "faculty" | "campus" | "work_regime"
>;

const EMPTY = {
  full_name: "",
  siape: "",
  titration: "",
  position: "",
  unit_id: "",
  faculty: "",
  campus: "",
  work_regime: "",
} as unknown as FormData;

const TITRATIONS: [string, string][] = [
  ["GRADUACAO", "Graduação"],
  ["ESPECIALIZACAO", "Especialização"],
  ["MESTRADO", "Mestrado"],
  ["DOUTORADO", "Doutorado"],
];
const REGIMES: [string, string][] = [
  ["20H", "20 horas"],
  ["40H", "40 horas"],
  ["DE", "Dedicação exclusiva"],
];

export function ProfessorForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm] = useState<FormData>(EMPTY);
  const [version, setVersion] = useState<number | null>(null);
  const [units, setUnits] = useState<Unit[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    request<Unit[]>("GET", "/api/units")
      .then((all) => setUnits(all.filter((u) => !u.archived)))
      .catch((err) => setError(errorMessage(err)));
    if (id) {
      request<Professor>("GET", `/api/professors/${id}`)
        .then((p) => {
          const { full_name, siape, titration, position, unit_id, faculty, campus, work_regime } = p;
          setForm({ full_name, siape, titration, position, unit_id, faculty, campus, work_regime });
          setVersion(p.version);
        })
        .catch((err) => setError(errorMessage(err)));
    }
  }, [id]);

  function set<K extends keyof FormData>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setError(null);
    try {
      if (id) {
        await request("PUT", `/api/professors/${id}`, { ...form, expected_version: version });
      } else {
        await request("POST", "/api/professors", form);
      }
      navigate("/");
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const text = (name: keyof FormData, label: string, extra: Record<string, string> = {}) => (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <input
        id={name}
        value={form[name]}
        onChange={(e) => set(name, e.target.value)}
        {...extra}
        {...errorProps(name, errors)}
      />
      <FieldError id={`${name}-error`} message={errors[name]} />
    </div>
  );

  const select = (name: keyof FormData, label: string, options: [string, string][]) => (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      <select
        id={name}
        value={form[name]}
        onChange={(e) => set(name, e.target.value)}
        {...errorProps(name, errors)}
      >
        <option value="">Selecione…</option>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
      <FieldError id={`${name}-error`} message={errors[name]} />
    </div>
  );

  return (
    <form className="card" onSubmit={onSubmit} noValidate>
      <h1>{id ? "Editar docente" : "Cadastrar docente"}</h1>
      {text("full_name", "Nome completo")}
      {text("siape", "Matrícula SIAPE", { inputMode: "numeric", maxLength: "7" })}
      {select("titration", "Titulação", TITRATIONS)}
      {text("position", "Cargo")}
      {select(
        "unit_id",
        "Unidade acadêmica",
        units.map((u) => [u.id, `${u.acronym} — ${u.name}`]),
      )}
      {text("faculty", "Faculdade")}
      {text("campus", "Campus")}
      {select("work_regime", "Regime de trabalho", REGIMES)}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button type="submit" disabled={busy}>
        Salvar
      </button>
    </form>
  );
}
