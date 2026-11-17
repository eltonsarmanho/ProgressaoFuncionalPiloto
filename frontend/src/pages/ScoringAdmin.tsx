import { useCallback, useEffect, useState } from "react";
import { errorMessage, request } from "../api/client";
import type { ScoringTableInfo, ScoringVersion } from "../api/types";
import { ScoringAdminForms } from "../components/ScoringAdminForms";
import { TABLE_STATUS_LABELS, formatDate, formatDecimal, roman } from "../labels";

type Selection = { table: ScoringTableInfo; versionId: string; versionName: string };

function CriteriaTable({ version }: { version: ScoringVersion }) {
  return (
    <table className="scoring-table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Descrição</th>
          <th>Modo</th>
          <th>Pontos</th>
          <th>Limite</th>
        </tr>
      </thead>
      <tbody>
        {version.groups.flatMap((group) => [
          <tr className="group-head" key={`g${group.number}`}>
            <th colSpan={5}>
              Grupo {roman(group.number)} · {group.name}
              {group.counts_in_total ? "" : " (não conta no total)"}
            </th>
          </tr>,
          ...group.criteria.map((c) => (
            <tr key={`${c.group_number}.${c.item_number}`}>
              <td data-label="Item">
                {roman(c.group_number)}.{c.item_number}
              </td>
              <td data-label="Descrição">{c.description}</td>
              <td data-label="Modo">{c.mode}</td>
              <td data-label="Pontos">{formatDecimal(c.unit_points)}</td>
              <td data-label="Limite">{formatDecimal(c.max_points)}</td>
            </tr>
          )),
        ])}
      </tbody>
    </table>
  );
}

/** ADMUI-01: tables, their versions (validity, status, norm reference) and the criteria of one. */
export function ScoringAdmin() {
  const [tables, setTables] = useState<ScoringTableInfo[] | null>(null);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [version, setVersion] = useState<ScoringVersion | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    request<ScoringTableInfo[]>("GET", "/api/scoring-tables")
      .then((all) => {
        setTables(all);
        setError(null);
      })
      .catch((err) => setError(errorMessage(err)));
  }, []);

  useEffect(reload, [reload]);

  async function showCriteria(table: ScoringTableInfo, versionId: string, versionName: string) {
    try {
      setVersion(await request<ScoringVersion>("GET", `/api/scoring-versions/${versionId}`));
      setSelection({ table, versionId, versionName });
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  if (!tables) {
    return error ? (
      <p role="alert" className="error">
        {error}
      </p>
    ) : (
      <p className="muted">Carregando…</p>
    );
  }

  return (
    <>
      <h1>Tabelas de pontuação</h1>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {tables.map((table) => (
        <section className="card" key={table.id} aria-label={table.name}>
          <h2>{table.name}</h2>
          <table className="scoring-table">
            <thead>
              <tr>
                <th>Versão</th>
                <th>Vigência</th>
                <th>Situação</th>
                <th>Referência normativa</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {table.versions.map((v) => (
                <tr key={v.id}>
                  <td data-label="Versão">
                    {v.name} {v.in_use && <span className="badge">Em uso</span>}
                  </td>
                  <td data-label="Vigência">
                    {formatDate(v.valid_from)} a {v.valid_to ? formatDate(v.valid_to) : "em aberto"}
                  </td>
                  <td data-label="Situação">
                    <span className={v.status === "PENDENTE_VALIDACAO" ? "badge badge-pending" : "badge"}>
                      {TABLE_STATUS_LABELS[v.status]}
                    </span>
                  </td>
                  <td data-label="Referência normativa">{v.norm_reference}</td>
                  <td data-label="Ações">
                    <button
                      type="button"
                      className="link"
                      aria-label={`Ver critérios de ${v.name}`}
                      onClick={() => void showCriteria(table, v.id, v.name)}
                    >
                      Ver critérios
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      {selection && version && (
        <section
          className="card"
          aria-label={`Critérios de ${selection.table.name} · ${selection.versionName}`}
        >
          <h2>
            Critérios · {selection.table.name} · {selection.versionName}
          </h2>
          <CriteriaTable version={version} />
          <ScoringAdminForms
            table={selection.table}
            version={{ id: selection.versionId, name: selection.versionName }}
            onChanged={reload}
          />
        </section>
      )}
    </>
  );
}
