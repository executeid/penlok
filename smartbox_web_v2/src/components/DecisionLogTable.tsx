import React, { useState } from 'react'
import type { MASDecisionLog } from '../types'
import { Search, Eye, Filter } from 'lucide-react'

interface DecisionLogTableProps {
  logs: MASDecisionLog[]
  onSelectLog: (log: MASDecisionLog) => void
  totalCount: number
  edgeCount: number
  cloudCount: number
}

export const DecisionLogTable: React.FC<DecisionLogTableProps> = ({
  logs,
  onSelectLog,
  totalCount,
  edgeCount,
  cloudCount,
}) => {
  const [filterDecision, setFilterDecision] = useState<'ALL' | 0 | 1>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')

  const filteredLogs = logs.filter((log) => {
    // 1. Filter Decision
    if (filterDecision !== 'ALL' && log.decision !== filterDecision) {
      return false
    }
    // 2. Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchTask = log.task_id.toLowerCase().includes(q)
      const matchUser = (log.user_id || '').toLowerCase().includes(q)
      const matchNode = (log.execution_node || '').toLowerCase().includes(q)
      const matchStatus = (log.status || '').toLowerCase().includes(q)
      return matchTask || matchUser || matchNode || matchStatus
    }
    return true
  })

  return (
    <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 space-y-4">
      {/* Header Tabel, Filter & Pencarian */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#2C2C2E] pb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">
            Log Keputusan Eksekusi Multi-Agen (Real-Time Decision Logs)
          </h3>
          <p className="text-xs text-text-secondary mt-0.5">
            Daftar riwayat evaluasi alur tugas kecerdasan terdistribusi antara perangkat tepi dan awan
          </p>
        </div>

        {/* Input Pencarian */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-text-secondary absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cari Task ID, nama pengguna, atau node..."
            className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:border-[#00E5FF] transition-colors"
          />
        </div>
      </div>

      {/* Filter Tabs Keputusan */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-text-secondary" />
          <span className="text-text-secondary font-medium">Filter Keputusan:</span>

          <button
            type="button"
            onClick={() => setFilterDecision('ALL')}
            className={`px-3 py-1.5 rounded-lg border font-medium transition-all cursor-pointer ${
              filterDecision === 'ALL'
                ? 'bg-[#121212] text-[#00E5FF] border-[#00E5FF] shadow-sm'
                : 'bg-[#121212] text-text-secondary border-[#2C2C2E] hover:text-white'
            }`}
          >
            Semua ({totalCount})
          </button>

          <button
            type="button"
            onClick={() => setFilterDecision(0)}
            className={`px-3 py-1.5 rounded-lg border font-medium transition-all cursor-pointer ${
              filterDecision === 0
                ? 'bg-[#121212] text-[#32D74B] border-[#32D74B] shadow-sm'
                : 'bg-[#121212] text-text-secondary border-[#2C2C2E] hover:text-white'
            }`}
          >
            Lokal di Edge ({edgeCount})
          </button>

          <button
            type="button"
            onClick={() => setFilterDecision(1)}
            className={`px-3 py-1.5 rounded-lg border font-medium transition-all cursor-pointer ${
              filterDecision === 1
                ? 'bg-[#121212] text-[#00E5FF] border-[#00E5FF] shadow-sm'
                : 'bg-[#121212] text-text-secondary border-[#2C2C2E] hover:text-white'
            }`}
          >
            Migrasi ke Cloud ({cloudCount})
          </button>
        </div>

        <span className="text-text-secondary font-mono text-[11px]">
          Menampilkan {filteredLogs.length} dari {logs.length} catatan
        </span>
      </div>

      {/* Tabel Data Log Riil */}
      <div className="overflow-x-auto border border-[#2C2C2E] rounded-xl bg-[#121212]">
        <table className="w-full text-xs text-left">
          <thead>
            <tr className="border-b border-[#2C2C2E] text-[11px] font-semibold text-text-secondary uppercase bg-[#181818]">
              <th className="py-3 px-3 text-center" style={{ width: '4%' }}>No</th>
              <th className="py-3 px-3" style={{ width: '14%' }}>Waktu (WIB)</th>
              <th className="py-3 px-3" style={{ width: '16%' }}>Task ID</th>
              <th className="py-3 px-3" style={{ width: '14%' }}>Keputusan Alur</th>
              <th className="py-3 px-3" style={{ width: '14%' }}>Node Pelaksana</th>
              <th className="py-3 px-3" style={{ width: '12%' }}>Beban CPU & RAM</th>
              <th className="py-3 px-3 font-mono" style={{ width: '10%' }}>Waktu Proses</th>
              <th className="py-3 px-3" style={{ width: '10%' }}>Identitas Hasil</th>
              <th className="py-3 px-3 text-center" style={{ width: '6%' }}>Detail</th>
            </tr>
          </thead>
          <tbody>
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={9} className="py-8 text-center text-text-secondary font-mono">
                  Tidak ada catatan keputusan yang sesuai dengan filter pencarian.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log, idx) => {
                const isCloud = log.decision === 1
                return (
                  <tr
                    key={log.id || idx}
                    className="border-b border-[#2C2C2E] hover:bg-[#252525] transition-colors"
                  >
                    <td className="py-3 px-3 text-center text-text-secondary font-mono">
                      {idx + 1}
                    </td>
                    <td className="py-3 px-3 font-mono text-text-secondary whitespace-nowrap">
                      {log.timestamp}
                    </td>
                    <td className="py-3 px-3 font-mono font-medium text-white truncate max-w-[160px]" title={log.task_id}>
                      {log.task_id}
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap">
                      {isCloud ? (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#1E1E1E] border border-[#00E5FF] text-[#00E5FF]">
                          MIGRASI CLOUD (1)
                        </span>
                      ) : (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#1E1E1E] border border-[#32D74B] text-[#32D74B]">
                          LOKAL EDGE (0)
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-white text-[11px]">
                      {log.execution_node}
                    </td>
                    <td className="py-3 px-3 font-mono text-text-secondary whitespace-nowrap">
                      <span className={log.cpu_pct > 75 ? 'text-[#FF453A] font-semibold' : 'text-white'}>
                        {log.cpu_pct}%
                      </span>{' '}
                      / {log.ram_pct}%
                    </td>
                    <td className="py-3 px-3 font-mono font-semibold whitespace-nowrap">
                      <span className={isCloud ? 'text-[#00E5FF]' : 'text-white'}>
                        {log.execution_time_ms} ms
                      </span>
                    </td>
                    <td className="py-3 px-3 whitespace-nowrap font-medium text-white">
                      {log.user_id && log.user_id !== 'UNKNOWN' && log.user_id !== 'TIDAK_DIKENAL' ? (
                        <span className="text-[#32D74B]">{log.user_id}</span>
                      ) : (
                        <span className="text-[#FF453A]">Ditolak</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <button
                        type="button"
                        onClick={() => onSelectLog(log)}
                        className="p-1.5 rounded-lg bg-[#1E1E1E] hover:bg-[#00E5FF] hover:text-[#121212] text-text-secondary transition-all cursor-pointer inline-flex items-center justify-center border border-[#2C2C2E]"
                        title="Lihat 7 Vektor Fitur & Detail"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
