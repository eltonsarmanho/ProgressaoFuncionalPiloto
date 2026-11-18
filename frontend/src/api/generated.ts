/**
 * Types of the generated documents API (documentos-gerados, UIG-01): the generation rows, the
 * report draft and its wording jobs, the arrangement and plan of the Comprovante, the dossier
 * order and the conclusion. They follow `backend/app/presentation/schemas/generated.py`.
 *
 * Decimals and dates travel as strings, as in `types.ts`. Everything a refusal or an alert can say
 * is a code of `GENERATION_CODES` or `GENERATION_ALERT_CODES`, so a missing label is a compile
 * error in `labels.ts`.
 */
import type { ProcessStatus } from "./types";

export type DocumentKind = "TABELA" | "RELATORIO" | "COMPROVANTE";
export type GenerationState = "GERANDO" | "PRONTO" | "FALHOU";
/** The format of a file; in a download URL the extension is lowercase (`/files/pdf`). */
export type DocumentFormat = "DOCX" | "PDF";
export type EntrySource = "MODELO" | "IA" | "USUARIO";
export type PageKind = "CAPA" | "SUMARIO" | "SEPARADOR" | "ORIGINAL";
export type TocLevel = "GRUPO" | "ITEM" | "ATIVIDADE";

export const DOCUMENT_KINDS: DocumentKind[] = ["TABELA", "RELATORIO", "COMPROVANTE"];
export const DOCUMENT_FORMATS: DocumentFormat[] = ["DOCX", "PDF"];

/** Refusals and failures: a 422 or 409 `code`, or the `error_code` of a row or a job. */
export const GENERATION_CODES = [
  "SEM_ATIVIDADES_VALIDADAS",
  "TABELA_NAO_ESCOLHIDA",
  "ATIVIDADE_SEM_DESCRICAO",
  "COMPROVANTE_GRANDE_DEMAIS",
  "IMAGEM_GRANDE_DEMAIS",
  "ORIGINAL_INDISPONIVEL",
  "ORIGINAIS_EXCLUIDOS",
  "INTERROMPIDA",
  "ESPACO_INSUFICIENTE",
  "ERRO_INTERNO",
  "GERACAO_EM_ANDAMENTO",
  "REDACAO_EM_ANDAMENTO",
  "ARTEFATOS_PENDENTES",
  "CONFIRMACAO_OBRIGATORIA",
  "OPERACAO_EM_ANDAMENTO",
  "CONCLUSAO_EXIGE_EXCLUSAO",
  "ARQUIVO_EXCLUIDO",
  "PAGINA_FORA_DO_DOCUMENTO",
  "VERSAO_DESATUALIZADA",
  "PROCESSO_SOMENTE_LEITURA",
] as const;
export type GenerationCode = (typeof GENERATION_CODES)[number];

/** Alerts that travel with a result without refusing it. */
export const GENERATION_ALERT_CODES = [
  "ATIVIDADE_SEM_COMPROVANTE",
  "REDACAO_REJEITADA",
  "REDACAO_INDISPONIVEL",
  "ARRANJO_DESATUALIZADO",
  "NUMERACAO_DIVERGENTE",
  "ATIVIDADES_FORA_DO_DOCUMENTO",
  "PAGINA_REPETIDA_JUSTIFICADA",
  "PAGINA_RASTERIZADA",
  "RASCUNHO_DESATUALIZADO",
  "EXCLUSAO_PARCIAL",
] as const;
export type GenerationAlertCode = (typeof GENERATION_ALERT_CODES)[number];

/** An alert with the text the server wrote (the label of the code is in `labels.ts`). */
export type GenerationAlert = { code: GenerationAlertCode; message: string };

// ---- generation rows and versions ------------------------------------------------------------

export type GeneratedFile = { format: DocumentFormat; size_bytes: number; sha256: string };

export type GeneratedDocument = {
  id: string;
  process_id: string;
  kind: DocumentKind;
  state: GenerationState;
  /** Set only when the row is PRONTO: a failed generation does not use a number. */
  version_number: number | null;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_code: GenerationCode | null;
  error_message: string | null;
  alerts: GenerationAlert[];
  files: GeneratedFile[];
};

/** What a version used, in short; the full snapshot stays on the server. */
export type SnapshotSummary = {
  table_name: string | null;
  norm_reference: string | null;
  interstice_start: string | null;
  interstice_end: string | null;
  total: string | null;
  subtotals: Record<string, string>;
  pit_total_hours: string | null;
  activity_count: number;
  excluded: Record<string, number>;
};

