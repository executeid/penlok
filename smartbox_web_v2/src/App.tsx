import { useState, useEffect } from 'react'
import type {
  UserProfile,
  LockerCompartment,
  PackageEntry,
  MASSchedulerTelemetry,
  ActivityNotificationLog,
} from './types'
import { Navbar, type NavTab } from './components/Navbar'
import { LoginView } from './components/LoginView'
import { AdminDashboard } from './components/AdminDashboard'
import { PenghuniDashboard } from './components/PenghuniDashboard'
import { FaceOnboardingView } from './components/FaceOnboardingView'
import { PackageTrackingView } from './components/PackageTrackingView'

const INITIAL_LOCKERS: LockerCompartment[] = [
  {
    id: 1,
    name: 'Loker 1 (Pintu Masuk Kurir Ekspedisi)',
    type: 'inbound',
    status: 'TERSEDIA',
    relayPin: 10,
    relayState: 'TERKUNCI',
    sensorDistanceCm: 5.0,
    lastEvent: 'Paket terdeteksi oleh sensor ultrasonik',
  },
  {
    id: 2,
    name: 'Loker 2 (Penyimpanan Aman Pemilik)',
    type: 'personal',
    status: 'TERKUNCI_AMAN',
    relayPin: 9,
    relayState: 'TERKUNCI',
    assignedTo: 'akmal',
    lastEvent: 'Kunci magnetik dan pintu penutup tertutup rapat',
  },
  {
    id: 3,
    name: 'Loker 3 (Marketplace / Pengambilan Langsung)',
    type: 'marketplace',
    status: 'SIAP_AMBIL',
    relayPin: 6,
    relayState: 'TERKUNCI',
    otpCode: '789123',
    lastEvent: 'Menunggu pengambilan dengan kode sandi OTP',
  },
]

const INITIAL_TELEMETRY: MASSchedulerTelemetry = {
  cpuUsage: 24.5,
  decision: 0,
  decisionReason: 'Beban prosesor Pi 5 <= 75%, verifikasi diproses langsung di perangkat tepi',
  totalLatencyMs: 38.2,
  yunetLatencyMs: 14.5,
  embeddingLatencyMs: 23.7,
  edgePiIp: '10.1.1.224',
  cloudGpuIp: '10.1.1.186',
  schedulerIp: '10.1.1.57',
  lastInferenceTime: '13:50:00',
}

const INITIAL_LOGS: ActivityNotificationLog[] = [
  {
    id: 'log_01',
    timestamp: '13:48:15',
    event: 'AUTENTIKASI_WAJAH',
    compartment: 'LOKER #2',
    node: 'CLOUD_GPU',
    status: 'SUCCESS',
    details: 'Pengguna Akmal terverifikasi sukses (InceptionResnetV1 CUDA 96.1%). Relai BCM 9 terbuka 2.5 detik.',
  },
  {
    id: 'log_02',
    timestamp: '13:45:00',
    event: 'SENSOR_ULTRASONIK',
    compartment: 'LOKER #1',
    node: 'EDGE',
    status: 'SUCCESS',
    details: 'Jarak terbaca 5.0 cm <= 23.0 cm. Paket barang terdeteksi di Loker 1.',
  },
  {
    id: 'log_03',
    timestamp: '12:30:22',
    event: 'SINKRONISASI_MODEL',
    compartment: 'SISTEM',
    node: 'EDGE',
    status: 'SUCCESS',
    details: 'Model luring LBPH lokal diperbarui otomatis dengan data wajah Akmal.',
  },
]

