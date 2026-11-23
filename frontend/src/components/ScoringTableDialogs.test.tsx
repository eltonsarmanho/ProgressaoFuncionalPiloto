import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ScoringTableInfo, Unit } from "../api/types";
import { setCsrfToken } from "../api/client";
import { mockFetch } from "../test/fetchMock";
import { CreateTableDialog } from "./ScoringTableDialogs";

const UNITS: Unit[] = [
  { id: "u1", name: "Faculdade de Sistemas", acronym: "FASI", kind: "FACULDADE", parent_id: null, archived: false },
  { id: "u2", name: "Instituto de Ciências Humanas", acronym: "IFCH", kind: "INSTITUTO", parent_id: null, archived: false },
  { id: "u3", name: "Instituto antigo", acronym: "ICEN", kind: "INSTITUTO", parent_id: null, archived: true },
];

const VERSION = {
  id: "v1",
  table_id: "t1",
  name: "Sintética 2026",
  valid_from: "2026-03-01",
  valid_to: null,
  norm_reference: "Res. sintética 1",
  status: "OFICIAL" as const,
  superseded_by_id: null,
  in_use: false,
  process_count: 0,
  default_for_unit_ids: [],
  read_only_reason: null,
  delete_blocked_reason: null,
};

const TABLES: ScoringTableInfo[] = [
  {
    id: "t1",
    name: "Tabela sintética A",
    archived: false,
    unit_ids: ["u1"],
    archive_blocked_reason: null,
    delete_blocked_reason: null,
    versions: [
      { ...VERSION, id: "v-old", name: "Sintética 2022", valid_to: "2026-02-28", superseded_by_id: "v1" },
      VERSION,
    ],
  },
  {
    id: "t2",
    name: "Tabela sintética B",
    archived: false,
    unit_ids: ["u2"],
    archive_blocked_reason: null,
    delete_blocked_reason: null,
    versions: [{ ...VERSION, id: "v2", table_id: "t2", name: "B 2025" }],
  },
];

function bodyOf(calls: { method: string; path: string; init?: RequestInit }[], key: string) {
  const call = calls.find((c) => `${c.method} ${c.path}` === key);
  return call ? JSON.parse(String(call.init?.body)) : undefined;
}

