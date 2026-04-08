#!/bin/bash
# Oracle Cloud 무료 ARM 인스턴스 셋업 스크립트
# Cloud Shell에 업로드하거나 직접 붙여넣어 실행하세요.
# 실행: bash oracle_setup.sh

set -euo pipefail

# ─────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✅ $*"; }
err()  { echo "[$(date '+%H:%M:%S')] ❌ $*" >&2; exit 1; }

# ─────────────────────────────────────────────
# 0. 전제 조건 확인
# ─────────────────────────────────────────────
log "OCI_TENANCY 확인 중..."
[[ -z "${OCI_TENANCY:-}" ]] && err "OCI_TENANCY 환경 변수가 없습니다. OCI Cloud Shell에서 실행하세요."
ok "Tenancy: $OCI_TENANCY"

# ─────────────────────────────────────────────
# 1. SSH 키 생성 (이미 있으면 스킵)
# ─────────────────────────────────────────────
if [[ -f ~/.ssh/id_rsa.pub ]]; then
  ok "SSH 키 이미 존재 — 스킵"
else
  log "SSH 키 생성 중..."
  ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -q
  ok "SSH 키 생성 완료"
fi

# ─────────────────────────────────────────────
# 2. VCN — 이미 memoir-vcn이 있으면 재사용
# ─────────────────────────────────────────────
log "기존 memoir-vcn 조회 중..."
VCN_ID=$(oci network vcn list \
  --compartment-id "$OCI_TENANCY" \
  --display-name "memoir-vcn" \
  --query 'data[0].id' \
  --raw-output 2>/dev/null || true)

if [[ -z "$VCN_ID" || "$VCN_ID" == "null" ]]; then
  log "VCN 생성 중..."
  VCN_ID=$(oci network vcn create \
    --compartment-id "$OCI_TENANCY" \
    --display-name "memoir-vcn" \
    --cidr-block "10.0.0.0/16" \
    --wait-for-state AVAILABLE \
    --query 'data.id' \
    --raw-output)
  ok "VCN 생성 완료: $VCN_ID"
else
  ok "기존 VCN 재사용: $VCN_ID"
fi

# ─────────────────────────────────────────────
# 3. Internet Gateway — 이미 있으면 재사용
# ─────────────────────────────────────────────
log "기존 Internet Gateway 조회 중..."
IGW_ID=$(oci network internet-gateway list \
  --compartment-id "$OCI_TENANCY" \
  --vcn-id "$VCN_ID" \
  --query 'data[0].id' \
  --raw-output 2>/dev/null || true)

if [[ -z "$IGW_ID" || "$IGW_ID" == "null" ]]; then
  log "Internet Gateway 생성 중..."
  IGW_ID=$(oci network internet-gateway create \
    --compartment-id "$OCI_TENANCY" \
    --vcn-id "$VCN_ID" \
    --display-name "memoir-igw" \
    --is-enabled true \
    --wait-for-state AVAILABLE \
    --query 'data.id' \
    --raw-output)
  ok "IGW 생성 완료: $IGW_ID"
else
  ok "기존 IGW 재사용: $IGW_ID"
fi

# ─────────────────────────────────────────────
# 4. Route Table 업데이트 (0.0.0.0/0 → IGW)
# ─────────────────────────────────────────────
log "Route Table 업데이트 중..."
RT_ID=$(oci network route-table list \
  --compartment-id "$OCI_TENANCY" \
  --vcn-id "$VCN_ID" \
  --query 'data[0].id' \
  --raw-output)

oci network route-table update \
  --rt-id "$RT_ID" \
  --route-rules "[{\"networkEntityId\":\"$IGW_ID\",\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\"}]" \
  --force > /dev/null

ok "Route Table 업데이트 완료"

# ─────────────────────────────────────────────
# 5. Subnet — 이미 있으면 재사용
# ─────────────────────────────────────────────
log "기존 memoir-subnet 조회 중..."
SUBNET_ID=$(oci network subnet list \
  --compartment-id "$OCI_TENANCY" \
  --vcn-id "$VCN_ID" \
  --display-name "memoir-subnet" \
  --query 'data[0].id' \
  --raw-output 2>/dev/null || true)

if [[ -z "$SUBNET_ID" || "$SUBNET_ID" == "null" ]]; then
  log "Subnet 생성 중..."
  SUBNET_ID=$(oci network subnet create \
    --compartment-id "$OCI_TENANCY" \
    --vcn-id "$VCN_ID" \
    --display-name "memoir-subnet" \
    --cidr-block "10.0.0.0/24" \
    --wait-for-state AVAILABLE \
    --query 'data.id' \
    --raw-output)
  ok "Subnet 생성 완료: $SUBNET_ID"
else
  ok "기존 Subnet 재사용: $SUBNET_ID"
fi

# ─────────────────────────────────────────────
# 6. Security List — 포트 22(내 IP만), 80, 443 열기
# ─────────────────────────────────────────────
log "Security List 포트 열기 (22(내 IP), 80, 443)..."
SL_ID=$(oci network security-list list \
  --compartment-id "$OCI_TENANCY" \
  --vcn-id "$VCN_ID" \
  --query 'data[0].id' \
  --raw-output)

