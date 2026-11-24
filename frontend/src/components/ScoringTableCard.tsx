import type { ScoringTableInfo, ScoringVersionSummary } from "../api/types";
import type { TableAction } from "./VersionRow";
import { ActionBar, VersionRow } from "./VersionRow";

/** GTAB-33: a scoring table as a card with its units and its versions stacked (never a <table>). */
export function ScoringTableCard({
  table,
  acronymsOf,
  today,
  isAdmin,
  tableActions,
  versionActions,
  onShowCriteria,
}: {
  table: ScoringTableInfo;
  acronymsOf: (unitIds: string[]) => string[];
  today: string;
  /** The write actions show only to the ADMIN (GTAB-15). */
  isAdmin: boolean;
  tableActions: () => TableAction[];
  versionActions: (version: ScoringVersionSummary) => TableAction[];
  onShowCriteria: (versionId: string) => void;
}) {
  const acronyms = acronymsOf(table.unit_ids);
  const barActions = isAdmin ? tableActions() : [];
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
            isAdmin={isAdmin}
            actions={versionActions(version)}
            onShowCriteria={() => onShowCriteria(version.id)}
          />
        ))}
      </ul>
      {isAdmin && barActions.length > 0 && (
        <div className="tbl-actions" role="group" aria-label={`Ações da tabela ${table.name}`}>
          <ActionBar actions={barActions} />
        </div>
      )}
    </section>
  );
}
