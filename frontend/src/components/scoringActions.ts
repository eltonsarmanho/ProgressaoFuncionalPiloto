import type { ReactNode } from "react";
import type { ScoringTableInfo, ScoringVersionSummary } from "../api/types";
import type { TableAction } from "./VersionRow";

/** What an action needs from the page: the announcement, the reload and a place for its dialog (GTAB-16). */
export type ActionContext = {
  announce: (message: string) => void;
  reload: () => Promise<void>;
  open: (dialog: ReactNode) => void;
  close: () => void;
};

type VersionActionBuilder = (ctx: ActionContext, table: ScoringTableInfo, version: ScoringVersionSummary) => TableAction[];
type TableActionBuilder = (ctx: ActionContext, table: ScoringTableInfo) => TableAction[];

/** The registry of the actions of a version and of a table; each operation adds its builder here (GTAB-35). */
const VERSION_ACTIONS: VersionActionBuilder[] = [];
const TABLE_ACTIONS: TableActionBuilder[] = [];

export function versionActions(ctx: ActionContext, table: ScoringTableInfo, version: ScoringVersionSummary): TableAction[] {
  return VERSION_ACTIONS.flatMap((build) => build(ctx, table, version));
}

export function tableActions(ctx: ActionContext, table: ScoringTableInfo): TableAction[] {
  return TABLE_ACTIONS.flatMap((build) => build(ctx, table));
}
