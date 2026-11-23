import type { ScoringTableInfo } from "../api/types";
import { VersionRow } from "./VersionRow";

/** GTAB-33: a scoring table as a card with its units and its versions stacked (never a <table>). */
export function ScoringTableCard({
  table,
  acronymsOf,
  today,
  onShowCriteria,
}: {
  table: ScoringTableInfo;
  acronymsOf: (unitIds: string[]) => string[];
  today: string;
  onShowCriteria: (versionId: string) => void;
}) {
  const acronyms = acronymsOf(table.unit_ids);
  return (
    <section className="card tbl-card" aria-label={table.name}>
      <h2>{table.name}</h2>
      <p className="tbl-units">{acronyms.length > 0 ? `Unidades: ${acronyms.join(", ")}` : "Nenhuma unidade associada"}</p>
      <ul className="tbl-versions">
        {table.versions.map((version) => (
          <VersionRow
            key={version.id}
            version={version}
            tableArchived={table.archived}
            acronymsOf={acronymsOf}
            today={today}
            onShowCriteria={() => onShowCriteria(version.id)}
          />
        ))}
      </ul>
    </section>
  );
}
