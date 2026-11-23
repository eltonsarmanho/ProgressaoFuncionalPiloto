import type { ReactNode } from "react";
import { errorMessage, request } from "../api/client";
import type { ScoringTableInfo, ScoringVersionSummary, Unit } from "../api/types";
import { CsvDialog, DuplicateDialog, VersionDialog } from "./ScoringAdminForms";
import { SET_DEFAULT_LABELS, blockReasonText } from "../labels";
import { DeleteScoringDialog, type DeleteTarget } from "./DeleteScoringDialog";
import { SetDefaultDialog, UnitsDialog } from "./ScoringTableDialogs";
import type { TableAction } from "./VersionRow";

/** What an action needs from the page: the announcement, the reload and a place for its dialog (GTAB-16). */
export type ActionContext = {
  announce: (message: string) => void;
  reload: () => Promise<void>;
  open: (dialog: ReactNode) => void;
  close: () => void;
  /** The units of the system, for the dialogs that ask for one or several. */
  units: Unit[];
  /** Moves the focus to the title of the page: where it goes when the opener of a dialog no longer exists. */
  focusTitle: () => void;
};

type VersionActionBuilder = (ctx: ActionContext, table: ScoringTableInfo, version: ScoringVersionSummary) => TableAction[];
type TableActionBuilder = (ctx: ActionContext, table: ScoringTableInfo) => TableAction[];

/** A dialog finished its write: close it, announce the result and reload the list (GTAB-16). */
function finish(ctx: ActionContext, message: string): void {
  ctx.close();
  ctx.announce(message);
  void ctx.reload();
}

/** GTAB-14, GTAB-35: "Unidades" of a table. */
const unitsAction: TableActionBuilder = (ctx, table) => [
  {
    key: "units",
    label: "Unidades",
    ariaLabel: `Unidades da tabela ${table.name}`,
    run: () =>
      ctx.open(
        <UnitsDialog
          table={table}
          units={ctx.units}
          onDone={(message) => finish(ctx, message)}
          onClose={ctx.close}
        />,
      ),
  },
];

/** GTAB-12, GTAB-13, GTAB-35: "Duplicar" and "Importar CSV" of a table. */
const formActions: TableActionBuilder = (ctx, table) => [
  {
    key: "duplicate",
    label: "Duplicar",
    ariaLabel: `Duplicar a tabela ${table.name}`,
    run: () =>
      ctx.open(<DuplicateDialog table={table} onDone={(message) => finish(ctx, message)} onClose={ctx.close} />),
  },
  {
    key: "csv",
    label: "Importar CSV",
    ariaLabel: `Importar CSV para a tabela ${table.name}`,
    run: () => ctx.open(<CsvDialog table={table} onDone={(message) => finish(ctx, message)} onClose={ctx.close} />),
  },
];

/** GTAB-12, GTAB-35: "Nova versão a partir desta" of a version. */
const newVersionAction: VersionActionBuilder = (ctx, table, version) => [
  {
    key: "new-version",
    label: "Nova versão a partir desta",
    ariaLabel: `Nova versão a partir de ${version.name}`,
    run: () =>
      ctx.open(
        <VersionDialog
          table={table}
          version={{ id: version.id, name: version.name }}
          onDone={(message) => finish(ctx, message)}
          onClose={ctx.close}
        />,
      ),
  },
];

/** Why "Definir como em uso" is not allowed on this version, or undefined when it is (GTAB-03, GTAB-36). */
function setDefaultBlock(table: ScoringTableInfo, version: ScoringVersionSummary): string | undefined {
  if (version.superseded_by_id) return blockReasonText("VERSAO_SUBSTITUIDA");
  if (table.archived) return blockReasonText("TABELA_ARQUIVADA");
  if (table.unit_ids.length === 0) return SET_DEFAULT_LABELS.noUnit;
  if (table.unit_ids.every((unitId) => version.default_for_unit_ids.includes(unitId))) {
    return SET_DEFAULT_LABELS.alreadyInUse;
  }
  return undefined;
}

/** The dialog of a deletion is over: close it, announce, wait for the new list, then focus the title (GTAB-30). */
async function finishDeletion(ctx: ActionContext, message: string): Promise<void> {
  ctx.close();
  ctx.announce(message);
  await ctx.reload();
  ctx.focusTitle();
}

function openDeletion(ctx: ActionContext, target: DeleteTarget): void {
  ctx.open(
    <DeleteScoringDialog
      target={target}
      onDeleted={(message) => void finishDeletion(ctx, message)}
      onClose={ctx.close}
    />,
  );
}

/** GTAB-27, GTAB-35, GTAB-36: "Excluir versão", blocked with the reason the list carries. */
const deleteVersionAction: VersionActionBuilder = (ctx, _table, version) => {
  const acronyms = ctx.units.filter((u) => version.default_for_unit_ids.includes(u.id)).map((u) => u.acronym);
  return [
    {
      key: "delete-version",
      label: "Excluir versão",
      ariaLabel: `Excluir versão ${version.name}`,
      disabledReason: version.delete_blocked_reason
        ? blockReasonText(version.delete_blocked_reason, { processCount: version.process_count, acronyms })
        : undefined,
      run: () => openDeletion(ctx, { kind: "version", id: version.id, name: version.name }),
    },
  ];
};

