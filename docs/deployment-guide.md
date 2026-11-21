# 生產部署指南

從開發環境到生產環境的完整部署步驟。

## 方案一：Docker（推薦）

```bash
# 1. 克隆項目
git clone https://github.com/cwchon310/enterprise-ai-agent.git
cd enterprise-ai-agent

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env，設定 AGENT_API_KEY 與 LLM_PROVIDER

# 3. 建立並啟動
docker compose up --build -d

# 4. 確認健康狀態
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

### docker-compose.yml 要點

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 30s
      timeout: 5s
      retries: 3
```

---

## 方案二：手動 + systemd

### 安裝依賴

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip
```

### 部署

```bash
# 1. 建立使用者
sudo useradd -m -s /bin/bash agent

# 2. 克隆代碼
sudo -u agent git clone https://github.com/cwchon310/enterprise-ai-agent.git /opt/enterprise-ai-agent
cd /opt/enterprise-ai-agent

# 3. 虛擬環境
sudo -u agent python3 -m venv .venv
sudo -u agent .venv/bin/pip install -r requirements.txt

# 4. 設定 .env
sudo -u agent cp .env.example .env
sudo -u agent nano .env

# 5. systemd 服務
sudo tee /etc/systemd/system/enterprise-ai-agent.service <<'EOF'
[Unit]
Description=Enterprise AI Agent
After=network.target

[Service]
User=agent
WorkingDirectory=/opt/enterprise-ai-agent
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/enterprise-ai-agent/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now enterprise-ai-agent
```

---

## Nginx 反向代理（可選）

```nginx
server {
    listen 80;
    server_name ai.yourcompany.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 安全檢查清單

- [ ] `AGENT_API_KEY` 已改為強隨機密碼
- [ ] `.env` 不在版本控制內（已在 `.gitignore`）
- [ ] `CORS_ORIGINS` 只允許信任的域名
- [ ] Docker 以非 root 用戶運行（可加 `USER` 指令）
- [ ] 啟用 HTTPS（Nginx + Let's Encrypt）

---

## 備份

```bash
# 備份 SQLite 資料庫
cp agent.db agent.db.backup.$(date +%F)

# 備份上傳的檔案（若有）
tar czf uploads-backup.tar.gz ./data/uploads
```
