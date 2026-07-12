# Backup e Restauração

## Backup manual

```bash
./scripts/backup.sh
```

Gera na pasta `/var/backups/rbm-task` (configurável via `BACKUP_DIR`):
- `db_<timestamp>.sql.gz` — dump completo do Postgres
- `minio_<timestamp>.tar.gz` — arquivo com os anexos guardados no MinIO

Backups com mais de `RETENTION_DAYS` dias (padrão 7) são apagados automaticamente a cada execução.

## Agendar backup diário (regra 3-2-1)

Adicione ao crontab da VPS (`crontab -e`):

```cron
0 3 * * * cd /root/rbm-task && ./scripts/backup.sh >> /var/log/rbm-backup.log 2>&1
```

Isso cobre "2 mídias" (volume da VPS + arquivo compactado) mas **não** cobre "1 cópia fora do ambiente" sozinho.
Para completar a regra 3-2-1, configure `RCLONE_REMOTE` (ex: `rclone config` apontando para S3/Backblaze/Google Drive)
e exporte a variável antes do cron rodar, ou adicione `RCLONE_REMOTE=meuremoto:rbm-backups` na linha do cron.

## Restaurar um backup

```bash
./scripts/restore.sh /var/backups/rbm-task/db_20260712_030000.sql.gz /var/backups/rbm-task/minio_20260712_030000.tar.gz
```

O script restaura para um banco separado (`<nome>_restoring`) para você validar antes de promover — ele imprime os
comandos de promoção (renomear banco) ao final. Isso evita substituir o banco em produção por engano antes de
conferir que o backup está íntegro.

**Teste a restauração periodicamente** (ex: uma vez por trimestre) num ambiente separado — um backup nunca
testado não é um backup confiável.