/** GTAB-29, GTAB-35, GTAB-36: "Excluir tabela". */
const deleteTableAction: TableActionBuilder = (ctx, table) => {
  const markedIds = new Set(table.versions.flatMap((v) => v.default_for_unit_ids));
  const acronyms = ctx.units.filter((u) => markedIds.has(u.id)).map((u) => u.acronym);
  const processCount = table.versions.reduce((total, v) => total + v.process_count, 0);
  return [
    {
      key: "delete-table",
      label: "Excluir tabela",
      ariaLabel: `Excluir tabela ${table.name}`,
      disabledReason: table.delete_blocked_reason
        ? blockReasonText(table.delete_blocked_reason, { processCount, acronyms })
        : undefined,
      run: () => openDeletion(ctx, { kind: "table", id: table.id, name: table.name }),
    },
  ];
};

/** Runs a write that acts at once: the result (or the API's text on a refusal) goes to the page status. */
async function actNow(ctx: ActionContext, write: () => Promise<void>, success: string): Promise<void> {
  try {
    await write();
  } catch (err) {
    ctx.announce(errorMessage(err));
    return;
  }
  ctx.announce(success);
  await ctx.reload();
}

/** GTAB-02, GTAB-04, GTAB-35: "Definir como em uso" and, for each unit that has the version, "Remover marcação". */
const defaultActions: VersionActionBuilder = (ctx, table, version) => {
  const acronymOf = (unitId: string) => ctx.units.find((u) => u.id === unitId)?.acronym ?? unitId;
  const set: TableAction = {
    key: "set-default",
    label: "Definir como em uso",
    ariaLabel: `Definir ${version.name} como em uso`,
    disabledReason: setDefaultBlock(table, version),
    run: () => {
      if (table.unit_ids.length === 1) {
        const unitId = table.unit_ids[0];
        void actNow(
          ctx,
          () => request("PUT", `/api/scoring-units/${unitId}/default-version`, { version_id: version.id }),
          SET_DEFAULT_LABELS.done(version.name, acronymOf(unitId)),
        );
        return;
      }
      ctx.open(
        <SetDefaultDialog
          table={table}
          version={version}
          units={ctx.units}
          onDone={(message) => finish(ctx, message)}
          onClose={ctx.close}
        />,
      );
    },
  };
  const clears: TableAction[] = version.default_for_unit_ids.map((unitId) => ({
    key: `clear-default-${unitId}`,
    label: `Remover marcação de ${acronymOf(unitId)}`,
    ariaLabel: `Remover marcação de ${acronymOf(unitId)} em ${version.name}`,
    run: () =>
      void actNow(
        ctx,
        () => request("DELETE", `/api/scoring-units/${unitId}/default-version`),
        SET_DEFAULT_LABELS.cleared(acronymOf(unitId)),
      ),
  }));
  return [set, ...clears];
};

/** GTAB-23, GTAB-25, GTAB-35: "Arquivar" or "Desarquivar" of a table, at once, blocked with the reason and the acronyms. */
const archiveAction: TableActionBuilder = (ctx, table) => {
  const archiving = !table.archived;
  const markedIds = new Set(table.versions.flatMap((v) => v.default_for_unit_ids));
  const acronyms = ctx.units.filter((u) => markedIds.has(u.id)).map((u) => u.acronym);
  return [
    {
      key: "archive",
      label: archiving ? "Arquivar" : "Desarquivar",
      ariaLabel: `${archiving ? "Arquivar" : "Desarquivar"} a tabela ${table.name}`,
      disabledReason: table.archive_blocked_reason
        ? blockReasonText(table.archive_blocked_reason, { acronyms })
        : undefined,
      run: () =>
        void actNow(
          ctx,
          () => request("POST", `/api/scoring-tables/${table.id}/${archiving ? "archive" : "unarchive"}`),
          `Tabela "${table.name}" ${archiving ? "arquivada" : "desarquivada"}.`,
        ),
    },
  ];
};

/** The registry of the actions of a version and of a table; each operation adds its builder here (GTAB-35). */
const VERSION_ACTIONS: VersionActionBuilder[] = [defaultActions, newVersionAction, deleteVersionAction];
const TABLE_ACTIONS: TableActionBuilder[] = [formActions, unitsAction, archiveAction, deleteTableAction];

export function versionActions(ctx: ActionContext, table: ScoringTableInfo, version: ScoringVersionSummary): TableAction[] {
  return VERSION_ACTIONS.flatMap((build) => build(ctx, table, version));
}

export function tableActions(ctx: ActionContext, table: ScoringTableInfo): TableAction[] {
  return TABLE_ACTIONS.flatMap((build) => build(ctx, table));
}
