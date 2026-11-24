import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ChosenTable, ScoringTableInfo } from "../api/types";
import { mockFetch } from "../test/fetchMock";
import { TablePicker } from "./TablePicker";

const FASI: ChosenTable = {
  table_name: "Tabela FASI",
  version: {
    id: "v-fasi",
    table_id: "t-fasi",
    name: "FASI 2022",
    valid_from: "2022-01-01",
    valid_to: null,
    norm_reference: "Res. FASI 2022, Anexo I",
    status: "PENDENTE_VALIDACAO",
    superseded_by_id: null,
  },
};
const IFCH: ChosenTable = {
  table_name: "Tabela IFCH",
  version: {
    id: "v-ifch",
    table_id: "t-ifch",
    name: "IFCH 2020",
    valid_from: "2020-03-02",
    valid_to: "2024-12-31",
    norm_reference: "Res. IFCH 2020",
    status: "OFICIAL",
    superseded_by_id: null,
  },
};
const SUMMARY = { process_count: 0, default_for_unit_ids: [], read_only_reason: null, delete_blocked_reason: null };
const TABLES: ScoringTableInfo[] = [
  {
    id: "t-fasi",
    name: "Tabela FASI",
    archived: false,
    unit_ids: ["u1"],
    archive_blocked_reason: null,
    delete_blocked_reason: null,
    versions: [{ ...FASI.version, ...SUMMARY, in_use: false }],
  },
  {
    id: "t-ifch",
    name: "Tabela IFCH",
    archived: false,
    unit_ids: ["u2"],
    archive_blocked_reason: null,
    delete_blocked_reason: null,
    versions: [{ ...IFCH.version, ...SUMMARY, process_count: 1, in_use: true }],
  },
];

