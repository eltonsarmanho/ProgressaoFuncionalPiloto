import { useState, type FormEvent, type ReactNode } from "react";
import { ApiError, errorMessage, fieldErrors, request } from "../api/client";
import type { Norm, NormKind } from "../api/types";
import { NORM_KIND_LABELS } from "../labels";
import { FieldError, errorProps } from "./FieldError";

type Errors = Record<string, string>;

const STALE_MESSAGE = "A norma foi alterada por outra pessoa; recarregue";
export const NORM_FILE_HINT = "PDF de até 20 MB. Um novo arquivo substitui o anterior.";
const FILE_FIELD = "arquivo";

function Field({ name, label, errors, children }: { name: string; label: string; errors: Errors; children: (props: object) => ReactNode }) {
  return (
    <div className="field">
      <label htmlFor={name}>{label}</label>
      {children({ id: name, ...errorProps(name, errors) })}
      <FieldError id={`${name}-error`} message={errors[name]} />
    </div>
  );
}

/** Shared submit flow: busy flag, 422 per field, 409 as the stale-version message, any other error as an alert. */
function useSubmit(action: () => Promise<Norm>, onSaved: (norm: Norm) => void) {
  const [errors, setErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setErrors({});
    setError(null);
    setBusy(true);
    try {
      onSaved(await action());
    } catch (err) {
      if (err instanceof FormProblem) setErrors({ [err.field]: err.message });
      else if (err instanceof ApiError && err.status === 409) setError(STALE_MESSAGE);
      else if (Object.keys(fieldErrors(err)).length > 0) setErrors(fieldErrors(err));
      else setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }
  return { submit, errors, error, busy };
}

class FormProblem extends Error {
  readonly field: string;
  constructor(field: string, message: string) {
    super(message);
    this.field = field;
  }
}

function Alert({ message }: { message: string | null }) {
  return message ? (
    <p role="alert" className="error">
      {message}
    </p>
  ) : null;
}

const orNull = (value: string) => value.trim() || null;

type Props = { norm?: Norm; onSaved: (norm: Norm) => void; onCancel?: () => void };

/**
 * NBASE-01..04, 07, 10: register (no `norm`) or edit a norm. The code is read only when editing;
 * a 422 shows its message at the field, a 409 says the norm was changed by someone else.
 */
export function NormForm({ norm, onSaved, onCancel }: Props) {
  const [code, setCode] = useState(norm?.code ?? "");
  const [title, setTitle] = useState(norm?.title ?? "");
  const [kind, setKind] = useState<NormKind | "">(norm?.kind ?? "");
  const [issuer, setIssuer] = useState(norm?.issuer ?? "");
  const [publishedOn, setPublishedOn] = useState(norm?.published_on ?? "");
  const [validFrom, setValidFrom] = useState(norm?.valid_from ?? "");
  const [validTo, setValidTo] = useState(norm?.valid_to ?? "");
  const [sourceUrl, setSourceUrl] = useState(norm?.source_url ?? "");
  const [notes, setNotes] = useState(norm?.notes ?? "");

  const { submit, errors, error, busy } = useSubmit(() => {
    const fields = {
      title: title.trim(),
      kind,
      issuer: issuer.trim(),
      published_on: publishedOn,
      valid_from: orNull(validFrom),
      valid_to: orNull(validTo),
      source_url: orNull(sourceUrl),
      notes: orNull(notes),
    };
    return norm
      ? request<Norm>("PUT", `/api/norms/${norm.id}`, { ...fields, expected_version: norm.version })
      : request<Norm>("POST", "/api/norms", { code: code.trim(), ...fields });
  }, onSaved);

  return (
    <form className="card" onSubmit={submit} noValidate aria-label={norm ? "Editar norma" : "Cadastrar norma"}>
      <h3>{norm ? "Editar norma" : "Cadastrar norma"}</h3>
      <Field name="code" label="Código" errors={errors}>
        {(p) => <input {...p} value={code} readOnly={Boolean(norm)} onChange={(e) => setCode(e.target.value)} />}
      </Field>
      <Field name="title" label="Título" errors={errors}>
        {(p) => <input {...p} value={title} onChange={(e) => setTitle(e.target.value)} />}
      </Field>
      <Field name="kind" label="Tipo" errors={errors}>
        {(p) => (
          <select {...p} value={kind} onChange={(e) => setKind(e.target.value as NormKind | "")}>
            <option value="">Selecione o tipo</option>
            {Object.entries(NORM_KIND_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        )}
      </Field>
      <Field name="issuer" label="Órgão emissor" errors={errors}>
        {(p) => <input {...p} value={issuer} onChange={(e) => setIssuer(e.target.value)} />}
      </Field>
      <Field name="published_on" label="Data de publicação" errors={errors}>
        {(p) => <input {...p} type="date" value={publishedOn} onChange={(e) => setPublishedOn(e.target.value)} />}
      </Field>
      <Field name="valid_from" label="Início da vigência (opcional)" errors={errors}>
        {(p) => <input {...p} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />}
      </Field>
      <Field name="valid_to" label="Fim da vigência (opcional)" errors={errors}>
        {(p) => <input {...p} type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />}
      </Field>
      <Field name="source_url" label="URL da fonte (opcional)" errors={errors}>
        {(p) => <input {...p} value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} />}
      </Field>
      <Field name="notes" label="Observação (opcional)" errors={errors}>
        {(p) => <textarea {...p} value={notes} onChange={(e) => setNotes(e.target.value)} />}
      </Field>
      <Alert message={error} />
      <button type="submit" disabled={busy}>
        {norm ? "Salvar norma" : "Cadastrar norma"}
      </button>
      {onCancel && (
        <button type="button" className="link" onClick={onCancel}>
          Cancelar
        </button>
      )}
    </form>
  );
}

/** NBASE-05, 06, 10: attach (or replace) the PDF of a norm as multipart with the version read. */
export function NormFileForm({ norm, onSaved, onCancel }: Props & { norm: Norm }) {
  const [file, setFile] = useState<File | null>(null);
  const { submit, errors, error, busy } = useSubmit(() => {
    if (!file) throw new FormProblem(FILE_FIELD, "Selecione o arquivo PDF.");
    const form = new FormData();
    form.set("file", file);
    form.set("expected_version", String(norm.version));
    return request<Norm>("PUT", `/api/norms/${norm.id}/file`, form);
  }, onSaved);

  return (
    <form className="card" onSubmit={submit} noValidate aria-label="Anexar PDF">
      <h3>Anexar PDF</h3>
      <p className="muted">{NORM_FILE_HINT}</p>
      <Field name={FILE_FIELD} label="Arquivo PDF" errors={errors}>
        {(p) => (
          <input
            {...p}
            type="file"
            accept=".pdf,application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        )}
      </Field>
      <Alert message={error} />
      <button type="submit" disabled={busy}>
        Anexar PDF
      </button>
      {onCancel && (
        <button type="button" className="link" onClick={onCancel}>
          Cancelar
        </button>
      )}
    </form>
  );
}
