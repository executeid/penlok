import React from 'react'
import type { MASDecisionLog, DecisionSummary } from '../types'
import { CheckCircle2, Shield, ArrowUpRight, Cpu } from 'lucide-react'

interface TimelineChartProps {
  logs: MASDecisionLog[]
  summary: DecisionSummary
}

export const TimelineChart: React.FC<TimelineChartProps> = ({ logs, summary }) => {
  // Ambil 15 log terakhir untuk visualisasi garis waktu (kronologis)
  const recentLogs = [...logs.slice(0, 15)].reverse()

  const points = recentLogs.map((log, idx) => {
    const x = recentLogs.length > 1 ? (idx / (recentLogs.length - 1)) * 500 : 250
    // Y berdasarkan CPU pct (0 - 100%) dipetakan ke 15 - 135px
    const cpu = log.cpu_pct || 40.0
    const y = Math.max(15, Math.min(135, 140 - (cpu / 100) * 120))
    return { x, y, log }
  })

  const pathLine = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`, '')
  const pathArea = `${pathLine} L 500,150 L 0,150 Z`

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Kolom Kiri (8 Kolom): Visualisasi Garis Waktu Keputusan */}
      <div className="lg:col-span-8 bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
        <div>
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <div>
              <h3 className="text-lg font-semibold text-white">
                Kurva Beban CPU Edge & Titik Keputusan Alur (Timeline)
              </h3>
              <p className="text-xs text-text-secondary">
                Pemetaan kronologis beban prosesor Pi 5 (%) dan titik di mana tugas dialihkan ke Cloud GPU
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs font-mono">
              <span className="flex items-center gap-1.5 text-text-secondary">
                <span className="w-2.5 h-2.5 rounded-full bg-[#00E5FF]"></span>
                Migrasi Cloud (1)
              </span>
              <span className="flex items-center gap-1.5 text-text-secondary">
                <span className="w-2.5 h-2.5 rounded-full bg-[#32D74B]"></span>
                Lokal Edge (0)
              </span>
            </div>
          </div>

          {/* Area Chart SVG */}
          <div className="h-56 w-full relative bg-[#121212] rounded-xl p-4 border border-[#2C2C2E] overflow-hidden">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 500 150">
              <defs>
                <linearGradient id="chartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.45" />
                  <stop offset="60%" stopColor="#32D74B" stopOpacity="0.12" />
                  <stop offset="100%" stopColor="#121212" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Garis Grid Ambang Batas 75% CPU */}
              <line x1="0" y1="35" x2="500" y2="35" stroke="#FF453A" strokeDasharray="3 3" strokeWidth="1" opacity="0.6" />
              <line x1="0" y1="75" x2="500" y2="75" stroke="#2C2C2E" strokeDasharray="4 4" strokeWidth="1" />
              <line x1="0" y1="115" x2="500" y2="115" stroke="#2C2C2E" strokeDasharray="4 4" strokeWidth="1" />

              {/* Kurva Area */}
              {points.length > 0 && (
                <>
                  <path d={pathArea} fill="url(#chartGrad)" />
                  <path d={pathLine} fill="none" stroke="#00E5FF" strokeWidth="2.5" />
                  {points.map((p, idx) => {
                    const isCloud = p.log.decision === 1
                    return (
                      <circle
                        key={idx}
                        cx={p.x}
                        cy={p.y}
                        r={isCloud ? '4.5' : '3.5'}
                        fill={isCloud ? '#00E5FF' : '#32D74B'}
                        stroke="#121212"
                        strokeWidth="1.5"
                      />
                    )
                  })}
                </>
              )}
            </svg>

            {/* Label Ambang Batas 75% */}
            <div className="absolute top-8 right-5 text-[10px] text-[#FF453A] font-mono bg-[#1E1E1E]/80 px-2 py-0.5 rounded border border-[#FF453A]/30">
              Batas Beban Kritis CPU (75%)
            </div>

            <div className="absolute bottom-2 left-4 right-4 flex justify-between text-[11px] text-text-secondary font-mono">
              <span>Sampel Terdahulu</span>
              <span>Aliran Data Masuk</span>
              <span>Terbaru</span>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#2C2C2E] flex flex-wrap items-center justify-between text-xs text-text-secondary">
          <span>
            Rata-rata CPU saat Diproses di Edge: <strong className="text-[#32D74B]">{summary.avg_edge_cpu}%</strong>
          </span>
          <span>
            Rata-rata CPU saat Dialihkan ke Cloud: <strong className="text-[#00E5FF]">{summary.avg_cloud_cpu}%</strong>
          </span>
        </div>
      </div>

      {/* Kolom Kanan (4 Kolom): Panel Logika Orquestasi Cerdas */}
      <div className="lg:col-span-4 bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
        <div>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#00E5FF]" />
              Aturan Keputusan Model
            </h4>
            <span className="text-xs px-2 py-0.5 rounded bg-[#121212] border border-[#2C2C2E] text-[#32D74B] font-mono">
              {summary.active_model}
            </span>
          </div>

          <p className="text-xs text-text-secondary mb-4 leading-relaxed">
            Klasifikasi penempatan tugas ditentukan oleh model machine learning XGBoost dengan 7 variabel masukan secara real-time:
          </p>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
              <div className="flex items-center justify-between text-white font-medium mb-1">
                <span className="flex items-center gap-1.5 text-[#32D74B]">
                  <CheckCircle2 className="w-3.5 h-3.5" /> 0 : Diproses di Edge
                </span>
                <span className="font-mono text-[11px] text-text-secondary">&le; 75% CPU</span>
              </div>
              <p className="text-[11px] text-text-secondary">
                Dijalankan lokal di Pi 5 menggunakan model LBPH offline saat beban prosesor rendah dan latensi jaringan stabil.
              </p>
            </div>

            <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
              <div className="flex items-center justify-between text-white font-medium mb-1">
                <span className="flex items-center gap-1.5 text-[#00E5FF]">
                  <ArrowUpRight className="w-3.5 h-3.5" /> 1 : Migrasi ke Cloud
                </span>
                <span className="font-mono text-[11px] text-text-secondary">&gt; 75% CPU</span>
              </div>
              <p className="text-[11px] text-text-secondary">
                Dialihkan melalui koneksi terenkripsi ke GPU NVIDIA RTX 3050 CUDA untuk mempertahankan responsivitas perangkat tepi.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-[#2C2C2E] text-[11px] text-text-secondary flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-[#00E5FF] flex-shrink-0" />
          <span>Arsitektur Multi-Agen mencegah thermal throttling pada CPU Pi 5.</span>
        </div>
      </div>
    </div>
  )
}