describe("TablePicker", () => {
  it("TELA-06: sem tabela escolhida mostra a sugestão com nome, situação em destaque e referência", () => {
    render(
      <TablePicker processId="p1" choice={{ chosen: null, suggested: FASI, alerts: [] }} onChanged={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Tabela sugerida" })).toBeInTheDocument();
    expect(screen.getByText(/Tabela FASI/)).toBeInTheDocument();
    const status = screen.getByText("Pendente de validação");
    expect(status).toHaveClass("badge-pending");
    expect(screen.getByText("Referência normativa: Res. FASI 2022, Anexo I")).toBeInTheDocument();
  });

  it("TELA-06: pede confirmação e só grava a tabela ao confirmar", async () => {
    const { calls } = mockFetch({
      "PUT /api/processes/p1/scoring/table": { status: 200, body: { chosen: FASI, suggested: FASI, alerts: [] } },
    });
    const onChanged = vi.fn();
    render(
      <TablePicker processId="p1" choice={{ chosen: null, suggested: FASI, alerts: [] }} onChanged={onChanged} />,
    );
    expect(calls).toHaveLength(0);
    expect(onChanged).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Confirmar tabela e calcular" }));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ version_id: "v-fasi" });
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  it("TELA-06: com tabela escolhida mostra 'Tabela escolhida' e a situação oficial sem destaque", () => {
    render(
      <TablePicker processId="p1" choice={{ chosen: IFCH, suggested: FASI, alerts: [] }} onChanged={vi.fn()} />,
    );
    expect(screen.getByRole("heading", { name: "Tabela escolhida" })).toBeInTheDocument();
    expect(screen.getByText("Oficial")).not.toHaveClass("badge-pending");
    expect(screen.queryByRole("button", { name: /Confirmar tabela/ })).not.toBeInTheDocument();
  });

  it("UIM-18: tabela de outra unidade confirma direto, sem campo de justificativa", async () => {
    const { calls } = mockFetch({
      "PUT /api/processes/p1/scoring/table": { status: 200, body: { chosen: IFCH, suggested: FASI, alerts: [] } },
    });
    const onChanged = vi.fn();
    render(
      <TablePicker
        processId="p1"
        choice={{ chosen: null, suggested: FASI, alerts: [] }}
        tables={TABLES}
        onChanged={onChanged}
      />,
    );
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Escolher outra tabela"), "v-ifch");
    expect(screen.queryByLabelText(/Justificativa/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar tabela e calcular" }));
    expect(JSON.parse(calls[0].init!.body as string)).toEqual({ version_id: "v-ifch" });
    expect(onChanged).toHaveBeenCalledTimes(1);
  });

  it("UIM-18: um erro do servidor ao escolher a tabela aparece como alerta e não recarrega", async () => {
    mockFetch({
      "PUT /api/processes/p1/scoring/table": { status: 409, body: { detail: "O processo foi alterado por outro usuário; recarregue" } },
    });
    const onChanged = vi.fn();
    render(
      <TablePicker
        processId="p1"
        choice={{ chosen: null, suggested: FASI, alerts: [] }}
        tables={TABLES}
        onChanged={onChanged}
      />,
    );
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Escolher outra tabela"), "v-ifch");
    await user.click(screen.getByRole("button", { name: "Confirmar tabela e calcular" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("O processo foi alterado por outro usuário; recarregue");
    expect(onChanged).not.toHaveBeenCalled();
  });

  describe("GI-07: versão substituída", () => {
    const OLD_VERSION = { ...IFCH.version, id: "v-old", name: "Tabela oficial antiga", superseded_by_id: "v-new" };
    const NEW_VERSION = { ...IFCH.version, id: "v-new", name: "Tabela oficial nova", superseded_by_id: null };
    const SUPERSEDED_TABLES: ScoringTableInfo[] = [
      {
        id: "t-ifch",
        name: "Tabela IFCH",
        archived: false,
        unit_ids: ["u2"],
        archive_blocked_reason: null,
        delete_blocked_reason: null,
        versions: [
          { ...OLD_VERSION, ...SUMMARY, process_count: 1, in_use: true },
          { ...NEW_VERSION, ...SUMMARY, in_use: false },
        ],
      },
    ];

    it("a lista de escolha só traz a versão nova", () => {
      render(
        <TablePicker
          processId="p1"
          choice={{ chosen: null, suggested: { table_name: "Tabela IFCH", version: NEW_VERSION }, alerts: [] }}
          tables={SUPERSEDED_TABLES}
          onChanged={vi.fn()}
        />,
      );
      const options = screen.getAllByRole("option").map((o) => o.textContent);
      expect(options).toEqual(["Selecione…", "Tabela IFCH · Tabela oficial nova"]);
    });

    it("processo que ainda usa a versão antiga mostra o nome dela e nenhum botão nem campo de troca", () => {
      render(
        <TablePicker
          processId="p1"
          choice={{ chosen: { table_name: "Tabela IFCH", version: OLD_VERSION }, suggested: null, alerts: [] }}
          tables={SUPERSEDED_TABLES}
          onChanged={vi.fn()}
        />,
      );
      expect(screen.getByRole("heading", { name: "Tabela escolhida" })).toBeInTheDocument();
      expect(screen.getByText(/Tabela oficial antiga/)).toBeInTheDocument();
      expect(screen.queryByRole("button")).not.toBeInTheDocument();
      expect(screen.queryByLabelText("Escolher outra tabela")).not.toBeInTheDocument();
      expect(screen.queryByText(/mais nova/)).not.toBeInTheDocument();
    });

    it("o erro 422 VERSAO_SUBSTITUIDA da API aparece em role=alert e não recarrega", async () => {
      mockFetch({
        "PUT /api/processes/p1/scoring/table": {
          status: 422,
          body: {
            detail: [
              {
                field: "version_id",
                message: "Esta versão da tabela foi substituída; use a versão atual",
                code: "VERSAO_SUBSTITUIDA",
              },
            ],
          },
        },
      });
      const onChanged = vi.fn();
      render(
        <TablePicker
          processId="p1"
          choice={{ chosen: null, suggested: { table_name: "Tabela IFCH", version: NEW_VERSION }, alerts: [] }}
          tables={SUPERSEDED_TABLES}
          onChanged={onChanged}
        />,
      );
      await userEvent.click(screen.getByRole("button", { name: "Confirmar tabela e calcular" }));
      expect(await screen.findByRole("alert")).toHaveTextContent("Esta versão da tabela foi substituída; use a versão atual");
      expect(onChanged).not.toHaveBeenCalled();
    });
  });
});
