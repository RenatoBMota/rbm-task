#!/usr/bin/env bash
# Restores a Postgres backup produced by backup.sh.
# WARNING: this replaces the current database contents.
#
# Usage: ./scripts/restore.sh /var/backups/rbm-task/db_20260712_030000.sql.gz [minio_backup.tar.gz]

set -euo pipefail

DB_BACKUP_FILE="${1:?Uso: restore.sh <arquivo db_*.sql.gz> [arquivo minio_*.tar.gz]}"
MINIO_BACKUP_FILE="${2:-}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-rbm_postgres}"
MINIO_CONTAINER="${MINIO_CONTAINER:-rbm_minio}"
POSTGRES_USER="${POSTGRES_USER:-rbm}"
POSTGRES_DB="${POSTGRES_DB:-rbmtask}"

echo "Isso vai APAGAR e recriar o banco '$POSTGRES_DB'. Digite 'sim' para confirmar:"
read -r CONFIRMATION
if [ "$CONFIRMATION" != "sim" ]; then
  echo "Cancelado."
  exit 1
fi

echo "[$(date)] Restaurando banco a partir de $DB_BACKUP_FILE"
docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres \
  -c "DROP DATABASE IF EXISTS ${POSTGRES_DB}_restoring;"
docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d postgres \
  -c "CREATE DATABASE ${POSTGRES_DB}_restoring;"
gunzip -c "$DB_BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "${POSTGRES_DB}_restoring"

echo "[$(date)] Banco restaurado em '${POSTGRES_DB}_restoring'. Valide os dados antes de promover:"
echo "  docker exec -it $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d ${POSTGRES_DB}_restoring -c '\\dt'"
echo "Para promover (troca o banco em uso), rode manualmente:"
echo "  docker compose stop backend"
echo "  docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d postgres -c \"ALTER DATABASE ${POSTGRES_DB} RENAME TO ${POSTGRES_DB}_old;\""
echo "  docker exec -i $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d postgres -c \"ALTER DATABASE ${POSTGRES_DB}_restoring RENAME TO ${POSTGRES_DB};\""
echo "  docker compose start backend"

if [ -n "$MINIO_BACKUP_FILE" ]; then
  echo "[$(date)] Restaurando arquivos do MinIO a partir de $MINIO_BACKUP_FILE"
  docker run --rm --volumes-from "$MINIO_CONTAINER" -v "$(dirname "$MINIO_BACKUP_FILE"):/backup" alpine \
    sh -c "cd / && tar xzf /backup/$(basename "$MINIO_BACKUP_FILE")"
  echo "[$(date)] Arquivos MinIO restaurados"
fi
