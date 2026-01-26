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

export interface FeatureAnalysisReport {
  id: string;
  experiment_id: string;
  best_node_id?: string;
  
  // 数据概况统计
  data_profile?: {
    file_name: string;
    sample_count: number;
    feature_count: number;
    majority_class_count: number;
    minority_class_count: number;
    majority_minority_ratio: string;
    dataset_stats: Array<{
      name: string;
      cnt: number;
      blk_cnt: number;
      blk_rate: string;
      dt_min: string;
      dt_max: string;
    }>;
  };
  
  // 特征重要性分析
  feature_importance?: {
    iv_results: Array<{
      feature: string;
      iv: number;
      iv_strength: string;
    }>;
    model_importance?: Array<{
      feature: string;
      importance: number;
      importance_pct: string;
      cumulative_pct: string;
      rank: number;
    }>;
  };
  
  // 特征稳定性分析
  feature_stability?: {
    base_period: string;
    feature_timelines: Array<{
      feature: string;
      max_psi: number;
      avg_psi: number;
      is_stable: boolean;
    }>;
    unstable_features: string[];
  };
  
  // 模型稳定性
  model_stability?: {
    score_column: string;
    base_period: string;
    overall_psi: number;
    is_stable: boolean;
    stability_level: string;
  };
  
  // 模型评估
  model_evaluation?: {
    overall_auc: number;
    overall_ks: number;
    dataset_metrics: Array<{
      dataset_name: string;
      period: string;
      auc: number;
      ks: number;
      lift: number;
      sample_count: number;
      positive_count: number;
      negative_count: number;
    }>;
  };
  
  // 特征统计
  feature_statistics?: Array<{
    col: string;
    missing_rate: string;
    mode_rate: string;
    mean?: number;
    median?: number;
    ks?: number;
  }>;
  
  // 完整报告
  full_report_md?: string;
  
  // 分析配置
  analysis_config?: {
    total_nodes: number;
    good_nodes: number;
    buggy_nodes: number;
    best_node_metric: number;
    node_statistics?: {
      count: number;
      mean: number;
      std: number;
      min: number;
      max: number;
      median: number;
    };
  };
  
  error_message?: string;
  created_at: string;
  updated_at?: string;
}
