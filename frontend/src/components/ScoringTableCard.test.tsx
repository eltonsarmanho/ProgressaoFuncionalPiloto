import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ScoringTableInfo } from "../api/types";
import { ScoringTableCard } from "./ScoringTableCard";
import type { TableAction } from "./VersionRow";

const TABLE: ScoringTableInfo = {
  id: "t1",
  name: "Tabela da FASI",
  archived: false,
  unit_ids: ["u1"],
  archive_blocked_reason: null,
  delete_blocked_reason: null,
  versions: [
    {
      id: "v1",
      table_id: "t1",
      name: "FASI 2026",
      valid_from: "2026-03-01",
      valid_to: null,
      norm_reference: "Res. 7.000/2026",
      status: "OFICIAL",
      superseded_by_id: null,
      in_use: false,
      process_count: 0,
      default_for_unit_ids: [],
      read_only_reason: null,
      delete_blocked_reason: null,
    },
  ],
};

function setup(isAdmin: boolean, tableActions: TableAction[], versionActions: TableAction[] = []) {
  render(
    <ScoringTableCard
      table={TABLE}
      acronymsOf={(ids) => ids.map(() => "FASI")}
      today="2026-11-23"
      isAdmin={isAdmin}
      tableActions={() => tableActions}
      versionActions={() => versionActions}
      onShowCriteria={vi.fn()}
    />,
  );
}

describe("GTAB-15, GTAB-35: barra de ações da tabela", () => {
  const archive: TableAction = {
    key: "archive",
    label: "Arquivar",
    ariaLabel: "Arquivar a tabela Tabela da FASI",
    run: vi.fn(),
  };

  it("o ADMIN vê a barra da tabela, com rótulo de texto e aria-label com o nome da tabela", async () => {
    const run = vi.fn();
    setup(true, [{ ...archive, run }]);

    const group = screen.getByRole("group", { name: "Ações da tabela Tabela da FASI" });
    const button = within(group).getByRole("button", { name: "Arquivar a tabela Tabela da FASI" });
    expect(button).toHaveTextContent("Arquivar");
    await userEvent.setup().click(button);
    expect(run).toHaveBeenCalledTimes(1);
  });

  it("quem não é ADMIN não vê a barra da tabela nem as ações das versões", () => {
    setup(false, [archive], [{ key: "x", label: "Excluir versão", ariaLabel: "Excluir versão FASI 2026", run: vi.fn() }]);

    expect(screen.queryByRole("group", { name: /Ações da tabela/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Arquivar|Excluir versão/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ver critérios de FASI 2026" })).toBeInTheDocument();
  });

  it("sem ações no registro o ADMIN não vê barra vazia", () => {
    setup(true, []);

    expect(screen.queryByRole("group", { name: /Ações da tabela/ })).not.toBeInTheDocument();
  });
});
