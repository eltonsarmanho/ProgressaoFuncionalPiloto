import { useState } from "react";
import { request } from "../api/client";
import type { ScoringTableInfo } from "../api/types";
import { Alert, Field, FormProblem, useSubmit } from "./formKit";

function DuplicateForm({ table, onChanged }: { table: ScoringTableInfo; onChanged: () => void }) {
  const [name, setName] = useState("");
  const { submit, errors, error, busy } = useSubmit(async () => {
    await request("POST", `/api/scoring-tables/${table.id}/duplicate`, { new_name: name.trim() });
    setName("");
  }, onChanged);

  return (
    <form className="card" onSubmit={submit} noValidate aria-label="Duplicar tabela">
      <h3>Duplicar tabela</h3>
      <p className="muted">Copia a última versão de {table.name} para uma tabela nova e independente.</p>
      <Field id="dup-name" label="Nome da nova tabela" error={errors.name}>
        {(p) => <input {...p} value={name} onChange={(e) => setName(e.target.value)} />}
      </Field>
      <Alert message={error} />
      <button type="submit" disabled={busy}>
        Duplicar tabela
      </button>
    </form>
  );
}

function VersionForm({
  table,
  version,
  onChanged,
}: {
  table: ScoringTableInfo;
  version: { id: string; name: string };
  onChanged: () => void;
}) {
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [reference, setReference] = useState("");
  const { submit, errors, error, busy } = useSubmit(async () => {
    await request("POST", `/api/scoring-tables/${table.id}/versions`, {
      source_version_id: version.id,
      valid_from: validFrom,
      ...(validTo ? { valid_to: validTo } : {}),
      norm_reference: reference.trim(),
    });
    setValidFrom("");
    setValidTo("");
    setReference("");
  }, onChanged);

  return (
    <form className="card" onSubmit={submit} noValidate aria-label="Nova versão">
      <h3>Nova versão</h3>
      <p className="muted">
        Copia grupos e critérios de {version.name}. A versão sem data final termina no dia anterior ao início.
      </p>
      <Field id="ver-valid_from" label="Início da vigência da nova versão" error={errors.valid_from}>
        {(p) => <input {...p} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />}
      </Field>
      <Field id="ver-valid_to" label="Fim da vigência da nova versão (opcional)" error={errors.valid_to}>
        {(p) => <input {...p} type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />}
      </Field>
      <Field id="ver-norm_reference" label="Referência normativa da nova versão" error={errors.norm_reference}>
        {(p) => <input {...p} value={reference} onChange={(e) => setReference(e.target.value)} />}
      </Field>
      <Alert message={error} />
      <button type="submit" disabled={busy}>
        Criar nova versão
      </button>
    </form>
  );
}

function CsvForm({ table, onChanged }: { table: ScoringTableInfo; onChanged: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [reference, setReference] = useState("");
  const [status, setStatus] = useState("PENDENTE_VALIDACAO");
  const { submit, errors, fileIssues, error, busy } = useSubmit(async () => {
    if (!file) throw new FormProblem("file", "Selecione o arquivo CSV.");
    const form = new FormData();
    form.set("file", file);
    form.set("valid_from", validFrom);
    form.set("norm_reference", reference.trim());
    form.set("status", status);
    if (validTo) form.set("valid_to", validTo);
    await request("POST", `/api/scoring-tables/${table.id}/versions/import`, form);
    setFile(null);
  }, onChanged);

  return (
    <form className="card" onSubmit={submit} noValidate aria-label="Importar CSV">
      <h3>Importar CSV como nova versão</h3>
      <p className="muted">
        Colunas: grupo, item, descricao, unidade, modo, pontos, horas_por_bloco, limite e min_hours (opcional,
        carga horária mínima em horas; vazio ou ausente = sem mínimo). UTF-8, separado por
        vírgulas, ponto decimal. Tudo ou nada.
      </p>
      <Field id="csv-file" label="Arquivo CSV" error={errors.file}>
        {(p) => (
          <input {...p} type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        )}
      </Field>
      <Field id="csv-valid_from" label="Início da vigência do CSV" error={errors.valid_from}>
        {(p) => <input {...p} type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />}
      </Field>
      <Field id="csv-valid_to" label="Fim da vigência do CSV (opcional)" error={errors.valid_to}>
        {(p) => <input {...p} type="date" value={validTo} onChange={(e) => setValidTo(e.target.value)} />}
      </Field>
      <Field id="csv-norm_reference" label="Referência normativa do CSV" error={errors.norm_reference}>
        {(p) => <input {...p} value={reference} onChange={(e) => setReference(e.target.value)} />}
      </Field>
      <Field id="csv-status" label="Situação da nova versão">
        {(p) => (
          <select {...p} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="PENDENTE_VALIDACAO">Pendente de validação</option>
            <option value="OFICIAL">Oficial</option>
          </select>
        )}
      </Field>
      {fileIssues.length > 0 && (
        <div role="alert" className="error">
          <p>O arquivo tem erros e nada foi importado:</p>
          <ul>
            {fileIssues.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </div>
      )}
      <Alert message={error} />
      <button type="submit" disabled={busy}>
        Importar CSV
      </button>
    </form>
  );
}

/** ADMUI-02: duplicate the table, create a version from the selected one, upload a criteria CSV. */
export function ScoringAdminForms({
  table,
  version,
  onChanged,
}: {
  table: ScoringTableInfo;
  version: { id: string; name: string };
  onChanged: () => void;
}) {
  return (
    <>
      <DuplicateForm table={table} onChanged={onChanged} />
      <VersionForm table={table} version={version} onChanged={onChanged} />
      <CsvForm table={table} onChanged={onChanged} />
    </>
  );
}
