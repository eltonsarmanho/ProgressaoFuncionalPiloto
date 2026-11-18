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
  group1_percent: string | null;
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
  version: number;
};

export type ScoringTableInfo = {
  id: string;
  name: string;
  archived: boolean;
  unit_ids: string[];
  versions: (VersionInfo & { in_use: boolean })[];
};
