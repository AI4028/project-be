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

## Enable menu photo uploads on EC2

1. In CloudFormation in Sydney (`ap-southeast-2`), create a stack from
   [deploy/menu-photos.yml](../deploy/menu-photos.yml). Use `galjido-dev-menu`
   for development. Enter the EC2 instance's existing IAM **role name** if it
   has one. If it has no role, leave the field empty, then attach the stack's
   `NewInstanceProfile` to the instance under **Actions → Security → Modify IAM role**.
   Acknowledge IAM resource creation when creating the stack.
2. For production, create a second stack named `galjido-prod-menu`. On the
   shared EC2 host, use the same role name (available in the first stack's
   outputs). Each stack grants access to its own bucket's `menu/` objects.
3. Add the following to the environment file for **each** service, substituting
   that environment's `BucketName` output. Development reads
   `/home/ec2-user/project-be/.env`; production reads
   `/home/ec2-user/project-be-prod/.env`.

   ```dotenv
   MENU_PHOTO_BUCKET=<BucketName from this environment's stack>
   AWS_DEFAULT_REGION=ap-southeast-2
   ```

4. Deploy the backend. Both workflows copy the four bootstrap JPEGs into S3
   before restarting the API. On an already upgraded host, run the following
   in the backend directory for that environment, then restart its service:

   ```sh
   .venv/bin/python -m scripts.sync_menu_photos
   ```

5. After the frontend deploys, open `/kiosk`, sign in with the store's kiosk
   key, and choose **Change menu photo** beside an item. Open the store menu
   to see the replacement. For a sample, this read-only check follows the API
   redirect and should return `200 image/jpeg`:

   ```sh
   curl -fsSL -o /dev/null -w '%{http_code} %{content_type}\n' https://dev.galjido.shop/api/media/menu/americano.jpg
   ```

The API uses the EC2 role for AWS credentials. The database stores stable
`/media/menu/...` references. The API redirects image reads to short-lived S3
URLs. Keep the bucket and its objects alongside your database when restoring a
deployment. The four tracked JPEGs bootstrap fresh buckets and local demos.
Staff replacements are stored in S3 and survive application redeployments.


If EC2 temporarily lacks S3 access, deployment logs a photo sync warning and
continues. The API serves bundled sample photos and the kiosk hides its upload
button until the seed photo is readable in S3. After correcting the role, run
`.venv/bin/python -m scripts.sync_menu_photos` in the service directory. The
kiosk checks storage again within a minute.
