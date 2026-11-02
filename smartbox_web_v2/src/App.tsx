import { useState, useEffect, useCallback } from 'react'
import type {
  MASDecisionLog,
  DecisionSummary,
  NodeStatus,
} from './types'
import { Navbar } from './components/Navbar'
import { KPISection } from './components/KPISection'
import { TimelineChart } from './components/TimelineChart'
import { DecisionLogTable } from './components/DecisionLogTable'
import { DecisionDetailModal } from './components/DecisionDetailModal'

const INITIAL_SUMMARY: DecisionSummary = {
  total_decisions: 300,
  edge_count: 150,
  edge_percentage: 50.0,
  cloud_count: 150,
  cloud_percentage: 50.0,
  avg_edge_time_ms: 272.4,
  avg_cloud_time_ms: 148.9,
  avg_edge_cpu: 38.4,
  avg_cloud_cpu: 84.5,
  active_model: 'XGBoost v2.0',
  edge_host: '10.1.1.224',
  scheduler_host: '10.1.1.57',
  cloud_gpu_host: '10.1.1.186',
}

const INITIAL_STATUS: NodeStatus = {
  edgePi: { online: true, ip: '10.1.1.224', status: 'Ready' },
  brainScheduler: { online: true, ip: '10.1.1.57:8500', mode: 'xgboost' },
  cloudGpu: { online: true, ip: '10.1.1.186:9000', device: 'cuda:0', gpuName: 'RTX 3050' },
}

export default function App() {
  const [summary, setSummary] = useState<DecisionSummary>(INITIAL_SUMMARY)
  const [logs, setLogs] = useState<MASDecisionLog[]>([])
  const [nodeStatus, setNodeStatus] = useState<NodeStatus>(INITIAL_STATUS)
  const [selectedLog, setSelectedLog] = useState<MASDecisionLog | null>(null)
  const [isAutoRefresh, setIsAutoRefresh] = useState<boolean>(true)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)

  // Fetch real decision logs from backend gateway
  const fetchDecisionData = useCallback(async () => {
    setIsRefreshing(true)
    try {
      // 1. Fetch decision logs from /api/decision-logs (proxied to Cloud GPU 10.1.1.186:9000)
      const res = await fetch('/api/decision-logs?limit=50')
      if (res.ok) {
        const data = await res.json()
        if (data.summary) {
          setSummary(data.summary)
        }
        if (Array.isArray(data.logs)) {
          setLogs(data.logs)
        }
      }
    } catch (err) {
      console.error('Gagal mengambil data log keputusan:', err)
    }

    // 2. Fetch Node Health checks
    try {
      const gpuRes = await fetch('/api/gpu-health')
      const schedRes = await fetch('/api/scheduler')

      setNodeStatus((prev) => ({
        ...prev,
        cloudGpu: {
          ...prev.cloudGpu,
          online: gpuRes.ok,
        },
        brainScheduler: {
          ...prev.brainScheduler,
          online: schedRes.ok,
        },
      }))
    } catch {
      // Keep previous
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  // Initial load & Polling
  useEffect(() => {
    fetchDecisionData()
    if (!isAutoRefresh) return

    const interval = setInterval(() => {
      fetchDecisionData()
    }, 3000)

    return () => clearInterval(interval)
  }, [fetchDecisionData, isAutoRefresh])

  return (
    <div className="min-h-screen bg-background text-text-primary flex flex-col font-sans">
      {/* Top Navigation & Status Bar */}
      <Navbar
        nodeStatus={nodeStatus}
        isAutoRefresh={isAutoRefresh}
        onToggleAutoRefresh={() => setIsAutoRefresh((prev) => !prev)}
        onManualRefresh={fetchDecisionData}
        isRefreshing={isRefreshing}
      />

      {/* Main Content: Single Page MAS Observatory */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 space-y-6">
        {/* Row 1: KPI Summary Cards */}
        <KPISection summary={summary} />

        {/* Row 2: Timeline Curve & MAS Model Routing */}
        <TimelineChart logs={logs} summary={summary} />

        {/* Row 3: Interactive Real-Time Decision Log Table */}
        <DecisionLogTable
          logs={logs}
          onSelectLog={(log) => setSelectedLog(log)}
          totalCount={summary.total_decisions}
          edgeCount={summary.edge_count}
          cloudCount={summary.cloud_count}
        />
      </main>

      {/* Detail Inspection Modal for Selected Decision */}
      <DecisionDetailModal
        log={selectedLog}
        onClose={() => setSelectedLog(null)}
      />
    </div>
  )
}
