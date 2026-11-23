import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { errorMessage, request } from "../api/client";
import type { Criterion, ScoringTableInfo, ScoringVersion, Unit } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ReviewHighlight } from "../components/ReviewHighlight";
import { CriterionEditDialog } from "../components/CriterionEditDialog";
import { CreateTableDialog } from "../components/ScoringTableDialogs";
import { ScoringTableCard } from "../components/ScoringTableCard";
import { tableActions, versionActions, type ActionContext } from "../components/scoringActions";
import { blockReasonText, roman } from "../labels";

type Selection = { tableId: string; versionId: string };

const ALL_UNITS = "";

/** The count of the list: "1 tabela", "3 tabelas". */
/** The date of the user's own calendar as `aaaa-mm-dd`; `toISOString` would give the UTC date. */
function localIsoDate(date: Date): string {
  const two = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${two(date.getMonth() + 1)}-${two(date.getDate())}`;
}

function countText(n: number): string {
  return `${n} ${n === 1 ? "tabela" : "tabelas"}`;
}

/** ADMUI-01, GTAB-33: the tables as cards with their versions, filters, and the criteria of one version. */
export function ScoringAdmin() {
  const isAdmin = useAuth().user?.role === "ADMIN";
  const [tables, setTables] = useState<ScoringTableInfo[] | null>(null);
  const [units, setUnits] = useState<Unit[]>([]);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [version, setVersion] = useState<ScoringVersion | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [unitFilter, setUnitFilter] = useState(ALL_UNITS);
  const [showArchived, setShowArchived] = useState(false);
  const [dialog, setDialog] = useState<ReactNode>(null);
  const [focusTick, setFocusTick] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const criteriaTitle = useRef<HTMLHeadingElement>(null);
  const selectionRef = useRef<Selection | null>(null);
  useEffect(() => {
    selectionRef.current = selection;
  });

  const reload = useCallback(
    (): Promise<void> =>
      Promise.all([
        request<ScoringTableInfo[]>("GET", "/api/scoring-tables"),
        request<Unit[]>("GET", "/api/units"),
      ])
        .then(async ([all, allUnits]) => {
          setTables(all);
          setUnits(allUnits);
          setError(null);
          const open = selectionRef.current;
          const stillThere = open && all.some((t) => t.id === open.tableId && t.versions.some((v) => v.id === open.versionId));
          if (open && stillThere) {
            setVersion(await request<ScoringVersion>("GET", `/api/scoring-versions/${open.versionId}`));
          }
        })
        .catch((err) => setError(errorMessage(err))),
    [],
  );

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    if (focusTick > 0) criteriaTitle.current?.focus();
  }, [focusTick]);

  const acronymOf = useMemo(() => new Map(units.map((u) => [u.id, u.acronym])), [units]);
  const acronymsOf = useCallback(
    (ids: string[]) => ids.flatMap((id) => acronymOf.get(id) ?? []).sort(),
    [acronymOf],
  );
  const today = localIsoDate(new Date());

  async function showCriteria(tableId: string, versionId: string) {
    try {
      setVersion(await request<ScoringVersion>("GET", `/api/scoring-versions/${versionId}`));
      setSelection({ tableId, versionId });
      setFocusTick((n) => n + 1);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const actionContext: ActionContext = {
    announce: setNotice,
    reload,
    open: setDialog,
    close: () => setDialog(null),
    units,
    focusTitle: () => heading.current?.focus(),
  };

  function done(message: string) {
    setNotice(message);
    void reload();
  }

  /** A dialog finished its write: close it, announce the result and reload the list (GTAB-16). */
  function dialogDone(message: string) {
    setDialog(null);
    done(message);
  }

  /** GTAB-22: the API answered with the criterion as it is now; the open list shows it without a reload. */
  function criterionSaved(updated: Criterion) {
    setVersion((current) =>
      current && {
        ...current,
        groups: current.groups.map((g) => ({
          ...g,
          criteria: g.criteria.map((c) =>
            c.group_number === updated.group_number && c.item_number === updated.item_number ? { ...c, ...updated } : c,
          ),
        })),
      },
    );
    setDialog(null);
    setNotice(`Critério ${roman(updated.group_number)}.${updated.item_number} atualizado.`);
  }

  function clearFilters() {
    setUnitFilter(ALL_UNITS);
    setShowArchived(false);
  }

  if (!tables) {
    return error ? (
      <>
        <h1>Tabelas de pontuação</h1>
        <p role="alert" className="error">
          {error}
        </p>
        <button type="button" className="btn btn-secondary tbl-retry" onClick={() => void reload()}>
          Tentar de novo
        </button>
      </>
    ) : (
      <>
        <h1>Tabelas de pontuação</h1>
        <p className="muted">Carregando…</p>
      </>
    );
  }

  const shown = tables.filter(
    (t) => (showArchived || !t.archived) && (unitFilter === ALL_UNITS || t.unit_ids.includes(unitFilter)),
  );
  const openTable = selection && tables.find((t) => t.id === selection.tableId);
  const openVersion = openTable?.versions.find((v) => v.id === selection?.versionId);
  const hiddenArchived = !showArchived && tables.some((t) => t.archived);

  return (
    <>
      <div className="tbl-page-head">
        <h1 ref={heading} tabIndex={-1}>
          Tabelas de pontuação
        </h1>
        {isAdmin && (
          <button
            type="button"
            className="btn btn-primary"
            onClick={() =>
              setDialog(
                <CreateTableDialog
                  units={units}
                  tables={tables}
                  onDone={dialogDone}
                  onClose={() => setDialog(null)}
                />,
              )
            }
          >
            Nova tabela
          </button>
        )}
      </div>
      <p role="status" className="tbl-status">
        {notice}
      </p>
      {error && (
        <div role="alert" className="error">
          <p>{error}</p>
          <button type="button" className="btn btn-secondary tbl-retry" onClick={() => void reload()}>
            Tentar de novo
          </button>
        </div>
      )}
      <div className="card tbl-filters">
        <div className="field">
          <label htmlFor="tbl-unit-filter">Filtrar por unidade</label>
          <select id="tbl-unit-filter" value={unitFilter} onChange={(e) => setUnitFilter(e.target.value)}>
            <option value={ALL_UNITS}>Todas as unidades</option>
            {units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.acronym}
              </option>
            ))}
          </select>
        </div>
        <label className="tbl-filter-archived">
          <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
          Mostrar arquivadas
        </label>
      </div>
      <p className="tbl-count">{countText(shown.length)}</p>
      {shown.length === 0 ? (
        <div className="card tbl-empty">
          <p>
            {tables.length === 0
              ? "Nenhuma tabela cadastrada."
              : hiddenArchived
                ? 'Nenhuma tabela encontrada com estes filtros. Marque "Mostrar arquivadas" para ver as arquivadas.'
                : "Nenhuma tabela encontrada com estes filtros."}
          </p>
          {tables.length > 0 && (
            <button type="button" className="btn btn-secondary" onClick={clearFilters}>
              Limpar filtros
            </button>
          )}
        </div>
      ) : (
        shown.map((table) => (
          <ScoringTableCard
            key={table.id}
            table={table}
            acronymsOf={acronymsOf}
            today={today}
            isAdmin={isAdmin}
            tableActions={() => tableActions(actionContext, table)}
            versionActions={(v) => versionActions(actionContext, table, v)}
            onShowCriteria={(versionId) => void showCriteria(table.id, versionId)}
          />
        ))
      )}
      {openTable && openVersion && version?.id === openVersion.id && (
        <section className="card" aria-label={`Critérios de ${openTable.name} · ${openVersion.name}`}>
          <h2 ref={criteriaTitle} tabIndex={-1}>
            Critérios · {openTable.name} · {openVersion.name}
          </h2>
          {isAdmin && openVersion.read_only_reason && (
            <p className="muted">
              Somente leitura:{" "}
              {blockReasonText(openVersion.read_only_reason, { processCount: openVersion.process_count })}
            </p>
          )}
          <ReviewHighlight
            groups={version.groups}
            onEdit={
              isAdmin && !openVersion.read_only_reason
                ? (criterion) =>
                    setDialog(
                      <CriterionEditDialog
                        versionId={openVersion.id}
                        criterion={criterion}
                        onSaved={criterionSaved}
                        onClose={() => setDialog(null)}
                      />,
                    )
                : undefined
            }
          />
        </section>
      )}
      {isAdmin && dialog}
    </>
  );
}
