export type UserRole = 'admin' | 'penghuni'

export interface UserProfile {
  id: string
  username: string
  fullName: string
  role: UserRole
  faceId: number
  faceStatus: 'unregistered' | 'pending' | 'synced'
  email?: string
}

export type LockerType = 'inbound' | 'personal' | 'marketplace'
export type LockerStatus = 'TERSEDIA' | 'TERKUNCI_AMAN' | 'SIAP_AMBIL'
export type RelayState = 'TERKUNCI' | 'TERBUKA'

export interface LockerCompartment {
  id: number
  name: string
  type: LockerType
  status: LockerStatus
  relayPin: number
  relayState: RelayState
  sensorDistanceCm?: number
  assignedTo?: string
  otpCode?: string
  lastEvent?: string
}

export type PackageStatus =
  | 'DALAM_PERJALANAN'
  | 'DITERIMA_LOKER_1'
  | 'TERSIMPAN_LOKER_2'
  | 'SUDAH_DIAMBIL'
  | 'DIBATALKAN'

export interface PackageEntry {
  id: string
  trackingNumber: string
  courierName: string
  itemName: string
  status: PackageStatus
  dateAdded: string
  last5Digits: string
  recipient: string
  lockerId: number
}

export interface MASSchedulerTelemetry {
  cpuUsage: number
  decision: number
  decisionReason: string
  totalLatencyMs: number
  yunetLatencyMs: number
  embeddingLatencyMs: number
  edgePiIp: string
  cloudGpuIp: string
  schedulerIp: string
  lastInferenceTime: string
}

export interface ActivityNotificationLog {
  id: string
  timestamp: string
  event: string
  compartment: string
  node: 'EDGE' | 'CLOUD_GPU'
  status: 'SUCCESS' | 'WARN' | 'INFO' | 'ERROR'
  details: string
}
