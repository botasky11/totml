export enum ExperimentStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface Experiment {
  id: string;
  name: string;
  description?: string;
  goal: string;
  eval_metric: string;
  num_steps: number;
  model_name?: string;
  status: ExperimentStatus;
  current_step: number;
  progress: number;
  best_metric_value?: number;
  best_solution_code?: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  completed_at?: string;
  config?: any;
  journal_data?: any;
}

export interface ExperimentCreate {
  name: string;
  description?: string;
  goal: string;
  eval_metric: string;
  num_steps?: number;
  model_name?: string;
}

export interface ExperimentNode {
  id: string;
  experiment_id: string;
  step: number;
  parent_id?: string;
  plan?: string;
  code: string;
  metric_value?: number;
  is_buggy: boolean;
  term_out?: string;
  analysis?: string;
  created_at: string;
}

export interface WebSocketMessage {
  type: 'status_update' | 'log' | 'error' | 'complete';
  data: any;
  timestamp: string;
}
