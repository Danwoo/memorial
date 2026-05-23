# Oracle Cloud A1 마이그레이션 가이드

**대상**: AWS EC2 t2.micro (15.165.17.222) → Oracle Cloud A1 Flex (영구 무료)
**소요**: 인스턴스 잡으면 30~60분, capacity 잡기까지가 가장 오래 걸림
**비용**: $0 / 월 (Always Free Tier, A1 4 OCPU / 24GB RAM)

이 가이드는 메모이르 백엔드(FastAPI + KuzuDB Docker compose)를 그대로 이관합니다.
프론트엔드 Vercel은 건드릴 필요 없음 (도메인 `memoir-api.duckdns.org` 유지).

---

## 단계 요약

| # | 단계 | 자동화 | 소요 |
|---|---|---|---|
| 0 | Oracle 계정 + SSH 키 | 수동 | 5분~3일 (승인) |
| 1 | A1 인스턴스 capacity 잡기 | `grab-capacity.sh` 또는 콘솔 재시도 | 5분~며칠 |
| 2 | 서버 부트스트랩 (Docker, swap, 방화벽) | `bootstrap.sh` | 5분 |
| 3 | 시크릿 + 데이터 이관 | scp 명령 (아래) | 5분 |
| 4 | 도커 빌드/실행 | `docker compose up -d` | 10분 (첫 빌드) |
| 5 | DuckDNS IP 갱신 | curl 한 줄 | 1분 |
| 6 | HTTPS (certbot) | `tls.sh` | 5분 |
| 7 | 검증 + EC2 종료 | curl + AWS 콘솔 | 5분 |

---

## Phase 0 — 사전 준비

### 0.1 Oracle Cloud 계정

1. https://cloud.oracle.com/free 가입
2. **카드 인증** 통과 (VISA/Mastercard 데빗 가능, 1달러 임시 결제 후 환불)
3. **신분 확인** 통과 (영문 여권 사진 권장 — 한글 운전면허는 자주 거절)
4. **Home Region 선택**: **Seoul (ap-seoul-1)** 추천. 한국 latency 최소.
   - 가입 시 한 번만 정해짐, 나중에 변경 불가.

### 0.2 SSH 키

```bash
# 로컬(Windows PowerShell or WSL)에서:
ssh-keygen -t ed25519 -f ~/.ssh/oracle_a1 -C "memoir-oracle"
cat ~/.ssh/oracle_a1.pub   # 콘솔 인스턴스 생성 시 붙여넣기
```

---

## Phase 1 — A1 인스턴스 잡기

A1 Flex는 무료지만 capacity 부족이 흔함. **"Out of host capacity"** 떠도 정상.

### 1A — 콘솔 수동 시도 (운 좋으면 1회 성공)

OCI 콘솔 → **Compute → Instances → Create Instance**

| 필드 | 값 |
|---|---|
| Image | **Canonical Ubuntu 22.04** (ARM64) |
| Shape | **VM.Standard.A1.Flex** — 일단 **1 OCPU / 6GB**로 시작 (capacity 잡힐 확률↑) |
| Networking | 새 VCN 자동 생성 + Public IP |
| SSH key | `~/.ssh/oracle_a1.pub` 내용 붙여넣기 |
| Boot volume | 기본 47GB (무료 한도 200GB까지 늘려도 됨) |

**Tip**:
- 한국 시간 새벽 2~5시가 capacity 잘 잡히는 황금시간
- 서울 안 되면: Tokyo (ap-tokyo-1) → Singapore (ap-singapore-1) → Osaka (ap-osaka-1) 순으로 시도
- 다른 리전 시도하려면 Home region 사용 외 region을 sub로 enable해야 함 (콘솔 우상단 region switcher)

### 1B — 자동 재시도 스크립트 (capacity 자주 놓치면)

`grab-capacity.sh` 참고. OCI CLI + cron으로 5분마다 재시도.

설정 복잡(API 키 + tenancy OCID) — capacity가 1주일 넘게 안 잡힐 때만 권장.

