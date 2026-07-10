# Production Deployment

This guide outlines how to deploy the MedNexus AI Flask application to a production Linux server (e.g. Ubuntu 22.04 LTS) using **Gunicorn**, **Nginx**, and **Systemd**.

---

## 1. Server Provisioning & Dependencies

Update your system packages and install Python, pip, Nginx, and SQLite:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-venv nginx sqlite3 git -y
```

Clone your repository into a directory (e.g. `/var/www/mednexus-ai`):

```bash
sudo mkdir -p /var/www/mednexus-ai
sudo chown -R $USER:$USER /var/www/mednexus-ai
git clone https://github.com/Salman7292/MedNexusAI.git /var/www/mednexus-ai
cd /var/www/mednexus-ai
```

---

## 2. Virtual Environment & Dependencies

Initialize and activate your production virtual environment, and install requirements:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Install production WSGI server
```

---

## 3. Production Environment Configuration

Create your production `.env` file at `/var/www/mednexus-ai/.env`:

```bash
nano .env
```
Populate it with your actual production keys.

---

## 4. Configuring Gunicorn Systemd Service

Create a systemd service file to manage the Gunicorn application process, keeping it active in the background and starting it automatically on boot:

```bash
sudo nano /etc/systemd/system/mednexus.service
```

Add the following configuration:

```ini
[Unit]
Description=Gunicorn instance to serve MedNexus AI
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/mednexus-ai
Environment="PATH=/var/www/mednexus-ai/venv/bin"
ExecStart=/var/www/mednexus-ai/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start mednexus
sudo systemctl enable mednexus
```

Verify it is running:
```bash
sudo systemctl status mednexus
```

---

## 5. Nginx Reverse Proxy Setup

Nginx acts as a reverse proxy, handling external client HTTPS requests and forwarding them to the local Gunicorn socket/address on port `8000`.

Create an Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/mednexus
```

Add the following config block:

```nginx
server {
    listen 80;
    server_name your_domain_or_ip;

    # Image upload directory access
    location /static/ {
        alias /var/www/mednexus-ai/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Reverse proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Enable SSE response streaming (Disable buffering)
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_read_timeout 24h;
    }
}
```

Enable the site config and reload Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/mednexus /etc/nginx/sites-enabled/
sudo nginx -t  # Test config syntax
sudo systemctl restart nginx
```

---

## 6. Securing with HTTPS (SSL)

To encrypt client-to-server requests, install Certbot and generate Let's Encrypt certificates:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your_domain
```
Certbot will automatically modify the Nginx configuration to force secure HTTPS connections.
