# Yupoo to ERP Sync - Docker Official Documentation

## Quick Start (快速启动)

1. **Build the image (构建镜像)**:
   ```bash
   docker compose build
   ```

2. **Run the synchronization (运行同步)**:
   ```bash
   # Use the following format:
   docker compose run erp-sync --album-id [YOUR_ALBUM_ID]
   ```

3. **Example (示例)**:
   ```bash
   docker compose run erp-sync --album-id 231967755
   ```

## Configuration (配置)

The container automatically mounts the standard project `.env` file. Ensure `ERP_USERNAME` and `ERP_PASSWORD` are set correctly in `.env`.

## Persistence (持久化)

Logs and screenshots are automatically synchronized to your local machine:
- `./logs/`: Sync activity logs
- `./screenshots/`: Success/Error verification images

## CDP Mode (CDP 模式)

If you have a persistent browser running on the host machine (e.g., at port 9222), you can use:
```bash
docker compose run erp-sync --album-id [ID] --use-cdp --cdp-url http://host.docker.internal:9222
```
