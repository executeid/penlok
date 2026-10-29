import React, { useState } from 'react'
import type { UserProfile, UserRole } from '../types'
import { Shield, User, ArrowRight, Lock } from 'lucide-react'

interface LoginViewProps {
  onLoginSuccess: (user: UserProfile) => void
}

const PRESET_USERS: Record<UserRole, UserProfile> = {
  admin: {
    id: 'usr_admin_01',
    username: 'admin',
    fullName: 'Operator Sistem (Admin)',
    role: 'admin',
    faceId: 100001,
    faceStatus: 'synced',
    email: 'admin@penlok.id',
  },
  penghuni: {
    id: 'usr_penghuni_02',
    username: 'akmal',
    fullName: 'Akmal (Pemilik Loker)',
    role: 'penghuni',
    faceId: 789123,
    faceStatus: 'synced',
    email: 'akmal@smartbox.id',
  },
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const [selectedRole, setSelectedRole] = useState<UserRole>('admin')
  const [username, setUsername] = useState<string>('admin')
  const [password, setPassword] = useState<string>('password')
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)

  const handleRoleChange = (role: UserRole) => {
    setSelectedRole(role)
    const preset = PRESET_USERS[role]
    setUsername(preset.username)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setTimeout(() => {
      setIsSubmitting(false)
      const user = PRESET_USERS[selectedRole]
      onLoginSuccess({
        ...user,
        username,
      })
    }, 400)
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-8 shadow-2xl">
        {/* Logo / Header Penlok */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-[#121212] border border-[#2C2C2E] flex items-center justify-center mx-auto text-[#00E5FF] mb-3">
            <Lock className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            Portal Smart Locker Penlok
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Sistem Manajemen Loker Pintar & Pemantauan IoT Multi-Agen
          </p>
        </div>

        {/* Pemilih Peran Akun */}
        <div className="grid grid-cols-2 gap-3 mb-6 p-1 bg-[#121212] rounded-xl border border-[#2C2C2E]">
          <button
            type="button"
            onClick={() => handleRoleChange('admin')}
            className={`flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              selectedRole === 'admin'
                ? 'bg-[#1E1E1E] text-[#00E5FF] border border-[#2C2C2E]'
                : 'text-text-secondary hover:text-white'
            }`}
          >
            <Shield className="w-4 h-4" />
            Admin Sistem
          </button>
          <button
            type="button"
            onClick={() => handleRoleChange('penghuni')}
            className={`flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              selectedRole === 'penghuni'
                ? 'bg-[#1E1E1E] text-[#00E5FF] border border-[#2C2C2E]'
                : 'text-text-secondary hover:text-white'
            }`}
          >
            <User className="w-4 h-4" />
            Pemilik / Penghuni
          </button>
        </div>

        {/* Formulir Masuk */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-text-secondary block mb-1.5 font-medium">
              Nama Pengguna (Username)
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn px-4 py-2.5 text-sm focus:outline-none focus:border-[#00E5FF]"
            />
          </div>

          <div>
            <label className="text-xs text-text-secondary block mb-1.5 font-medium">
              Kata Sandi (Password)
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn px-4 py-2.5 text-sm focus:outline-none focus:border-[#00E5FF]"
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-3 rounded-lg text-sm font-semibold bg-[#00E5FF] hover:bg-[#00E5FF]/90 text-[#121212] transition-all flex items-center justify-center gap-2 shadow-sm cursor-pointer"
          >
            <span>{isSubmitting ? 'Memverifikasi...' : 'Masuk ke Sistem'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  )
}
