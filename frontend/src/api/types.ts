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
