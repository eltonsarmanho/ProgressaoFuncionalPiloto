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
