import type { BoardView, ChecklistItem, ChecklistState, Opinion, Ordinance, RequestSettings } from "../api/board";

/** Synthetic data of the Etapa 6 screens: no name here belongs to a real person. */
export function ordinance(over: Partial<Ordinance> = {}): Ordinance {
  return {
    number: "123/2026",
    number_page: 1,
    number_source: "EXTRAIDO",
    ordinance_date: "2026-10-05",
    date_page: 1,
    date_source: "EXTRAIDO",
    members: [
      { name: "Ana Sintética", role: "PRESIDENTE", page: 2, source: "EXTRAIDO" },
      { name: "Bruno Fictício", role: "MEMBRO", page: 2, source: "EXTRAIDO" },
      { name: "Carla Exemplo", role: "SUPLENTE", page: 2, source: "EXTRAIDO" },
    ],
    file: { original_name: "portaria-sintetica.pdf", mime: "application/pdf", size_bytes: 2048, page_count: 2, deleted: false },
    reading_state: "LIDA",
    reading_code: null,
    warnings: [],
    version: 3,
    ...over,
  };
}

/** A process with no ordinance yet: the server sends version 0 and nothing else. */
export function emptyOrdinance(over: Partial<Ordinance> = {}): Ordinance {
  return {
    number: null,
    number_page: null,
    number_source: null,
    ordinance_date: null,
    date_page: null,
    date_source: null,
    members: [],
    file: null,
    reading_state: "SEM_ARQUIVO",
    reading_code: null,
    warnings: [],
    version: 0,
    ...over,
  };
}

/** The fields of the Parecer as the server sends them before anyone saved them: no conclusion. */
export function opinion(over: Partial<Opinion> = {}): Opinion {
  return { conclusion: null, opinion_date: null, place: null, notes: null, version: 0, ...over };
}

export function requestSettings(over: Partial<RequestSettings> = {}): RequestSettings {
  return { city: null, version: 0, ...over };
}

export function board(over: Partial<BoardView> = {}): BoardView {
  return { ordinance: ordinance(), opinion: opinion(), request_settings: requestSettings(), ...over };
}

type Row = [key: string, title: string, source: ChecklistItem["source"]];
const DOSSIER_ROWS: Row[] = [
  ["REQUERIMENTO", "Requerimento", "GERADO"],
  ["PORTARIA_ULTIMA_PROGRESSAO", "Portaria da última progressão", "MANUAL"],
  ["DECLARACAO_PAGAMENTO", "Declaração de pagamento de exercícios anteriores", "MANUAL"],
  ["RELATORIO", "Relatório de Atividades", "GERADO"],
  ["TABELA", "Tabela de Pontuação", "GERADO"],
  ["COMPROVANTE", "Comprovante de Documentos", "GERADO"],
  ["CURRICULO_LATTES", "Currículo Lattes", "MANUAL"],
  ["PORTARIA_BANCA", "Portaria da banca", "PORTARIA_BANCA"],
  ["PARECER", "Parecer da banca", "GERADO"],
];

/** The nine items of the dossier, all pending; `over` changes one item by key. */
export function checklist(over: Record<string, Partial<ChecklistItem>> = {}): ChecklistItem[] {
  return DOSSIER_ROWS.map(([key, title, source], i) => ({
    key,
    order: i + 1,
    title,
    source,
    state: "PENDENTE" as ChecklistState,
    version_number: null,
    generation_id: null,
    outdated_table: false,
    ...over[key],
  }));
}
