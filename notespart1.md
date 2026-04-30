# Day 3 — Docker (Parts 1–3)

Covered: install, images vs containers, networking, volumes. Resume tomorrow at Part 4 (Dockerfile iteration).

---

## Part 1: Install Docker in the VM

### Why install from Docker's official apt repo, not `apt install docker.io`
- Distro package lags upstream; bug fixes only available by upgrading.
- Feature parity (BuildKit defaults, `docker compose` v2 plugin, newer containerd).
- Different package name (`docker.io` vs `docker-ce`) → different unit names and config paths; online docs assume `docker-ce`.

### Post-install steps
- Verify: `docker --version`, `docker run hello-world`.
- Add user to docker group: `sudo usermod -aG docker $USER`
  - `-a` = append. Without it, `-G` *replaces* all supplementary groups (would lock out of `sudo`).
- Group membership only re-read on new login → fully exit and SSH back in.
- Verify: `docker ps` works without sudo.

### docker group ≈ root
- Mechanism: grants access to `/var/run/docker.sock`. The daemon runs as root and does whatever you tell it.
- Concrete escalation: `docker run -v /:/host -it alpine chroot /host sh` → root shell on host, no `sudo` audit trail.
- Hardened systems use rootless Docker or Podman.

### Docker Engine vs Docker Desktop
- **Engine** = `dockerd` + CLI + containerd + runc. Native on Linux. Apache 2.0.
- **Desktop** = packaged product (Mac/Win/Linux): bundles Engine in a hidden Linux VM + GUI + K8s + extensions. Not fully open source. **Paid license** for orgs >250 employees or >$10M revenue (2021 license change).
- Alternatives: colima, Rancher Desktop, OrbStack, Podman Desktop.

### What `docker run hello-world` actually does
1. Client → daemon (over `/var/run/docker.sock`).
2. Daemon checks **local image cache**.
3. If missing: pulls **manifest** (JSON) from registry, then each **layer** (content-addressed digest, deduped).
4. Daemon hands off to **containerd** → **runc**, which uses Linux **namespaces** (PID, net, mount, UTS, IPC, user) + **cgroups** to create the container.
5. Container is just an isolated process. stdout/stderr stream back through daemon to CLI.
- **Runtime stack: docker → containerd → runc.** K8s 1.24 dropped Docker, talks containerd directly.

---

## Part 2: Images vs Containers

### Image
- Read-only template. Physically: stack of layer tarballs + manifest + config JSON.
- Identified by content-addressed **digest** (`sha256:...`). Same content anywhere → same digest.
- Tags (`nginx:alpine`) are mutable pointers to a digest.

### Container
- Image's read-only layers + a thin **read-write layer** + namespaced/cgrouped process.
- RW layer destroyed when container is deleted → why volumes exist.

### Layer
- Each `RUN`/`COPY`/`ADD` produces one layer (filesystem diff).
- Reasons they exist:
  1. **Build caching** (unchanged inputs → reused layer).
  2. **Cross-image sharing** (10 images `FROM python:3.11-slim` share base layers on disk once).

### Registry
- Docker Hub, ECR, GCR/Artifact Registry, ACR, ghcr.io, Quay, self-hosted (Harbor, `registry`).
- **Interview Q:** tag vs digest in production? → Pin by digest (`nginx@sha256:...`); tags are mutable.

### Inspection commands
- `docker pull nginx:alpine`
- `docker images`
- `docker history nginx:alpine` — build story; small layers (KB) = metadata-only (`ENV`, `EXPOSE`, `CMD`); large = real fs changes.
- `docker inspect nginx:alpine` — current config: env, cmd, entrypoint, exposed ports, healthcheck, layer digests under `RootFS.Layers`.

### Lifecycle
```
docker run -d --name web nginx:alpine
docker ps           # running
docker ps -a        # incl. stopped
docker logs web
docker exec -it web /bin/sh
docker stop web     # SIGTERM, 10s grace, then SIGKILL
docker kill web     # SIGKILL immediately (or --signal=HUP etc.)
docker rm web
docker rmi nginx:alpine
```

### Inside the container
- `ps aux` → nginx is **PID 1** (own PID namespace).
- `cat /etc/os-release` → Alpine, even though host is Ubuntu — **userspace only differs**, kernel is shared.
- `hostname` → container short ID (own UTS namespace, override with `--hostname`).

### PID 1 gotchas (interview gold)
- PID 1 has no default signal handlers → naive apps don't handle SIGTERM → `docker stop` hangs 10s then SIGKILLs.
- PID 1 reaps zombies. Naive apps leak them.
- Fix: `docker run --init` or use `tini` as PID 1.
- **Q: "Why might you need `tini`/`--init`?"** → signal handling + zombie reaping.

### Disk usage of image layers
- Read-only layers shared across containers via **overlayfs (overlay2)** union filesystem + copy-on-write.
- 1 image × 5 containers = 1 image + 5 small RW layers.
- 5 different images = base layers deduped by digest if shared.
- **Q: "How does Docker make starting 100 containers from one image cheap?"** → shared RO layers + per-container RW layer + COW.

