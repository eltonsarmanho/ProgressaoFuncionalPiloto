import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ScoringVersionSummary } from "../api/types";
import { VersionRow, type TableAction } from "./VersionRow";

const VERSION: ScoringVersionSummary = {
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
};

function setup(actions: TableAction[], isAdmin = true) {
  const onShowCriteria = vi.fn();
  render(
    <ul>
      <VersionRow
        version={VERSION}
        tableArchived={false}
        acronymsOf={() => []}
        today="2026-11-23"
        isAdmin={isAdmin}
        actions={actions}
        onShowCriteria={onShowCriteria}
      />
    </ul>,
  );
  return { onShowCriteria, user: userEvent.setup() };
}

function synthetic(run = vi.fn()): { actions: TableAction[]; run: ReturnType<typeof vi.fn> } {
  return {
    run,
    actions: [
      { key: "free", label: "Nova versão a partir desta", ariaLabel: "Nova versão a partir de FASI 2026", run },
      {
        key: "blocked",
        label: "Excluir versão",
        ariaLabel: "Excluir versão FASI 2026",
        run: vi.fn(),
        disabledReason: "A versão é usada por 2 processos e não pode ser excluída.",
      },
    ],
  };
}

describe("GTAB-15, GTAB-35: barra de ações da versão", () => {
  it("o ADMIN vê a barra, com rótulo de texto e aria-label com o nome da versão", () => {
    setup(synthetic().actions);

    const free = screen.getByRole("button", { name: "Nova versão a partir de FASI 2026" });
    expect(free).toHaveTextContent("Nova versão a partir desta");
    const blocked = screen.getByRole("button", { name: "Excluir versão FASI 2026" });
    expect(blocked).toHaveTextContent("Excluir versão");
  });

  it("quem não é ADMIN não vê nenhum botão de escrita, só 'Ver critérios'", () => {
    setup(synthetic().actions, false);

    expect(screen.queryByRole("button", { name: /Nova versão|Excluir versão/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("button").map((b) => b.textContent)).toEqual(["Ver critérios"]);
  });

  it("'Ver critérios' aparece para todos e chama o que a página pediu", async () => {
    const { onShowCriteria, user } = setup([], false);

    await user.click(screen.getByRole("button", { name: "Ver critérios de FASI 2026" }));

    expect(onShowCriteria).toHaveBeenCalledTimes(1);
  });

  it("a ação livre chama run ao clicar", async () => {
    const { actions, run } = synthetic();
    const { user } = setup(actions);

    await user.click(screen.getByRole("button", { name: "Nova versão a partir de FASI 2026" }));

    expect(run).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Nova versão a partir de FASI 2026" })).not.toHaveAttribute("aria-disabled");
  });

  it("GTAB-36: a ação bloqueada fica aria-disabled e focável, com o motivo visível ligado por aria-describedby, e o clique não chama run", async () => {
    const blockedRun = vi.fn();
    const { user } = setup([
      {
        key: "blocked",
        label: "Excluir versão",
        ariaLabel: "Excluir versão FASI 2026",
        run: blockedRun,
        disabledReason: "A versão é usada por 2 processos e não pode ser excluída.",
      },
    ]);
    const button = screen.getByRole("button", { name: "Excluir versão FASI 2026" });

    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).not.toBeDisabled();
    const reason = screen.getByText("A versão é usada por 2 processos e não pode ser excluída.");
    expect(reason).toBeVisible();
    expect(reason.id).not.toBe("");
    expect(button).toHaveAttribute("aria-describedby", reason.id);
    expect(button).toHaveAccessibleDescription("A versão é usada por 2 processos e não pode ser excluída.");
    button.focus();
    expect(button).toHaveFocus();
    await user.click(button);
    expect(blockedRun).not.toHaveBeenCalled();
  });

  it("a ação livre não tem motivo nem aria-describedby", () => {
    setup(synthetic().actions);

    const free = screen.getByRole("button", { name: "Nova versão a partir de FASI 2026" });
    expect(free).not.toHaveAttribute("aria-describedby");
    expect(within(free.closest(".tbl-action") as HTMLElement).queryByText(/processos/)).not.toBeInTheDocument();
  });

  it("os botões ficam na barra da versão (classe com a altura mínima de toque)", () => {
    setup(synthetic().actions);

    const bar = screen.getByRole("button", { name: "Nova versão a partir de FASI 2026" }).closest(".tbl-actions");
    expect(bar).not.toBeNull();
    for (const button of within(bar as HTMLElement).getAllByRole("button")) expect(button).toHaveClass("btn");
  });
});
