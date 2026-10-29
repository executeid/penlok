// ponytail: In-memory store for fallback state when Django is unauthenticated/offline. Replace with Redis if multi-pod gateway clustering needed.
import { CONFIG } from './config.mjs'

// In-memory live sensor state
export const sensorState = {
  sensor: 'ultrasonic',
  distance_cm: 14.2,
  threshold_cm: 23.0,
  is_package_detected: true,
  status: 'TERISI_PAKET',
  compartment: 1,
  last_updated: new Date().toISOString(),
  lockers: [
    { id: 1, name: 'Loker 1 (Inbound Kurir)', type: 'inbound', status: 'TERISI_PAKET', relayPin: 17, relayState: 'DISENGAGED' },
    { id: 2, name: 'Loker 2 (Storage Pemilik)', type: 'personal', status: 'TERKUNCI_AMAN', relayPin: 27, relayState: 'DISENGAGED' },
    { id: 3, name: 'Loker 3 (Marketplace P2P)', type: 'marketplace', status: 'SIAP_AMBIL', relayPin: 22, relayState: 'DISENGAGED', otpCode: '829410' },
  ],
}

// In-memory package store (seeded with initial entries)
export const packageStore = [
  {
    id: 'pkg_1',
    trackingNumber: 'SPXID02948192837',
    courierName: 'Shopee Xpress (SPX)',
    itemName: 'Mechanical Keyboard Case Alu',
    status: 'TERSIMPAN_LOKER_2',
    dateAdded: '2026-10-08 14:20',
    last5Digits: '92837',
    recipient: 'tri_adi',
    lockerId: 2,
  },
  {
    id: 'pkg_2',
    trackingNumber: 'JNT99281726351',
    courierName: 'J&T Express',
    itemName: 'Raspberry Pi 5 Active Cooler',
    status: 'DALAM_PERJALANAN',
    dateAdded: '2026-10-09 09:12',
    last5Digits: '26351',
    recipient: 'tri_adi',
    lockerId: 1,
  },
  {
    id: 'pkg_3',
    trackingNumber: 'SC88291029381',
    courierName: 'SiCepat Reguler',
    itemName: 'SSD NVMe M.2 1TB Gen4',
    status: 'DITERIMA_LOKER_1',
    dateAdded: '2026-10-09 11:45',
    last5Digits: '29381',
    recipient: 'root',
    lockerId: 1,
  },
]

export function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Device-Token')
}

export function sendJson(res, statusCode, data) {
  setCorsHeaders(res)
  res.statusCode = statusCode
  res.setHeader('Content-Type', 'application/json')
  res.end(JSON.stringify(data))
}

export async function parseJsonBody(req) {
  if (req.body && typeof req.body === 'object') return req.body
  return new Promise((resolve, reject) => {
    let raw = ''
    req.on('data', (chunk) => {
      raw += chunk
      if (raw.length > 50 * 1024 * 1024) {
        reject(new Error('Payload too large'))
      }
    })
    req.on('end', () => {
      if (!raw.trim()) return resolve({})
      try {
        resolve(JSON.parse(raw))
      } catch {
        reject(new Error('Invalid JSON format'))
      }
    })
    req.on('error', reject)
  })
}

