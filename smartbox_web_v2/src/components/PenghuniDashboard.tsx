import React, { useState } from 'react'
import type { UserProfile, LockerCompartment, PackageEntry } from '../types'
import {
  Key,
  Camera,
  PackageCheck,
  CheckCircle,
  Truck,
  ShieldCheck,
  User,
  Scale,
} from 'lucide-react'

interface PenghuniDashboardProps {
  user: UserProfile
  personalLocker: LockerCompartment
  packages: PackageEntry[]
  onOpenLocker: (lockerId: number) => void
  onCancelPackage: (packageId: string) => void
  onNavigateToResi: () => void
  onNavigateToOnboard: () => void
}

export const PenghuniDashboard: React.FC<PenghuniDashboardProps> = ({
  user,
  personalLocker,
  packages,
  onOpenLocker,
  onCancelPackage,
  onNavigateToResi,
  onNavigateToOnboard,
}) => {
  const [unlocking, setUnlocking] = useState<boolean>(false)
  const [successNotice, setSuccessNotice] = useState<string | null>(null)

  const myPackages = packages.filter(
    (p) => p.recipient.toLowerCase() === user.username.toLowerCase() || p.recipient === 'ALL'
  )

  const handleUnlockClick = () => {
    setUnlocking(true)
    onOpenLocker(personalLocker.id)
    setTimeout(() => {
      setUnlocking(false)
      setSuccessNotice('Loker 2 berhasil dibuka! Kunci otomatis akan mengunci kembali setelah beberapa saat.')
      setTimeout(() => setSuccessNotice(null), 4000)
    }, 2000)
  }

  return (
    <div className="space-y-6">
      {/* Sapaan Pengguna & Aksi Cepat */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <User className="w-5 h-5 text-[#00E5FF]" />
            Selamat Datang, {user.fullName}
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Kelola kompartemen loker pribadi, status paket kiriman, dan pendaftaran wajah Anda
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onNavigateToResi}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-[#121212] hover:bg-[#252525] text-white border border-[#2C2C2E] transition-all cursor-pointer"
          >
            <PackageCheck className="w-4 h-4 text-[#00E5FF]" />
            Tambah Nomor Resi
          </button>
          <button
            type="button"
            onClick={onNavigateToOnboard}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-[#00E5FF] hover:bg-[#00E5FF]/80 text-[#121212] transition-all cursor-pointer"
          >
            <Camera className="w-4 h-4" />
            Atur Wajah Saya
          </button>
        </div>
      </div>

      {successNotice && (
        <div className="bg-[#121212] border border-[#32D74B] text-[#32D74B] px-4 py-3 rounded-card text-sm flex items-center gap-2">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          <span>{successNotice}</span>
        </div>
      )}

      {/* Grid: Status Loker Pribadi & Kartu Biometrik Wajah */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Kartu Kompartemen Pribadi (2 Kolom) */}
        <div className="md:col-span-2 bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-text-secondary">
                Loker Terdaftar #{personalLocker.id}
              </span>
              <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-[#121212] border border-[#32D74B] text-[#32D74B]">
                <span className="w-2 h-2 rounded-full bg-[#32D74B]"></span>
                {personalLocker.status}
              </span>
            </div>

            <h3 className="text-lg font-bold text-white mb-2">
              {personalLocker.name}
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 my-4 p-4 rounded-xl bg-[#121212] border border-[#2C2C2E] text-xs">
              <div>
                <span className="text-text-secondary block">Pin Relai Perangkat</span>
                <span className="font-mono text-white font-semibold">GPIO BCM {personalLocker.relayPin}</span>
              </div>
              <div>
                <span className="text-text-secondary block">Mekanisme Pengaman</span>
                <span className="text-[#00E5FF] font-semibold flex items-center gap-1">
                  <Scale className="w-3.5 h-3.5" /> Pintu Geser Bermotor
                </span>
              </div>
              <div>
                <span className="text-text-secondary block">Metode Pembukaan</span>
                <span className="text-[#32D74B] font-semibold">Wajah / Tombol Pemilik</span>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-[#2C2C2E] flex flex-wrap items-center justify-between gap-3">
            <span className="text-xs text-text-secondary flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-[#32D74B]" />
              Terhubung langsung ke modul pengendali fisik loker
            </span>
            <button
              type="button"
              disabled={unlocking}
              onClick={handleUnlockClick}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-[#00E5FF] hover:bg-[#00E5FF]/90 text-[#121212] transition-all disabled:opacity-50 cursor-pointer"
            >
              <Key className="w-4 h-4" />
              {unlocking ? 'Membuka Kunci...' : 'Buka Loker Saya'}
            </button>
          </div>
        </div>

        {/* Kartu Status Biometrik Wajah */}
        <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-col justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-text-secondary mb-3">
              Identitas Pengenalan
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-[#121212] border border-[#2C2C2E] flex items-center justify-center text-[#00E5FF]">
                <Camera className="w-6 h-6" />
              </div>
              <div>
                <div className="text-sm font-bold text-white">ID Pengenalan Wajah</div>
                <div className="text-xs font-mono text-[#00E5FF] font-bold">#{user.faceId}</div>
              </div>
            </div>

            <div className="space-y-2 text-xs py-3 border-y border-[#2C2C2E] text-text-secondary">
              <div className="flex justify-between">
                <span>Model Luring Pi 5:</span>
                <span className="text-[#32D74B] font-medium">Tersinkronkan</span>
              </div>
              <div className="flex justify-between">
                <span>Model GPU Daring:</span>
                <span className="text-[#00E5FF] font-medium">Aktif</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onNavigateToOnboard}
            className="w-full mt-4 py-2 rounded-lg text-xs font-semibold bg-[#121212] hover:bg-[#252525] text-text-secondary hover:text-white border border-[#2C2C2E] transition-all cursor-pointer"
          >
            Perbarui Foto Wajah
          </button>
        </div>
      </div>

      {/* Tabel Paket Milik Penghuni */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Truck className="w-5 h-5 text-[#00E5FF]" />
            Daftar Paket Saya
          </h3>
          <span className="text-xs font-mono text-text-secondary">
            Total: {myPackages.length} Paket
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-[#2C2C2E] text-xs font-semibold text-text-secondary uppercase">
                <th className="py-3 px-4">No</th>
                <th className="py-3 px-4">Nomor Resi</th>
                <th className="py-3 px-4">Ekspedisi</th>
                <th className="py-3 px-4">Nama Barang</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">PIN Angka (5 Digit)</th>
                <th className="py-3 px-4 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {myPackages.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-text-secondary">
                    Belum ada paket yang terdaftar atas nama akun Anda.
                  </td>
                </tr>
              ) : (
                myPackages.map((pkg, idx) => (
                  <tr
                    key={pkg.id}
                    className="border-b border-[#2C2C2E] hover:bg-[#252525] transition-colors"
                  >
                    <td className="py-3 px-4 font-mono text-text-secondary">{idx + 1}</td>
                    <td className="py-3 px-4 font-mono font-bold text-white">{pkg.trackingNumber}</td>
                    <td className="py-3 px-4 text-text-secondary">{pkg.courierName}</td>
                    <td className="py-3 px-4 text-white">{pkg.itemName}</td>
                    <td className="py-3 px-4">
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#121212] border border-[#2C2C2E] text-[#32D74B]">
                        {pkg.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-base font-bold text-[#00E5FF]">
                      {pkg.last5Digits}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {pkg.status === 'DALAM_PERJALANAN' ? (
                        <button
                          type="button"
                          onClick={() => onCancelPackage(pkg.id)}
                          className="text-xs text-[#FF453A] hover:underline cursor-pointer"
                        >
                          Batalkan
                        </button>
                      ) : (
                        <span className="text-text-secondary text-xs">-</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
