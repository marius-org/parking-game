# Park Like a Pro 🚗

Top-down parking simulator deployed on k3s homelab.

## Stack
- **Frontend:** Vanilla HTML5 Canvas
- **Backend:** FastAPI + asyncpg
- **Database:** PostgreSQL 16 (StatefulSet)
- **Storage:** NFS PVC (2Gi)
- **CI/CD:** GitHub Actions → Docker Hub → k3s

## Local dev
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Deploy to k3s

**1. Create namespace + database (first time only):**
```bash
# Create secret manually — do NOT commit credentials
kubectl create secret generic parking-secret \
  -n parking-game \
  --from-literal=POSTGRES_DB=parkingdb \
  --from-literal=POSTGRES_USER=parking \
  --from-literal=POSTGRES_PASSWORD=parkingpass \
  --from-literal=DATABASE_URL="postgresql://parking:parkingpass@postgres-service:5432/parkingdb"

# Apply namespace + postgres (remove Secret block from file first)
kubectl apply -f k3s/postgres.yaml
```

**2. Deploy app:**
```bash
kubectl apply -f k3s/deployment.yaml
```

**3. Add HAProxy backend (on 192.168.1.99 — edit `/etc/haproxy/haproxy.cfg`):**
```
# Parking Game - port 8092
frontend parking_front
    bind *:8092
    default_backend parking_back

backend parking_back
    balance roundrobin
    option httpchk GET /health
    server worker01 192.168.1.54:32529 check inter 30s rise 2 fall 3
    server worker02 192.168.1.55:32529 check inter 30s rise 2 fall 3
```

Then reload HAProxy:
```bash
ssh ubuntu@192.168.1.99 "sudo systemctl reload haproxy"
```

**4. Add Cloudflare Tunnel route:**
```
parking.slax.ro → http://192.168.1.99:8092
```

## Useful commands
```bash
# Check pods
kubectl get pods -n parking-game

# Check service
kubectl get svc -n parking-game

# View logs
kubectl logs -l app=parking-game -n parking-game -f

# Query scores
kubectl exec -it postgres-0 -n parking-game -- \
  psql -U parking -d parkingdb -c "SELECT * FROM scores ORDER BY score DESC;"

# Insert test score
kubectl exec -it postgres-0 -n parking-game -- \
  psql -U parking -d parkingdb -c \
  "INSERT INTO scores (player_name, score) VALUES ('Marius', 9999);"
```

## NodePort
`32529` — add to HAProxy config pointing to this port on workers.