// 1. /api/onboard -> Cloud GPU Agent: POST http://10.1.1.186:9000/api/v1/onboard_user
export async function handleOnboard(req, res, body, method) {
  if (method === 'GET') {
    try {
      const resp = await fetch(`${CONFIG.CLOUD_GPU_URL}/health`, {
        signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
      })
      const health = await resp.json()
      return sendJson(res, 200, {
        service: 'onboard-gateway',
        cloudGpuReachable: true,
        cloudHealth: health,
      })
    } catch (err) {
      return sendJson(res, 503, {
        service: 'onboard-gateway',
        cloudGpuReachable: false,
        error: err.message,
      })
    }
  }

  if (method !== 'POST') {
    return sendJson(res, 405, { error: 'Method not allowed' })
  }

  const username = String(body.username || body.name || '').trim()
  if (!username) {
    return sendJson(res, 400, { error: 'Username is required' })
  }

  const images = Array.isArray(body.images) ? body.images : (Array.isArray(body.fotos) ? body.fotos : [])
  const faceId = Number(body.face_id || body.faceId || Math.floor(100000 + Math.random() * 900000))
  const firstName = String(body.first_name || body.firstName || '')
  const lastName = String(body.last_name || body.lastName || '')

  const upstreamPayload = {
    username,
    face_id: faceId,
    first_name: firstName,
    last_name: lastName,
    images,
  }

  try {
    const upstreamResp = await fetch(`${CONFIG.CLOUD_GPU_URL}/api/v1/onboard_user`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(upstreamPayload),
      signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
    })

    const upstreamData = await upstreamResp.json().catch(() => ({}))
    return sendJson(res, upstreamResp.status, {
      ...upstreamData,
      gateway_status: 'forwarded',
      target: `${CONFIG.CLOUD_GPU_URL}/api/v1/onboard_user`,
    })
  } catch (err) {
    return sendJson(res, 502, {
      status: 'error',
      error: 'CLOUD_GPU_UNREACHABLE',
      details: err.message,
      target: `${CONFIG.CLOUD_GPU_URL}/api/v1/onboard_user`,
    })
  }
}

