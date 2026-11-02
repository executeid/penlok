import React, { useEffect } from 'react'
import type { MASDecisionLog } from '../types'
import {
  X,
  Cpu,
  Layers,
  Clock,
  User,
  Sliders,
  CheckCircle2,
  XCircle,
} from 'lucide-react'

interface DecisionDetailModalProps {
  log: MASDecisionLog | null
  onClose: () => void
}

export const DecisionDetailModal: React.FC<DecisionDetailModalProps> = ({ log, onClose }) => {
  // ESC key listener to close modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!log) return null

  const isCloud = log.decision === 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-[#1E1E1E] border border-[#2C2C2E] rounded-card shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="p-5 border-b border-[#2C2C2E] flex items-center justify-between bg-[#181818]">
          <div className="flex items-center gap-2.5">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${
              isCloud ? 'border-[#00E5FF] text-[#00E5FF] bg-[#121212]' : 'border-[#32D74B] text-[#32D74B] bg-[#121212]'
            }`}>
              {isCloud ? <Cpu className="w-4 h-4" /> : <Layers className="w-4 h-4" />}
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">
                Detail Vektor Keputusan MAS
              </h3>
              <span className="text-xs font-mono text-text-secondary">
                Task ID: {log.task_id}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#121212] border border-[#2C2C2E] flex items-center justify-center text-text-secondary hover:text-white transition-colors cursor-pointer"
            title="Tutup (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[75vh]">
          {/* Status Banner */}
          <div className={`p-4 rounded-xl border flex items-center justify-between ${
            isCloud
              ? 'bg-[#121212] border-[#00E5FF] text-white'
              : 'bg-[#121212] border-[#32D74B] text-white'
          }`}>
            <div>
              <span className="text-[11px] uppercase tracking-wider text-text-secondary block font-mono">
                Hasil Klasifikasi Alur
              </span>
              <div className="text-base font-bold mt-0.5 flex items-center gap-2">
                <span className={isCloud ? 'text-[#00E5FF]' : 'text-[#32D74B]'}>
                  {log.decision_label} (Target: {log.decision})
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-[#1E1E1E] text-text-secondary border border-[#2C2C2E] font-normal">
                  {log.execution_node}
                </span>
              </div>
            </div>

            <div className="text-right font-mono">
              <span className="text-xs text-text-secondary block">Model Inferensi</span>
              <span className="text-sm font-semibold text-[#00E5FF]">{log.model_used}</span>
            </div>
          </div>

          {/* Vektor 7 Fitur Telemetri */}
          <div>
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-[#00E5FF]" />
              7 Variabel Masukan Telemetri (Feature Vector)
            </h4>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">1. Beban CPU</span>
                <span className={`text-sm font-bold ${log.cpu_pct > 75 ? 'text-[#FF453A]' : 'text-white'}`}>
                  {log.cpu_pct}%
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">2. Memori RAM</span>
                <span className="text-sm font-bold text-white">
                  {log.ram_pct}%
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">3. Latensi Jaringan</span>
                <span className="text-sm font-bold text-white">
                  {log.latency_ms} ms
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">4. Prioritas Tugas</span>
                <span className="text-sm font-bold text-[#00E5FF]">
                  Level {log.priority}
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">5. Panjang Antrean</span>
                <span className="text-sm font-bold text-white">
                  {log.queue_len} Antrean
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">6. Throughput Data</span>
                <span className="text-sm font-bold text-white">
                  0.5 MB/s
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">7. Bandwidth Net</span>
                <span className="text-sm font-bold text-white">
                  1.0 MB/s
                </span>
              </div>

              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-text-secondary block text-[11px]">Keyakinan Model</span>
                <span className="text-sm font-bold text-[#32D74B]">
                  {(log.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          {/* Hasil Autentikasi Biometrik */}
          <div className="p-4 rounded-xl bg-[#121212] border border-[#2C2C2E] space-y-3">
            <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-[#00E5FF]" />
              Hasil Autentikasi Pengenalan Wajah
            </h4>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <span className="text-text-secondary block">Pengguna Dikenali:</span>
                <span className="font-semibold text-white text-sm">
                  {log.user_id || 'UNKNOWN'}
                </span>
              </div>

              <div>
                <span className="text-text-secondary block">Waktu Eksekusi:</span>
                <span className="font-mono text-sm font-semibold text-[#00E5FF]">
                  {log.execution_time_ms} ms
                </span>
              </div>

              <div>
                <span className="text-text-secondary block">Status Akses:</span>
                <span className="inline-flex items-center gap-1 text-sm font-semibold mt-0.5">
                  {log.status === 'SUCCESS' ? (
                    <span className="text-[#32D74B] flex items-center gap-1">
                      <CheckCircle2 className="w-4 h-4" /> DITERIMA (Loker Dibuka)
                    </span>
                  ) : (
                    <span className="text-[#FF453A] flex items-center gap-1">
                      <XCircle className="w-4 h-4" /> DITOLAK
                    </span>
                  )}
                </span>
              </div>
            </div>

            {log.notes && (
              <p className="text-[11px] text-text-secondary border-t border-[#2C2C2E] pt-2 font-mono">
                Catatan Alur: {log.notes}
              </p>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#2C2C2E] bg-[#181818] flex items-center justify-between text-xs text-text-secondary">
          <span className="flex items-center gap-1 font-mono">
            <Clock className="w-3.5 h-3.5" />
            Waktu: {log.timestamp}
          </span>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#121212] hover:bg-[#252525] text-white border border-[#2C2C2E] font-medium transition-colors cursor-pointer"
          >
            Tutup Jendela
          </button>
        </div>
      </div>
    </div>
  )
}
