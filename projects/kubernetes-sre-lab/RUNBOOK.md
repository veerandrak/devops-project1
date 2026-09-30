# Reliability runbook

## Local availability incident

1. Start Compose and confirm `up{job="platform-demo"} == 1` in Prometheus.
2. Run `docker compose stop app`. After a scrape and the one-minute alert duration, inspect **Alerts → DemoServiceDown**.
3. Inspect `docker compose ps` and `docker compose logs --tail=50 app`; distinguish process failure from bad scrape address.
4. Recover with `docker compose start app`. Confirm `/readyz`, `up == 1`, and alert resolution.
5. Record detection and recovery timestamps. Do not invent measured recovery times.

There is no Alertmanager receiver configured. The alert appears in Prometheus; it sends no email or pager message.

## Kubernetes failed rollout

Use only your disposable lab cluster:

```bash
kubectl -n platform-demo set image deployment/platform-demo app=platform-demo:does-not-exist
kubectl -n platform-demo rollout status deployment/platform-demo --timeout=30s
kubectl -n platform-demo get pods
kubectl -n platform-demo describe deployment platform-demo
kubectl -n platform-demo get events --sort-by=.lastTimestamp
kubectl -n platform-demo rollout undo deployment/platform-demo
kubectl -n platform-demo rollout status deployment/platform-demo --timeout=120s
```

The intentional failed rollout command is expected to time out. Existing healthy replicas should remain because `maxUnavailable` is zero; verify rather than assume. Check node capacity if replacement pods remain Pending.

## Boundaries and cleanup

The NetworkPolicy permits inbound traffic only from pods in the same namespace and blocks application egress. Probes/port-forward use kubelet/control-plane paths whose behavior depends on the CNI; verify policy with actual pod-to-pod traffic on a policy-capable cluster. No secrets belong in manifests or Git.

```bash
docker compose down
kind delete cluster --name portfolio
```

Do not run the cluster deletion command against a shared cluster. For a shared lab cluster, delete only the explicitly created `platform-demo` namespace after checking ownership.