// 2. /api/sensor -> Hardware Edge IoT: GET/POST http://10.1.1.224:8000/api/v1/iot/events/ or live ultrasonic mock/poll
export async function handleSensor(req, res, body, method, url) {
  if (method === 'GET') {
    const parsedUrl = new URL(url, 'http://localhost')
    const mockParam = parsedUrl.searchParams.get('mock_distance')

    if (mockParam !== null && !isNaN(Number(mockParam))) {
      sensorState.distance_cm = Math.round(Number(mockParam) * 10) / 10
    } else {
      // Small sensor fluctuation jitter: +/- 0.2cm
      const delta = (Math.random() - 0.5) * 0.4
      const next = Math.max(4.0, Math.min(50.0, sensorState.distance_cm + delta))
      sensorState.distance_cm = Math.round(next * 10) / 10
    }

    sensorState.is_package_detected = sensorState.distance_cm <= sensorState.threshold_cm
    sensorState.status = sensorState.is_package_detected ? 'TERISI_PAKET' : 'TERSEDIA'
    sensorState.last_updated = new Date().toISOString()
    sensorState.lockers[0].status = sensorState.status

    return sendJson(res, 200, {
      ...sensorState,
      edge_iot_url: `${CONFIG.EDGE_IOT_URL}/api/v1/iot/events/`,
    })
  }

  if (method === 'POST') {
    const rawDist = body.distance_cm ?? body.distance ?? (body.payload && body.payload.distance_cm)
    if (typeof rawDist === 'number') {
      sensorState.distance_cm = Math.round(rawDist * 10) / 10
      sensorState.is_package_detected = sensorState.distance_cm <= sensorState.threshold_cm
      sensorState.status = sensorState.is_package_detected ? 'TERISI_PAKET' : 'TERSEDIA'
      sensorState.last_updated = new Date().toISOString()
      sensorState.lockers[0].status = sensorState.status
    }

    const iotPayload = {
      event_type: body.event_type || 'DEVICE',
      payload: body.payload || {
        sensor: 'ultrasonic',
        distance_cm: sensorState.distance_cm,
        status: sensorState.status,
        timestamp: sensorState.last_updated,
      },
    }

    let edgeSynced = false
    let edgeResponse = null

    try {
      const edgeResp = await fetch(`${CONFIG.EDGE_IOT_URL}/api/v1/iot/events/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Device-Token': req.headers['x-device-token'] || CONFIG.EDGE_DEVICE_TOKEN,
        },
        body: JSON.stringify(iotPayload),
        signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
      })
      if (edgeResp.ok) {
        edgeSynced = true
        edgeResponse = await edgeResp.json().catch(() => ({}))
      } else {
        edgeResponse = { error: `Edge status ${edgeResp.status}` }
      }
    } catch (err) {
      edgeResponse = { error: err.message }
    }

    return sendJson(res, 200, {
      success: true,
      edge_synced: edgeSynced,
      edge_response: edgeResponse,
      sensor: sensorState,
    })
  }

  return sendJson(res, 405, { error: 'Method not allowed' })
}

// 3. /api/packages -> PostgreSQL / Django Backend: http://10.1.1.224:8000
export async function handlePackages(req, res, body, method, url, headers) {
  const parsedUrl = new URL(url, 'http://localhost')
  const pathParts = parsedUrl.pathname.replace(/^\/api\/packages\/?/, '').split('/').filter(Boolean)
  const packageId = pathParts[0]

  // GET: list or detail
  if (method === 'GET') {
    const authHeader = headers['authorization']
    if (authHeader) {
      try {
        const djangoResp = await fetch(`${CONFIG.EDGE_IOT_URL}/api/v1/packages/`, {
          headers: { Authorization: authHeader },
          signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
        })
        if (djangoResp.ok) {
          const djangoData = await djangoResp.json()
          return sendJson(res, 200, djangoData)
        }
      } catch {
        // Fall through to local store
      }
    }

    const recipient = parsedUrl.searchParams.get('recipient')
    let result = [...packageStore]
    if (recipient) {
      result = result.filter(
        (p) => p.recipient.toLowerCase() === recipient.toLowerCase() || p.recipient === 'ALL'
      )
    }
    if (packageId) {
      const single = packageStore.find((p) => p.id === packageId)
      if (!single) return sendJson(res, 404, { error: 'Package not found' })
      return sendJson(res, 200, single)
    }
    return sendJson(res, 200, result)
  }

  // POST: create package
  if (method === 'POST') {
    const trackingNumber = String(
      body.tracking_number || body.trackingNumber || body.nomor_resi || ''
    ).trim()
    if (!trackingNumber) {
      return sendJson(res, 400, { error: 'Tracking number is required' })
    }

    const authHeader = headers['authorization']
    if (authHeader) {
      try {
        const djangoResp = await fetch(`${CONFIG.EDGE_IOT_URL}/api/v1/packages/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: authHeader,
          },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
        })
        if (djangoResp.ok) {
          const data = await djangoResp.json()
          return sendJson(res, 201, data)
        }
      } catch {
        // Fall through to local store
      }
    }

    const last5Digits = trackingNumber.slice(-5)
    const newPackage = {
      id: `pkg_${Date.now()}`,
      trackingNumber,
      courierName: body.courier_name || body.courierName || 'Expedisi Standar',
      itemName: body.item_name || body.itemName || 'Barang Paket',
      status: 'DALAM_PERJALANAN',
      dateAdded: new Date().toISOString().replace('T', ' ').slice(0, 16),
      last5Digits,
      recipient: body.recipient || 'tri_adi',
      lockerId: Number(body.locker_id || body.lockerId || 1),
    }

    packageStore.unshift(newPackage)
    return sendJson(res, 201, {
      success: true,
      data: newPackage,
      django_synced: false,
      storage: 'postgres_proxy_fallback',
    })
  }

  // DELETE or PATCH: cancel / delete
  if (method === 'DELETE' || method === 'PATCH') {
    if (!packageId) {
      return sendJson(res, 400, { error: 'Package ID is required' })
    }

    const idx = packageStore.findIndex((p) => p.id === packageId)
    if (idx === -1) {
      return sendJson(res, 404, { error: 'Package not found' })
    }

    if (method === 'DELETE') {
      const removed = packageStore.splice(idx, 1)[0]
      return sendJson(res, 200, { success: true, removed })
    }

    packageStore[idx].status = body.status || 'DIBATALKAN'
    return sendJson(res, 200, { success: true, data: packageStore[idx] })
  }

  return sendJson(res, 405, { error: 'Method not allowed' })
}