export default function App() {
  const [currentUser, setCurrentUser] = useState<UserProfile | null>({
    id: 'usr_admin_01',
    username: 'admin',
    fullName: 'Operator Sistem (Admin)',
    role: 'admin',
    faceId: 100001,
    faceStatus: 'synced',
    email: 'admin@penlok.id',
  })
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard')
  const [lockers, setLockers] = useState<LockerCompartment[]>(INITIAL_LOCKERS)
  const [packages, setPackages] = useState<PackageEntry[]>([])
  const [telemetry, setTelemetry] = useState<MASSchedulerTelemetry>(INITIAL_TELEMETRY)
  const [logs] = useState<ActivityNotificationLog[]>(INITIAL_LOGS)

  // Mengambil data paket riil dan telemetri langsung dari modul Edge & Cloud
  useEffect(() => {
    const loadRealData = async () => {
      // 1. Muat paket riil dari database PostgreSQL Edge Pi 5
      try {
        const resPkg = await fetch('/api/packages')
        if (resPkg.ok) {
          const pkgData = await resPkg.json()
          if (Array.isArray(pkgData)) {
            setPackages(pkgData)
          }
        }
      } catch (err) {
        console.error('Gagal memuat paket:', err)
      }

      // 2. Muat telemetri CPU riil dari Edge Pi 5
      try {
        const resTelem = await fetch('/api/telemetry')
        if (resTelem.ok) {
          const tData = await resTelem.json()
          if (typeof tData.cpu_usage === 'number') {
            setTelemetry((prev) => ({
              ...prev,
              cpuUsage: tData.cpu_usage,
              lastInferenceTime: new Date().toLocaleTimeString('id-ID'),
            }))
          }
        }
      } catch (err) {
        console.error('Gagal memuat telemetri CPU:', err)
      }
    }

    loadRealData()
    const timer = setInterval(loadRealData, 3000)
    return () => clearInterval(timer)
  }, [])

  const handleOpenLocker = async (lockerId: number) => {
    setLockers((prev) =>
      prev.map((l) =>
        l.id === lockerId
          ? { ...l, relayState: 'TERBUKA' as const }
          : l
      )
    )

    setTimeout(() => {
      setLockers((prev) =>
        prev.map((l) =>
          l.id === lockerId
            ? { ...l, relayState: 'TERKUNCI' as const }
            : l
        )
      )
    }, 2500)
  }

  const handleAddPackage = async (newPkg: Omit<PackageEntry, 'id' | 'dateAdded'>) => {
    try {
      const resp = await fetch('/api/packages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tracking_number: newPkg.trackingNumber,
          courier_name: newPkg.courierName,
          item_name: newPkg.itemName,
          recipient: newPkg.recipient,
        }),
      })
      if (resp.ok) {
        const resJson = await resp.json()
        const entry: PackageEntry = {
          ...newPkg,
          id: `pkg_${resJson.id}`,
          dateAdded: new Date().toISOString().replace('T', ' ').substring(0, 16),
        }
        setPackages((prev) => [entry, ...prev])
      }
    } catch (err) {
      console.error('Gagal menyimpan paket:', err)
    }
  }

  const handleCancelPackage = async (packageId: string) => {
    try {
      await fetch(`/api/packages/${packageId}`, { method: 'DELETE' })
      setPackages((prev) =>
        prev.map((p) =>
          p.id === packageId ? { ...p, status: 'DIBATALKAN' as const } : p
        )
      )
    } catch (err) {
      console.error('Gagal membatalkan paket:', err)
    }
  }

  if (!currentUser) {
    return (
      <LoginView
        onLoginSuccess={(user) => {
          setCurrentUser(user)
          setActiveTab('dashboard')
        }}
      />
    )
  }

  return (
    <div className="min-h-screen bg-background text-text-primary flex flex-col">
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        currentUser={currentUser}
        onLogout={() => setCurrentUser(null)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8">
        {activeTab === 'dashboard' && (
          <AdminDashboard
            lockers={lockers}
            telemetry={telemetry}
            activityLogs={logs}
            onTriggerRelay={handleOpenLocker}
          />
        )}

        {activeTab === 'penghuni' && (
          <PenghuniDashboard
            user={currentUser}
            personalLocker={lockers[1]}
            packages={packages}
            onOpenLocker={handleOpenLocker}
            onCancelPackage={handleCancelPackage}
            onNavigateToResi={() => setActiveTab('packages')}
            onNavigateToOnboard={() => setActiveTab('onboarding')}
          />
        )}

        {activeTab === 'onboarding' && (
          <FaceOnboardingView
            user={currentUser}
            onOnboardComplete={(updated) => {
              setCurrentUser(updated)
            }}
          />
        )}

        {activeTab === 'packages' && (
          <PackageTrackingView
            packages={packages}
            onAddPackage={handleAddPackage}
            onCancelPackage={handleCancelPackage}
          />
        )}
      </main>
    </div>
  )
}