export type GeneratedDocumentDetail = GeneratedDocument & { summary: SnapshotSummary | null };

export type GenerationRequest = { kind: DocumentKind };

// ---- report draft and wording ----------------------------------------------------------------

export type DraftEntry = {
  activity_id: string;
  text: string;
  source: EntrySource;
  warnings: GenerationAlert[];
};

export type DraftSection = {
  key: string;
  title: string;
  free_text: string;
  entries: DraftEntry[];
  warnings: GenerationAlert[];
};

/** The draft as the writes return it. */
export type ReportDraft = {
  process_id: string;
  template_id: string;
  template_version: number;
  /** 0 for a proposal that was never saved; the first write sends `expected_version: 0`. */
  version: number;
  sections: DraftSection[];
};

export type ActivityRef = {
  id: string;
  title: string;
  group_number: number | null;
  item_number: number | null;
  event_date: string | null;
  academic_period: string | null;
};

export type ItemName = { group_number: number; item_number: number; name: string };

/** `GET /processes/{id}/report-draft`: the draft with what the screen needs around it. */
export type ReportDraftView = ReportDraft & {
  saved: boolean;
  empty_sections: string[];
  alerts: GenerationAlert[];
  activities: ActivityRef[];
  item_names: ItemName[];
};

export type EntryTextBody = { expected_version: number; text: string };
export type SectionTextBody = { expected_version: number; free_text: string };
export type MoveEntryBody = { expected_version: number; section_key: string };

/** The wording task of one section (`POST .../sections/{key}/wording` and `GET .../wording`). */
export type WordingJob = {
  id: string;
  section_key: string;
  state: GenerationState;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_code: GenerationCode | null;
  warnings: GenerationAlert[];
};

// ---- arrangement and plan of the Comprovante -------------------------------------------------

export type LayoutPage = { document_id: string; page: number; repeat_justification: string | null };

export type LayoutActivity = {
  activity_id: string;
  group_number: number | null;
  item_number: number | null;
  pages: LayoutPage[];
};

export type Layout = {
  /** 0 for an arrangement derived and never saved. */
  version: number;
  activities: LayoutActivity[];
};

export type Staleness = {
  left_activity_ids: string[];
  moved_activity_ids: string[];
  new_link_activity_ids: string[];
  joined_activity_ids: string[];
};

/** A page link of the arrangement that points to a document or page that is no longer there. */
export type EvidenceKey = { activity_id: string; document_id: string; page: number };

export type PlanPage = {
  kind: PageKind;
  number: number;
  group_number: number | null;
  document_id: string | null;
  source_page: number | null;
};

export type PageRef = {
  document_id: string;
  source_page: number;
  comprovante_page: number;
  remission: boolean;
  justification: string | null;
};

export type TocEntry = {
  level: TocLevel;
  group_number: number;
  item_number: number | null;
  activity_id: string | null;
  title: string;
  first_page: number | null;
  last_page: number | null;
  sources: PageRef[];
  note: string | null;
};

export type PlanAlert = {
  code: GenerationAlertCode;
  activity_id: string;
  document_id: string | null;
  page: number | null;
  justification: string | null;
};

/** The numbering the Comprovante will have (page 1 is the cover). */
export type Plan = { plan_hash: string; pages: PlanPage[]; toc: TocEntry[]; alerts: PlanAlert[] };

export type LayoutView = {
  layout: Layout;
  saved: boolean;
  staleness: Staleness;
  stale: boolean;
  invalid: EvidenceKey[];
  plan: Plan;
  alerts: GenerationAlert[];
};

export type LayoutSaveBody = {
  expected_version: number;
  activities: {
    activity_id: string;
    pages: { document_id: string; page: number; repeat_justification?: string | null }[];
    group_number?: number | null;
    item_number?: number | null;
  }[];
};

// ---- dossier order and conclusion ------------------------------------------------------------

export type DossierItem = { order: number; title: string; generated_by: DocumentKind | null };

/** `GET /processes/{id}/conclusion`: what concluding frees and which kinds have a ready version. */
export type ConclusionPreview = { files: number; bytes: number; artifacts: Record<DocumentKind, boolean> };

export type ConclusionBody = { expected_version: number; confirmar: boolean; justificativa?: string | null };

export type ConclusionResult = {
  status: ProcessStatus;
  arquivos_removidos: number;
  arquivos_pendentes: number;
  bytes_liberados: number;
  alertas: GenerationAlert[];
};
