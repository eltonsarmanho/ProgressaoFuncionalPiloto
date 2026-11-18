import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";
import { ProfessorForm } from "./ProfessorForm";
import { setCsrfToken } from "../api/client";
import { mockFetch } from "../test/fetchMock";

const UNITS = [
  { id: "u-fasi", name: "Faculdade de Sistemas de Informação", acronym: "FASI", kind: "FACULDADE", parent_id: null, archived: false },
  { id: "u-old", name: "Unidade Antiga", acronym: "OLD", kind: "FACULDADE", parent_id: null, archived: true },
];

const PROFESSOR = {
  id: "p1",
  full_name: "Maria Souza",
  siape: "1234567",
  titration: "DOUTORADO",
  position: "Professor do Magistério Superior",
  career: "MAGISTERIO_SUPERIOR",
  unit_id: "u-fasi",
  faculty: "FASI",
  campus: "Campus Tocantins/Cametá",
  work_regime: "DE",
  archived: false,
  version: 3,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<h1>Painel</h1>} />
        <Route path="/professores/novo" element={<ProfessorForm />} />
        <Route path="/professores/:id" element={<ProfessorForm />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function fillForm(siape: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Nome completo"), "Maria Souza");
  await user.type(screen.getByLabelText("Matrícula SIAPE"), siape);
  await user.selectOptions(screen.getByLabelText("Titulação"), "DOUTORADO");
  await user.type(screen.getByLabelText("Cargo"), "Professor do Magistério Superior");
  await user.selectOptions(screen.getByLabelText("Unidade acadêmica"), "u-fasi");
  await user.type(screen.getByLabelText("Faculdade"), "FASI");
  await user.type(screen.getByLabelText("Campus"), "Campus Tocantins/Cametá");
  await user.selectOptions(screen.getByLabelText("Regime de trabalho"), "DE");
  return user;
}

describe("ProfessorForm", () => {
  it("UI-05: 422 exibe a mensagem junto ao campo siape", async () => {
    mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "POST /api/professors": {
        status: 422,
        body: { detail: [{ field: "siape", message: "A matrícula SIAPE deve conter exatamente 7 dígitos" }] },
      },
    });
    renderAt("/professores/novo");
    const user = await fillForm("12345");
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    const siape = screen.getByLabelText("Matrícula SIAPE");
    expect(await screen.findByText("A matrícula SIAPE deve conter exatamente 7 dígitos")).toBeInTheDocument();
    expect(siape).toHaveAttribute("aria-invalid", "true");
    expect(siape).toHaveAccessibleDescription("A matrícula SIAPE deve conter exatamente 7 dígitos");
    expect(siape.nextElementSibling).toHaveTextContent("A matrícula SIAPE deve conter exatamente 7 dígitos");
    expect(screen.getByLabelText("Nome completo")).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("heading", { name: "Cadastrar docente" })).toBeInTheDocument();
  });

  it("DOC-01: cadastro envia todos os campos com CSRF e volta ao painel", async () => {
    setCsrfToken("csrf-1");
    const { calls } = mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "POST /api/professors": { status: 201, body: PROFESSOR },
    });
    renderAt("/professores/novo");
    expect(await screen.findByRole("option", { name: "FASI — Faculdade de Sistemas de Informação" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /Unidade Antiga/ })).not.toBeInTheDocument();
    const user = await fillForm("1234567");
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByRole("heading", { name: "Painel" })).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST")!;
    expect(new Headers(post.init!.headers).get("X-CSRF-Token")).toBe("csrf-1");
    expect(JSON.parse(post.init!.body as string)).toEqual({
      full_name: "Maria Souza",
      siape: "1234567",
      titration: "DOUTORADO",
      position: "Professor do Magistério Superior",
      unit_id: "u-fasi",
      faculty: "FASI",
      campus: "Campus Tocantins/Cametá",
      work_regime: "DE",
    });
  });

  it("edição carrega o docente e envia PUT com expected_version", async () => {
    const { calls } = mockFetch({
      "GET /api/units": { status: 200, body: UNITS },
      "GET /api/professors/p1": { status: 200, body: PROFESSOR },
      "PUT /api/professors/p1": { status: 200, body: { ...PROFESSOR, campus: "Cametá", version: 4 } },
    });
    renderAt("/professores/p1");
    const campus = await screen.findByDisplayValue("Campus Tocantins/Cametá");
    expect(screen.getByRole("heading", { name: "Editar docente" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.clear(campus);
    await user.type(campus, "Cametá");
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByRole("heading", { name: "Painel" })).toBeInTheDocument();
    const put = calls.find((c) => c.method === "PUT")!;
    expect(JSON.parse(put.init!.body as string)).toMatchObject({
      siape: "1234567",
      campus: "Cametá",
      expected_version: 3,
    });
  });
});
