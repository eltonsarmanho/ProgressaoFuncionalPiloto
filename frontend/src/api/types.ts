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
