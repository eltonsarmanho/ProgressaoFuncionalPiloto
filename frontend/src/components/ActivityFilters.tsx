import { GROUP_NAMES, roman } from "../labels";

export type SituationFilter = "TODAS" | "AGUARDANDO" | "VALIDADAS" | "PRECISA_CATEGORIA";
export type SituationCounts = Record<SituationFilter, number>;
export type ActivityFilterState = { query: string; situation: SituationFilter; group: number | null };

// eslint-disable-next-line react-refresh/only-export-components
export const DEFAULT_FILTERS: ActivityFilterState = { query: "", situation: "TODAS", group: null };

const CHIPS: { situation: SituationFilter; label: string }[] = [
  { situation: "TODAS", label: "Todas" },
  { situation: "AGUARDANDO", label: "Aguardando validação" },
  { situation: "VALIDADAS", label: "Validadas" },
  { situation: "PRECISA_CATEGORIA", label: "Precisa de categoria" },
];

/**
 * SEC-03: search by title, situation chips with their counts and the filter by group. It holds no
 * state: the section owns `filters`, filters the list and computes `counts` over the whole list.
 */
export function ActivityFilters({
  filters,
  counts,
  groups,
  onChange,
}: {
  filters: ActivityFilterState;
  counts: SituationCounts;
  /** The group numbers the list has, so the filter offers only those. */
  groups: number[];
  onChange: (filters: ActivityFilterState) => void;
}) {
  const active = filters.query !== "" || filters.situation !== "TODAS" || filters.group !== null;
  return (
    <div className="activity-filters">
      <div className="activity-filters-fields">
        <div className="field">
          <label htmlFor="activity-search">Buscar por título</label>
          <input
            id="activity-search"
            type="search"
            value={filters.query}
            onChange={(e) => onChange({ ...filters, query: e.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="activity-group-filter">Filtrar por grupo</label>
          <select
            id="activity-group-filter"
            value={filters.group === null ? "" : String(filters.group)}
            onChange={(e) => onChange({ ...filters, group: e.target.value === "" ? null : Number(e.target.value) })}
          >
            <option value="">Todos os grupos</option>
            {[...groups]
              .sort((a, b) => a - b)
              .map((g) => (
                <option key={g} value={g}>
                  {`${roman(g)} · ${GROUP_NAMES[g] ?? `Grupo ${g}`}`}
                </option>
              ))}
          </select>
        </div>
      </div>
      <div className="chip-row" role="group" aria-label="Situação">
        {CHIPS.map(({ situation, label }) => (
          <button
            key={situation}
            type="button"
            className="chip"
            aria-pressed={filters.situation === situation}
            onClick={() => onChange({ ...filters, situation })}
          >
            {`${label} (${counts[situation]})`}
          </button>
        ))}
        {active && (
          <button type="button" className="btn btn-secondary" onClick={() => onChange(DEFAULT_FILTERS)}>
            Limpar filtros
          </button>
        )}
      </div>
    </div>
  );
}
