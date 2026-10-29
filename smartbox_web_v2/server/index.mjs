import http from 'node:http'
import { CONFIG } from './config.mjs'
import { handleApiRequest, sendJson } from './handlers.mjs'

const server = http.createServer(async (req, res) => {
  try {
    const handled = await handleApiRequest(req, res)
    if (!handled) {
      sendJson(res, 404, { error: 'Route not found', path: req.url })
    }
  } catch (err) {
    sendJson(res, 500, { error: 'Internal gateway error', message: err.message })
  }
})

server.listen(CONFIG.PORT, CONFIG.HOST, () => {
  console.log(`[PENLOK_GATEWAY] Listening on http://${CONFIG.HOST}:${CONFIG.PORT}`)
  console.log(`  -> Cloud GPU Agent:   ${CONFIG.CLOUD_GPU_URL}/api/v1/onboard_user`)
  console.log(`  -> Hardware Edge IoT: ${CONFIG.EDGE_IOT_URL}/api/v1/iot/events/`)
  console.log(`  -> PostgreSQL/Django: ${CONFIG.EDGE_IOT_URL}/api/v1/packages/`)
  console.log(`  -> Edge Scheduler:    ${CONFIG.EDGE_SCHEDULER_URL}/health`)
})

process.on('SIGINT', () => {
  server.close(() => process.exit(0))
})
process.on('SIGTERM', () => {
  server.close(() => process.exit(0))
})