### Container vs VM
- Container = isolated process on host kernel (namespaces + cgroups). No kernel inside.
- VM = virtualized hardware running its own kernel.
- Can't run Windows containers on Linux (and vice versa). `uname -r` inside any container = host kernel.

### `docker stop` vs `docker kill`
- `stop` → SIGTERM, wait `--time` (default 10s), SIGKILL.
- `kill` → SIGKILL by default; `--signal=HUP` is a legit way to trigger config reload on daemons.

---

## Part 3: Networking and Volumes

### Built-in network drivers
- **bridge** (default): virtual `docker0` bridge on host; containers get veth pair, private IPs (`172.17.0.0/16`), NAT/MASQUERADE outbound.
- **host**: shares host network namespace. No `-p`, no NAT, no isolation. Doesn't behave the same on Mac/Win (Docker is in a VM there).
- **none**: own netns, only loopback. For sandboxed batch jobs.
- **overlay**: multi-host (Swarm). Out of scope.

### Docker + iptables
- Docker writes iptables rules: MASQUERADE for outbound, DNAT for `-p` published ports.
- **Q: "What does Docker do with iptables?"** ← that.

### Default bridge has no DNS
- `docker exec web1 ping web2` → "bad address" (DNS failure, not network failure).
- Pinging by IP works; only name resolution fails.
- Default bridge kept for backward compat; no embedded resolver.

### User-defined networks
```
docker network create mynet
docker run -d --name web3 --network mynet nginx:alpine
docker run -d --name web4 --network mynet nginx:alpine
docker exec web3 ping -c 2 web4   # works
```
- Embedded DNS server at **`127.0.0.11`** inside each container, knows all container names + aliases on that network.
- Better isolation between user-defined networks.
- `--network-alias`, `docker network connect` work.
- **Compose creates a user-defined network automatically** — part of why it "just works".

### Port publishing
- `-p 8080:80` → host:container, binds 0.0.0.0.
- `-p 80` → publish to a **random** high host port (find with `docker port` or `docker ps`).
- `-p 127.0.0.1:8080:80` → bind only to host loopback (good for dev DBs).
- `-P` → publish all `EXPOSE`d ports to random host ports.
- **`EXPOSE` is documentation only** — does NOT publish. Only `-p`/`-P` actually publishes. **Common interview gotcha.**

### Volumes — three types

**Named volume** (Docker manages):
```
docker volume create mydata
docker run -d --name v1 -v mydata:/data alpine sleep 3600
docker exec v1 sh -c "echo hello > /data/file.txt"
docker rm -f v1
docker run --rm -v mydata:/data alpine cat /data/file.txt   # "hello" — survived
```
- `--rm` auto-removes container on exit.
- Inspect: `docker volume inspect mydata` → `Mountpoint: /var/lib/docker/volumes/mydata/_data`.
- It's just a host directory. Backup with `tar`. **Anyone with host root can read volume contents — not encrypted/isolated.**

**Bind mount** (host path → container):
```
docker run --rm -v ~/drills/day3/sharedir:/mnt alpine cat /mnt/test.txt
```
- Inherits host permissions/SELinux/AppArmor → "permission denied" surprises.

**tmpfs** (in-memory, never disk):
```
docker run --rm --tmpfs /tmp alpine sh -c "echo hi > /tmp/x && cat /tmp/x"
```

### Named volume vs bind mount — rule of thumb
- **Named**: data the container owns (DB data dir, uploads). Portable, survives container deletion, decoupled from host paths.
- **Bind**: data the host owns (source code for live reload, config files, `/var/run/docker.sock`).

### Concurrent writes to a shared volume
- Docker adds **no** locking. POSIX semantics on the host filesystem.
- Different files: fine. Same file: can interleave/corrupt. `flock` works (same inode).
- DBs assuming exclusive access (Postgres, SQLite) **corrupt** if shared. Volumes give shared filesystem, not shared DB.

### Volume lifecycle on container removal
- `docker rm <ctr>` → named volumes survive.
- `docker rm -v <ctr>` → removes anonymous volumes (named still survive).
- `docker volume rm mydata` to delete named.
- `docker volume prune` for unused.
- Anonymous volumes (`VOLUME /data` in Dockerfile, or `-v /data` without name) accumulate → disk bloat. `docker volume ls` regularly.

---

## Tomorrow: pick up at Part 4 — Dockerfile iteration
Build path: `~/drills/day3/flaskapp/` with `app.py`, `requirements.txt`, `Dockerfile`. Five iterations:
1. Naive `python:3.11`.
2. Reorder COPY for layer caching.
3. `python:3.11-slim`.
4. Multi-stage build.
5. Non-root user, HEALTHCHECK, SHA-pinned base, `.dockerignore`.

Then Part 5 (Compose: Flask + Redis), Part 6 (Ansible — installed on Mac, not VM).

### Cleanup before stopping today
```
docker rm -f $(docker ps -aq)        # remove any leftover containers
docker volume prune -f               # optional
multipass stop devbox                # if you're done
```
