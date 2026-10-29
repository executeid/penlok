import React, { useState, useEffect } from 'react'
import type {
  LockerCompartment,
  MASSchedulerTelemetry,
  ActivityNotificationLog,
} from '../types'
import {
  Cpu,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Unlock,
  Radio,
  CheckCircle2,
  XCircle,
  Network,
  Scale,
} from 'lucide-react'

interface AdminDashboardProps {
  lockers: LockerCompartment[]
  telemetry: MASSchedulerTelemetry
  activityLogs: ActivityNotificationLog[]
  onTriggerRelay: (lockerId: number) => void
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({
  lockers,
  telemetry,
  activityLogs,
  onTriggerRelay,
}) => {
  const [liveDistance, setLiveDistance] = useState<number>(5.0)
  const [statusText, setStatusText] = useState<string>('Membaca sensor...')
  const [triggeringId, setTriggeringId] = useState<number | null>(null)
  const [latencyHistory, setLatencyHistory] = useState<number[]>([32.4, 38.1, 35.6, 42.0, 39.5, 36.8, 38.2])

  // Polling sensor ultrasonik live dari Edge Pi 5 (/api/sensor)
  useEffect(() => {
    const fetchSensor = async () => {
      try {
        const res = await fetch('/api/sensor')
        if (res.ok) {
          const data = await res.json()
          if (typeof data.distance_cm === 'number') {
            setLiveDistance(data.distance_cm)
            setStatusText(data.status || 'Aktif')
            return
          }
        }
      } catch {
        // Fallback jika jaringan offline sementara
      }
    }

    fetchSensor()
    const interval = setInterval(fetchSensor, 2500)
    return () => clearInterval(interval)
  }, [])

  // Mengumpulkan riwayat latensi riil setiap kali telemetri terupdate
  useEffect(() => {
    if (telemetry.totalLatencyMs > 0) {
      setLatencyHistory((prev) => {
        const next = [...prev.slice(1), telemetry.totalLatencyMs]
        return next
      })
    }
  }, [telemetry.totalLatencyMs, telemetry.lastInferenceTime])

  const handleManualUnlock = (lockerId: number) => {
    setTriggeringId(lockerId)
    onTriggerRelay(lockerId)
    setTimeout(() => setTriggeringId(null), 2500)
  }

  // Generate SVG path koordinat dari data riil
  const points = latencyHistory.map((val, idx) => {
    const x = (idx / (latencyHistory.length - 1)) * 500
    // skala 0-100 ms ke tinggi 150px
    const y = Math.max(15, Math.min(135, 140 - (val / 100) * 120))
    return { x, y }
  })
  const pathLine = points.reduce((acc, p, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`, '')
  const pathArea = `${pathLine} L 500,150 L 0,150 Z`

  return (
    <div className="space-y-6">
      {/* 1. Baris 3 Kartu Metrik Utama */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Indikator 1: Sensor Ultrasonik */}
        <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-text-secondary text-sm">
            <span>Sensor Ultrasonik (Loker 1)</span>
            <Radio className="w-5 h-5 text-[#32D74B]" />
          </div>
          <div className="my-3">
            <div className="text-3xl kpi-mono text-white flex items-baseline gap-2">
              {liveDistance}{' '}
              <span className="text-lg font-normal text-text-secondary">cm</span>
              {liveDistance <= 23.0 ? (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#121212] border border-[#32D74B] text-[#32D74B] font-sans font-medium">
                  Terisi
                </span>
              ) : (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#121212] border border-[#2C2C2E] text-text-secondary font-sans">
                  Kosong
                </span>
              )}
            </div>
            <div className="text-xs text-text-secondary mt-1">
              Status Ruang: <span className={liveDistance <= 23.0 ? 'text-[#32D74B] font-semibold' : 'text-text-secondary'}>{statusText}</span>
            </div>
          </div>
          <div className="text-[11px] text-text-secondary flex justify-between border-t border-[#2C2C2E] pt-2 font-mono">
            <span>Ambang Batas: 23.0 cm</span>
            <span className="text-[#00E5FF]">BCM 15 (Trig) / 17 (Echo)</span>
          </div>
        </div>

        {/* Indikator 2: Beban Komputasi Riil Pi 5 */}
        <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-text-secondary text-sm">
            <span>Beban Komputasi Pi 5 (Edge)</span>
            <Cpu className="w-5 h-5 text-[#00E5FF]" />
          </div>
          <div className="my-3">
            <div className="text-3xl kpi-mono text-white">
              {telemetry.cpuUsage.toFixed(1)} <span className="text-lg font-normal text-text-secondary">%</span>
            </div>
            <div className="text-xs text-text-secondary mt-1 flex items-center gap-1.5">
              <span>Alur Pemrosesan:</span>
              <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-[#121212] border border-[#2C2C2E] text-[#00E5FF]">
                {telemetry.decision === 0 ? '0: Diproses di Perangkat Tepi' : '1: Dialihkan ke Komputasi Awan'}
              </span>
            </div>
          </div>
          <div className="w-full bg-[#121212] h-2 rounded-full overflow-hidden border border-[#2C2C2E]">
            <div
              className={`h-full transition-all duration-500 ${
                telemetry.cpuUsage > 75 ? 'bg-[#FF453A]' : 'bg-[#32D74B]'
              }`}
              style={{ width: `${Math.min(100, telemetry.cpuUsage)}%` }}
            ></div>
          </div>
        </div>

        {/* Indikator 3: Waktu Tanggap Pengenalan Wajah */}
        <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between text-text-secondary text-sm">
            <span>Waktu Tanggap Total</span>
            <Network className="w-5 h-5 text-[#00E5FF]" />
          </div>
          <div className="my-3">
            <div className="text-3xl kpi-mono text-white">
              {telemetry.totalLatencyMs.toFixed(1)} <span className="text-lg font-normal text-text-secondary">ms</span>
            </div>
            <div className="text-xs text-text-secondary mt-1 font-mono">
              Komputasi GPU: <span className="text-[#32D74B]">{telemetry.embeddingLatencyMs} ms</span> | Deteksi Wajah: <span className="text-[#00E5FF]">{telemetry.yunetLatencyMs} ms</span>
            </div>
          </div>
          <div className="text-[11px] text-text-secondary flex justify-between border-t border-[#2C2C2E] pt-2">
            <span>Jalur: Jaringan Terenkripsi</span>
            <span className="text-[#32D74B]">Standar &lt; 400 ms</span>
          </div>
        </div>
      </div>

      {/* 2. Grid Utama */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Kolom Kiri: Grafik Riil dan Status Kompartemen */}
        <div className="lg:col-span-8 space-y-6">
          {/* Grafik Pemantauan Waktu Nyata dari Data Riil */}
          <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Grafik Waktu Tanggap Sistem
                </h3>
                <p className="text-xs text-text-secondary">
                  Titik data riil latensi bolak-balik pengenalan wajah multi-agen
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono">
                <span className="flex items-center gap-1.5 text-text-secondary">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#00E5FF]"></span>
                  Titik Data Terkini: {telemetry.totalLatencyMs} ms
                </span>
                <span className="flex items-center gap-1.5 text-text-secondary">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#32D74B]"></span>
                  Terakhir: {telemetry.lastInferenceTime}
                </span>
              </div>
            </div>

            {/* Visualisasi Kurva Area SVG Dinamis dari Data Riil */}
            <div className="h-56 w-full relative bg-[#121212] rounded-xl p-4 border border-[#2C2C2E] overflow-hidden">
              <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 500 150">
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.40" />
                    <stop offset="60%" stopColor="#32D74B" stopOpacity="0.12" />
                    <stop offset="100%" stopColor="#121212" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                <line x1="0" y1="35" x2="500" y2="35" stroke="#2C2C2E" strokeDasharray="4 4" strokeWidth="1" />
                <line x1="0" y1="75" x2="500" y2="75" stroke="#2C2C2E" strokeDasharray="4 4" strokeWidth="1" />
                <line x1="0" y1="115" x2="500" y2="115" stroke="#2C2C2E" strokeDasharray="4 4" strokeWidth="1" />

                <path d={pathArea} fill="url(#areaGrad)" />
                <path d={pathLine} fill="none" stroke="#00E5FF" strokeWidth="2.5" />
                {points.map((p, idx) => (
                  <circle key={idx} cx={p.x} cy={p.y} r="3.5" fill="#121212" stroke="#00E5FF" strokeWidth="2" />
                ))}
              </svg>

              <div className="absolute bottom-2 left-4 right-4 flex justify-between text-[11px] text-text-secondary font-mono">
                <span>-60 detik</span>
                <span>-45 detik</span>
                <span>-30 detik</span>
                <span>-15 detik</span>
                <span>Saat ini</span>
              </div>
            </div>
          </div>

          {/* Matriks 3 Kompartemen Loker Fisik */}
          <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-white">
                  Status Kompartemen Loker Fisik
                </h3>
                <p className="text-xs text-text-secondary">
                  Kendali sakelar relai magnetik, sensor inframerah pintu, dan pemantauan beban
                </p>
              </div>
              <span className="text-xs font-mono text-[#00E5FF] px-2.5 py-1 rounded bg-[#121212] border border-[#2C2C2E]">
                3 Loker Siap
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {lockers.map((locker) => (
                <div
                  key={locker.id}
                  className="bg-[#121212] border border-[#2C2C2E] rounded-xl p-4 flex flex-col justify-between hover:border-[#00E5FF]/40 transition-all"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-text-secondary uppercase">
                        Kompartemen #{locker.id}
                      </span>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-[#1E1E1E] text-[#32D74B] border border-[#2C2C2E] font-medium">
                        {locker.status}
                      </span>
                    </div>
                    <div className="text-sm font-semibold text-white mb-1">
                      {locker.name}
                    </div>
                    <div className="text-xs text-text-secondary font-mono mb-3">
                      Pin Relai: BCM {locker.relayPin} • Status: {locker.relayState}
                    </div>
                    {locker.id === 1 && (
                      <div className="text-xs text-[#00E5FF] bg-[#1E1E1E] p-2 rounded border border-[#2C2C2E] mb-3">
                        Pintu masuk kurir (Otentikasi 5 angka terakhir resi)
                      </div>
                    )}
                    {locker.id === 2 && (
                      <div className="text-xs text-[#32D74B] bg-[#1E1E1E] p-2 rounded border border-[#2C2C2E] mb-3 flex items-center gap-1.5">
                        <Scale className="w-3.5 h-3.5" />
                        Ruang simpan tertutup (Mekanisme pintu geser motor)
                      </div>
                    )}
                    {locker.id === 3 && (
                      <div className="text-xs text-[#00E5FF] bg-[#1E1E1E] p-2 rounded border border-[#2C2C2E] mb-3">
                        Loker transaksi bersama (Otentikasi sandi OTP 6 angka)
                      </div>
                    )}
                  </div>

                  <button
                    type="button"
                    disabled={triggeringId === locker.id}
                    onClick={() => handleManualUnlock(locker.id)}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-semibold bg-[#1E1E1E] hover:bg-[#00E5FF] hover:text-[#121212] text-white border border-[#2C2C2E] transition-all disabled:opacity-50 cursor-pointer"
                  >
                    <Unlock className="w-3.5 h-3.5" />
                    {triggeringId === locker.id ? 'Membuka 2.5 Detik...' : 'Buka Kunci Manual'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Kolom Kanan: Peringatan Keamanan & Riwayat Catatan */}
        <div className="lg:col-span-4 space-y-6">
          {/* Kotak Pemberitahuan Keamanan */}
          <div className="bg-[#3A1C1C] border-l-4 border-l-[#FF453A] rounded-card p-5">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-[#FF453A] flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-[#FF453A]">
                  Pemberitahuan Sistem Keamanan
                </h4>
                <p className="text-xs text-[#FFFFFF]/90 mt-1 leading-relaxed">
                  Semua relai sakelar dikendalikan secara otomatis dengan pembatasan durasi maksimum 2.5 detik guna melindungi komponen elektronik dari beban panas berlebih. Apabila jaringan utama terputus, autentikasi dialihkan ke mode luring mandiri secara seketika.
                </p>
                <div className="mt-3 flex items-center gap-2 text-[11px] text-text-secondary">
                  <ShieldCheck className="w-3.5 h-3.5 text-[#32D74B]" />
                  <span>Perlindungan otomatis aktif</span>
                </div>
              </div>
            </div>
          </div>

          {/* Panel Riwayat Catatan Aktivitas */}
          <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-text-secondary" />
                Catatan Aktivitas Terkini
              </h3>
              <span className="text-[11px] text-text-secondary font-mono">Waktu Nyata</span>
            </div>

            <div className="space-y-3">
              {activityLogs.slice(0, 5).map((log) => (
                <div
                  key={log.id}
                  className="p-3 bg-[#121212] rounded-xl border border-[#2C2C2E] hover:bg-[#252525] transition-colors"
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-semibold text-white">{log.event}</span>
                    <span className="text-[11px] text-text-secondary font-mono">{log.timestamp}</span>
                  </div>
                  <p className="text-xs text-text-secondary line-clamp-2">
                    {log.details}
                  </p>
                  <div className="mt-2 flex items-center justify-between text-[11px]">
                    <span className="text-[#00E5FF] font-mono">{log.compartment}</span>
                    {log.status === 'SUCCESS' ? (
                      <span className="flex items-center gap-1 text-[#32D74B] font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Berhasil
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[#FF453A] font-medium">
                        <XCircle className="w-3 h-3" /> Gagal
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
