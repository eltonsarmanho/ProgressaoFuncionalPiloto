import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { ScoringTableInfo } from "../api/types";
import { setCsrfToken } from "../api/client";
import { mockFetch } from "../test/fetchMock";
import { CsvDialog, DuplicateDialog, VersionDialog } from "./ScoringAdminForms";

const TABLE: ScoringTableInfo = {
  id: "t-fasi",
  name: "Tabela da FASI",
  archived: false,
  unit_ids: [],
  archive_blocked_reason: null,
  delete_blocked_reason: null,
  versions: [],
};
const VERSION = { id: "v-fasi", name: "FASI 2022" };

/** GTAB-12, GTAB-13: each of the three forms now opens by itself in a dialog (before, they shared one card). */
function setup(routes: Parameters<typeof mockFetch>[0], which: "duplicate" | "version" | "csv") {
  setCsrfToken("csrf-abc");
  const mock = mockFetch({ ...routes });
  const onChanged = vi.fn();
  const onClose = vi.fn();
  render(
    which === "duplicate" ? (
      <DuplicateDialog table={TABLE} onDone={onChanged} onClose={onClose} />
    ) : which === "version" ? (
      <VersionDialog table={TABLE} version={VERSION} onDone={onChanged} onClose={onClose} />
    ) : (
      <CsvDialog table={TABLE} onDone={onChanged} onClose={onClose} />
    ),
  );
  return { ...mock, onChanged, onClose, user: userEvent.setup() };
}

function call(calls: { method: string; path: string; init?: RequestInit }[], key: string) {
  return calls.find((c) => `${c.method} ${c.path}` === key);
}

