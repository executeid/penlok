import assert from 'node:assert/strict'
import http from 'node:http'
import { handleApiRequest } from '../server/handlers.mjs'

// ponytail: Ephemeral in-process HTTP test verifies all 4 API gateway routes without external test runners.
const testPort = 3099
const baseUrl = `http://127.0.0.1:${testPort}`

const server = http.createServer(async (req, res) => {
  const handled = await handleApiRequest(req, res)
  if (!handled) {
    res.statusCode = 404
    res.end(JSON.stringify({ error: 'not found' }))
  }
})

await new Promise((resolve) => server.listen(testPort, '127.0.0.1', resolve))

try {
  // 1. Health check
  const resHealth = await fetch(`${baseUrl}/health`)
  assert.equal(resHealth.status, 200, 'Health endpoint should return 200')
  const jsonHealth = await resHealth.json()
  assert.equal(jsonHealth.status, 'ok')
  console.log('✓ PASS: /health probe ok')

  // 2. /api/mas-status (Edge Scheduler :8500 + Cloud GPU :9000)
  const resMas = await fetch(`${baseUrl}/api/mas-status`)
  assert.equal(resMas.status, 200, '/api/mas-status should return 200')
  const jsonMas = await resMas.json()
  assert.ok(['HEALTHY', 'DEGRADED', 'OFFLINE'].includes(jsonMas.status), 'MAS status must be valid enum')
  assert.ok(jsonMas.edgeScheduler, 'edgeScheduler block must be present')
  assert.ok(jsonMas.cloudGpu, 'cloudGpu block must be present')
  assert.ok(jsonMas.telemetry, 'telemetry block must be present')
  console.log(`✓ PASS: /api/mas-status (status: ${jsonMas.status}, scheduler: ${jsonMas.edgeScheduler.status}, gpu: ${jsonMas.cloudGpu.status})`)

  // 3. /api/sensor (GET & POST)
  const resSensorGet = await fetch(`${baseUrl}/api/sensor?mock_distance=18.5`)
  assert.equal(resSensorGet.status, 200, 'GET /api/sensor should return 200')
  const jsonSensorGet = await resSensorGet.json()
  assert.equal(jsonSensorGet.distance_cm, 18.5)
  assert.equal(jsonSensorGet.is_package_detected, true, 'distance <= 23cm should indicate package detected')
  assert.equal(jsonSensorGet.status, 'TERISI_PAKET')

  const resSensorPost = await fetch(`${baseUrl}/api/sensor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ distance_cm: 28.0 }),
  })
  assert.equal(resSensorPost.status, 200, 'POST /api/sensor should return 200')
  const jsonSensorPost = await resSensorPost.json()
  assert.equal(jsonSensorPost.sensor.distance_cm, 28.0)
  assert.equal(jsonSensorPost.sensor.is_package_detected, false, 'distance > 23cm should indicate empty/tersedia')
  assert.equal(jsonSensorPost.sensor.status, 'TERSEDIA')
  console.log('✓ PASS: /api/sensor GET & POST ok')

  // 4. /api/packages (GET & POST & DELETE)
  const resPkgsGet = await fetch(`${baseUrl}/api/packages`)
  assert.equal(resPkgsGet.status, 200, 'GET /api/packages should return 200')
  const jsonPkgsGet = await resPkgsGet.json()
  assert.ok(Array.isArray(jsonPkgsGet), 'Packages response must be an array')

  const resPkgPost = await fetch(`${baseUrl}/api/packages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      tracking_number: 'TESTRESI98765',
      courier_name: 'Test Ekspedisi',
      item_name: 'Microcontroller ESP32',
      recipient: 'tri_adi',
    }),
  })
  assert.equal(resPkgPost.status, 201, 'POST /api/packages should return 201')
  const jsonPkgPost = await resPkgPost.json()
  assert.equal(jsonPkgPost.data.last5Digits, '98765', 'Last 5 digits must match last 5 of tracking number')
  const createdId = jsonPkgPost.data.id

  const resPkgDel = await fetch(`${baseUrl}/api/packages/${createdId}`, {
    method: 'DELETE',
  })
  assert.equal(resPkgDel.status, 200, 'DELETE /api/packages/:id should return 200')
  console.log('✓ PASS: /api/packages GET, POST, DELETE ok')

  // 5. /api/onboard (Cloud GPU Agent :9000/api/v1/onboard_user)
  const resOnboardGet = await fetch(`${baseUrl}/api/onboard`)
  assert.ok([200, 503].includes(resOnboardGet.status), 'GET /api/onboard should return 200 or 503')

  const resOnboardPost = await fetch(`${baseUrl}/api/onboard`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: 'test_ci_user',
      face_id: 888777,
      images: [],
    }),
  })
  assert.ok([200, 502].includes(resOnboardPost.status), 'POST /api/onboard should return 200 or 502')
  const jsonOnboardPost = await resOnboardPost.json()
  if (resOnboardPost.status === 200) {
    assert.equal(jsonOnboardPost.status, 'success')
  }
  console.log(`✓ PASS: /api/onboard ok (status: ${resOnboardPost.status})`)

  console.log('\nALL GATEWAY INTEGRATION TESTS PASSED!')
} finally {
  server.close()
}
