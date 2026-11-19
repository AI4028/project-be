# Production deployment on the shared EC2 host

The production workflows deploy `main` to separate paths from development:

| Environment | Backend | Frontend | Service | Port |
| --- | --- | --- | --- | --- |
| Development | `/home/ec2-user/project-be` | `/var/www/galjido` | `galjido-api` | 8000 |
| Production | `/home/ec2-user/project-be-prod` | `/var/www/galjido-prod` | `galjido-api-prod` | 8001 |

Run this setup once on EC2 before merging the production workflows.

```sh
mkdir -p /home/ec2-user/project-be-prod /home/ec2-user/galjido-web-prod
python3.11 -m venv /home/ec2-user/project-be-prod/.venv
sudo mkdir -p /var/www/galjido-prod

cat > /home/ec2-user/project-be-prod/.env <<'EOF'
DATABASE_URL=sqlite:////home/ec2-user/project-be-prod/linkage.db
CORS_ORIGINS=https://galjido.shop
DEMO_MODE=0
EOF
chmod 600 /home/ec2-user/project-be-prod/.env
```

Create `/etc/systemd/system/galjido-api-prod.service`:

```ini
[Unit]
Description=Galjido production API
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/project-be-prod
EnvironmentFile=/home/ec2-user/project-be-prod/.env
ExecStart=/home/ec2-user/project-be-prod/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001 --workers 1 --root-path /api --proxy-headers --forwarded-allow-ips 127.0.0.1 --no-access-log
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Reload the service manager, but do not start the service until the first backend workflow has uploaded application code:

```sh
sudo systemctl daemon-reload
sudo systemctl enable galjido-api-prod
```

Create `/etc/nginx/conf.d/galjido-prod.conf`:

```nginx
map $http_upgrade $galjido_prod_connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    server_name galjido.shop;

    root /var/www/galjido-prod;
    index index.html;
    access_log off;

    location = /api {
        return 308 /api/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $galjido_prod_connection_upgrade;
        proxy_read_timeout 3600s;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Validate and reload Nginx:

```sh
sudo nginx -t
sudo systemctl reload nginx
```

Point the `galjido.shop` A record to the EC2 public IP and allow inbound HTTPS
(TCP 443) in its security group. After the first successful main deployment,
create the certificate:

```sh
sudo certbot --nginx -d galjido.shop --redirect
sudo systemctl enable --now certbot-renew.timer
sudo certbot renew --dry-run
```

The first production deployment creates an empty database. Seed it once, then
issue and store the kiosk key once:

```sh
cd /home/ec2-user/project-be-prod
DATABASE_URL=sqlite:////home/ec2-user/project-be-prod/linkage.db \
  .venv/bin/python -m scripts.seed seed/gist-cafe.json
DATABASE_URL=sqlite:////home/ec2-user/project-be-prod/linkage.db \
  .venv/bin/python -m scripts.create_kiosk GK01
```

Never copy development's SQLite database or kiosk key into production.
