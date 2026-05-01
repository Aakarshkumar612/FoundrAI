export interface Upload {
  upload_id: string;
  filename: string;
  file_type: string;
  row_count?: number;
  columns?: string[];
  uploaded_at: string;
  is_financial: boolean;
  storage_path?: string;
}

export interface ForecastMonth { month: number; p10: number; p50: number; p90: number; }

export interface SimulationResult {
  simulation_id?: string;
  forecast: ForecastMonth[];
  runway_months: number;
  runway_p10: number;
  runway_p90: number;
  model_used: string;
  simulation_runs: number;
}

export interface Dashboard { id: string; title: string; description: string; }
