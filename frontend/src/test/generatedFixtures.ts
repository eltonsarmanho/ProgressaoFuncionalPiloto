import type {
  ConclusionPreview,
  GeneratedDocument,
  LayoutView,
  ReportDraftView,
  WordingJob,
} from "../api/generated";

/** Synthetic data of the Etapa 5 screens: nothing here comes from a real document. */
export const ACT_A = "a0000000-0000-0000-0000-000000000001";
export const ACT_B = "a0000000-0000-0000-0000-000000000002";
export const DOC_1 = "d0000000-0000-0000-0000-000000000001";
export const DOC_2 = "d0000000-0000-0000-0000-000000000002";

export function draftView(over: Partial<ReportDraftView> = {}): ReportDraftView {
  return {
    process_id: "p1",
    template_id: "ufpa-modelo-2",
    template_version: 1,
    version: 4,
    saved: true,
    sections: [
      {
        key: "1.1",
        title: "Ensino de graduação",
        free_text: "",
        warnings: [],
        entries: [
          { activity_id: ACT_A, text: "Disciplina Algoritmos, 60 h.", source: "MODELO", warnings: [] },
          { activity_id: ACT_B, text: "Disciplina Redes, 45 h.", source: "IA", warnings: [] },
        ],
      },
      { key: "2", title: "Pesquisa", free_text: "", warnings: [], entries: [] },
    ],
    empty_sections: ["2"],
    alerts: [],
    activities: [
      { id: ACT_A, title: "Algoritmos", group_number: 1, item_number: 1, event_date: "2023-03-01", academic_period: "2023.1" },
      { id: ACT_B, title: "Redes", group_number: 1, item_number: 1, event_date: "2023-08-01", academic_period: "2023.2" },
    ],
    item_names: [{ group_number: 1, item_number: 1, name: "Disciplina de graduação" }],
    ...over,
  };
}

export function job(over: Partial<WordingJob> = {}): WordingJob {
  return {
    id: "j1",
    section_key: "1.1",
    state: "GERANDO",
    requested_at: "2026-11-18T10:00:00Z",
    started_at: null,
    finished_at: null,
    error_code: null,
    warnings: [],
    ...over,
  };
}

export function layoutView(over: Partial<LayoutView> = {}): LayoutView {
  return {
    layout: {
      version: 3,
      activities: [
        {
          activity_id: ACT_A,
          group_number: 1,
          item_number: 1,
          pages: [
            { document_id: DOC_1, page: 2, repeat_justification: null },
            { document_id: DOC_1, page: 5, repeat_justification: null },
          ],
        },
        { activity_id: ACT_B, group_number: 1, item_number: 1, pages: [{ document_id: DOC_2, page: 1, repeat_justification: null }] },
      ],
    },
    saved: true,
    staleness: { left_activity_ids: [], moved_activity_ids: [], new_link_activity_ids: [], joined_activity_ids: [] },
    stale: false,
    invalid: [],
    plan: {
      plan_hash: "h".repeat(64),
      pages: [
        { kind: "CAPA", number: 1, group_number: null, document_id: null, source_page: null },
        { kind: "SUMARIO", number: 2, group_number: null, document_id: null, source_page: null },
        { kind: "SEPARADOR", number: 3, group_number: 1, document_id: null, source_page: null },
        { kind: "ORIGINAL", number: 4, group_number: 1, document_id: DOC_1, source_page: 2 },
        { kind: "ORIGINAL", number: 5, group_number: 1, document_id: DOC_1, source_page: 5 },
        { kind: "ORIGINAL", number: 6, group_number: 1, document_id: DOC_2, source_page: 1 },
      ],
      toc: [
        { level: "GRUPO", group_number: 1, item_number: null, activity_id: null, title: "Docência", first_page: 3, last_page: 6, sources: [], note: null },
        {
          level: "ATIVIDADE",
          group_number: 1,
          item_number: 1,
          activity_id: ACT_A,
          title: "Algoritmos",
          first_page: 4,
          last_page: 5,
          sources: [
            { document_id: DOC_1, source_page: 2, comprovante_page: 4, remission: false, justification: null },
            { document_id: DOC_1, source_page: 5, comprovante_page: 5, remission: false, justification: null },
          ],
          note: null,
        },
        {
          level: "ATIVIDADE",
          group_number: 1,
          item_number: 1,
          activity_id: ACT_B,
          title: "Redes",
          first_page: 6,
          last_page: 6,
          sources: [{ document_id: DOC_2, source_page: 1, comprovante_page: 6, remission: false, justification: null }],
          note: null,
        },
      ],
      alerts: [],
    },
    alerts: [],
    ...over,
  };
}

export function generated(over: Partial<GeneratedDocument> = {}): GeneratedDocument {
  return {
    id: "g1",
    process_id: "p1",
    kind: "TABELA",
    state: "PRONTO",
    version_number: 1,
    requested_at: "2026-11-18T10:00:00Z",
    started_at: "2026-11-18T10:00:01Z",
    finished_at: "2026-11-18T10:00:05Z",
    error_code: null,
    error_message: null,
    alerts: [],
    files: [
      { format: "DOCX", size_bytes: 40_960, sha256: "a".repeat(64) },
      { format: "PDF", size_bytes: 61_440, sha256: "b".repeat(64) },
    ],
    ...over,
  };
}

export function preview(over: Partial<ConclusionPreview> = {}): ConclusionPreview {
  return { files: 3, bytes: 5_242_880, artifacts: { TABELA: true, RELATORIO: true, COMPROVANTE: true }, ...over };
}