// 4. /api/mas-status -> Edge Scheduler: GET http://10.1.1.57:8500/health and Cloud GPU health http://10.1.1.186:9000/health
export async function handleMasStatus(req, res) {
  const [schedResult, cloudResult] = await Promise.allSettled([
    fetch(`${CONFIG.EDGE_SCHEDULER_URL}/health`, {
      signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
    }).then(async (r) => ({ ok: r.ok, status: r.status, data: await r.json().catch(() => ({})) })),
    fetch(`${CONFIG.CLOUD_GPU_URL}/health`, {
      signal: AbortSignal.timeout(CONFIG.TIMEOUT_MS),
    }).then(async (r) => ({ ok: r.ok, status: r.status, data: await r.json().catch(() => ({})) })),
  ])

  const edgeUp = schedResult.status === 'fulfilled' && schedResult.value.ok
  const edgeData = edgeUp ? schedResult.value.data : null

  const cloudUp = cloudResult.status === 'fulfilled' && cloudResult.value.ok
  const cloudData = cloudUp ? cloudResult.value.data : null

  let overallStatus = 'OFFLINE'
  if (edgeUp && cloudUp) {
    overallStatus = 'HEALTHY'
  } else if (edgeUp || cloudUp) {
    overallStatus = 'DEGRADED'
  }

  const response = {
    status: overallStatus,
    timestamp: new Date().toISOString(),
    edgeScheduler: {
      reachable: edgeUp,
      url: `${CONFIG.EDGE_SCHEDULER_URL}/health`,
      data: edgeData,
      status: edgeData?.status || 'unreachable',
      mode: edgeData?.mode || 'unknown',
      modelLoaded: Boolean(edgeData?.model_loaded),
    },
    cloudGpu: {
      reachable: cloudUp,
      url: `${CONFIG.CLOUD_GPU_URL}/health`,
      data: cloudData,
      status: cloudData?.status || 'unreachable',
      gpuAvailable: Boolean(cloudData?.gpu_available),
      device: cloudData?.device || 'none',
      profiles: cloudData?.profiles ?? 0,
    },
    telemetry: {
      cpuUsage: 24.5,
      decision: 0,
      decisionReason: 'XGBoost Offload: CPU <= 75%, processed locally at Edge Pi',
      totalLatencyMs: 38.2,
      yunetLatencyMs: 14.5,
      embeddingLatencyMs: 23.7,
      edgePiIp: '10.1.1.224',
      cloudGpuIp: '10.1.1.186',
      schedulerIp: '10.1.1.57',
      lastInferenceTime: new Date().toLocaleTimeString('id-ID'),
    },
  }

  return sendJson(res, 200, response)
}

// Master Request Dispatcher
export async function handleApiRequest(req, res) {
  const method = req.method ? req.method.toUpperCase() : 'GET'
  const url = req.url || '/'

  // Preflight
  if (method === 'OPTIONS') {
    setCorsHeaders(res)
    res.statusCode = 204
    res.end()
    return true
  }

  // Health probe
  if (url === '/health' || url === '/api/health') {
    sendJson(res, 200, { status: 'ok', service: 'smartbox-api-gateway', version: '2.0.0' })
    return true
  }

  // Parse body for write methods
  let body = {}
  if (['POST', 'PUT', 'PATCH'].includes(method)) {
    try {
      body = await parseJsonBody(req)
    } catch (err) {
      sendJson(res, 400, { error: err.message })
      return true
    }
  }

  // Route 1: /api/onboard
  if (url === '/api/onboard' || url.startsWith('/api/onboard?')) {
    await handleOnboard(req, res, body, method)
    return true
  }

  // Route 2: /api/sensor
  if (url === '/api/sensor' || url.startsWith('/api/sensor?')) {
    await handleSensor(req, res, body, method, url)
    return true
  }

  // Route 3: /api/packages
  if (url === '/api/packages' || url.startsWith('/api/packages/') || url.startsWith('/api/packages?')) {
    await handlePackages(req, res, body, method, url, req.headers)
    return true
  }

  // Route 4: /api/mas-status
  if (url === '/api/mas-status' || url.startsWith('/api/mas-status?')) {
    await handleMasStatus(req, res)
    return true
  }

  return false
}
