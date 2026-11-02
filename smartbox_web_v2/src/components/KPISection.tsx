import React from 'react'
import type { DecisionSummary } from '../types'
import { Layers, Radio, Cpu, Clock } from 'lucide-react'

interface KPISectionProps {
  summary: DecisionSummary
}

export const KPISection: React.FC<KPISectionProps> = ({ summary }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      {/* KPI 1: Total Keputusan */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-text-secondary text-sm">
          <span>Total Tugas Dievaluasi</span>
          <Layers className="w-5 h-5 text-[#00E5FF]" />
        </div>
        <div className="my-3">
          <div className="text-3xl kpi-mono text-white">
            {summary.total_decisions.toLocaleString()}
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Total permintaan verifikasi wajah MAS
          </p>
        </div>
        <div className="text-[11px] text-text-secondary border-t border-[#2C2C2E] pt-2 flex justify-between font-mono">
          <span>Model: {summary.active_model}</span>
          <span className="text-[#00E5FF]">Multi-Variabel 7 Fitur</span>
        </div>
      </div>

      {/* KPI 2: Diproses di Edge (Lokal) */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-text-secondary text-sm">
          <span>Diproses Lokal di Edge (0)</span>
          <Radio className="w-5 h-5 text-[#32D74B]" />
        </div>
        <div className="my-3">
          <div className="text-3xl kpi-mono text-[#32D74B] flex items-baseline gap-2">
            {summary.edge_count.toLocaleString()}{' '}
            <span className="text-sm font-sans font-medium text-text-secondary">
              ({summary.edge_percentage}%)
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            CPU normal (&le; 75%), inferensi LBPH lokal
          </p>
        </div>
        <div className="w-full bg-[#121212] h-2 rounded-full overflow-hidden border border-[#2C2C2E]">
          <div
            className="bg-[#32D74B] h-full transition-all duration-500"
            style={{ width: `${summary.edge_percentage}%` }}
          ></div>
        </div>
      </div>

      {/* KPI 3: Dimigrasikan ke Cloud GPU */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-text-secondary text-sm">
          <span>Dimigrasikan ke Cloud GPU (1)</span>
          <Cpu className="w-5 h-5 text-[#00E5FF]" />
        </div>
        <div className="my-3">
          <div className="text-3xl kpi-mono text-[#00E5FF] flex items-baseline gap-2">
            {summary.cloud_count.toLocaleString()}{' '}
            <span className="text-sm font-sans font-medium text-text-secondary">
              ({summary.cloud_percentage}%)
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1">
            Beban tinggi (&gt; 75%), dialihkan ke GPU RTX 3050
          </p>
        </div>
        <div className="w-full bg-[#121212] h-2 rounded-full overflow-hidden border border-[#2C2C2E]">
          <div
            className="bg-[#00E5FF] h-full transition-all duration-500"
            style={{ width: `${summary.cloud_percentage}%` }}
          ></div>
        </div>
      </div>

      {/* KPI 4: Perbandingan Waktu Tanggap */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
        <div className="flex items-center justify-between text-text-secondary text-sm">
          <span>Rata-rata Waktu Tanggap</span>
          <Clock className="w-5 h-5 text-[#00E5FF]" />
        </div>
        <div className="my-3">
          <div className="text-3xl kpi-mono text-white flex items-baseline gap-2">
            {summary.avg_cloud_time_ms}{' '}
            <span className="text-sm font-sans font-normal text-text-secondary">
              ms (GPU)
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-1 font-mono">
            Rerata Edge Pi 5: <span className="text-text-secondary font-semibold">{summary.avg_edge_time_ms} ms</span>
          </p>
        </div>
        <div className="text-[11px] text-text-secondary border-t border-[#2C2C2E] pt-2 flex justify-between font-mono">
          <span>Efisiensi GPU: ~{(summary.avg_edge_time_ms / Math.max(1, summary.avg_cloud_time_ms)).toFixed(1)}x lebih cepat</span>
        </div>
      </div>
    </div>
  )
}
