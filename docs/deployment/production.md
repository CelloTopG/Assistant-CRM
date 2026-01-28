# Production Deployment Guide

This guide covers the complete process of deploying WCFCB Assistant CRM to a production environment with enterprise-grade reliability, security, and performance.

## Pre-Deployment Checklist

### Infrastructure Requirements

#### Minimum Production Specifications
- **CPU**: 4 cores (8 cores recommended)
- **RAM**: 16GB (32GB recommended)
- **Storage**: 100GB SSD (500GB recommended)
- **Network**: High-speed internet with low latency to AI services
- **OS**: Ubuntu 20.04 LTS or CentOS 8

#### Recommended Production Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │  Application    │    │    Database     │
│   (Nginx/HAProxy)│    │    Servers      │    │    Cluster     │
│                 │    │  (2+ instances) │    │ (Master/Slave)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  Cache Layer    │
                    │ (Redis Cluster) │
                    └─────────────────┘
```

### Security Requirements

#### SSL/TLS Configuration
- Valid SSL certificate (Let's Encrypt or commercial)
- TLS 1.2+ enforcement
- HSTS headers enabled
- Secure cipher suites only

#### Network Security
- Firewall configuration (UFW/iptables)
- VPN access for administrative tasks
- Database access restricted to application servers
- Regular security updates

#### Data Protection
- Encrypted database storage
- Secure API key management
- Regular automated backups
- GDPR compliance measures

## Deployment Process

### 1. Server Preparation

#### Update System
```bash
# Update package lists and system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git nginx redis-server supervisor
```

#### Create Application User
```bash
# Create frappe user
sudo adduser frappe --disabled-password --gecos ""
sudo usermod -aG sudo frappe

# Switch to frappe user
sudo su - frappe
```

#### Install Dependencies
```bash
# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.10
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3-pip

# Install MariaDB
sudo apt install -y mariadb-server mariadb-client
```

### 2. Database Setup

#### Configure MariaDB
```bash
# Secure MariaDB installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
```

```sql
-- Create database
CREATE DATABASE wcfcb_assistant_crm CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user with proper permissions
CREATE USER 'assistant_crm'@'localhost' IDENTIFIED BY 'secure_password_here';
GRANT ALL PRIVILEGES ON wcfcb_assistant_crm.* TO 'assistant_crm'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Optimize Database Configuration
```bash
# Edit MariaDB configuration
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add these optimizations:
```ini
[mysqld]
# Performance optimizations
innodb_buffer_pool_size = 8G
innodb_log_file_size = 512M
innodb_flush_log_at_trx_commit = 2
query_cache_size = 256M
query_cache_type = 1
max_connections = 200

# Character set
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

### 3. Frappe Bench Installation

#### Install Frappe Bench
```bash
# Install bench
pip3 install frappe-bench

# Initialize bench
bench init --frappe-branch version-14 frappe-bench
cd frappe-bench

# Create new site
bench new-site wcfcb.local --db-name wcfcb_assistant_crm --db-user assistant_crm --db-password secure_password_here
```

#### Install ERPNext (if required)
```bash
# Get ERPNext
bench get-app erpnext --branch version-14

# Install ERPNext on site
bench --site wcfcb.local install-app erpnext
```

### 4. Assistant CRM Installation

#### Get and Install App
```bash
# Get Assistant CRM app
bench get-app https://github.com/your-org/assistant_crm.git

# Install on site
bench --site wcfcb.local install-app assistant_crm

# Run migrations
bench --site wcfcb.local migrate

# Build assets
bench build --app assistant_crm
```

#### Configure Production Settings
```bash
# Enable production mode
bench --site wcfcb.local set-config developer_mode 0
bench --site wcfcb.local set-config server_script_enabled 0
bench --site wcfcb.local set-config disable_website_cache 0

# Configure email
bench --site wcfcb.local set-config mail_server "smtp.gmail.com"
bench --site wcfcb.local set-config mail_port 587
bench --site wcfcb.local set-config use_tls 1
bench --site wcfcb.local set-config mail_login "your-email@wcfcb.com"
bench --site wcfcb.local set-config mail_password "app-password"
```

### 5. Environment Configuration

#### Create Production Environment File
```bash
# Create .env.ai file
nano .env.ai
```

