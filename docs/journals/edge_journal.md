# Edge Node (penlok@10.1.1.57) — Discovery & Architecture Journal

**Date**: 25 September 2026  
**Target Host**: `penlok@10.1.1.57` (`edge-penlok`)  
**Tailscale IP**: `100.75.230.102`  
**Role in System**: Edge Orchestrator, K3s Cluster Host, Telemetry Aggregator, ML Task Offloading Engine

---

## 1. Host Infrastructure & System Specifications

| Component | Specification |
|---|---|
| **Hardware** | Raspberry Pi 5 Model B Rev 1.0 (BCM2712 aarch64, 4-core Cortex-A76 @ 2.4GHz) |
| **Operating System** | Debian GNU/Linux 13 (trixie) |
| **Kernel** | `Linux edge-penlok 6.18.39+rpt-rpi-2712 #1 SMP PREEMPT Debian 1:6.18.39-1+rpt1 arm64` |
| **Memory** | 16 GB Total (Used: ~2.9 GB, Available: ~13.3 GB, Swap: 2.0 GB) |
| **Storage** | 58 GB SD Card (`/dev/mmcblk0p2`), 29 GB used (53%), 27 GB free |
| **Networking** | Internal IP: `10.1.1.57`, Tailscale VPN: `100.75.230.102`, Default Gateway: `10.1.1.1` |
| **System Python** | Python 3.13.5 (`/usr/bin/python3`) |
| **Core Python Libraries** | `xgboost` 3.4.0, `scikit-learn` 1.9.0, `pandas` 2.2.3, `numpy` 2.2.4, `psutil` 7.0.0, `joblib` 1.5.3 |
| **Virtual Environments** | `/home/penlok/venv-test` (Python 3.13, FastAPI 0.141.1, Uvicorn 0.52.3) |
| **System Uptime** | 3 days, 8 hours |

---

## 2. Multi-Pi Architecture Topology

This node (`10.1.1.57`) serves as the **Brain & Edge Orchestrator** in a dual-Raspberry Pi architecture:

