import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ScoringTableInfo, Unit } from "../api/types";
import { setCsrfToken } from "../api/client";
import { mockFetch } from "../test/fetchMock";
import { CreateTableDialog, HistoryDialog, SetDefaultDialog, UnitsDialog } from "./ScoringTableDialogs";

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

describe("GTAB-14, GTAB-43, GTAB-16: unidades da tabela", () => {
  const WITH_ARCHIVED: ScoringTableInfo = { ...TABLES[0], unit_ids: ["u1", "u3"] };

  function setup(routes: Parameters<typeof mockFetch>[0] = {}, table: ScoringTableInfo = WITH_ARCHIVED) {
    setCsrfToken("csrf-abc");
    const mock = mockFetch({ ...routes });
    const onDone = vi.fn();
    const onClose = vi.fn();
    render(<UnitsDialog table={table} units={UNITS} onDone={onDone} onClose={onClose} />);
    return { ...mock, onDone, onClose, user: userEvent.setup() };
  }

  it("mostra as unidades da tabela marcadas e a arquivada que ela já tem, marcada e rotulada", () => {
    setup();

    const dialog = screen.getByRole("dialog", { name: "Unidades da tabela Tabela sintética A" });
    expect(within(dialog).getByRole("checkbox", { name: "FASI" })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: "IFCH" })).not.toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: "ICEN (arquivada)" })).toBeChecked();
  });

  it("uma unidade arquivada que a tabela não tem não é oferecida", () => {
    setup({}, { ...TABLES[0], unit_ids: ["u1"] });

    expect(screen.queryByRole("checkbox", { name: /ICEN/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("checkbox")).toHaveLength(2);
  });

  it("o PUT leva todas as unidades marcadas, inclusive a arquivada que a tabela já tinha, e o sucesso é anunciado", async () => {
    const { calls, onDone, user } = setup({
      "PUT /api/scoring-tables/t1/units": { status: 200, body: { id: "t1" } },
    });

    await user.click(screen.getByRole("checkbox", { name: "IFCH" }));
    await user.click(screen.getByRole("button", { name: "Salvar unidades" }));

    await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith('Unidades da tabela "Tabela sintética A" atualizadas.'));
    expect(bodyOf(calls, "PUT /api/scoring-tables/t1/units")).toEqual({ unit_ids: ["u1", "u2", "u3"] });
  });

  it("tirar uma unidade a remove do corpo do PUT", async () => {
    const { calls, onDone, user } = setup({
      "PUT /api/scoring-tables/t1/units": { status: 200, body: { id: "t1" } },
    });

    await user.click(screen.getByRole("checkbox", { name: "FASI" }));
    await user.click(screen.getByRole("button", { name: "Salvar unidades" }));

    await vi.waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
    expect(bodyOf(calls, "PUT /api/scoring-tables/t1/units")).toEqual({ unit_ids: ["u3"] });
  });

  it("o 409 de unidade com versão em uso mostra as siglas, mantém as marcações e não anuncia sucesso", async () => {
    const withMark: ScoringTableInfo = {
      ...WITH_ARCHIVED,
      versions: [{ ...VERSION, default_for_unit_ids: ["u1"] }],
    };
    const { onDone, user } = setup(
      {
        "PUT /api/scoring-tables/t1/units": {
          status: 409,
          body: { detail: "texto do servidor", code: "UNIDADE_COM_VERSAO_EM_USO" },
        },
      },
      withMark,
    );

    await user.click(screen.getByRole("checkbox", { name: "FASI" }));
    await user.click(screen.getByRole("button", { name: "Salvar unidades" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("A unidade FASI tem versão desta tabela em uso; desmarque a versão antes de retirar a unidade.");
    expect(alert).not.toHaveTextContent("texto do servidor");
    expect(screen.getByRole("checkbox", { name: "FASI" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "ICEN (arquivada)" })).toBeChecked();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("se a tela não sabe as siglas do 409, mostra o texto do servidor, que já as traz", async () => {
    const { user } = setup({
      "PUT /api/scoring-tables/t1/units": {
        status: 409,
        body: { detail: "A tabela tem versão em uso da unidade FASI; desmarque a versão antes de retirá-la", code: "UNIDADE_COM_VERSAO_EM_USO" },
      },
    });

    await user.click(screen.getByRole("checkbox", { name: "FASI" }));
    await user.click(screen.getByRole("button", { name: "Salvar unidades" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("da unidade FASI; desmarque a versão antes de retirá-la");
  });
});

describe("GTAB-02, GTAB-16, GTAB-35: definir como em uso com várias unidades", () => {
  const TWO_UNITS: ScoringTableInfo = {
    ...TABLES[0],
    unit_ids: ["u1", "u2"],
    versions: [{ ...VERSION, default_for_unit_ids: ["u1"] }],
  };

  function setup(routes: Parameters<typeof mockFetch>[0] = {}) {
    setCsrfToken("csrf-abc");
    const mock = mockFetch({ ...routes });
    const onDone = vi.fn();
    const onClose = vi.fn();
    render(
      <SetDefaultDialog table={TWO_UNITS} version={TWO_UNITS.versions[0]} units={UNITS} onDone={onDone} onClose={onClose} />,
    );
    return { ...mock, onDone, onClose, user: userEvent.setup() };
  }

  it("pergunta a unidade, mostra desabilitada a que já tem a versão e oferece só as unidades da tabela", () => {
    setup();

    const dialog = screen.getByRole("dialog", { name: "Definir Sintética 2026 como em uso" });
    const group = within(dialog).getByRole("group", { name: "Unidade" });
    expect(within(group).getAllByRole("radio").map((r) => (r as HTMLInputElement).labels?.[0]?.textContent)).toEqual([
      "FASI (já é a versão em uso)",
      "IFCH",
    ]);
    expect(within(group).getByRole("radio", { name: /FASI/ })).toBeDisabled();
    expect(within(group).getByRole("radio", { name: "IFCH" })).toBeEnabled();
  });

  it("envia o PUT só para a unidade escolhida e anuncia a confirmação", async () => {
    const { calls, onDone, user } = setup({
      "PUT /api/scoring-units/u2/default-version": { status: 200, body: { unit_id: "u2", version_id: "v1" } },
    });

    await user.click(screen.getByRole("radio", { name: "IFCH" }));
    await user.click(screen.getByRole("button", { name: "Definir como em uso" }));

    await vi.waitFor(() => expect(onDone).toHaveBeenCalledWith("Sintética 2026 é agora a versão em uso de IFCH."));
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual(["PUT /api/scoring-units/u2/default-version"]);
    expect(bodyOf(calls, "PUT /api/scoring-units/u2/default-version")).toEqual({ version_id: "v1" });
  });

  it("sem unidade escolhida não envia e pede a unidade junto do campo", async () => {
    const { calls, onDone, user } = setup();

    await user.click(screen.getByRole("button", { name: "Definir como em uso" }));

    expect(await screen.findByText("Escolha a unidade.")).toBeInTheDocument();
    expect(calls).toEqual([]);
    expect(onDone).not.toHaveBeenCalled();
  });

  it("o 409 da API aparece como texto no diálogo e nada é anunciado", async () => {
    const { onDone, user } = setup({
      "PUT /api/scoring-units/u2/default-version": {
        status: 409,
        body: { detail: "A tabela está arquivada", code: "TABELA_ARQUIVADA" },
      },
    });

    await user.click(screen.getByRole("radio", { name: "IFCH" }));
    await user.click(screen.getByRole("button", { name: "Definir como em uso" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("A tabela está arquivada");
    expect(onDone).not.toHaveBeenCalled();
  });

  it("o 422 de unit_id aparece junto do campo", async () => {
    const { user } = setup({
      "PUT /api/scoring-units/u2/default-version": {
        status: 422,
        body: { detail: [{ field: "unit_id", message: "A tabela não está associada à unidade" }] },
      },
    });

    await user.click(screen.getByRole("radio", { name: "IFCH" }));
    await user.click(screen.getByRole("button", { name: "Definir como em uso" }));

    expect(await screen.findByText("A tabela não está associada à unidade")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Unidade" })).toHaveAttribute("aria-invalid", "true");
  });
});

describe("GTAB-17, GTAB-35: histórico da tabela", () => {
  const UUID_VERSION = "33333333-3333-4333-8333-333333333333";
  const UUID_ADMIN = "44444444-4444-4444-8444-444444444444";
  const UUID_GONE = "55555555-5555-4555-8555-555555555555";
  const HISTORY = {
    versions: [
      { ...VERSION, id: UUID_VERSION, name: "Sintética 2026", valid_from: "2026-03-01", valid_to: null, norm_reference: "Res. sintética 1", status: "OFICIAL" },
    ],
    events: [
      {
        id: 1,
        occurred_at: "2026-11-20T15:00:00Z",
        user_id: UUID_ADMIN,
        entity: "scoring_table",
        entity_id: "t1",
        action: "ARCHIVE",
        changes: { archived: { before: false, after: true } },
        justification: null,
      },
      {
        id: 2,
        occurred_at: "2026-11-21T15:00:00Z",
        user_id: null,
        entity: "scoring_version",
        entity_id: UUID_VERSION,
        action: "UPDATE",
        changes: { "criteria.2.7.unit_points": { before: "10", after: "12" } },
        justification: "Res. sintética 3, art. 2º",
      },
      {
        id: 3,
        occurred_at: "2026-11-22T15:00:00Z",
        user_id: UUID_GONE,
        entity: "scoring_table",
        entity_id: "t1",
        action: "UPDATE",
        changes: { unit_ids: { before: ["u1"], after: ["u1", "u2"] } },
        justification: null,
      },
    ],
  };
  const USERS = [{ id: UUID_ADMIN, name: "Maria Admin", role: "ADMIN" }];

  function setup(routes: Parameters<typeof mockFetch>[0] = {}) {
    setCsrfToken("csrf-abc");
    const mock = mockFetch({
      "GET /api/scoring-tables/t1/history": { status: 200, body: HISTORY },
      "GET /api/users": { status: 200, body: USERS },
      ...routes,
    });
    const onClose = vi.fn();
    render(<HistoryDialog table={TABLES[0]} units={UNITS} onClose={onClose} />);
    return { ...mock, onClose, user: userEvent.setup() };
  }

  it("mostra as versões com vigência, situação e referência", async () => {
    setup();

    const versions = await screen.findByRole("list", { name: "Versões da tabela" });
    expect(versions).toHaveTextContent("Sintética 2026");
    expect(versions).toHaveTextContent("01/03/2026 a em aberto");
    expect(versions).toHaveTextContent("Oficial");
    expect(versions).toHaveTextContent("Res. sintética 1");
  });

  it("mostra cada evento com data, nome do autor ('Sistema' sem usuário, 'Usuário removido' para id desconhecido), ação e o que mudou", async () => {
    setup();

    const events = await screen.findByRole("list", { name: "Eventos de auditoria" });
    const [archive, edit, units] = within(events).getAllByRole("listitem");
    expect(archive).toHaveTextContent("20/11/2026");
    expect(archive).toHaveTextContent("Maria Admin");
    expect(archive).toHaveTextContent("Arquivamento");
    expect(archive).toHaveTextContent("Tabela");
    expect(archive).toHaveTextContent("Arquivada: não → sim");
    expect(edit).toHaveTextContent("Sistema");
    expect(edit).toHaveTextContent("Alteração");
    expect(edit).toHaveTextContent('Versão "Sintética 2026"');
    expect(edit).toHaveTextContent("II.7: Pontos por unidade: 10 → 12");
    expect(edit).toHaveTextContent("Referência: Res. sintética 3, art. 2º");
    expect(units).toHaveTextContent("Usuário removido");
    expect(units).toHaveTextContent("Unidades: FASI → FASI, IFCH");
  });

  it("nenhum UUID aparece no diálogo", async () => {
    setup();

    const dialog = await screen.findByRole("dialog", { name: "Histórico de Tabela sintética A" });
    await screen.findByRole("list", { name: "Eventos de auditoria" });
    expect(dialog.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
  });

  it("mostra 'Carregando…' enquanto os dados não chegam", async () => {
    setup();

    expect(screen.getByText("Carregando…")).toBeInTheDocument();
    await screen.findByRole("list", { name: "Eventos de auditoria" });
    expect(screen.queryByText("Carregando…")).not.toBeInTheDocument();
  });

  it("se a API falha mostra o erro e 'Tentar de novo' carrega o histórico", async () => {
    let loads = 0;
    const { user } = setup({
      "GET /api/scoring-tables/t1/history": () => {
        loads += 1;
        return loads === 1 ? { status: 500, body: { detail: "Falha no servidor" } } : { status: 200, body: HISTORY };
      },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Falha no servidor");
    await user.click(screen.getByRole("button", { name: "Tentar de novo" }));

    expect(await screen.findByRole("list", { name: "Eventos de auditoria" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("sem eventos diz que não há eventos", async () => {
    setup({ "GET /api/scoring-tables/t1/history": { status: 200, body: { ...HISTORY, events: [] } } });

    expect(await screen.findByText("Nenhum evento registrado.")).toBeInTheDocument();
  });
});
