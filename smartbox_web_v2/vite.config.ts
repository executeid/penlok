import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { handleApiRequest } from './server/handlers.mjs'

// ponytail: Integrated Vite middleware routes /api directly in dev. In K3s production, Node server/index.mjs runs as container entrypoint.
function apiGatewayPlugin(): Plugin {
  return {
    name: 'smartbox-api-gateway',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.url && (req.url === '/api' || req.url.startsWith('/api/') || req.url === '/health')) {
          const handled = await handleApiRequest(req, res)
          if (handled) return
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), apiGatewayPlugin()],
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
})
