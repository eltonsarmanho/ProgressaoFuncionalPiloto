import type { ReactNode } from "react";
import type { ScoringTableInfo, ScoringVersionSummary, Unit } from "../api/types";
import { CsvDialog, DuplicateDialog, VersionDialog } from "./ScoringAdminForms";
import { UnitsDialog } from "./ScoringTableDialogs";
import type { TableAction } from "./VersionRow";

/** What an action needs from the page: the announcement, the reload and a place for its dialog (GTAB-16). */
export type ActionContext = {
  announce: (message: string) => void;
  reload: () => Promise<void>;
  open: (dialog: ReactNode) => void;
  close: () => void;
  /** The units of the system, for the dialogs that ask for one or several. */
  units: Unit[];
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

/** The registry of the actions of a version and of a table; each operation adds its builder here (GTAB-35). */
const VERSION_ACTIONS: VersionActionBuilder[] = [newVersionAction];
const TABLE_ACTIONS: TableActionBuilder[] = [formActions, unitsAction];

export function versionActions(ctx: ActionContext, table: ScoringTableInfo, version: ScoringVersionSummary): TableAction[] {
  return VERSION_ACTIONS.flatMap((build) => build(ctx, table, version));
}

export function tableActions(ctx: ActionContext, table: ScoringTableInfo): TableAction[] {
  return TABLE_ACTIONS.flatMap((build) => build(ctx, table));
}
