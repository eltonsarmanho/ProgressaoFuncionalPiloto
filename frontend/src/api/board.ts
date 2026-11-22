/**
 * Client of the board and dossier API (banca-parecer): the ordinance of the board, the fields of the
 * Parecer, the city of the Requerimento and the checklist of the dossier. The types follow
 * `backend/app/presentation/schemas/board.py` and `schemas/generated.py` (`ChecklistItemOut`).
 *
 * Dates travel as `YYYY-MM-DD` strings, as in `types.ts`. The first save of each part sends
 * `expected_version` 0; a stale version is a 409 `VERSAO_DESATUALIZADA` and a value over a limit is a
 * 422 that names the field (`members[1].name`, `place`, `notes`, `city`). No call asks for a
 * justification (regra 5).
 */
import { request } from "./client";

export const BOARD_ROLES = ["PRESIDENTE", "MEMBRO", "SUPLENTE"] as const;
export type BoardRole = (typeof BOARD_ROLES)[number];

/** Where a value came from: read from the ordinance or typed by the person. */
export const VALUE_SOURCES = ["EXTRAIDO", "INFORMADO"] as const;
export type ValueSource = (typeof VALUE_SOURCES)[number];

export const READING_STATES = ["SEM_ARQUIVO", "PENDENTE", "LENDO", "LIDA", "FALHOU"] as const;
export type ReadingState = (typeof READING_STATES)[number];

/** Why a reading failed (PORT-07). */
export const READING_CODES = [
  "IA_INDISPONIVEL",
  "IA_CREDENCIAL_RECUSADA",
  "RESPOSTA_INVALIDA",
  "TEXTO_ILEGIVEL",
  "INTERROMPIDA",
  "ERRO_INTERNO",
] as const;
export type ReadingCode = (typeof READING_CODES)[number];

export const ORDINANCE_WARNING_CODES = ["VALOR_SEM_ORIGEM", "MEMBROS_NAO_ENCONTRADOS"] as const;
export type OrdinanceWarningCode = (typeof ORDINANCE_WARNING_CODES)[number];

export type OpinionConclusion = "FAVORAVEL" | "DESFAVORAVEL";

export type BoardMember = { name: string; role: BoardRole; page: number | null; source: ValueSource };

export type OrdinanceFile = {
  original_name: string;
  mime: string;
  size_bytes: number;
  page_count: number | null;
  /** The file left the disk when the process was concluded; the data stay. */
  deleted: boolean;
};

export type OrdinanceWarning = { code: OrdinanceWarningCode; field: string };

export type Ordinance = {
  number: string | null;
  number_page: number | null;
  number_source: ValueSource | null;
  ordinance_date: string | null;
  date_page: number | null;
  date_source: ValueSource | null;
  members: BoardMember[];
  file: OrdinanceFile | null;
  reading_state: ReadingState;
  reading_code: ReadingCode | null;
  warnings: OrdinanceWarning[];
  version: number;
};

/** The fields of the Parecer; `conclusion` has no initial value and the system never suggests it. */
export type Opinion = {
  conclusion: OpinionConclusion | null;
  opinion_date: string | null;
  place: string | null;
  notes: string | null;
  version: number;
};

export type RequestSettings = { city: string | null; version: number };

export type BoardView = { ordinance: Ordinance; opinion: Opinion; request_settings: RequestSettings };

export type OrdinanceBody = {
  number: string | null;
  ordinance_date: string | null;
  members: { name: string; role: BoardRole }[];
  expected_version: number;
};

export type OpinionBody = {
  conclusion: OpinionConclusion | null;
  opinion_date: string | null;
  place: string | null;
  notes: string | null;
  expected_version: number;
};

export const CHECKLIST_STATES = ["GERADO", "REGISTRADA", "ENTREGUE", "PENDENTE"] as const;
export type ChecklistState = (typeof CHECKLIST_STATES)[number];
export type DossierSource = "GERADO" | "PORTARIA_BANCA" | "MANUAL";

/** One document of the dossier of a process and where it stands (DOS-01 to DOS-06). */
export type ChecklistItem = {
  key: string;
  order: number;
  title: string;
  source: DossierSource;
  state: ChecklistState;
  version_number: number | null;
  generation_id: string | null;
  /** The last Tabela was generated with another version of the scoring table (DOS-06). */
  outdated_table: boolean;
};

export const getBoard = (processId: string) => request<BoardView>("GET", `/api/processes/${processId}/board`);

export const saveOrdinance = (processId: string, body: OrdinanceBody) =>
  request<Ordinance>("PUT", `/api/processes/${processId}/board/ordinance`, body);

/** PORT-01, PORT-08: `replace` confirms that a file already stored is substituted. */
export function uploadOrdinance(processId: string, file: File, expectedVersion: number, replace: boolean) {
  const form = new FormData();
  form.set("file", file);
  form.set("expected_version", String(expectedVersion));
  form.set("replace", String(replace));
  return request<Ordinance>("PUT", `/api/processes/${processId}/board/ordinance/file`, form);
}

export const rereadOrdinance = (processId: string, expectedVersion: number) =>
  request<Ordinance>("POST", `/api/processes/${processId}/board/ordinance/reread`, { expected_version: expectedVersion });

export const saveOpinion = (processId: string, body: OpinionBody) =>
  request<Opinion>("PUT", `/api/processes/${processId}/board/opinion`, body);

export const saveCity = (processId: string, city: string | null, expectedVersion: number) =>
  request<RequestSettings>("PUT", `/api/processes/${processId}/request-settings`, {
    city,
    expected_version: expectedVersion,
  });

export const getDossier = (processId: string) => request<ChecklistItem[]>("GET", `/api/processes/${processId}/dossier`);

/** DOS-04: marks or unmarks "Entregue" on an item the system does not produce; returns the new list. */
export const setDelivered = (processId: string, key: string, entregue: boolean) =>
  request<ChecklistItem[]>("PUT", `/api/processes/${processId}/dossier/items/${key}`, { entregue });
