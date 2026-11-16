#!/bin/bash
set -e

TARGET_HOST="10.1.1.224"
TARGET_PORT="2523"
TARGET_USER="pi"
JUMP_HOST="penlok@100.75.230.102"

echo "=================================================================="
echo "  PENLOK EDGE CONTAINER DEPLOYMENT RUNNER"
echo "=================================================================="

echo "[1/4] Checking SSH connection to ${TARGET_USER}@${TARGET_HOST}:${TARGET_PORT}..."
if ssh -o ConnectTimeout=3 -o BatchMode=yes -p ${TARGET_PORT} ${TARGET_USER}@${TARGET_HOST} "echo ok" 2>/dev/null; then
    echo "[+] Direct route to ${TARGET_HOST} is available."
    SSH_CMD="ssh -p ${TARGET_PORT}"
    SCP_CMD="scp -P ${TARGET_PORT}"
elif ssh -o ConnectTimeout=3 -o BatchMode=yes -J ${JUMP_HOST} -p ${TARGET_PORT} ${TARGET_USER}@${TARGET_HOST} "echo ok" 2>/dev/null; then
    echo "[+] Routing via Jump Host ${JUMP_HOST}."
    SSH_CMD="ssh -J ${JUMP_HOST} -p ${TARGET_PORT}"
    SCP_CMD="scp -J ${JUMP_HOST} -P ${TARGET_PORT}"
elif ssh -o ConnectTimeout=3 -o BatchMode=yes -J tcc@10.1.1.186 -p ${TARGET_PORT} ${TARGET_USER}@${TARGET_HOST} "echo ok" 2>/dev/null; then
    echo "[+] Routing via Jump Host tcc@10.1.1.186."
    SSH_CMD="ssh -J tcc@10.1.1.186 -p ${TARGET_PORT}"
    SCP_CMD="scp -J tcc@10.1.1.186 -P ${TARGET_PORT}"
else
    echo "[-] ERROR: Cannot reach ${TARGET_HOST}:${TARGET_PORT} directly or via Jump Host."
    exit 1
fi

echo "[2/4] Copying centralized .env, docker-compose.yml, Dockerfiles, and syncer modules..."
${SCP_CMD} \
    /home/execute/penlok/edge_package/.env \
    /home/execute/penlok/edge_package/docker-compose.yml \
    /home/execute/penlok/edge_package/Dockerfile.edge-hardware-daemon \
    /home/execute/penlok/edge_package/decision_syncer.py \
    /home/execute/penlok/edge_package/edge_mas_controller.py \
    /home/execute/penlok/edge_package/servo_config.json \
    ${TARGET_USER}@${TARGET_HOST}:/home/pi/penlock/

echo "[3/4] Building and launching Edge containers..."
${SSH_CMD} ${TARGET_USER}@${TARGET_HOST} '
cd /home/pi/penlock
docker compose build edge-hardware-daemon
docker compose up -d
sleep 3
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
'

echo "[4/4] Verifying health and sensor endpoints..."
${SSH_CMD} ${TARGET_USER}@${TARGET_HOST} '
curl -s http://localhost:8600/health
echo ""
curl -s http://localhost:8600/api/sensor
echo ""
curl -s http://localhost:8600/api/telemetry
echo ""
'

echo "=================================================================="
echo "  [SUCCESS] Edge Locker is fully deployed and synced with Cloud!"
echo "=================================================================="