```bash
# AI Configuration
google_gemini_api_key=your_production_gemini_api_key
gemini_model=gemini-1.5-pro

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=wcfcb_assistant_crm
DB_USER=assistant_crm
DB_PASSWORD=secure_password_here

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password_here

# Security
SECRET_KEY=your_very_long_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# External Integrations
MAKE_COM_WEBHOOK_SECRET=your_make_com_secret
COREBUSINESS_API_KEY=your_corebusiness_api_key
COREBUSINESS_API_URL=https://api.corebusiness.wcfcb.com

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
LOG_LEVEL=INFO
```

#### Set File Permissions
```bash
# Secure environment file
chmod 600 .env.ai
chown frappe:frappe .env.ai

# Set proper permissions for app files
find apps/assistant_crm -type f -exec chmod 644 {} \;
find apps/assistant_crm -type d -exec chmod 755 {} \;
```

### 6. Web Server Configuration

#### Configure Nginx
```bash
# Generate nginx configuration
bench setup nginx --yes

# Create custom configuration for Assistant CRM
sudo nano /etc/nginx/sites-available/wcfcb_assistant_crm
```

```nginx
upstream frappe-bench-frappe {
    server 127.0.0.1:8000 fail_timeout=0;
}

upstream frappe-bench-socketio {
    server 127.0.0.1:9000 fail_timeout=0;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=chat:10m rate=60r/m;

server {
    listen 80;
    server_name wcfcb.com www.wcfcb.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name wcfcb.com www.wcfcb.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/wcfcb.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wcfcb.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # Rate limiting for API endpoints
    location /api/method/assistant_crm.api.chat {
        limit_req zone=chat burst=20 nodelay;
        proxy_pass http://frappe-bench-frappe;
        include proxy_params;
    }

    location /api/ {
        limit_req zone=api burst=5 nodelay;
        proxy_pass http://frappe-bench-frappe;
        include proxy_params;
    }

    # WebSocket support
    location /socket.io/ {
        proxy_pass http://frappe-bench-socketio;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # Main application
    location / {
        proxy_pass http://frappe-bench-frappe;
        include proxy_params;
    }

    # File upload size
    client_max_body_size 50M;

    # Logging
    access_log /var/log/nginx/wcfcb_access.log;
    error_log /var/log/nginx/wcfcb_error.log;
}
```

#### Enable Site and Restart Nginx
```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/wcfcb_assistant_crm /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 7. SSL Certificate Setup

#### Install Certbot
```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d wcfcb.com -d www.wcfcb.com

# Set up auto-renewal
sudo crontab -e
```

Add this line for auto-renewal:
```bash
0 12 * * * /usr/bin/certbot renew --quiet
```

### 8. Process Management

#### Configure Supervisor
```bash
# Generate supervisor configuration
bench setup supervisor --yes

# Create custom supervisor configuration
sudo nano /etc/supervisor/conf.d/frappe-bench.conf
```

```ini
[group:frappe-bench-web]
programs=frappe-bench-frappe-web,frappe-bench-node-socketio

[program:frappe-bench-frappe-web]
command=/home/frappe/frappe-bench/env/bin/gunicorn -b 127.0.0.1:8000 -w 4 --max-requests 5000 --max-requests-jitter 500 --preload --timeout 120 frappe.app:application
directory=/home/frappe/frappe-bench
user=frappe
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/frappe/frappe-bench/logs/web.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PYTHONPATH="/home/frappe/frappe-bench/apps"

[program:frappe-bench-node-socketio]
command=node /home/frappe/frappe-bench/apps/frappe/socketio.js
directory=/home/frappe/frappe-bench
user=frappe
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/frappe/frappe-bench/logs/socketio.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10

[group:frappe-bench-workers]
programs=frappe-bench-frappe-schedule,frappe-bench-frappe-default-worker,frappe-bench-frappe-short-worker,frappe-bench-frappe-long-worker

[program:frappe-bench-frappe-schedule]
command=/home/frappe/frappe-bench/env/bin/python -m frappe.utils.scheduler
directory=/home/frappe/frappe-bench
user=frappe
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/frappe/frappe-bench/logs/schedule.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10

[program:frappe-bench-frappe-default-worker]
command=/home/frappe/frappe-bench/env/bin/python -m frappe.utils.worker --queue default
directory=/home/frappe/frappe-bench
user=frappe
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/frappe/frappe-bench/logs/worker.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10