describe("GTAB-11, GTAB-35: nova tabela", () => {
  function setup(routes: Parameters<typeof mockFetch>[0] = {}) {
    setCsrfToken("csrf-abc");
    const mock = mockFetch({ ...routes });
    const onDone = vi.fn();
    const onClose = vi.fn();
    render(<CreateTableDialog units={UNITS} tables={TABLES} onDone={onDone} onClose={onClose} />);
    return { ...mock, onDone, onClose, user: userEvent.setup() };
  }

  async function fillRequired(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText("Nome da tabela"), "Tabela nova");
    await user.type(screen.getByLabelText("Início da vigência"), "2026-03-01");
    await user.type(screen.getByLabelText("Referência normativa"), "Res. sintética 9/2026");
  }

  it("o diálogo se chama 'Nova tabela', oferece só as unidades não arquivadas e traz a situação, a vigência e a referência", () => {
    setup();

    const dialog = screen.getByRole("dialog", { name: "Nova tabela" });
    const units = within(dialog).getByRole("group", { name: "Unidades associadas" });
    expect(within(units).getAllByRole("checkbox").map((c) => (c as HTMLInputElement).labels?.[0]?.textContent)).toEqual([
      "FASI",
      "IFCH",
    ]);
    expect(within(dialog).getByLabelText("Situação")).toHaveValue("PENDENTE_VALIDACAO");
    expect(within(dialog).getByLabelText("Fim da vigência (opcional)")).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Nome da versão (opcional)")).toBeInTheDocument();
  });

  it("o POST leva nome, unidades, situação, vigência, referência, nome da versão e a versão de origem", async () => {
    const { calls, onDone, user } = setup({
      "POST /api/scoring-tables": { status: 201, body: { id: "t-new", name: "Tabela nova" } },
    });

    await fillRequired(user);
    await user.click(screen.getByRole("checkbox", { name: "FASI" }));
    await user.click(screen.getByRole("checkbox", { name: "IFCH" }));
    await user.selectOptions(screen.getByLabelText("Situação"), "OFICIAL");
    await user.type(screen.getByLabelText("Fim da vigência (opcional)"), "2027-02-28");
    await user.type(screen.getByLabelText("Nome da versão (opcional)"), "Nova 2026");
    await user.selectOptions(screen.getByLabelText("Copiar critérios de (opcional)"), "v2");
    await user.click(screen.getByRole("button", { name: "Criar tabela" }));

    await vi.waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(bodyOf(calls, "POST /api/scoring-tables")).toEqual({
      name: "Tabela nova",
      unit_ids: ["u1", "u2"],
      status: "OFICIAL",
      valid_from: "2026-03-01",
      valid_to: "2027-02-28",
      norm_reference: "Res. sintética 9/2026",
      version_name: "Nova 2026",
      base_version_id: "v2",
    });
  });

  it("sem os campos opcionais o POST não os envia (nem unidades marcadas) e o aviso de sucesso vai em texto", async () => {
    const { calls, onDone, user } = setup({
      "POST /api/scoring-tables": { status: 201, body: { id: "t-new", name: "Tabela nova" } },
    });

    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Criar tabela" }));

    await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('Tabela "Tabela nova" criada.'));
    expect(bodyOf(calls, "POST /api/scoring-tables")).toEqual({
      name: "Tabela nova",
      unit_ids: [],
      status: "PENDENTE_VALIDACAO",
      valid_from: "2026-03-01",
      norm_reference: "Res. sintética 9/2026",
    });
  });

  it("'Copiar critérios de' lista 'Tabela · Versão' e deixa de fora a versão substituída", () => {
    setup();

    const select = screen.getByLabelText("Copiar critérios de (opcional)");
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Não copiar",
      "Tabela sintética A · Sintética 2026",
      "Tabela sintética B · B 2025",
    ]);
  });

  it("nome repetido (422 em name) aparece junto do campo e mantém o que foi digitado", async () => {
    const { onDone, user } = setup({
      "POST /api/scoring-tables": {
        status: 422,
        body: { detail: [{ field: "name", message: "Já existe uma tabela com este nome" }] },
      },
    });

    await fillRequired(user);
    await user.click(screen.getByRole("checkbox", { name: "FASI" }));
    await user.click(screen.getByRole("button", { name: "Criar tabela" }));

    expect(await screen.findByText("Já existe uma tabela com este nome")).toBeInTheDocument();
    const name = screen.getByLabelText("Nome da tabela");
    expect(name).toHaveAttribute("aria-invalid", "true");
    expect(name).toHaveValue("Tabela nova");
    expect(screen.getByLabelText("Referência normativa")).toHaveValue("Res. sintética 9/2026");
    expect(screen.getByRole("checkbox", { name: "FASI" })).toBeChecked();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("o 422 de unit_ids aparece junto do grupo de unidades", async () => {
    const { user } = setup({
      "POST /api/scoring-tables": {
        status: 422,
        body: { detail: [{ field: "unit_ids", message: "Unidade acadêmica não encontrada" }] },
      },
    });

    await fillRequired(user);
    await user.click(screen.getByRole("button", { name: "Criar tabela" }));

    const message = await screen.findByText("Unidade acadêmica não encontrada");
    const group = screen.getByRole("group", { name: "Unidades associadas" });
    expect(group).toHaveAttribute("aria-invalid", "true");
    expect(group).toHaveAttribute("aria-describedby", message.id);
  });

  it("'Fechar' fecha o diálogo sem enviar nada", async () => {
    const { calls, onClose, user } = setup();

    await user.click(screen.getByRole("button", { name: "Fechar" }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(calls).toEqual([]);
  });
});