---

## Phase 2 — 서버 부트스트랩

인스턴스 생성됐다면 콘솔에서 **Public IP** 복사. SSH 접속:

```bash
ssh -i ~/.ssh/oracle_a1 ubuntu@<A1_IP>
```

부트스트랩 스크립트 실행 (Docker, swap, 방화벽 한 번에):

```bash
curl -sL https://raw.githubusercontent.com/Danwoo/memorial/main/deploy/oracle/bootstrap.sh | bash
# 또는 git clone 후
# bash deploy/oracle/bootstrap.sh
```

### 부트스트랩 후 Oracle 콘솔에서 할 일

Oracle은 **2층 방화벽** — iptables + Security List 둘 다 통과해야 함.
`bootstrap.sh`가 iptables는 처리. Security List는 수동:

1. 콘솔 → **Networking → Virtual Cloud Networks → 인스턴스 VCN → Security Lists → Default**
2. **Ingress Rules**에 추가:
   - Source `0.0.0.0/0`, TCP, Destination Port `80` (HTTP)
   - Source `0.0.0.0/0`, TCP, Destination Port `443` (HTTPS)
3. (8000은 nginx 뒤에 숨길 거니까 안 열어도 됨)

---

## Phase 3 — 시크릿 + 데이터 이관

### 3.1 .env 가져오기 (EC2 → 로컬 → A1)

```bash
# 로컬에서:
scp -i ~/.ssh/aws-key.pem ubuntu@15.165.17.222:/home/ubuntu/memorial/backend/.env ./memoir.env

# 내용 한번 훑어서 SUPABASE_URL / OPENROUTER_API_KEY 등 확인:
cat memoir.env

# A1으로 전송:
scp -i ~/.ssh/oracle_a1 ./memoir.env ubuntu@<A1_IP>:/tmp/.env

# A1에서:
ssh -i ~/.ssh/oracle_a1 ubuntu@<A1_IP>
cd /home/ubuntu
git clone https://github.com/Danwoo/memorial.git
cd memorial
mv /tmp/.env ./.env          # 루트 .env (compose가 읽음)
ln -sf ../.env backend/.env  # backend 작업 시 편의용 심볼릭
```

⚠️ EC2가 이미 꺼졌으면 AWS 콘솔에서 인스턴스 다시 Start 후 scp.

### 3.2 KuzuDB 그래프 데이터

두 가지 선택지:

**선택 A — 데이터 그대로 복사** (5분, 정확)
```bash
# EC2에서:
cd /home/ubuntu/memorial
docker compose down
tar czf /tmp/kuzu_data.tar.gz kuzu_data/
ls -lh /tmp/kuzu_data.tar.gz  # 크기 확인 (보통 수십MB)

# 로컬로:
scp -i ~/.ssh/aws-key.pem ubuntu@15.165.17.222:/tmp/kuzu_data.tar.gz ./

# A1으로:
scp -i ~/.ssh/oracle_a1 ./kuzu_data.tar.gz ubuntu@<A1_IP>:/tmp/
ssh -i ~/.ssh/oracle_a1 ubuntu@<A1_IP>
cd /home/ubuntu/memorial
tar xzf /tmp/kuzu_data.tar.gz
rm /tmp/kuzu_data.tar.gz
```

**선택 B — 그래프 리빌드** (배포 후 1-2분, 간단)

이관 직후 인증된 사용자로:
```bash
# 프론트엔드에서 로그인 후 JWT 토큰 확인 (브라우저 DevTools → Application → localStorage → auth_token)
curl -X POST https://memoir-api.duckdns.org/api/v1/mindmap/rebuild \
  -H "Authorization: Bearer <YOUR_JWT>"
```
Supabase의 다이어리/스크랩에서 그래프 재구축. 사용자마다 한 번씩 필요.

---

## Phase 4 — Docker 컴포즈 빌드 + 실행

