export interface MASDecisionLog {
  id: number
  task_id: string
  timestamp: string
  decision: number // 0 = Edge, 1 = Cloud
  decision_label: 'PROSES_DI_EDGE' | 'MIGRASI_KE_CLOUD'
  execution_node: string
  model_used: string
  cpu_pct: number
  ram_pct: number
  latency_ms: number
  priority: number
  queue_len: number
  execution_time_ms: number
  user_id: string
  confidence: number
  status: 'SUCCESS' | 'UNAUTHORIZED' | 'FAILED' | string
  notes: string
}

export interface DecisionSummary {
  total_decisions: number
  edge_count: number
  edge_percentage: number
  cloud_count: number
  cloud_percentage: number
  avg_edge_time_ms: number
  avg_cloud_time_ms: number
  avg_edge_cpu: number
  avg_cloud_cpu: number
  active_model: string
  edge_host: string
  scheduler_host: string
  cloud_gpu_host: string
}

export interface DecisionApiResponse {
  summary: DecisionSummary
  logs: MASDecisionLog[]
}

export interface NodeStatus {
  edgePi: { online: boolean; ip: string; status: string }
  brainScheduler: { online: boolean; ip: string; mode: string }
  cloudGpu: { online: boolean; ip: string; device: string; gpuName: string }
}
