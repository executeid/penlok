import React from 'react'
import type { UserProfile } from '../types'
import {
  Box,
  UserCheck,
  Package,
  Activity,
  LogOut,
  Cpu,
  Server,
  Radio,
  Lock,
} from 'lucide-react'

export type NavTab = 'dashboard' | 'penghuni' | 'onboarding' | 'packages'

interface NavbarProps {
  activeTab: NavTab
  onSelectTab: (tab: NavTab) => void
  currentUser: UserProfile | null
  onLogout: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  currentUser,
  onLogout,
}) => {
  return (
    <header className="border-b border-[#2C2C2E] bg-[#1E1E1E] sticky top-0 z-50 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Brand / Logo Proyek Penlok */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-card bg-[#121212] border border-[#2C2C2E] flex items-center justify-center text-[#00E5FF] shadow-sm">
            <Lock className="w-5 h-5 text-[#00E5FF]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-lg tracking-tight text-white">
                Penlok <span className="text-[#00E5FF] font-mono text-sm">// Smart Locker MAS</span>
              </span>
              <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-[#121212] border border-[#2C2C2E] text-[#32D74B]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#32D74B] "></span>
                Sistem Aktif
              </span>
            </div>
            <p className="text-xs text-text-secondary">
              Platform Kendali Loker Pintar & Pengenalan Wajah Multi-Agen
            </p>
          </div>
        </div>

        {/* Tab Navigasi Utama */}
        <nav className="flex items-center gap-1 bg-[#121212] p-1 rounded-xl border border-[#2C2C2E]">
          <button
            type="button"
            onClick={() => onSelectTab('dashboard')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'dashboard'
                ? 'bg-[#1E1E1E] text-[#00E5FF] shadow-sm border border-[#2C2C2E]'
                : 'text-text-secondary hover:text-white hover:bg-[#1E1E1E]/50'
            }`}
          >
            <Activity className="w-4 h-4" />
            Beranda Admin
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('penghuni')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'penghuni'
                ? 'bg-[#1E1E1E] text-[#00E5FF] shadow-sm border border-[#2C2C2E]'
                : 'text-text-secondary hover:text-white hover:bg-[#1E1E1E]/50'
            }`}
          >
            <Box className="w-4 h-4" />
            Loker Pemilik
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('onboarding')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'onboarding'
                ? 'bg-[#1E1E1E] text-[#00E5FF] shadow-sm border border-[#2C2C2E]'
                : 'text-text-secondary hover:text-white hover:bg-[#1E1E1E]/50'
            }`}
          >
            <UserCheck className="w-4 h-4" />
            Pendaftaran Wajah
          </button>

          <button
            type="button"
            onClick={() => onSelectTab('packages')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
              activeTab === 'packages'
                ? 'bg-[#1E1E1E] text-[#00E5FF] shadow-sm border border-[#2C2C2E]'
                : 'text-text-secondary hover:text-white hover:bg-[#1E1E1E]/50'
            }`}
          >
            <Package className="w-4 h-4" />
            Paket & Resi
          </button>
        </nav>

        {/* Status Node Multi-Agen & Sesi Pengguna */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 text-xs text-text-secondary">
            <span className="flex items-center gap-1 bg-[#121212] px-2.5 py-1 rounded-lg border border-[#2C2C2E]">
              <Server className="w-3.5 h-3.5 text-[#00E5FF]" />
              K3s Cloud (10.1.1.186)
            </span>
            <span className="flex items-center gap-1 bg-[#121212] px-2.5 py-1 rounded-lg border border-[#2C2C2E]">
              <Cpu className="w-3.5 h-3.5 text-[#32D74B]" />
              GPU RTX 3050 CUDA
            </span>
            <span className="flex items-center gap-1 bg-[#121212] px-2.5 py-1 rounded-lg border border-[#2C2C2E]">
              <Radio className="w-3.5 h-3.5 text-text-secondary" />
              Edge Pi 5 (10.1.1.224)
            </span>
          </div>

          {currentUser && (
            <div className="flex items-center gap-3 pl-3 border-l border-[#2C2C2E]">
              <div className="text-right">
                <div className="text-xs font-semibold text-white">
                  {currentUser.fullName}
                </div>
                <div className="text-[11px] text-[#00E5FF] font-mono">
                  @{currentUser.username} [{currentUser.role.toUpperCase()}]
                </div>
              </div>
              <button
                type="button"
                onClick={onLogout}
                className="w-9 h-9 rounded-lg bg-[#121212] border border-[#2C2C2E] flex items-center justify-center text-text-secondary hover:text-[#FF453A] hover:border-[#FF453A]/40 transition-colors cursor-pointer"
                title="Keluar dari sistem"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
