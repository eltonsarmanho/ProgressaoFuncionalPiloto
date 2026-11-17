import { useState } from "react";
import { errorMessage, fieldErrors, request } from "../api/client";
import type { ChosenTable, ScoringTableInfo, TableChoice } from "../api/types";
import { TABLE_STATUS_LABELS, formatDate } from "../labels";
import { FieldError, errorProps } from "./FieldError";

function TableCard({ title, table }: { title: string; table: ChosenTable }) {
  const { version } = table;
  const pending = version.status === "PENDENTE_VALIDACAO";
  return (
    <div className="table-card">
      <h3>{title}</h3>
      <p>
        <strong>{table.table_name}</strong> · {version.name}
      </p>
      <p>
        Situação:{" "}
        <span className={pending ? "badge badge-pending" : "badge"}>{TABLE_STATUS_LABELS[version.status]}</span>
      </p>
      <p>
        Vigência: {formatDate(version.valid_from)} a {version.valid_to ? formatDate(version.valid_to) : "em aberto"}
      </p>
      <p>
        <small>Referência normativa: {version.norm_reference}</small>
      </p>
    </div>
  );
}

/** TELA-06: chosen or suggested table, status, norm reference; confirmation before computing. */
export function TablePicker({
  processId,
  choice,
  tables = [],
  onChanged,
}: {
  processId: string;
  choice: TableChoice;
  tables?: ScoringTableInfo[];
  onChanged: () => void;
}) {
  const { chosen, suggested } = choice;
  const shown = chosen ?? suggested;
  const [versionId, setVersionId] = useState(shown?.version.id ?? "");
  const [justificativa, setJustificativa] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const options = tables.flatMap((t) => t.versions.map((v) => ({ id: v.id, text: `${t.name} · ${v.name}` })));
  const differs = versionId !== "" && versionId !== chosen?.version.id;
  const askJustification = versionId !== (suggested?.version.id ?? "") || "justificativa" in errors;

  async function confirm() {
    setBusy(true);
    setErrors({});
    setError(null);
    try {
      await request("PUT", `/api/processes/${processId}/scoring/table`, {
        version_id: versionId,
        ...(justificativa.trim() ? { justificativa: justificativa.trim() } : {}),
      });
      setJustificativa("");
      onChanged();
    } catch (err) {
      const byField = fieldErrors(err);
      setErrors(byField);
      if (Object.keys(byField).length === 0) setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-labelledby="table-picker-title">
      <h2 id="table-picker-title">Tabela de pontuação</h2>
      {chosen && <TableCard title="Tabela escolhida" table={chosen} />}
      {!chosen && suggested && <TableCard title="Tabela sugerida" table={suggested} />}
      {!chosen && !suggested && <p>Nenhuma tabela vigente encontrada para a unidade e a data.</p>}

      {options.length > 0 && (
        <div className="field">
          <label htmlFor="version_id">Escolher outra tabela</label>
          <select id="version_id" value={versionId} onChange={(e) => setVersionId(e.target.value)}>
            <option value="">Selecione…</option>
            {options.map((o) => (
              <option key={o.id} value={o.id}>
                {o.text}
              </option>
            ))}
          </select>
        </div>
      )}

      {versionId !== "" && askJustification && (
        <div className="field">
          <label htmlFor="justificativa">Justificativa (tabela de outra unidade)</label>
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
      {(!chosen || differs) && versionId !== "" && (
        <button type="button" disabled={busy} onClick={() => void confirm()}>
          {chosen ? "Trocar tabela e recalcular" : "Confirmar tabela e calcular"}
        </button>
      )}
    </section>
  );
}
