#!/usr/bin/env bash
# Oracle Cloud A1 capacity 자동 재시도 스크립트
#
# 사용법:
#   1) OCI CLI 설치 + 설정 완료 후
#   2) 아래 변수 채우기
#   3) bash grab-capacity.sh
#   ─ 또는 cron으로 등록: */5 * * * * /home/ubuntu/grab-capacity.sh
#
# OCI CLI 설치:
#   bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
#   oci setup config
#   (tenancy OCID + user OCID + region + API 키 등록)

set -euo pipefail

# ───────── 사용자 설정 ─────────
COMPARTMENT_OCID="${COMPARTMENT_OCID:-}"     # 콘솔 → Identity → Compartments → root OCID
AVAILABILITY_DOMAIN="${AVAILABILITY_DOMAIN:-}" # 예: "AD-1" (oci iam availability-domain list 로 확인)
SUBNET_OCID="${SUBNET_OCID:-}"                # 미리 생성한 VCN의 public subnet OCID
IMAGE_OCID="${IMAGE_OCID:-}"                  # Ubuntu 22.04 ARM64 image OCID (region별 다름)
SSH_PUBKEY_PATH="${SSH_PUBKEY_PATH:-$HOME/.ssh/oracle_a1.pub}"

DISPLAY_NAME="${DISPLAY_NAME:-memoir-a1}"
SHAPE="VM.Standard.A1.Flex"
OCPUS="${OCPUS:-1}"      # 1로 시작하면 capacity 잡힐 확률↑. 잡힌 뒤 콘솔에서 4까지 늘릴 수 있음.
RAM_GB="${RAM_GB:-6}"    # OCPU×6GB 권장 (Always Free 한도: 4 OCPU + 24GB)

# ───────── 변수 검증 ─────────
for v in COMPARTMENT_OCID AVAILABILITY_DOMAIN SUBNET_OCID IMAGE_OCID; do
  if [ -z "${!v}" ]; then
    echo "환경변수 $v 가 비어 있음. 스크립트 상단 또는 export 로 설정해야 함."
    exit 1
  fi
done

if ! command -v oci >/dev/null 2>&1; then
  echo "OCI CLI 없음. 먼저 설치:"
  echo "  bash -c \"\$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)\""
  exit 1
fi

# ───────── 한 번 시도 ─────────
attempt=1
while true; do
  ts=$(date '+%F %T')
  echo "[$ts] attempt #$attempt — A1 ${OCPUS} OCPU / ${RAM_GB}GB 시도"

  set +e
  out=$(oci compute instance launch \
    --availability-domain "$AVAILABILITY_DOMAIN" \
    --compartment-id "$COMPARTMENT_OCID" \
    --shape "$SHAPE" \
    --shape-config "{\"ocpus\": ${OCPUS}, \"memoryInGBs\": ${RAM_GB}}" \
    --image-id "$IMAGE_OCID" \
    --subnet-id "$SUBNET_OCID" \
    --display-name "$DISPLAY_NAME" \
    --assign-public-ip true \
    --metadata "{\"ssh_authorized_keys\": \"$(cat "$SSH_PUBKEY_PATH")\"}" \
    --wait-for-state RUNNING 2>&1)
  rc=$?
  set -e

  if [ $rc -eq 0 ]; then
    echo "================================"
    echo "🎉 인스턴스 생성 성공!"
    echo "$out" | grep -E 'public-ip|id' | head -10
    echo "================================"
    break
  fi

  if echo "$out" | grep -q "Out of host capacity"; then
    echo "  → out of capacity, 5분 대기 후 재시도"
    sleep 300
  elif echo "$out" | grep -qi "limit"; then
    echo "  → 한도 초과 (이미 A1 4 OCPU 다 쓰는 중일 수도). 콘솔 확인:"
    echo "$out" | head -3
    exit 2
  else
    echo "  → 기타 에러:"
    echo "$out" | head -5
    echo "  60초 후 재시도"
    sleep 60
  fi

  attempt=$((attempt + 1))
done
