#!/usr/bin/env bash
# ==============================================================================
# SABIN BALAN FINANCE (GUARDIANTREE FP) — TURNKEY UBUNTU VPS DEPLOYMENT SCRIPT
# Usage: sudo bash deployment/deploy.sh
# Supported OS: Ubuntu 20.04 / 22.04 / 24.04 LTS, Debian 11 / 12
# ==============================================================================

set -euo pipefail

echo "==========================================================================="
echo " 🚀 SABIN BALAN FINANCE — PRODUCTION VPS TURNKEY DEPLOYMENT SCRIPT"
echo "==========================================================================="

# Auto-detect script directory or fallback to standard /var/www/sabin_finance
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$SCRIPT_DIR}"
VENV_DIR="$PROJECT_DIR/venv"
LOG_DIR="/var/log/sabin_finance"

echo "--> Target Project Root: $PROJECT_DIR"

# 1. Ensure Root Privileges
if [ "$EUID" -ne 0 ]; then
    echo "❌ ERROR: Please run this script with sudo/root privileges (e.g. sudo bash deployment/deploy.sh)"
    exit 1
fi

# 2. System Package Updates & Prerequisites
echo "--> [1/9] Updating system packages & installing production toolchain..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-dev python3-pip build-essential \
                   libpq-dev libjpeg-dev zlib1g-dev libssl-dev libffi-dev \
                   nginx certbot python3-certbot-nginx ufw git curl

# 3. Create Logging & Media Directories
echo "--> [2/9] Setting up log files and application directories..."
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_DIR/media"
mkdir -p "$PROJECT_DIR/staticfiles"
chown -R www-data:www-data "$LOG_DIR"

# 4. Virtual Environment Setup
echo "--> [3/9] Configuring Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

echo "--> [4/9] Upgrading pip & installing Python requirements..."
"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

# 5. Environment File Checks
echo "--> [5/9] Validating environment configuration (.env)..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  WARNING: No .env found. Copying .env.example template to .env..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    # Generate secure django secret key
    SECRET_KEY_GEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
    sed -i "s/django-insecure-change-this-in-production-immediately/$SECRET_KEY_GEN/g" "$PROJECT_DIR/.env"
    echo "✅ Created production .env with auto-generated secure secret key."
fi

# 6. Django Database Migrations & Static Files Collection
echo "--> [6/9] Applying database migrations..."
"$VENV_DIR/bin/python" "$PROJECT_DIR/manage.py" migrate --noinput

echo "--> [7/9] Compiling and compressing static assets (collectstatic)..."
"$VENV_DIR/bin/python" "$PROJECT_DIR/manage.py" collectstatic --noinput --clear

# 7. File Permissions Setup
echo "--> [8/9] Securing file ownership and permissions for www-data..."
chown -R www-data:www-data "$PROJECT_DIR"
chmod -R 755 "$PROJECT_DIR"
if [ -f "$PROJECT_DIR/.env" ]; then
    chmod 600 "$PROJECT_DIR/.env"
fi

# 8. Install Systemd Service
echo "--> [9/9] Configuring and starting Systemd & Nginx services..."
cp "$PROJECT_DIR/deployment/sabin_finance.service" /etc/systemd/system/sabin_finance.service
systemctl daemon-reload
systemctl enable sabin_finance
systemctl restart sabin_finance

# 9. Configure Nginx Web Server
cp "$PROJECT_DIR/deployment/nginx_sabin_finance.conf" /etc/nginx/sites-available/sabin_finance
ln -sf /etc/nginx/sites-available/sabin_finance /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl restart nginx

# 10. Firewall Configuration (UFW)
if command -v ufw >/dev/null 2>&1; then
    echo "--> Configuring UFW firewall rules for Nginx & SSH..."
    ufw allow 'Nginx Full' || true
    ufw allow OpenSSH || true
    ufw --force enable || true
fi

echo "==========================================================================="
echo " 🎉 SUCCESS: SABIN BALAN FINANCE IS LIVE ON YOUR UBUNTU VPS!"
echo "==========================================================================="
echo " Gunicorn Status: $(systemctl is-active sabin_finance)"
echo " Nginx Status:    $(systemctl is-active nginx)"
echo ""
echo " To attach your custom domain & obtain a free SSL certificate, run:"
echo "   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com"
echo "==========================================================================="