```
+-----------------------------------------------------------------------------------------+
|                                    SMART LOCKER SYSTEM                                   |
|                                                                                         |
|  +-------------------------------------+       +-------------------------------------+  |
|  |     RASPI 1 (10.1.1.224:2523)       |       |     RASPI 2 / EDGE (10.1.1.57)      |  |
|  |           "Device Edge"             |       |          "Cluster / Brain"          |  |
|  |-------------------------------------|       |-------------------------------------|  |
|  | • Hardware Control (Relays/Lockers) |       | • K3s Single-Node Kubernetes        |  |
|  | • Arduino Serial Matrix Keypad      |       | • Mosquitto MQTT Broker (:1883)     |  |
|  | • OpenCV Face Recognition           |       | • Prometheus & Grafana Monitoring   |  |
|  | • Django Backend & PostgreSQL       |       | • Edge-Agent Telemetry Collector    |  |
|  | • Node-Exporter (:31100)            | ----> | • Scrapes metrics from Raspi 1      |  |
|  |                                     |       | • XGBoost Offload Engine (AI)       |  |
|  +-------------------------------------+       +-------------------------------------+  |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Home Directory Analysis (`/home/penlok`)

### Directory Tree & Key Files

```text
/home/penlok/
├── edge-agent/                   # Source code & deployment manifests for Edge Agent microservice
│   ├── app/                      # Application core (monitor, mqtt, main telemetry loop)
│   ├── config/                   # Config definitions
│   ├── data/                     # Local data directory (telemetry.csv)
│   ├── docker/                   # Dockerfile, docker-compose, jmeter configs
│   ├── k8s/                      # Kubernetes manifests (edge-agent, mqtt-broker, monitoring)
│   ├── scripts/                  # Helper scripts (dummy_api.py)
│   ├── tests/                    # Unit tests (test_monitor.py, test_logger.py)
│   └── edge-agent.tar            # 531 MB exported Docker image imported to K3s containerd
├── edge-agent.zip                # 11.7 MB source archive
├── dataset_smartbox.csv          # Raw telemetry dataset collected from edge-agent container (1,234 rows)
├── dataset_smartbox_raspi1.csv   # Raw telemetry dataset scraped from Raspi 1 (1,973 rows)
├── dataset_smartbox_clean.csv    # Cleaned telemetry dataset with standard CSV headers (261 rows)
├── dataset_seimbang_final.csv    # Balanced training dataset for edge vs cloud scheduling (359 rows)
├── scheduler_agent_xgb.pkl       # 1.6 MB serialized XGBoost model for live offloading decisions
├── model_orchestration.pkl       # 377 KB serialized model for orchestration scheduling
├── scheduler_agent_xgboost.ipynb # Jupyter notebook for model training, cross-validation, and metrics
├── live_test.py                  # Live inference script querying system metrics & running XGBoost model
├── stress_simulation.py          # Interactive stress-ng workload injection script (Light/Med/High/Auto)
├── dummy_api.py                  # FastAPI mock endpoint (/api/buka-loker) simulating heavy CPU (Face Recog)
└── venv-test/                    # Python virtual environment for FastAPI / Uvicorn testing
```

### Purpose of Individual Artifacts

#### A. Telemetry Collection & Datasets
- **`edge-agent/app/main.py`**:
  - Periodically reads system metrics (`cpu_usage`, `ram_usage`, `disk_io`, `network_bandwidth`).
  - Publishes JSON telemetry payloads to MQTT topic `smartbox/telemetry` every 3 seconds.
  - Generates rule-based training labels (`Target: 0 = Process on Edge, 1 = Cloud Offloading`) based on thresholds:
    $$\text{Target} = 1 \iff \text{CPU} > 65\% \lor \text{Execution Time} > 3.5\text{s} \lor (\text{CPU} > 45\% \land \text{Priority} = 3)$$
  - Appends records directly to `/edge-agent/data/dataset_smartbox.csv` inside the container.
- **CSV Datasets**:
  - `dataset_smartbox.csv`: Real-time telemetry dumped by the active K3s container.
  - `dataset_smartbox_raspi1.csv`: Telemetry captured from Raspi 1 to model multi-node load.
  - `dataset_smartbox_clean.csv` & `dataset_seimbang_final.csv`: Processed datasets with balanced classes for training the offloading classifier.

#### B. Machine Learning & Scheduling Agent
- **`scheduler_agent_xgb.pkl`**:
  - Trained XGBoost binary classifier.
  - Features: `['CPU', 'RAM', 'Throughput', 'Network_Bandwidth', 'Priority', 'Latency', 'Queue']`.
  - Predictions: `0 = MIGRASI KE CLOUD`, `1 = TETAP DI EDGE`.
- **`live_test.py`**:
  - Standalone edge inference loop running on the host.
  - Samples CPU (`psutil.cpu_percent`), RAM (`psutil.virtual_memory`), disk I/O delta, network delta, ping latency to `8.8.8.8`, and queue length.
  - Feeds telemetry into `scheduler_agent_xgb.pkl` every 5 seconds to output live decisions and confidence scores.

#### C. Stress Testing & Workload Simulation
- **`stress_simulation.py`**:
  - Wrapper around `stress-ng` with four predefined scenarios:
    1. Light: 2 cores, 30% load, 100 MB RAM, 8 seconds.
    2. Medium: 3 cores, 60% load, 200 MB RAM, 10 seconds.
    3. High: 4 cores, 95% load, 350 MB RAM, 15 seconds.
    4. Auto Cycle: Idle $\rightarrow$ Medium $\rightarrow$ Critical/Max $\rightarrow$ Recovery.
  - Used to drive CPU and memory metrics over threshold to generate realistic offloading events.
- **`dummy_api.py` & JMeter**:
  - Endpoint `/api/buka-loker` performs 5,000,000 square root calculations per request to mimic face recognition computation on an edge device.
  - Tested with Apache JMeter plan `tesjmeter.jmx` recorded in `jmeter.log`.

---

## 4. Kubernetes (K3s) Cluster Environment

### K3s Overview
- **K3s Version**: `v1.36.2+k3s1`
- **Node**: `edge-penlok` (`Ready`, `control-plane`, IP: `10.1.1.57`)
- **Container Runtime**: Containerd `2.3.2-k3s2`
- **Cluster Network**: Flannel CNI (`10.42.0.0/16`), Traefik Ingress (`10.1.1.57:80, :443`)

### Active Pods & Workloads

#### 1. Namespace `default` (Application Workloads)
| Pod Name | Status | Restarts | Description |
|---|---|---|---|
| `edge-agent-79cf96b45c-9xdlw` | Running | 0 | Active edge telemetry logger (`app.main`), mounts PVC `edge-agent-data-pvc` (1Gi) |
| `mqtt-broker-6544d5bfc4-j8lw2` | Running | 3 | Eclipse Mosquitto broker listening on TCP :1883 |
| `prometheus-7f5888b4c-rldfn` | Running | 0 | Standalone Prometheus instance scraping local + Raspi 1 metrics |
| `grafana-86dbbdf645-wws5m` | Running | 3 | Grafana dashboard, exposed via NodePort `:30000` |
| `node-exporter-67wkf` | Running | 3 | Local hardware metrics exporter on port `:9100` |
| `nginx-7f8fbb96d-xcpz2` | Running | 7 | Nginx web server mapped to ingress host `nginx.local` |

#### 2. Namespace `monitoring` (Kube-Prometheus Stack)
| Pod Name | Status | Restarts | Description |
|---|---|---|---|
| `prometheus-operator-7df4f6d7f8-hrgxn` | Running | 6 | Prometheus Operator v0.92.1 managing CRDs |
| `prometheus-prometheus-kube-prometheus-0` | Running | 12 | Main cluster Prometheus v3.13.1 |
| `alertmanager-prometheus-...-0` | Running | 12 | Prometheus Alertmanager v0.33.1 |
| `prometheus-grafana-d5b68ddf5-6hjpr` | Running | 18 | Stack Grafana instance, exposed via NodePort `:30369` |
| `prometheus-kube-state-metrics-...` | Running | 46 | Kube state metrics exporter v2.19.1 |
| `prometheus-node-exporter-v2jbt` | Running | 69 | Host-level node exporter |

#### 3. Namespace `kube-system`
- `coredns-5f5694d56b-wq4gs`: CoreDNS internal resolution.
- `local-path-provisioner-58d557dc48-r6bwc`: Manages hostpath PVCs (backing `edge-agent-data-pvc`).
- `metrics-server-7c86f97b8d-9qmz6`: Cluster resource metrics (`kubectl top`).
- `traefik-6cd8c7cd89-96rkp` + `svclb-traefik-...`: Traefik loadbalancer binding to host ports 80/443.

### Prometheus Multi-Node Scraping Configuration
In `default/prometheus-config`, Prometheus is configured to scrape:
1. `localhost:9090` (Self metrics)
2. `node-exporter:9100` (Local Edge RPi 5 metrics)
3. `10.1.1.224:31100` (Raspi 1 hardware controller node-exporter)

**Status**: Verified via Prometheus API (`/api/v1/targets`), all three endpoints are `UP` and actively collecting.

---

## 5. Active Processes & Network Sockets

### Network Ports (Host Level)
- **Port 22/TCP**: OpenSSH (`sshd`)
- **Port 80/TCP & 443/TCP**: Traefik Ingress LoadBalancer (Klipper LB)
- **Port 6443/TCP**: K3s Kubernetes API Server
- **Port 9100/TCP**: Prometheus Node Exporter
- **Port 30000/TCP**: K3s NodePort for Grafana (`default`)
- **Port 30369/TCP**: K3s NodePort for Prometheus Grafana (`monitoring`)
- **Port 41641/UDP & 35478/TCP**: Tailscale VPN daemon

### Suspended Process Alert
In process table:
- `PID 177693 / 177695`: `sudo kubectl edit configmap prometheus-config`
- `PID 177710`: `vi /tmp/kubectl-edit-1136579769.yaml`  
**Note**: A suspended vi session from a previous terminal session remains stopped in background on `pts/2`. Can be safely cleaned or resumed if necessary.

---

## 6. Recent User Operations Summary (Bash History Audit)

1. **Dataset Generation & Rotation**:
   - Monitored data inside `deploy/edge-agent` via `kubectl exec`.
   - Copied data out using `kubectl cp deploy/edge-agent:/edge-agent/data/dataset_smartbox.csv`.
   - Cleared and restarted edge-agent deployment (`kubectl rollout restart deployment/edge-agent`) to obtain fresh benchmarks.
2. **Stress Testing**:
   - Installed `stress` utility via apt.
   - Ran `stress --cpu 2 --vm 1 --vm-bytes 256M --timeout 600s` to induce heavy load and trigger Cloud Offloading labels in dataset.
3. **Container Image Lifecycle**:
   - Built new container locally: `sudo docker build -t edge-agent:latest -f docker/Dockerfile .`.
   - Exported image: `sudo docker save edge-agent:latest > edge-agent.tar`.
   - Imported into K3s runtime: `sudo k3s ctr images import edge-agent.tar`.
4. **Monitoring Reconfiguration**:
   - Edited Prometheus configmap to add scrape targets for Raspi 1 (`10.1.1.224:31100`).