```bash
cd /home/ubuntu/memorial
docker compose up -d --build  # 첫 빌드 10분 (ARM64 wheel 빌드, networkx + kuzu)

# 로그로 정상 부팅 확인 (Ctrl+C로 나가도 컨테이너는 계속 실행)
docker compose logs -f backend

# 헬스 체크 (컨테이너 안에서 8000번)
curl http://localhost:8000/health
# → {"status":"ok"} 비슷한 응답
```

---

## Phase 5 — 도메인 전환 (DuckDNS)

EC2 IP에 묶여 있던 `memoir-api.duckdns.org`를 A1 IP로 바꿉니다:

```bash
A1_IP=<your-a1-public-ip>
curl "https://www.duckdns.org/update?domains=memoir-api&token=c2c740e1-7b5d-443e-a2f4-086d6641a885&ip=${A1_IP}"
# 응답 "OK" 나오면 성공

# 전파 확인 (보통 1~3분, 최대 5분):
dig memoir-api.duckdns.org +short
# A1 IP가 나와야 함
```

⚠️ DuckDNS 토큰은 메모리에서 가져옴. 만료/회전됐으면 https://www.duckdns.org 로그인해서 새로 받기.

---

## Phase 6 — HTTPS (Let's Encrypt + nginx)

도메인이 새 IP로 가리키게 됐으면 certbot으로 새 인증서 발급:

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx

# nginx 리버스 프록시 설정 (8000 → 443)
sudo tee /etc/nginx/sites-available/memoir <<'EOF'
server {
    listen 80;
    server_name memoir-api.duckdns.org;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/memoir /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# certbot 발급 + 자동 80→443 redirect
sudo certbot --nginx -d memoir-api.duckdns.org \
  --non-interactive --agree-tos -m your-email@example.com --redirect

# 자동 갱신 등록
sudo systemctl enable --now certbot.timer
```

---

## Phase 7 — 검증

```bash
# A1 외부에서:
curl https://memoir-api.duckdns.org/health
# {"status":"ok"} 응답

# 프론트엔드 확인:
# https://memoir-knowledge.vercel.app 접속 → 로그인 → 캘린더 데이터 떠야 함
```

Vercel 환경변수 `VITE_API_URL`은 `https://memoir-api.duckdns.org/api/v1` 그대로 두면 됨 (도메인 변경 없음).

---

## Phase 8 — EC2 종료 (비용 0원 만들기)

1. AWS 콘솔 → **EC2 → Instances** → 인스턴스 선택 → **Terminate**
2. **EBS Volumes** → 자동 삭제 안 됐으면 수동 Delete
3. **Elastic IP** 있으면 → Release (안 하면 미사용 EIP에 시간당 과금됨!)
4. CloudWatch / RDS / S3 등 다른 쓰는 게 없으면 Billing dashboard에서 0달러 확인

---

## 트러블슈팅

### Q: capacity가 며칠째 안 잡힘
- A1 4OCPU 대신 1OCPU / 6GB로 줄여 시도
- Home region이 아닌 sub region 시도 (Tokyo 권장)
- 새벽 KST 2-5시
- `grab-capacity.sh` 같은 자동 retry

### Q: Docker 빌드 중 networkx/kuzu wheel 컴파일 에러 (ARM64)
- 대부분 자동으로 ARM64 wheel 받지만 가끔 빌드. `bootstrap.sh`에 빌드 도구 포함됨.
- 만약 메모리 부족이면 `--memory=4g` 또는 swap 확인.

### Q: certbot이 80 포트 못 잡음
- Security List에 80 인바운드 열렸는지 확인
- `sudo iptables -L INPUT -n | grep 80` 으로 iptables도 확인
- 다른 프로세스가 80 점유: `sudo lsof -i :80`

### Q: 프론트엔드 로그인하면 CORS 에러
- `.env`의 `ALLOWED_ORIGINS`에 `https://memoir-knowledge.vercel.app` 포함됐는지 확인
- 백엔드 재시작: `docker compose restart backend`
