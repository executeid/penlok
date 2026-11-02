import React from 'react'
import type { NodeStatus } from '../types'
import {
  Activity,
  Cpu,
  
  Radio,
  RefreshCw,
  Sliders,
} from 'lucide-react'

interface NavbarProps {
  nodeStatus: NodeStatus
  isAutoRefresh: boolean
  onToggleAutoRefresh: () => void
  onManualRefresh: () => void
  isRefreshing: boolean
}

export const Navbar: React.FC<NavbarProps> = ({
  nodeStatus,
  isAutoRefresh,
  onToggleAutoRefresh,
  onManualRefresh,
  isRefreshing,
}) => {
  return (
    <header className="border-b border-[#2C2C2E] bg-[#1E1E1E] sticky top-0 z-50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Brand Header */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-card bg-[#121212] border border-[#2C2C2E] flex items-center justify-center text-[#00E5FF] shadow-sm">
            <Activity className="w-5 h-5 text-[#00E5FF]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg tracking-tight text-white">
                Penlok MAS <span className="text-[#00E5FF] font-mono text-sm">// Decision Observatory</span>
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[#121212] border border-[#32D74B] text-[#32D74B]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#32D74B]"></span>
                Pemantauan Aktif
              </span>
            </div>
            <p className="text-xs text-text-secondary">
              Observasi Alur Keputusan Komputasi Multi-Agen (Lokal di Edge vs. Migrasi ke Cloud GPU)
            </p>
          </div>
        </div>

        {/* Node Status Indicators & Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Node 1: Edge Pi 5 */}
          <div className="hidden md:flex items-center gap-2 text-xs text-text-secondary bg-[#121212] px-3 py-1.5 rounded-xl border border-[#2C2C2E]">
            <Radio className={`w-3.5 h-3.5 ${nodeStatus.edgePi.online ? 'text-[#32D74B]' : 'text-[#FF453A]'}`} />
            <span>Edge Pi 5:</span>
            <span className={`font-mono font-medium ${nodeStatus.edgePi.online ? 'text-white' : 'text-[#FF453A]'}`}>
              {nodeStatus.edgePi.ip}
            </span>
          </div>

          {/* Node 2: Scheduler Brain */}
          <div className="hidden lg:flex items-center gap-2 text-xs text-text-secondary bg-[#121212] px-3 py-1.5 rounded-xl border border-[#2C2C2E]">
            <Sliders className={`w-3.5 h-3.5 ${nodeStatus.brainScheduler.online ? 'text-[#00E5FF]' : 'text-[#FF453A]'}`} />
            <span>Scheduler:</span>
            <span className="font-mono text-[#00E5FF] font-medium">
              {nodeStatus.brainScheduler.mode.toUpperCase()}
            </span>
          </div>

          {/* Node 3: Cloud GPU RTX 3050 */}
          <div className="hidden sm:flex items-center gap-2 text-xs text-text-secondary bg-[#121212] px-3 py-1.5 rounded-xl border border-[#2C2C2E]">
            <Cpu className={`w-3.5 h-3.5 ${nodeStatus.cloudGpu.online ? 'text-[#32D74B]' : 'text-[#FF453A]'}`} />
            <span>Cloud GPU:</span>
            <span className="font-mono text-white font-medium">
              RTX 3050 CUDA
            </span>
          </div>

          {/* Refresh Controls */}
          <div className="flex items-center gap-2 pl-2 border-l border-[#2C2C2E]">
            <button
              type="button"
              onClick={onToggleAutoRefresh}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                isAutoRefresh
                  ? 'bg-[#121212] text-[#32D74B] border-[#32D74B]'
                  : 'bg-[#121212] text-text-secondary border-[#2C2C2E] hover:text-white'
              }`}
              title="Perbarui data secara otomatis setiap 3 detik"
            >
              Auto-Refresh (3s): {isAutoRefresh ? 'ON' : 'OFF'}
            </button>

            <button
              type="button"
              disabled={isRefreshing}
              onClick={onManualRefresh}
              className="w-8 h-8 rounded-lg bg-[#121212] border border-[#2C2C2E] flex items-center justify-center text-text-secondary hover:text-[#00E5FF] hover:border-[#00E5FF]/40 transition-colors cursor-pointer disabled:opacity-50"
              title="Segarkan data keputusan sekarang"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-[#00E5FF]' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
