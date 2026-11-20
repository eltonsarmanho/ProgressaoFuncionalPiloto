import { useState } from "react";
import { errorMessage, request } from "../api/client";
import type { ChosenTable, ScoringTableInfo, TableChoice } from "../api/types";
import { TABLE_STATUS_LABELS, formatDate } from "../labels";

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
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // GI-07: a superseded version is never offered. A process that still uses one is read-only (the
  // editable ones were moved to the new version), so it shows the name and offers no switch.
  const locked = chosen?.version.superseded_by_id != null;
  const options = locked
    ? []
    : tables.flatMap((t) =>
        t.versions.filter((v) => v.superseded_by_id == null).map((v) => ({ id: v.id, text: `${t.name} · ${v.name}` })),
      );
  const differs = versionId !== "" && versionId !== chosen?.version.id;

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await request("PUT", `/api/processes/${processId}/scoring/table`, { version_id: versionId });
      onChanged();
    } catch (err) {
      setError(errorMessage(err));
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

      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {!locked && (!chosen || differs) && versionId !== "" && (
        <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void confirm()}>
          {chosen ? "Trocar tabela e recalcular" : "Confirmar tabela e calcular"}
        </button>
      )}
    </section>
  );
}