# 보안: SSH(22)는 현재 접속 IP로만 제한. IP 조회 실패 시 스크립트 중단.
MY_IP=$(curl -sf https://api.ipify.org) || { err "공인 IP 조회 실패. 스크립트를 중단합니다. 네트워크 연결을 확인하세요."; exit 1; }
MY_IP="${MY_IP}/32"
log "SSH 허용 IP: $MY_IP"

oci network security-list update \
  --security-list-id "$SL_ID" \
  --ingress-security-rules "[
    {\"source\":\"${MY_IP}\",\"protocol\":\"6\",\"isStateless\":false,\"tcpOptions\":{\"destinationPortRange\":{\"min\":22,\"max\":22}}},
    {\"source\":\"0.0.0.0/0\",\"protocol\":\"6\",\"isStateless\":false,\"tcpOptions\":{\"destinationPortRange\":{\"min\":80,\"max\":80}}},
    {\"source\":\"0.0.0.0/0\",\"protocol\":\"6\",\"isStateless\":false,\"tcpOptions\":{\"destinationPortRange\":{\"min\":443,\"max\":443}}}
  ]" \
  --force > /dev/null

ok "Security List 업데이트 완료"

# ─────────────────────────────────────────────
# 7. Oracle Linux ARM 이미지 OCID 확인
# ─────────────────────────────────────────────
log "Oracle Linux ARM 이미지 조회 중..."
IMG_ID=$(oci compute image list \
  --compartment-id "$OCI_TENANCY" \
  --operating-system "Oracle Linux" \
  --shape "VM.Standard.A1.Flex" \
  --sort-by TIMECREATED \
  --sort-order DESC \
  --query 'data[0].id' \
  --raw-output)

[[ -z "$IMG_ID" || "$IMG_ID" == "null" ]] && err "Oracle Linux ARM 이미지를 찾을 수 없습니다."
ok "이미지 OCID: $IMG_ID"

# ─────────────────────────────────────────────
# 8. 인스턴스 생성 Retry 루프
# ─────────────────────────────────────────────
echo ""
log "인스턴스 생성 시작 (용량 확보될 때까지 자동 재시도)..."
log "중단하려면 Ctrl+C"
echo ""

ATTEMPT=0
WAIT=60  # 초기 대기 시간(초) — 너무 빠른 반복은 API 차단 유발 가능

while true; do
  ATTEMPT=$((ATTEMPT + 1))
  log "시도 #$ATTEMPT ..."

  RESULT=$(oci compute instance launch \
    --compartment-id "$OCI_TENANCY" \
    --availability-domain "ivoq:AP-CHUNCHEON-1-AD-1" \
    --shape "VM.Standard.A1.Flex" \
    --shape-config '{"ocpus":4,"memoryInGBs":24}' \
    --image-id "$IMG_ID" \
    --subnet-id "$SUBNET_ID" \
    --display-name "memoir-backend" \
    --assign-public-ip true \
    --ssh-authorized-keys-file ~/.ssh/id_rsa.pub 2>&1) || true

  if echo "$RESULT" | grep -q '"lifecycle-state"'; then
    echo ""
    ok "인스턴스 생성 성공!"
    INSTANCE_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])" 2>/dev/null || echo "PARSE_FAIL")

    if [[ "$INSTANCE_ID" != "PARSE_FAIL" ]]; then
      log "IP 확인 중 (최대 60초)..."
      sleep 30
      PUBLIC_IP=$(oci compute instance list-vnics \
        --instance-id "$INSTANCE_ID" \
        --query 'data[0]."public-ip"' \
        --raw-output 2>/dev/null || echo "콘솔에서 확인")
    else
      INSTANCE_ID="(콘솔에서 확인)"
      PUBLIC_IP="(콘솔에서 확인)"
    fi

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  인스턴스 ID : $INSTANCE_ID"
    echo "  공인 IP     : $PUBLIC_IP"
    echo "  SSH 접속    : ssh opc@$PUBLIC_IP"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    break
  else
    # 에러 전체 출력 (첫 시도에만, 이후는 요약)
    ERR_CODE=$(echo "$RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('code','?'))" 2>/dev/null || echo "파싱불가")
    ERR_MSG=$(echo "$RESULT"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message','?'))" 2>/dev/null || echo "$RESULT")

    if [[ $ATTEMPT -eq 1 ]]; then
      log "  에러 코드   : $ERR_CODE"
      log "  에러 메시지 : $ERR_MSG"
      # Out of Capacity가 아닌 다른 에러면 즉시 중단
      if ! echo "$ERR_MSG $ERR_CODE" | grep -qi "capacity\|InternalError\|500"; then
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "용량 부족이 아닌 다른 에러입니다. 스크립트를 종료합니다."
        echo "전체 에러:"
        echo "$RESULT"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        exit 1
      fi
    else
      log "  → [$ERR_CODE] Out of Capacity — 계속 대기 중"
    fi

    log "  ${WAIT}초 후 재시도... (총 ${ATTEMPT}회 시도)"
    sleep $WAIT
  fi
done
