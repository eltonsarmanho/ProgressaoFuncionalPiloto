export type Severity = "ERRO" | "ALERTA" | "REQUER_ANALISE_NORMATIVA";
export type ProcessStatus = "RASCUNHO" | "EM_ANDAMENTO" | "CONCLUIDO" | "ARQUIVADO";
export type Modality = "PROGRESSAO" | "PROMOCAO";

export type Interstice = { months: number; days: number };

export type ProcessSummary = {
  id: string;
  status: ProcessStatus;
  professor_id: string;
  professor_name: string;
  unit_id: string;
  modality: Modality;
  start_date: string;
  end_date: string;
  interstice: Interstice;
  alert_counts: Record<Severity, number>;
};

export type Unit = {
  id: string;
  name: string;
  acronym: string;
  kind: "CAMPUS" | "INSTITUTO" | "FACULDADE";
  parent_id: string | null;
  archived: boolean;
};

export type Titration = "GRADUACAO" | "ESPECIALIZACAO" | "MESTRADO" | "DOUTORADO";
export type WorkRegime = "20H" | "40H" | "DE";

export type Professor = {
  id: string;
  full_name: string;
  siape: string;
  titration: Titration;
  position: string;
  career: string;
  unit_id: string;
  faculty: string;
  campus: string;
  work_regime: WorkRegime;
  archived: boolean;
  version: number;
};

export type Alert = {
  code: string;
  severity: Severity;
  message: string;
  norm_reference: string;
};

export type ProcessFields = {
  modality: Modality;
  current_class: string;
  current_denomination: string;
  current_level: number;
  target_class: string;
  target_denomination: string;
  target_level: number;
  start_date: string;
  end_date: string;
  opening_date: string;
  notes: string | null;
  resp_name: string | null;
  resp_position: string | null;
  resp_appointment: string | null;
  resp_admin_unit: string | null;
};

export type Process = ProcessFields & {
  id: string;
  professor_id: string;
  unit_id: string;
  status: ProcessStatus;
  version: number;
  created_at: string | null;
  updated_at: string | null;
  interstice: Interstice;
  alerts: Alert[];
};

/* ---- Pontuação (Etapa 4) ---- */

export type RowStatus = "PONTUADA" | "POTENCIAL" | "NAO_PONTUADA";
export type ActivityStatus = "AGUARDANDO_REVISAO" | "VALIDADA" | "REJEITADA";
export type ScoringMode = "POR_UNIDADE" | "POR_BLOCO_DE_HORAS" | "CARGA_SEMANAL" | "VALOR_INFORMADO";
export type TableStatus = "OFICIAL" | "PENDENTE_VALIDACAO";
export type MinimumStatus = "ATINGE" | "NAO_ATINGE" | "NAO_DEFINIDO";
export type Level = "GRADUACAO" | "POS_GRADUACAO";

export type ScoringRow = {
  activity_id: string;
  title: string;
  activity_status: ActivityStatus;
  evidence_note: string | null;
  group_number: number | null;
  item_number: number | null;
  unit_points: string | null;
  effective_quantity: string | null;
  formula_text: string | null;
  points: string;
  /** Group I only: PIT hours of the offer (null elsewhere). */
  pit_hours: string | null;
  status: RowStatus;
  reasons: string[];
  alerts: Alert[];
};

export type ScoringResult = {
  process_id: string;
  chosen: ChosenTable | null;
  suggested: ChosenTable | null;
  subtotals: { group_number: number; subtotal: string }[];
  total: string;
  potential_total: string;
  /** Potential points of activities with a date or period in the interstice (REAL-08). */
  potential_dated: string;
  /** Potential points of activities without date, awaiting review (REAL-08). */
  potential_undated: string;
  group1_percent: string | null;
  /** Group I PIT hours summed per academic period (e.g. "2023.1"), outside the total. */
  group1_hours_by_period: Record<string, string>;
  group1_total_hours: string;
  counters: {
    activities: number;
    with_evidence: number;
    pending: number;
    not_scored: number;
    with_alerts: number;
  };
  rows: ScoringRow[];
  limit_adjustments: unknown[];
  alerts: Alert[];
  minimum: { status: MinimumStatus; minimum: string | null; total: string };
};

export type VersionInfo = {
  id: string;
  table_id: string;
  name: string;
  valid_from: string;
  valid_to: string | null;
  norm_reference: string;
  status: TableStatus;
};