[program:frappe-bench-frappe-short-worker]
command=/home/frappe/frappe-bench/env/bin/python -m frappe.utils.worker --queue short
directory=/home/frappe/frappe-bench
user=frappe
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/frappe/frappe-bench/logs/worker.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10

[program:frappe-bench-frappe-long-worker]
command=/home/frappe/frappe-bench/env/bin/python -m frappe.utils.worker --queue long
directory=/home/frappe/frappe-bench
user=frappe
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/frappe/frappe-bench/logs/worker.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
```

#### Start Services
```bash
# Reload supervisor configuration
sudo supervisorctl reread
sudo supervisorctl update

# Start all services
sudo supervisorctl start frappe-bench-web:*
sudo supervisorctl start frappe-bench-workers:*

# Check status
sudo supervisorctl status
```

## Post-Deployment Configuration

### 1. System Verification

#### Run Health Checks
```bash
# Test database connectivity
bench --site wcfcb.local execute assistant_crm.utils.health_check.test_database

# Test AI service connectivity
bench --site wcfcb.local execute assistant_crm.utils.health_check.test_ai_service

# Test cache connectivity
bench --site wcfcb.local execute assistant_crm.utils.health_check.test_cache

# Run comprehensive system test
bench --site wcfcb.local execute assistant_crm.comprehensive_test.run_production_tests
```

#### Performance Testing
```bash
# Test response times
curl -w "@curl-format.txt" -o /dev/null -s "https://wcfcb.com/api/method/assistant_crm.api.chat.get_chat_status"

# Load testing with Apache Bench
ab -n 1000 -c 10 https://wcfcb.com/api/method/assistant_crm.api.chat.get_chat_status
```

### 2. Monitoring Setup

#### Configure Log Rotation
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/frappe-bench
```

```
/home/frappe/frappe-bench/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 frappe frappe
    postrotate
        supervisorctl restart frappe-bench-web:*
    endscript
}
```

#### Set Up Monitoring
```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Configure system monitoring
bench --site wcfcb.local execute assistant_crm.monitoring.setup_production_monitoring
```

### 3. Backup Configuration

#### Automated Backups
```bash
# Create backup script
nano /home/frappe/backup_script.sh
```

```bash
#!/bin/bash
SITE="wcfcb.local"
BACKUP_DIR="/home/frappe/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
bench --site $SITE backup --with-files

# Copy to backup directory
cp sites/$SITE/private/backups/* $BACKUP_DIR/

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar" -mtime +30 -delete

# Upload to cloud storage (optional)
# aws s3 sync $BACKUP_DIR s3://wcfcb-backups/
```

```bash
# Make script executable
chmod +x /home/frappe/backup_script.sh

# Add to crontab
crontab -e
```

Add this line for daily backups at 2 AM:
```bash
0 2 * * * /home/frappe/backup_script.sh
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. Fail2Ban Setup

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Configure fail2ban for nginx
sudo nano /etc/fail2ban/jail.local
```

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/*error.log
findtime = 600
bantime = 7200
maxretry = 10
```

### 3. System Updates

```bash
# Enable automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Maintenance Procedures

### 1. Regular Maintenance Tasks

#### Weekly Tasks
- Review system logs
- Check disk space usage
- Verify backup integrity
- Update security patches

#### Monthly Tasks
- Performance analysis
- Database optimization
- Security audit
- Capacity planning review

### 2. Update Procedures

#### Application Updates
```bash
# Update Assistant CRM app
cd /home/frappe/frappe-bench
bench get-app assistant_crm --branch main
bench --site wcfcb.local migrate
bench build --app assistant_crm
sudo supervisorctl restart frappe-bench-web:*
```

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python packages
pip3 install --upgrade frappe-bench

# Restart services
sudo systemctl restart nginx
sudo supervisorctl restart all
```

## Troubleshooting

### Common Issues

#### High Memory Usage
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Restart workers if needed
sudo supervisorctl restart frappe-bench-workers:*
```

#### Database Performance Issues
```bash
# Check slow queries
sudo mysql -u root -p -e "SHOW PROCESSLIST;"

# Optimize tables
bench --site wcfcb.local execute assistant_crm.utils.database_maintenance.optimize_tables
```

#### SSL Certificate Issues
```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew --force-renewal
```

---

**Next**: [Environment Configuration](environment.md) | [Monitoring & Maintenance](monitoring.md)
