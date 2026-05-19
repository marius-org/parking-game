# Park Like a Pro 🚗

> **Top-down parking simulator — Timișoara edition**

A browser-based top-down parking game with Ackermann steering physics, 15 levels, and a Timișoara-themed environment with animated RATT trams.

🎮 **Live:** [parking.slax.ro](https://parking.slax.ro)

---

## What It Does

The player maneuvers a car into a designated parking spot across 15 progressively harder levels. The game features realistic Ackermann steering physics, obstacles, and a scoring system based on time and precision. Scores are saved to a leaderboard backed by PostgreSQL.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Game frontend | HTML5 Canvas + Vanilla JavaScript |
| Backend API | Python / FastAPI + asyncpg |
| Leaderboard DB | PostgreSQL 16 (StatefulSet) |
| Storage | NFS PVC (2Gi) |
| Containerization | Docker |
| Container registry | Docker Hub (`mariuseu/parking-game`) |
| CI/CD | GitHub Actions (self-hosted runner on `control-node`) |
| GitOps | ArgoCD |
| Orchestration | Kubernetes (k3s HA cluster) |
| Ingress | ingress-nginx + Cloudflare Tunnel |
| Domain | [parking.slax.ro](https://parking.slax.ro) |

---

## Project Structure

```
parking-game/
├── .github/
│   └── workflows/
│       └── deploy.yml       # CI/CD pipeline
├── backend/
│   ├── main.py              # FastAPI backend (score API)
│   └── requirements.txt     # Python dependencies
├── frontend/
│   └── index.html           # Game (HTML5 Canvas)
├── k3s/
│   ├── deployment.yaml      # Kubernetes Deployment + Service
│   ├── ingress.yaml         # Ingress rule for parking.slax.ro
│   └── postgres.yaml        # PostgreSQL StatefulSet + PVC
└── Dockerfile
```

---

## CI/CD Pipeline

Every push to `main` triggers the GitHub Actions workflow:

1. **Build** Docker image
2. **Push** to Docker Hub with tag `mariuseu/parking-game:<run_number>` and `:latest`
3. **Update** `k3s/deployment.yaml` with the new image tag
4. **Commit & push** the manifest change back to the repo
5. **ArgoCD** detects the change and auto-syncs the deployment to the k3s cluster

```
git push → GitHub Actions → Docker Hub → manifest update → ArgoCD → k3s cluster
```

---

## Running Locally

### Prerequisites

- Docker

### Steps

```bash
git clone https://github.com/marius-org/parking-game.git
cd parking-game
docker build -t parking-game .
docker run -p 8000:8000 parking-game
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Kubernetes Deployment (k3s)

The app runs in its own namespace on a 3-master / 2-worker k3s HA cluster.

### First-time setup — create the secret manually (never commit credentials)

```bash
kubectl create secret generic parking-secret \
  -n parking-game \
  --from-literal=POSTGRES_DB=parkingdb \
  --from-literal=POSTGRES_USER=parking \
  --from-literal=POSTGRES_PASSWORD=parkingpass \
  --from-literal=DATABASE_URL="postgresql://parking:parkingpass@postgres-service:5432/parkingdb"
```

### Apply manifests (normally handled by ArgoCD)

```bash
kubectl apply -f k3s/postgres.yaml
kubectl apply -f k3s/deployment.yaml
kubectl apply -f k3s/ingress.yaml
```

Traffic flow:

```
Internet → Cloudflare Tunnel → ingress-nginx (MetalLB) → parking-game-service (ClusterIP) → pods
```

---

## Useful Commands

```bash
# Check pods
kubectl get pods -n parking-game

# Check service
kubectl get svc -n parking-game

# View logs
kubectl logs -l app=parking-game -n parking-game -f

# Query leaderboard
kubectl exec -it postgres-0 -n parking-game -- \
  psql -U parking -d parkingdb -c "SELECT * FROM scores ORDER BY score DESC;"

# Insert test score
kubectl exec -it postgres-0 -n parking-game -- \
  psql -U parking -d parkingdb -c \
  "INSERT INTO scores (player_name, score) VALUES ('Marius', 9999);"
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `DATABASE_URL` | Full asyncpg connection string |

---

## GitHub Secrets Required

| Secret | Description |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token |