export type ChosenTable = { table_name: string; version: VersionInfo };

export type TableChoice = {
  chosen: ChosenTable | null;
  suggested: ChosenTable | null;
  alerts: Alert[];
};

export type Criterion = {
  group_number: number;
  item_number: number;
  description: string;
  unit_label: string | null;
  mode: ScoringMode;
  unit_points: string | null;
  hours_per_block: string | null;
  weeks_per_semester: number | null;
  prep_ratio: string | null;
  /** Minimum course load in hours (e.g. "20.00"); null when the item has none. */
  min_hours: string | null;
  max_points: string | null;
  accepted_evidence: string | null;
  rules: string | null;
  review_note: string | null;
};

export type ScoringGroup = {
  number: number;
  name: string;
  counts_in_total: boolean;
  max_points: string | null;
  criteria: Criterion[];
};

export type ScoringVersion = VersionInfo & {
  minimums: unknown;
  notes: string | null;
  groups: ScoringGroup[];
};

export type Activity = {
  id: string;
  process_id: string;
  title: string;
  group_number: number | null;
  item_number: number | null;
  description: string | null;
  event_date: string | null;
  period_start: string | null;
  period_end: string | null;
  period_precision: "DAY" | "MONTH";
  academic_period: string | null;
  level: Level | null;
  quantidade: string | null;
  horas: string | null;
  course_hours: string | null;
  informed_points: string | null;
  points_override: string | null;
  evidence_note: string | null;
  source: string;
  status: ActivityStatus;
  distinct_justification: string | null;
  candidates: unknown[];
  /** Documents (and pages) linked to the activity; absent where the API call does not send them. */
  evidences?: Evidence[];
  version: number;
};

export type ScoringTableInfo = {
  id: string;
  name: string;
  archived: boolean;
  unit_ids: string[];
  versions: (VersionInfo & { in_use: boolean })[];
};

/* ---- Documentos (Etapa 2) ---- */

export type DocumentStatus =
  | "PENDENTE"
  | "PROCESSANDO"
  | "PROCESSADO"
  | "REQUER_REVISAO"
  | "EXTRAIDO_SEM_IA"
  | "FALHOU";

/** One file of an upload request: 201 stored, 409 duplicate, 422 refused, 429 rate limited. */
export type UploadResult = {
  original_name: string;
  status_code: number;
  document: DocumentSummary | null;
  existing_document_id: string | null;
  field: string | null;
  code: string | null;
  message: string | null;
};

export type DocumentSummary = {
  id: string;
  process_id: string;
  original_name: string;
  mime: string;
  size_bytes: number;
  sha256: string;
  page_count: number;
  status: DocumentStatus;
  /** Why the document is in this status (e.g. IA_INDISPONIVEL); null when there is nothing to say. */
  status_code: string | null;
  manual_type: string | null;
  manual_category: string | null;
  suggested_type: string | null;
  /** A taxonomy code, or SEM_ITEM_DE_PONTUACAO when the document has no scoring item. */
  suggested_category: string | null;
  /** 2-decimal string from 0.00 to 1.00; null while nothing was extracted. */
  confidence: string | null;
  uploaded_by: string;
  uploaded_at: string | null;
  updated_at: string | null;
  version: number;
};

export type TextMethod = "TEXTO" | "OCR";

export type DocumentPage = {
  page_number: number;
  method: TextMethod;
  char_count: number;
  /** Mean OCR confidence in percent ("87.50"); null for pages read from the text layer. */
  ocr_confidence: string | null;
  text: string;
};

export type DocumentRun = {
  id: string;
  model: string;
  duration_ms: number;
  /** What the AI returned, untouched; read only. */
  raw_json: Record<string, unknown>;
  created_at: string | null;
};

export type DocumentAlert = { code: string; field: string | null; activity_index: number | null };

/** A link between an activity and a page of a document (VINC-01). */
export type Evidence = {
  id: string;
  document_id: string;
  document_name: string;
  page: number;
  excerpt: string;
};

export type LinkedActivity = {
  id: string;
  title: string;
  group_number: number | null;
  item_number: number | null;
  source: string;
  status: string;
  version: number;
  evidences: Evidence[];
};

export type DocumentDetail = DocumentSummary & {
  pages: DocumentPage[];
  run: DocumentRun | null;
  alerts: DocumentAlert[];
  activities: LinkedActivity[];
};