describe("ADMUI-02: duplicar tabela", () => {
  it("chama a API com o nome informado e atualiza a lista", async () => {
    const { calls, onChanged, user } = setup({
      "POST /api/scoring-tables/t-fasi/duplicate": { status: 201, body: { id: "t-new" } },
    }, "duplicate");

    await user.type(screen.getByLabelText("Nome da nova tabela"), "Cópia da FASI");
    await user.click(screen.getByRole("button", { name: "Duplicar tabela" }));

    await vi.waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(JSON.parse(String(call(calls, "POST /api/scoring-tables/t-fasi/duplicate")?.init?.body))).toEqual({
      new_name: "Cópia da FASI",
    });
  });

  it("mostra o erro 422 junto ao campo nome e não atualiza a lista", async () => {
    const { onChanged, user } = setup({
      "POST /api/scoring-tables/t-fasi/duplicate": {
        status: 422,
        body: { detail: [{ field: "name", message: "Já existe uma tabela com este nome" }] },
      },
    }, "duplicate");

    await user.type(screen.getByLabelText("Nome da nova tabela"), "Tabela do IFCH");
    await user.click(screen.getByRole("button", { name: "Duplicar tabela" }));

    expect(await screen.findByText("Já existe uma tabela com este nome")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome da nova tabela")).toHaveAttribute("aria-invalid", "true");
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("ADMUI-02: nova versão", () => {
  it("copia a versão selecionada: envia origem, vigência e referência e atualiza a lista", async () => {
    const { calls, onChanged, user } = setup({
      "POST /api/scoring-tables/t-fasi/versions": { status: 201, body: { id: "v-new" } },
    }, "version");

    await user.type(screen.getByLabelText("Início da vigência da nova versão"), "2026-03-01");
    await user.type(screen.getByLabelText("Referência normativa da nova versão"), "Res. 7.000/2026");
    await user.click(screen.getByRole("button", { name: "Criar nova versão" }));

    await vi.waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    expect(JSON.parse(String(call(calls, "POST /api/scoring-tables/t-fasi/versions")?.init?.body))).toEqual({
      source_version_id: "v-fasi",
      valid_from: "2026-03-01",
      norm_reference: "Res. 7.000/2026",
    });
  });

  it("mostra a mensagem do conflito 409 sem atualizar a lista", async () => {
    const { onChanged, user } = setup({
      "POST /api/scoring-tables/t-fasi/versions": {
        status: 409,
        body: { detail: "Há processo com interstício terminando a partir de 23/11/2024" },
      },
    }, "version");

    await user.type(screen.getByLabelText("Início da vigência da nova versão"), "2024-11-23");
    await user.type(screen.getByLabelText("Referência normativa da nova versão"), "Res. 1");
    await user.click(screen.getByRole("button", { name: "Criar nova versão" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Há processo com interstício");
    expect(onChanged).not.toHaveBeenCalled();
  });
});

describe("ADMUI-02: importar CSV", () => {
  const CSV = new File(["grupo,item\n"], "criterios.csv", { type: "text/csv" });

  async function fill(user: ReturnType<typeof userEvent.setup>) {
    await user.upload(screen.getByLabelText("Arquivo CSV"), CSV);
    await user.type(screen.getByLabelText("Início da vigência do CSV"), "2026-03-01");
    await user.type(screen.getByLabelText("Referência normativa do CSV"), "Res. 7.000/2026");
  }

  it("OFI-06: a ajuda lista a coluna opcional min_hours (carga horária mínima)", () => {
    setup({}, "csv");

    const help = screen.getByText(/^Colunas:/);
    expect(help).toHaveTextContent("min_hours (opcional, carga horária mínima em horas; vazio ou ausente = sem mínimo)");
  });

  it("envia o arquivo e os campos em multipart com o token CSRF e atualiza a lista", async () => {
    const { calls, onChanged, user } = setup({
      "POST /api/scoring-tables/t-fasi/versions/import": { status: 201, body: { id: "v-csv" } },
    }, "csv");

    await fill(user);
    await user.click(screen.getByRole("button", { name: "Importar CSV" }));

    await vi.waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
    const sent = call(calls, "POST /api/scoring-tables/t-fasi/versions/import")!;
    const body = sent.init?.body as FormData;
    expect((body.get("file") as File).name).toBe("criterios.csv");
    expect(body.get("valid_from")).toBe("2026-03-01");
    expect(body.get("norm_reference")).toBe("Res. 7.000/2026");
    expect(body.get("status")).toBe("PENDENTE_VALIDACAO");
    expect(new Headers(sent.init?.headers).get("X-CSRF-Token")).toBe("csrf-abc");
    expect(new Headers(sent.init?.headers).has("Content-Type")).toBe(false);
    expect(calls.map((c) => `${c.method} ${c.path}`)).toEqual([
      "POST /api/scoring-tables/t-fasi/versions/import",
    ]);
  });

  it("lista a linha e o campo de cada erro do arquivo", async () => {
    const { onChanged, user } = setup({
      "POST /api/scoring-tables/t-fasi/versions/import": {
        status: 422,
        body: {
          detail: [
            { field: "file", message: "linha 2, campo grupo: deve estar entre 1 e 8" },
            { field: "file", message: "linha 5, campo pontos: número decimal inválido" },
          ],
        },
      },
    }, "csv");

    await fill(user);
    await user.click(screen.getByRole("button", { name: "Importar CSV" }));

    const items = await screen.findAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual([
      "linha 2, campo grupo: deve estar entre 1 e 8",
      "linha 5, campo pontos: número decimal inválido",
    ]);
    expect(onChanged).not.toHaveBeenCalled();
  });

  it("sem arquivo escolhido não envia e pede o arquivo", async () => {
    const { calls, user } = setup({}, "csv");

    await user.type(screen.getByLabelText("Início da vigência do CSV"), "2026-03-01");
    await user.type(screen.getByLabelText("Referência normativa do CSV"), "Res. 1");
    await user.click(screen.getByRole("button", { name: "Importar CSV" }));

    expect(await screen.findByText("Selecione o arquivo CSV.")).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST")).toEqual([]);
  });
});

describe("GTAB-12, GTAB-13, GTAB-16: cada formulário abre sozinho em um diálogo e anuncia o resultado", () => {
  it.each([
    ["duplicate", "Duplicar tabela"],
    ["version", "Nova versão a partir de FASI 2022"],
    ["csv", "Importar CSV como nova versão"],
  ] as const)("o diálogo %s tem o nome '%s' e nenhum dos outros dois formulários", (which, title) => {
    setup({}, which);

    expect(screen.getByRole("dialog", { name: title })).toBeInTheDocument();
    expect(screen.getAllByRole("form")).toHaveLength(1);
  });

  it("o sucesso de cada diálogo entrega a frase que a página anuncia", async () => {
    const dup = setup({ "POST /api/scoring-tables/t-fasi/duplicate": { status: 201, body: { id: "t-new" } } }, "duplicate");
    await dup.user.type(screen.getByLabelText("Nome da nova tabela"), "Cópia");
    await dup.user.click(screen.getByRole("button", { name: "Duplicar tabela" }));
    await vi.waitFor(() => expect(dup.onChanged).toHaveBeenCalledWith("Tabela duplicada."));
  });

  it("'Fechar' fecha o diálogo sem enviar nada", async () => {
    const { calls, onClose, user } = setup({}, "csv");

    await user.click(screen.getByRole("button", { name: "Fechar" }));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(calls).toEqual([]);
  });
});
