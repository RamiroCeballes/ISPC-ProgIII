#!/usr/bin/env bash
#
# Construye la imagen del backend y la publica en Amazon ECR.
#
# Uso:
#   ./deploy/ecr-push.sh                 # tag = SHA corto de git
#   ./deploy/ecr-push.sh v1.0.0          # tag explícito
#
# Configuración por variables de entorno (todas tienen default):
#   AWS_REGION       región del repositorio            (default: us-east-1)
#   ECR_REPOSITORY   nombre del repo en ECR            (default: ispc-progiii-backend)
#   AWS_ACCOUNT_ID   cuenta destino                    (default: la del perfil activo)
#   PLATFORM         arquitectura del runtime          (default: linux/amd64)
#   PUSH_LATEST      además del tag, empujar 'latest'  (default: true)
#
set -euo pipefail

AWS_REGION="${AWS_REGION:-sa-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-ispc-backend}"
PUSH_LATEST="${PUSH_LATEST:-true}"

# Fargate corre x86_64 salvo que el servicio se cree con runtimePlatform ARM64.
# En una Mac con Apple Silicon el build por defecto sale arm64 y la tarea muere
# con "exec format error", así que la plataforma se fija explícitamente.
PLATFORM="${PLATFORM:-linux/amd64}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# ── Verificaciones previas ──────────────────────────────────────────────────
command -v aws >/dev/null 2>&1 || {
    echo "ERROR: falta la AWS CLI. Instalar con: brew install awscli" >&2
    exit 1
}
command -v docker >/dev/null 2>&1 || {
    echo "ERROR: falta docker." >&2
    exit 1
}

if ! aws sts get-caller-identity >/dev/null 2>&1; then
    echo "ERROR: las credenciales de AWS no están configuradas o vencieron." >&2
    echo "       Ejecutar 'aws configure' (o 'aws sso login')." >&2
    exit 1
fi

AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REPO_URI="${REGISTRY}/${ECR_REPOSITORY}"

# ── Tag de la imagen ────────────────────────────────────────────────────────
if [ $# -ge 1 ]; then
    IMAGE_TAG="$1"
elif git -C "${PROJECT_ROOT}" rev-parse --short HEAD >/dev/null 2>&1; then
    IMAGE_TAG="$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD)"
    # Marcar como sucio si hay cambios sin commitear: evita confundir qué
    # código está corriendo en la nube.
    if ! git -C "${PROJECT_ROOT}" diff --quiet HEAD 2>/dev/null; then
        IMAGE_TAG="${IMAGE_TAG}-dirty"
    fi
else
    IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
fi

echo "──────────────────────────────────────────────────"
echo "  Cuenta     : ${AWS_ACCOUNT_ID}"
echo "  Región     : ${AWS_REGION}"
echo "  Repositorio: ${ECR_REPOSITORY}"
echo "  Tag        : ${IMAGE_TAG}"
echo "  Plataforma : ${PLATFORM}"
echo "──────────────────────────────────────────────────"

# ── Crear el repositorio si todavía no existe ───────────────────────────────
if ! aws ecr describe-repositories \
        --repository-names "${ECR_REPOSITORY}" \
        --region "${AWS_REGION}" >/dev/null 2>&1; then
    echo "==> El repositorio no existe; creándolo..."
    aws ecr create-repository \
        --repository-name "${ECR_REPOSITORY}" \
        --region "${AWS_REGION}" \
        --image-scanning-configuration scanOnPush=true \
        --image-tag-mutability MUTABLE \
        --encryption-configuration encryptionType=AES256 >/dev/null
    echo "==> Repositorio ${ECR_REPOSITORY} creado."
fi

# ── Login en el registry ────────────────────────────────────────────────────
echo "==> Autenticando contra ${REGISTRY}..."
aws ecr get-login-password --region "${AWS_REGION}" \
    | docker login --username AWS --password-stdin "${REGISTRY}"

# ── Build y push ────────────────────────────────────────────────────────────
TAGS=(--tag "${REPO_URI}:${IMAGE_TAG}")
if [ "${PUSH_LATEST}" = "true" ]; then
    TAGS+=(--tag "${REPO_URI}:latest")
fi

# --provenance=false: sin esto buildx sube un índice OCI con manifiestos de
# atestación que algunos runtimes de ECS no saben resolver.
echo "==> Construyendo y publicando la imagen..."
docker buildx build \
    --platform "${PLATFORM}" \
    --provenance=false \
    --build-arg ENV_NAME=produccion \
    "${TAGS[@]}" \
    --push \
    "${PROJECT_ROOT}"

echo ""
echo "Imagen publicada:"
echo "   ${REPO_URI}:${IMAGE_TAG}"
[ "${PUSH_LATEST}" = "true" ] && echo "   ${REPO_URI}:latest"
echo ""
echo "Para usarla en una task definition de ECS:"
echo "   \"image\": \"${REPO_URI}:${IMAGE_TAG}\""
