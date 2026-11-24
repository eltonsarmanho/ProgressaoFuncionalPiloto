import { useState } from "react";
import { request } from "../api/client";
import type { ScoringTableInfo } from "../api/types";
import { Alert, Field, FormProblem, useSubmit } from "./formKit";
import { Modal } from "./Modal";

function DuplicateForm({ table, onDone }: { table: ScoringTableInfo; onDone: (message: string) => void }) {
  const [name, setName] = useState("");
  const { submit, errors, error, busy } = useSubmit(async () => {
    await request("POST", `/api/scoring-tables/${table.id}/duplicate`, { new_name: name.trim() });
    setName("");
  }, () => onDone("Tabela duplicada."));

  return (
    <form onSubmit={submit} noValidate aria-label="Duplicar tabela">
      <p className="muted">Copia a última versão de {table.name} para uma tabela nova e independente.</p>
      <Field id="dup-name" label="Nome da nova tabela" error={errors.name}>
        {(p) => <input {...p} value={name} onChange={(e) => setName(e.target.value)} />}
      </Field>
      <Alert message={error} />
      <button type="submit" className="btn btn-primary" disabled={busy}>
        Duplicar tabela
      </button>
    </form>
  );
}

function VersionForm({
  table,
  version,
  onDone,
}: {
  table: ScoringTableInfo;
  version: { id: string; name: string };
  onDone: (message: string) => void;
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
  }, () => onDone("Nova versão criada."));

  return (
    <form onSubmit={submit} noValidate aria-label="Nova versão">
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
      <button type="submit" className="btn btn-primary" disabled={busy}>
        Criar nova versão
      </button>
    </form>
  );
}

function CsvForm({ table, onDone }: { table: ScoringTableInfo; onDone: (message: string) => void }) {
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
  }, () => onDone("Versão criada a partir do CSV."));

  return (
    <form onSubmit={submit} noValidate aria-label="Importar CSV">
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
      <button type="submit" className="btn btn-primary" disabled={busy}>
        Importar CSV
      </button>
    </form>
  );
}

type DialogProps = {
  /** Called after a write, with the sentence the page announces. */
  onDone: (message: string) => void;
  onClose: () => void;
};

/** GTAB-12, GTAB-35: "Duplicar" of a table, in a dialog. */
export function DuplicateDialog({ table, onDone, onClose }: DialogProps & { table: ScoringTableInfo }) {
  return (
    <Modal title="Duplicar tabela" onClose={onClose}>
      <DuplicateForm table={table} onDone={onDone} />
    </Modal>
  );
}

/** GTAB-12, GTAB-35: "Nova versão a partir desta", with the clicked version as the source. */
export function VersionDialog({
  table,
  version,
  onDone,
  onClose,
}: DialogProps & { table: ScoringTableInfo; version: { id: string; name: string } }) {
  return (
    <Modal title={`Nova versão a partir de ${version.name}`} onClose={onClose}>
      <VersionForm table={table} version={version} onDone={onDone} />
    </Modal>
  );
}

/** GTAB-13, GTAB-35: "Importar CSV" of a table, in a dialog. */
export function CsvDialog({ table, onDone, onClose }: DialogProps & { table: ScoringTableInfo }) {
  return (
    <Modal title="Importar CSV como nova versão" onClose={onClose}>
      <CsvForm table={table} onDone={onDone} />
    </Modal>
  );
}
