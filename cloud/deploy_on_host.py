"""Run on pengmas-tri after image import; never prints credential values."""
import json
import subprocess
from pathlib import Path


def run(args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def main():
    base = Path(__file__).resolve().parent.parent
    inspected = json.loads(subprocess.check_output(
        ["docker", "inspect", "cloud-face-agent"], text=True))[0]
    env = dict(item.split("=", 1) for item in inspected["Config"]["Env"] if "=" in item)
    required = ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME")
    if not all(env.get(key) for key in required):
        raise RuntimeError("Existing cloud container is missing database configuration")
    secret = {"apiVersion": "v1", "kind": "Secret",
              "metadata": {"name": "cloud-agent-db", "namespace": "cloud-agent"},
              "type": "Opaque", "stringData": {key: env[key] for key in required}}
    # create/apply from stdin; do not persist the JSON or secret in git/evidence.
    run(["sudo", "-n", "kubectl", "apply", "-f", "-"], input=json.dumps(secret),
        stdout=subprocess.DEVNULL)
    manifest = str(base / "cloud/k8s/cloud-api.yaml")
    run(["sudo", "-n", "kubectl", "apply", "--dry-run=server", "-f", manifest])
    run(["sudo", "-n", "kubectl", "apply", "-f", manifest])
    print("Deployment submitted. Verify rollout and /ready before using it.")


if __name__ == "__main__":
    main()
