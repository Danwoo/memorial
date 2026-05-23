#!/usr/bin/env bash
# Oracle Cloud A1 (Ubuntu 22.04 ARM64) 부트스트랩
#   - Docker + Docker Compose (apt 공식 저장소)
#   - swap 2GB (RAM 6GB 미만 인스턴스 보호)
#   - iptables 80/443 인바운드 허용 + 영구화
#
# 실행: curl -sL https://raw.githubusercontent.com/Danwoo/memorial/main/deploy/oracle/bootstrap.sh | bash
set -euo pipefail

log() { printf '\n\033[1;36m[bootstrap] %s\033[0m\n' "$*"; }

# ─── 1. 기본 패키지 ──────────────────────────────────────────────
log "apt 업데이트 + 기본 패키지 설치"
sudo apt-get update -y
sudo apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  git build-essential pkg-config \
  iptables-persistent netfilter-persistent

# ─── 2. Docker 공식 저장소에서 설치 ────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  log "Docker 설치"
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER"
  log "ubuntu 사용자 docker 그룹 추가됨 — 재로그인 후 sudo 없이 docker 사용 가능"
else
  log "Docker 이미 설치됨, 건너뜀"
fi

# ─── 3. swap 2GB (24GB RAM이면 안전망, 1OCPU/6GB면 필수) ─────────────
if ! sudo swapon --show | grep -q '/swapfile'; then
  log "swap 2GB 생성"
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
else
  log "swap 이미 존재, 건너뜀"
fi

# ─── 4. iptables 인바운드 80/443 허용 ──────────────────────────────
# Oracle Ubuntu 이미지는 default-DROP iptables가 깔려 있어서 명시적으로 열어야 함.
log "iptables 80/443 허용 + 영구화"

# 이미 들어있는지 확인 후 안 들어 있으면 추가
ensure_rule() {
  local port="$1"
  if ! sudo iptables -C INPUT -p tcp --dport "$port" -m state --state NEW,ESTABLISHED -j ACCEPT 2>/dev/null; then
    sudo iptables -I INPUT 6 -p tcp --dport "$port" -m state --state NEW,ESTABLISHED -j ACCEPT
  fi
}
ensure_rule 80
ensure_rule 443

# 영구화 (재부팅 후에도 유지)
sudo netfilter-persistent save

# ─── 5. 다음 단계 안내 ─────────────────────────────────────────────
cat <<'EOF'

────────────────────────────────────────────────────────────────
부트스트랩 완료. 다음 단계:

1) docker 그룹 적용을 위해 한 번 로그아웃 후 다시 SSH 접속:
     exit
     ssh -i ~/.ssh/oracle_a1 ubuntu@<A1_IP>

2) Oracle 콘솔에서 Security List Ingress Rules에 추가 (수동):
     - 0.0.0.0/0 TCP 80
     - 0.0.0.0/0 TCP 443

3) 코드 클론 + .env 배치:
     cd /home/ubuntu
     git clone https://github.com/Danwoo/memorial.git
     cd memorial
     # 로컬에서: scp -i ~/.ssh/oracle_a1 ./memoir.env ubuntu@<A1_IP>:/home/ubuntu/memorial/.env
     # (EC2의 backend/.env 미리 받아 놓을 것)

4) 빌드 + 실행:
     docker compose up -d --build
     docker compose logs -f backend

자세한 가이드: deploy/oracle/README.md
────────────────────────────────────────────────────────────────
EOF
