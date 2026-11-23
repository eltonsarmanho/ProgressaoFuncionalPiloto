import type { ReactNode } from "react";
import type { ScoringTableInfo, ScoringVersionSummary, Unit } from "../api/types";
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

/** The registry of the actions of a version and of a table; each operation adds its builder here (GTAB-35). */
const VERSION_ACTIONS: VersionActionBuilder[] = [];
const TABLE_ACTIONS: TableActionBuilder[] = [unitsAction];

export function versionActions(ctx: ActionContext, table: ScoringTableInfo, version: ScoringVersionSummary): TableAction[] {
  return VERSION_ACTIONS.flatMap((build) => build(ctx, table, version));
}

export function tableActions(ctx: ActionContext, table: ScoringTableInfo): TableAction[] {
  return TABLE_ACTIONS.flatMap((build) => build(ctx, table));
}
