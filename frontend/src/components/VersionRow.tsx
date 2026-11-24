import { useId } from "react";
import type { ScoringVersionSummary } from "../api/types";
import { TABLE_BADGE_LABELS, TABLE_STATUS_LABELS, formatDate, inUseBadge } from "../labels";

/**
 * GTAB-35, GTAB-36: one action of the bar of a version or of a table. `disabledReason` is the sentence that says
 * why it is not allowed; the button then stays focusable (`aria-disabled`) and the click does nothing.
 */
export type TableAction = {
  key: string;
  label: string;
  ariaLabel: string;
  run: () => void;
  disabledReason?: string;
};

/** The write actions of a version or of a table, ADMIN only: a text label on each, the reason under a blocked one. */
export function ActionBar({ actions }: { actions: TableAction[] }) {
  const base = useId();
  if (actions.length === 0) return null;
  return (
    <>
      {actions.map((action) => {
        const reasonId = `${base}-${action.key}`;
        return (
          <div className="tbl-action" key={action.key}>
            <button
              type="button"
              className="btn btn-secondary"
              aria-label={action.ariaLabel}
              aria-disabled={action.disabledReason ? true : undefined}
              aria-describedby={action.disabledReason ? reasonId : undefined}
              onClick={() => {
                if (!action.disabledReason) action.run();
              }}
            >
              {action.label}
            </button>
            {action.disabledReason && (
              <p id={reasonId} className="tbl-reason">
                {action.disabledReason}
              </p>
            )}
          </div>
        );
      })}
    </>
  );
}

/** GTAB-33, GTAB-34: one version of a table as a card: name, validity, status, reference and the tags. */
export function VersionRow({
  version,
  tableArchived,
  acronymsOf,
  today,
  isAdmin,
  actions = [],
  onShowCriteria,
}: {
  version: ScoringVersionSummary;
  tableArchived: boolean;
  /** The sorted acronyms of the units of the ids; an id that is not a known unit is left out. */
  acronymsOf: (unitIds: string[]) => string[];
  /** ISO date of today, to tell a version whose validity already ended. */
  today: string;
  /** The write actions show only to the ADMIN (GTAB-15). */
  isAdmin: boolean;
  actions?: TableAction[];
  onShowCriteria: () => void;
}) {
  const marked = acronymsOf(version.default_for_unit_ids);
  const ended = marked.length > 0 && version.valid_to !== null && version.valid_to < today;
  return (
    <li className="tbl-version">
      <p className="tbl-version-name">{version.name}</p>
      <p className="tbl-meta">
        Vigência: {formatDate(version.valid_from)} a {version.valid_to ? formatDate(version.valid_to) : "em aberto"}
      </p>
      <p className="tbl-meta">Referência normativa: {version.norm_reference}</p>
      <ul className="tbl-badges" aria-label={`Etiquetas de ${version.name}`}>
        <li>
          <span className={version.status === "PENDENTE_VALIDACAO" ? "badge badge-pending" : "badge"}>
            {TABLE_STATUS_LABELS[version.status]}
          </span>
        </li>
        {marked.map((acronym) => (
          <li key={acronym}>
            <span className="badge badge-ok">{inUseBadge(acronym)}</span>
          </li>
        ))}
        {ended && (
          <li>
            <span className="badge badge-pending">{TABLE_BADGE_LABELS.ended}</span>
          </li>
        )}
        {version.in_use && (
          <li>
            <span className="badge">{TABLE_BADGE_LABELS.usedByProcess}</span>
          </li>
        )}
        {version.superseded_by_id && (
          <li>
            <span className="badge">{TABLE_BADGE_LABELS.superseded}</span>
          </li>
        )}
        {tableArchived && (
          <li>
            <span className="badge">{TABLE_BADGE_LABELS.archived}</span>
          </li>
        )}
      </ul>
      <div className="tbl-actions">
        <button
          type="button"
          className="btn btn-secondary"
          aria-label={`Ver critérios de ${version.name}`}
          onClick={onShowCriteria}
        >
          Ver critérios
        </button>
        {isAdmin && <ActionBar actions={actions} />}
      </div>
    </li>
  );
}
