import React, { useState } from 'react'
import type { PackageEntry } from '../types'
import {
  Package,
  Plus,
  Search,
  Truck,
  CheckCircle2,
} from 'lucide-react'

interface PackageTrackingViewProps {
  packages: PackageEntry[]
  onAddPackage: (pkg: Omit<PackageEntry, 'id' | 'dateAdded'>) => void
  onCancelPackage: (packageId: string) => void
}

const COURIER_OPTIONS = [
  'SPX Express (Shopee)',
  'J&T Express',
  'SiCepat Ekspres',
  'JNE Express',
  'Ninja Van ID',
  'AnterAja',
  'POS Indonesia',
]

export const PackageTrackingView: React.FC<PackageTrackingViewProps> = ({
  packages,
  onAddPackage,
  onCancelPackage,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [courierName, setCourierName] = useState<string>(COURIER_OPTIONS[0])
  const [trackingNumber, setTrackingNumber] = useState<string>('')
  const [itemName, setItemName] = useState<string>('')
  const [recipient, setRecipient] = useState<string>('akmal')
  const [feedback, setFeedback] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const computeLast5Digits = (trackingNum: string): string => {
    const cleaned = trackingNum.replace(/[^0-9]/g, '')
    if (cleaned.length >= 5) {
      return cleaned.slice(-5)
    }
    return cleaned.padStart(5, '0')
  }

  const livePin = computeLast5Digits(trackingNumber)

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMsg(null)

    if (!trackingNumber.trim() || trackingNumber.trim().length < 5) {
      setErrorMsg('Nomor resi pengiriman minimal harus memiliki 5 karakter angka.')
      return
    }

    if (!itemName.trim()) {
      setErrorMsg('Deskripsi atau nama paket tidak boleh kosong.')
      return
    }

    const pin = computeLast5Digits(trackingNumber.trim())

    onAddPackage({
      trackingNumber: trackingNumber.trim().toUpperCase(),
      courierName,
      itemName: itemName.trim(),
      status: 'DALAM_PERJALANAN',
      last5Digits: pin,
      recipient: recipient.trim(),
      lockerId: 1,
    })

    setFeedback(`Nomor resi berhasil didaftarkan! PIN untuk kurir di tombol fisik adalah: ${pin}`)
    setTrackingNumber('')
    setItemName('')
    setTimeout(() => setFeedback(null), 5000)
  }

  const filteredPackages = packages.filter((pkg) => {
    return (
      pkg.trackingNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pkg.itemName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      pkg.last5Digits.includes(searchQuery) ||
      pkg.recipient.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })

  return (
    <div className="space-y-6">
      {/* Header Penjelasan Logistik */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Package className="w-5 h-5 text-[#00E5FF]" />
            Pendaftaran & Pelacakan Paket Resi Kurir
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Daftarkan nomor resi kurir agar dapat membuka Loker 1 secara otomatis melalui tombol angka fisik
          </p>
        </div>
      </div>

      {feedback && (
        <div className="bg-[#121212] border border-[#32D74B] text-[#32D74B] p-4 rounded-card text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{feedback}</span>
        </div>
      )}

      {/* Grid: Form Registrasi Resi (7 Kolom) + Panduan Perangkat Kurir (5 Kolom) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Formulir Pendaftaran */}
        <div className="lg:col-span-7 bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6">
          <h3 className="text-base font-semibold text-white mb-4">
            Formulir Tambah Nomor Resi Paket
          </h3>

          <form onSubmit={handleFormSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-text-secondary block mb-1.5 font-medium">
                  Perusahaan Ekspedisi
                </label>
                <select
                  value={courierName}
                  onChange={(e) => setCourierName(e.target.value)}
                  className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn px-3 py-2 text-sm focus:outline-none focus:border-[#00E5FF]"
                >
                  {COURIER_OPTIONS.map((c) => (
                    <option key={c} value={c} className="bg-[#1E1E1E]">
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs text-text-secondary block mb-1.5 font-medium">
                  Nama Penerima (Penghuni)
                </label>
                <input
                  type="text"
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder="Username penerima..."
                  className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn px-3 py-2 text-sm focus:outline-none focus:border-[#00E5FF]"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-text-secondary block mb-1.5 font-medium">
                Nomor Resi Pengiriman
              </label>
              <input
                type="text"
                value={trackingNumber}
                onChange={(e) => setTrackingNumber(e.target.value)}
                placeholder="Contoh: SPXID0981249821"
                className="w-full bg-[#121212] text-white font-mono border border-[#2C2C2E] rounded-btn px-3 py-2 text-sm focus:outline-none focus:border-[#00E5FF]"
              />
            </div>

            <div>
              <label className="text-xs text-text-secondary block mb-1.5 font-medium">
                Nama / Deskripsi Barang
              </label>
              <input
                type="text"
                value={itemName}
                onChange={(e) => setItemName(e.target.value)}
                placeholder="Contoh: Modul Kamera Raspberry Pi / Pakaian"
                className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn px-3 py-2 text-sm focus:outline-none focus:border-[#00E5FF]"
              />
            </div>

            {/* Preview PIN 5 Digit Tombol Angka */}
            <div className="p-4 rounded-xl bg-[#121212] border border-[#2C2C2E] flex items-center justify-between">
              <div>
                <span className="text-xs text-text-secondary block">
                  PIN Akses Pintu Fisik (5 Digit Terakhir):
                </span>
                <span className="text-2xl kpi-mono text-[#00E5FF]">
                  {livePin}
                </span>
              </div>
              <span className="text-xs text-text-secondary text-right max-w-[200px]">
                Kode yang akan ditekan oleh kurir ekspedisi pada tombol Loker 1.
              </span>
            </div>

            {errorMsg && (
              <div className="p-3 rounded-lg bg-[#3A1C1C] text-[#FF453A] text-xs">
                {errorMsg}
              </div>
            )}

            <button
              type="submit"
              className="w-full py-2.5 rounded-lg text-sm font-semibold bg-[#00E5FF] hover:bg-[#00E5FF]/90 text-[#121212] transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Simpan & Sinkronkan Resi ke Loker Fisik
            </button>
          </form>
        </div>

        {/* Panduan Alur Kerja Fisik Kurir */}
        <div className="lg:col-span-5 bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
              <Truck className="w-5 h-5 text-[#32D74B]" />
              Alur Penerimaan Paket di Smart Locker
            </h3>
            <p className="text-xs text-text-secondary mb-4 leading-relaxed">
              Kurir tidak membutuhkan aplikasi atau koneksi internet khusus saat mengantarkan barang.
            </p>

            <div className="space-y-3 text-xs text-text-secondary">
              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-white font-semibold block mb-0.5">1. Tekan 5 Digit Resi</span>
                Kurir memilih menu kirim paket di layar dan memasukkan 5 digit terakhir resi.
              </div>
              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-white font-semibold block mb-0.5">2. Pintu Loker 1 Terbuka</span>
                Relai BCM 10 aktif selama 2.5 detik untuk membuka kunci pintu penampungan masuk.
              </div>
              <div className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E]">
                <span className="text-white font-semibold block mb-0.5">3. Otomatisasi Pintu Geser & Sensor</span>
                Sensor ultrasonik mendeteksi paket (&le; 23 cm) dan motor memindahkan paket ke Loker 2 penyimpanan aman.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabel Master Paket Terdaftar */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <h3 className="text-lg font-semibold text-white">
            Daftar Paket Terdata di Sistem
          </h3>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-text-secondary absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari berdasarkan resi / PIN..."
              className="w-full bg-[#121212] text-white border border-[#2C2C2E] rounded-btn pl-9 pr-3 py-1.5 text-xs focus:outline-none focus:border-[#00E5FF]"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-[#2C2C2E] text-xs font-semibold text-text-secondary uppercase">
                <th className="py-3 px-4">No</th>
                <th className="py-3 px-4">Nomor Resi</th>
                <th className="py-3 px-4">Ekspedisi</th>
                <th className="py-3 px-4">Nama Barang</th>
                <th className="py-3 px-4">Penerima</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">PIN Angka (5 Digit)</th>
                <th className="py-3 px-4 text-right">Aksi</th>
              </tr>
            </thead>
            <tbody>
              {filteredPackages.map((pkg, idx) => (
                <tr
                  key={pkg.id}
                  className="border-b border-[#2C2C2E] hover:bg-[#252525] transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-text-secondary">{idx + 1}</td>
                  <td className="py-3 px-4 font-mono font-bold text-white">{pkg.trackingNumber}</td>
                  <td className="py-3 px-4 text-text-secondary">{pkg.courierName}</td>
                  <td className="py-3 px-4 text-white">{pkg.itemName}</td>
                  <td className="py-3 px-4 text-text-secondary">@{pkg.recipient}</td>
                  <td className="py-3 px-4">
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#121212] border border-[#2C2C2E] text-[#32D74B]">
                      {pkg.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 font-mono text-base font-bold text-[#00E5FF]">
                    {pkg.last5Digits}
                  </td>
                  <td className="py-3 px-4 text-right">
                    {pkg.status === 'DALAM_PERJALANAN' && (
                      <button
                        type="button"
                        onClick={() => onCancelPackage(pkg.id)}
                        className="text-xs text-[#FF453A] hover:underline cursor-pointer"
                      >
                        Batalkan
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
