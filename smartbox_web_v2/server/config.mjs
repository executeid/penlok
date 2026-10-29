// ponytail: Gateway config uses environment variables with fallback defaults. Add Consul/Vault when external secrets management is adopted.
export const CONFIG = {
  PORT: Number(process.env.PORT) || 3001,
  HOST: process.env.HOST || '0.0.0.0',
  CLOUD_GPU_URL: process.env.CLOUD_GPU_URL || 'http://10.1.1.186:9000',
  EDGE_IOT_URL: process.env.EDGE_IOT_URL || 'http://10.1.1.224:8000',
  EDGE_DEVICE_TOKEN: process.env.EDGE_DEVICE_TOKEN || 'IoT@event2025',
  EDGE_SCHEDULER_URL: process.env.EDGE_SCHEDULER_URL || 'http://10.1.1.57:8500',
  TIMEOUT_MS: Number(process.env.UPSTREAM_TIMEOUT_MS) || 6000,
}
