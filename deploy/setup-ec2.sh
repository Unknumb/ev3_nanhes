#!/bin/bash
set -e

# ═══════════════════════════════════════════════════════════════════
# SETUP COMPLETO: Nginx + Certbot + Systemd + Rebuild front + CORS
# ═══════════════════════════════════════════════════════════════════

REPO_DIR=/home/ubuntu/ev3_nanhes
DOMAIN=tuedad.me
API_DOMAIN=api.tuedad.me

echo "══ 1/10 Instalar Nginx ══"
sudo apt update && sudo apt install -y nginx

echo "══ 2/10 Crear config Nginx ══"
sudo tee /etc/nginx/sites-available/tuedad.me > /dev/null <<'NGINX'
server {
    listen 80;
    listen [::]:80;
    server_name tuedad.me www.tuedad.me;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade    $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 80;
    listen [::]:80;
    server_name api.tuedad.me;
    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
NGINX

sudo rm -f /etc/nginx/sites-enabled/tuedad.me /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/tuedad.me /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
echo "✓ Nginx OK (HTTP)"

echo "══ 3/10 Certbot (HTTPS) ══"
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tuedad.me -d www.tuedad.me -d api.tuedad.me
echo "✓ Certbot OK"

echo "══ 4/10 Detectar uvicorn ══"
UVICORN_PATH=$(which uvicorn 2>/dev/null || echo "$REPO_DIR/.venv/bin/uvicorn")
if [ ! -f "$UVICORN_PATH" ]; then
    UVICORN_PATH=$(find /home/ubuntu -name uvicorn -type f 2>/dev/null | head -1)
fi
echo "uvicorn -> $UVICORN_PATH"

echo "══ 5/10 Detectar npm ══"
NPM_PATH=$(which npm 2>/dev/null || echo "/usr/bin/npm")
echo "npm -> $NPM_PATH"

echo "══ 6/10 Secretos del backend ══"
sudo mkdir -p /etc/ev3
sudo tee /etc/ev3/api.env > /dev/null <<'SECRETS'
DATABASE_URL=postgresql://postgres.pvgwstqjcnselzejzslv:ev3nhanes2026@aws-1-us-east-1.pooler.supabase.com:6543/postgres
CORS_ORIGINS=https://tuedad.me,https://www.tuedad.me
SECRET_KEY=e336c9118b919a7b004c2e76431a12fb40b0acf527c567a7ce774dff65d958df
SMTP_HOST=smtp.resend.com
SMTP_PORT=587
SMTP_USER=resend
SMTP_PASSWORD=re_PHjFDkDD_B2JfdSDme5otYtotUfKEqCTh
SMTP_FROM=NHANES Longevity <noreply@tuedad.me>
SECRETS
sudo chmod 600 /etc/ev3/api.env
echo "✓ Secretos en /etc/ev3/api.env"

echo "══ 7/10 Servicio systemd: backend ══"
sudo tee /etc/systemd/system/ev3-api.service > /dev/null <<EOF
[Unit]
Description=EV3 NHANES Longevity API (uvicorn)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$REPO_DIR
EnvironmentFile=/etc/ev3/api.env
ExecStart=$UVICORN_PATH api.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "══ 8/10 Rebuild frontend con HTTPS ══"
echo "NEXT_PUBLIC_API_URL=https://api.tuedad.me" > "$REPO_DIR/web/.env.local"
cd "$REPO_DIR/web" && $NPM_PATH run build
echo "✓ Frontend reconstruido"

echo "══ 9/10 Servicio systemd: frontend ══"
sudo tee /etc/systemd/system/ev3-web.service > /dev/null <<EOF
[Unit]
Description=EV3 NHANES Longevity Web (Next.js)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$REPO_DIR/web
Environment=NODE_ENV=production
Environment=PORT=3000
ExecStart=$NPM_PATH run start
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "══ 10/10 Arrancar servicios ══"
pkill -f "uvicorn api.main" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
sleep 2

sudo systemctl daemon-reload
sudo systemctl enable --now ev3-api ev3-web
sleep 3

echo ""
echo "═══════════════════════════════════════════"
sudo systemctl status ev3-api --no-pager -l
echo ""
sudo systemctl status ev3-web --no-pager -l
echo "═══════════════════════════════════════════"
echo ""
echo "✓ TODO LISTO. Probar:"
echo "  curl -i https://api.tuedad.me/health"
echo "  Abrir https://tuedad.me en el navegador"
