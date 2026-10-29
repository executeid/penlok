import React, { useState, useRef, useEffect, useCallback } from 'react'
import type { UserProfile } from '../types'
import {
  Camera,
  Upload,
  CheckCircle2,
  Sparkles,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react'

interface FaceOnboardingViewProps {
  user: UserProfile
  onOnboardComplete: (updatedUser: UserProfile) => void
}

type PoseType = 'front' | 'left' | 'right'

interface PoseGuide {
  id: PoseType
  title: string
  subhead: string
  instruction: string
}

const POSES: PoseGuide[] = [
  {
    id: 'front',
    title: 'Pose 1: Wajah Tampak Depan',
    subhead: 'Tatap lurus ke arah lensa kamera',
    instruction: 'Posisikan wajah Anda tepat di dalam bingkai oval hijau di tengah layar.',
  },
  {
    id: 'left',
    title: 'Pose 2: Profil Miring Kiri',
    subhead: 'Tolehkan wajah sekitar 15 derajat ke kiri',
    instruction: 'Ambil sudut samping kiri untuk memperkaya data fitur wajah.',
  },
  {
    id: 'right',
    title: 'Pose 3: Profil Miring Kanan',
    subhead: 'Tolehkan wajah sekitar 15 derajat ke kanan',
    instruction: 'Ambil sudut samping kanan untuk pengenalan wajah multi-sudut yang optimal.',
  },
]

export const FaceOnboardingView: React.FC<FaceOnboardingViewProps> = ({
  user,
  onOnboardComplete,
}) => {
  const [activePoseIdx, setActivePoseIdx] = useState<number>(0)
  const [capturedImages, setCapturedImages] = useState<Record<PoseType, string | null>>({
    front: null,
    left: null,
    right: null,
  })
  const [inputMode, setInputMode] = useState<'camera' | 'upload'>('camera')
  const [isProcessing, setIsProcessing] = useState<boolean>(false)
  const [currentStep, setCurrentStep] = useState<string>('Menunggu pengambilan foto')
  const [statusMessage, setStatusMessage] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  // Inisialisasi Aliran Video Kamera
  const startCamera = useCallback(async () => {
    try {
      setErrorMessage(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }
      streamRef.current = stream
    } catch {
      setErrorMessage(
        'Kamera web tidak dapat diakses atau izin ditolak. Anda dapat menggunakan tab "Unggah Berkas".'
      )
      setInputMode('upload')
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
  }, [])

  useEffect(() => {
    if (inputMode === 'camera') {
      startCamera()
    } else {
      stopCamera()
    }
    return () => stopCamera()
  }, [inputMode, startCamera, stopCamera])

  const handleCapturePose = () => {
    if (!videoRef.current) return
    const canvas = document.createElement('canvas')
    canvas.width = 640
    canvas.height = 480
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.drawImage(videoRef.current, 0, 0, 640, 480)
    const dataUrl = canvas.toDataURL('image/jpeg', 0.9)
    const currentPose = POSES[activePoseIdx].id

    setCapturedImages((prev) => ({
      ...prev,
      [currentPose]: dataUrl,
    }))

    if (activePoseIdx < POSES.length - 1) {
      setActivePoseIdx((prev) => prev + 1)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const result = event.target?.result as string
      const currentPose = POSES[activePoseIdx].id
      setCapturedImages((prev) => ({
        ...prev,
        [currentPose]: result,
      }))
      if (activePoseIdx < POSES.length - 1) {
        setActivePoseIdx((prev) => prev + 1)
      }
    }
    reader.readAsDataURL(files[0])
  }

  const allPosesReady = Boolean(
    capturedImages.front && capturedImages.left && capturedImages.right
  )

  const handleCompleteOnboarding = async () => {
    if (!allPosesReady) return

    setIsProcessing(true)
    setErrorMessage(null)
    setCurrentStep('1. Mengunggah sampel foto ke Cloud GPU (10.1.1.186)...')

    const imagesList = [
      capturedImages.front!,
      capturedImages.left!,
      capturedImages.right!,
    ]

    try {
      setCurrentStep('2. Mengekstraksi embedding 512 dimensi via InceptionResnetV1 CUDA...')

      const response = await fetch('/api/onboard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: user.username,
          face_id: user.faceId,
          first_name: user.fullName.split(' ')[0],
          last_name: user.fullName.split(' ')[1] || 'Owner',
          images: imagesList,
        }),
      })

      if (!response.ok) {
        throw new Error(`Server Cloud merespons dengan kode: HTTP ${response.status}`)
      }

      const result = await response.json()
      setCurrentStep('3. Meneruskan dan memperbarui model LBPH lokal di Edge Pi 5 (10.1.1.224)...')

      setStatusMessage(
        `Pendaftaran wajah berhasil! Data embedding telah disinkronkan ke GPU Cloud dan penyimpanan luring loker fisik (${result.total_time_ms || 250} ms).`
      )

      onOnboardComplete({
        ...user,
        faceStatus: 'synced',
      })
    } catch (err: any) {
      setErrorMessage(
        `Gagal melakukan sinkronisasi: ${err.message}. Pastikan service Cloud dan jaringan lokal aktif.`
      )
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header Studio Pendaftaran Wajah */}
      <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Camera className="w-5 h-5 text-[#00E5FF]" />
            Studio Pendaftaran Biometrik Wajah
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            Pengambilan 3 sudut foto wajah untuk pengenalan AI di Cloud GPU dan penguncian luring lokal
          </p>
        </div>

        {/* Pemilih Mode Input */}
        <div className="flex bg-[#121212] p-1 rounded-xl border border-[#2C2C2E]">
          <button
            type="button"
            onClick={() => setInputMode('camera')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              inputMode === 'camera'
                ? 'bg-[#1E1E1E] text-[#00E5FF] shadow-sm'
                : 'text-text-secondary hover:text-white'
            }`}
          >
            Kamera Langsung
          </button>
          <button
            type="button"
            onClick={() => setInputMode('upload')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              inputMode === 'upload'
                ? 'bg-[#1E1E1E] text-[#00E5FF] shadow-sm'
                : 'text-text-secondary hover:text-white'
            }`}
          >
            Unggah Berkas Foto
          </button>
        </div>
      </div>

      {statusMessage && (
        <div className="bg-[#121212] border border-[#32D74B] text-[#32D74B] p-4 rounded-card text-sm flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{statusMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="bg-[#3A1C1C] text-[#FF453A] border-l-4 border-l-[#FF453A] p-4 rounded-card text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Grid: Tampilan Kamera (8 Kolom) + Panel Sampel Pose (4 Kolom) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Kolom Kiri: Layar Kamera Video */}
        <div className="lg:col-span-8 bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6 flex flex-col justify-between">
          <div className="mb-4 flex items-center justify-between">
            <span className="text-sm font-semibold text-white">
              {POSES[activePoseIdx].title}
            </span>
            <span className="text-xs text-[#00E5FF] font-mono">
              Langkah {activePoseIdx + 1} dari 3
            </span>
          </div>

          {/* Area Kamera Web */}
          <div className="relative w-full aspect-video bg-[#121212] rounded-xl overflow-hidden border border-[#2C2C2E] flex items-center justify-center">
            {inputMode === 'camera' ? (
              <>
                <video
                  ref={videoRef}
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                />
                {/* Bingkai Panduan Wajah Berwarna Sian */}
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <div className="w-52 h-64 border-2 border-[#00E5FF]/70 rounded-2xl relative">
                    <span className="absolute -top-6 left-1/2 -translate-x-1/2 text-[11px] font-semibold text-[#00E5FF] bg-[#121212]/90 px-2 py-0.5 rounded border border-[#2C2C2E]">
                      Posisikan Wajah di Sini
                    </span>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center p-8">
                <Upload className="w-12 h-12 text-text-secondary mx-auto mb-3" />
                <label className="cursor-pointer px-4 py-2 rounded-lg bg-[#00E5FF] text-[#121212] font-semibold text-xs hover:bg-[#00E5FF]/90 transition-all">
                  Pilih Berkas Foto
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            )}
          </div>

          <p className="text-xs text-text-secondary mt-3">
            {POSES[activePoseIdx].instruction}
          </p>

          <div className="mt-6 flex justify-between items-center pt-4 border-t border-[#2C2C2E]">
            <span className="text-xs text-text-secondary">
              ID Biometrik: <strong className="text-white font-mono">#{user.faceId}</strong>
            </span>

            {inputMode === 'camera' && (
              <button
                type="button"
                onClick={handleCapturePose}
                className="px-6 py-2.5 rounded-lg text-sm font-semibold bg-[#00E5FF] hover:bg-[#00E5FF]/90 text-[#121212] transition-all flex items-center gap-2 cursor-pointer"
              >
                <Camera className="w-4 h-4" />
                Ambil {POSES[activePoseIdx].title.split(':')[0]}
              </button>
            )}
          </div>
        </div>

        {/* Kolom Kanan: Daftar Pose & Tombol Sinergi */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-[#1E1E1E] border border-[#2C2C2E] rounded-card p-6">
            <h3 className="text-sm font-semibold text-white mb-4">
              Sampel Foto yang Diambil
            </h3>

            <div className="space-y-3">
              {POSES.map((pose, idx) => {
                const img = capturedImages[pose.id]
                const isActive = activePoseIdx === idx

                return (
                  <div
                    key={pose.id}
                    onClick={() => setActivePoseIdx(idx)}
                    className={`p-3 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                      isActive
                        ? 'border-[#00E5FF] bg-[#121212]'
                        : 'border-[#2C2C2E] bg-[#121212]/50 hover:bg-[#121212]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {img ? (
                        <img
                          src={img}
                          alt={pose.id}
                          className="w-12 h-12 object-cover rounded-lg border border-[#32D74B]"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-[#1E1E1E] border border-[#2C2C2E] flex items-center justify-center text-text-secondary text-xs">
                          {idx + 1}
                        </div>
                      )}
                      <div>
                        <div className="text-xs font-semibold text-white">
                          {pose.title.split(':')[0]}
                        </div>
                        <div className="text-[11px] text-text-secondary">
                          {img ? 'Sudah Diambil' : 'Belum Diambil'}
                        </div>
                      </div>
                    </div>

                    {img && <CheckCircle2 className="w-4 h-4 text-[#32D74B]" />}
                  </div>
                )
              })}
            </div>

            <div className="mt-6 pt-4 border-t border-[#2C2C2E]">
              {isProcessing && (
                <div className="text-xs text-[#00E5FF]  mb-3 font-mono">
                  {currentStep}
                </div>
              )}

              <button
                type="button"
                disabled={!allPosesReady || isProcessing}
                onClick={handleCompleteOnboarding}
                className="w-full py-3 rounded-lg text-sm font-semibold bg-[#32D74B] hover:bg-[#32D74B]/90 text-[#121212] transition-all disabled:opacity-40 flex items-center justify-center gap-2 cursor-pointer"
              >
                <Sparkles className="w-4 h-4" />
                {isProcessing ? 'Memproses...' : 'Sinkronkan Wajah ke Loker'}
              </button>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-[#121212] border border-[#2C2C2E] text-xs text-text-secondary flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-[#00E5FF] flex-shrink-0 mt-0.5" />
            <span>
              Foto wajah Anda akan diolah secara aman dan otomatis disinkronkan ke memori VRAM GPU RTX 3050 serta modul luring Raspberry Pi 5.
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
