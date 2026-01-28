#!/bin/bash

# WCFCB Assistant CRM - Omnichannel Integration Deployment Script
# Automated deployment and configuration for omnichannel platforms

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BENCH_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
APP_NAME="assistant_crm"
SITE_NAME="${1:-localhost}"
ENVIRONMENT="${2:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check if running as correct user
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root"
        exit 1
    fi
    
    # Check if bench directory exists
    if [[ ! -d "$BENCH_DIR" ]]; then
        error "Bench directory not found: $BENCH_DIR"
        exit 1
    fi
    
    # Check if site exists
    if [[ ! -d "$BENCH_DIR/sites/$SITE_NAME" ]]; then
        error "Site not found: $SITE_NAME"
        exit 1
    fi
    
    # Check required commands
    local required_commands=("curl" "openssl" "python3" "node" "npm")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    success "Prerequisites check passed"
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."
    
    # Update package list
    sudo apt update
    
    # Install required packages
    sudo apt install -y \
        python3-dev \
        python3-pip \
        nodejs \
        npm \
        redis-server \
        nginx \
        certbot \
        python3-certbot-nginx \
        htop \
        curl \
        wget \
        git
    
    success "System dependencies installed"
}

# Install Python packages
install_python_packages() {
    log "Installing Python packages..."
    
    cd "$BENCH_DIR"
    
    # Install required Python packages
    ./env/bin/pip install --upgrade pip
    ./env/bin/pip install \
        requests>=2.28.0 \
        python-telegram-bot>=20.0 \
        facebook-sdk>=3.1.0 \
        twilio>=8.0.0 \
        boto3>=1.26.0 \
        vonage>=3.0.0 \
        websockets>=11.0 \
        aiohttp>=3.8.0 \
        cryptography>=3.4.8 \
        pyjwt>=2.6.0 \
        psutil>=5.9.0
    
    success "Python packages installed"
}

# Setup SSL certificate
setup_ssl() {
    log "Setting up SSL certificate..."
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Check if certificate already exists
        if [[ -f "/etc/letsencrypt/live/$SITE_NAME/fullchain.pem" ]]; then
            warning "SSL certificate already exists for $SITE_NAME"
            return 0
        fi
        
        # Get SSL certificate from Let's Encrypt
        sudo certbot --nginx -d "$SITE_NAME" --non-interactive --agree-tos --email "admin@$SITE_NAME"
        
        if [[ $? -eq 0 ]]; then
            success "SSL certificate obtained for $SITE_NAME"
        else
            error "Failed to obtain SSL certificate"
            exit 1
        fi
    else
        warning "Skipping SSL setup for $ENVIRONMENT environment"
    fi
}

# Configure Nginx
configure_nginx() {
    log "Configuring Nginx..."
    
    # Create Nginx configuration
    cat > "/tmp/nginx_$SITE_NAME.conf" << EOF
upstream frappe_server {
    server 127.0.0.1:8000 fail_timeout=0;
}

upstream socketio_server {
    server 127.0.0.1:9000 fail_timeout=0;
}

server {
    listen 80;
    server_name $SITE_NAME;
    
    # Redirect HTTP to HTTPS in production
    if (\$scheme = http) {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $SITE_NAME;
    
    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$SITE_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$SITE_NAME/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Increase client max body size for file uploads
    client_max_body_size 100M;
    
    # Webhook endpoints with increased timeout
    location /api/omnichannel/webhook/ {
        proxy_pass http://frappe_server;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    # Socket.IO
    location /socket.io/ {
        proxy_pass http://socketio_server;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Main application
    location / {
        proxy_pass http://frappe_server;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Static files
    location /assets/ {
        alias $BENCH_DIR/sites/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Install Nginx configuration
    sudo mv "/tmp/nginx_$SITE_NAME.conf" "/etc/nginx/sites-available/$SITE_NAME"
    sudo ln -sf "/etc/nginx/sites-available/$SITE_NAME" "/etc/nginx/sites-enabled/$SITE_NAME"
    
    # Test Nginx configuration
    sudo nginx -t
    if [[ $? -eq 0 ]]; then
        sudo systemctl reload nginx
        success "Nginx configured successfully"
    else
        error "Nginx configuration test failed"
        exit 1
    fi
}

# Update Frappe app
update_app() {
    log "Updating Assistant CRM app..."
    
    cd "$BENCH_DIR"
    
    # Pull latest changes
    bench get-app --branch main https://github.com/your-repo/assistant_crm.git || true
    
    # Install/update the app
    bench --site "$SITE_NAME" install-app assistant_crm || bench --site "$SITE_NAME" migrate
    
    # Build assets
    bench build --app assistant_crm
    
    success "App updated successfully"
}

# Configure environment variables
setup_environment() {
    log "Setting up environment configuration..."
    
    # Create environment file
    cat > "$BENCH_DIR/.env" << EOF
# Environment Configuration
FRAPPE_ENV=$ENVIRONMENT
SITE_NAME=$SITE_NAME

# Assistant CRM Configuration
ASSISTANT_CRM_ENCRYPTION_KEY=$(openssl rand -base64 32)

# Webhook Configuration
WEBHOOK_BASE_URL=https://$SITE_NAME
WEBHOOK_TIMEOUT=30
MAX_RETRY_ATTEMPTS=3
RATE_LIMIT_PER_MINUTE=100

# Logging Configuration
LOG_LEVEL=INFO
DEBUG_MODE=false

# Security Configuration
SSL_VERIFY=true
WEBHOOK_RETRY_ENABLED=true
EOF

    # Secure the environment file
    chmod 600 "$BENCH_DIR/.env"
    
    success "Environment configuration created"
}

# Setup monitoring
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring script
    cat > "$BENCH_DIR/monitor_omnichannel.py" << 'EOF'
#!/usr/bin/env python3
"""
WCFCB Assistant CRM - Omnichannel Monitoring Script
"""

import frappe
import requests
import time
import json
from datetime import datetime

def check_webhook_endpoints():
    """Check if webhook endpoints are responding"""
    endpoints = [
        "/api/omnichannel/webhook/whatsapp",
        "/api/omnichannel/webhook/facebook", 
        "/api/omnichannel/webhook/telegram"
    ]
    
    base_url = "https://localhost"  # Replace with actual domain
    results = {}
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            results[endpoint] = {
                "status": "UP" if response.status_code in [200, 405] else "DOWN",
                "response_time": response.elapsed.total_seconds(),
                "status_code": response.status_code
            }
        except Exception as e:
            results[endpoint] = {
                "status": "DOWN",
                "error": str(e)
            }
    
    return results

def check_database_health():
    """Check database connectivity and performance"""
    try:
        start_time = time.time()
        frappe.db.sql("SELECT 1")
        response_time = time.time() - start_time
        
        return {
            "status": "UP",
            "response_time": response_time
        }
    except Exception as e:
        return {
            "status": "DOWN", 
            "error": str(e)
        }

def main():
    frappe.init()
    frappe.connect()
    
    # Run health checks
    webhook_status = check_webhook_endpoints()
    db_status = check_database_health()
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "webhooks": webhook_status,
        "database": db_status
    }
    
    print(json.dumps(report, indent=2))
    
    # Log to file
    with open("/tmp/omnichannel_health.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    main()
EOF

    chmod +x "$BENCH_DIR/monitor_omnichannel.py"
    
    # Create systemd service for monitoring
    cat > "/tmp/omnichannel-monitor.service" << EOF
[Unit]
Description=WCFCB Omnichannel Health Monitor
After=network.target

[Service]
Type=oneshot
User=$(whoami)
WorkingDirectory=$BENCH_DIR
ExecStart=$BENCH_DIR/env/bin/python $BENCH_DIR/monitor_omnichannel.py
EOF

    sudo mv "/tmp/omnichannel-monitor.service" "/etc/systemd/system/"
    
    # Create timer for regular monitoring
    cat > "/tmp/omnichannel-monitor.timer" << EOF
[Unit]
Description=Run Omnichannel Health Monitor every 5 minutes
Requires=omnichannel-monitor.service

[Timer]
OnCalendar=*:0/5
Persistent=true

[Install]
WantedBy=timers.target
EOF

    sudo mv "/tmp/omnichannel-monitor.timer" "/etc/systemd/system/"
    
    # Enable and start monitoring
    sudo systemctl daemon-reload
    sudo systemctl enable omnichannel-monitor.timer
    sudo systemctl start omnichannel-monitor.timer
    
    success "Monitoring setup completed"
}

# Run tests
run_tests() {
    log "Running integration tests..."
    
    cd "$BENCH_DIR"
    
    # Run the test suite
    bench --site "$SITE_NAME" run-tests assistant_crm.tests.test_omnichannel_integration --verbose
    
    if [[ $? -eq 0 ]]; then
        success "All tests passed"
    else
        warning "Some tests failed - check logs for details"
    fi
}

# Restart services
restart_services() {
    log "Restarting services..."
    
    cd "$BENCH_DIR"
    
    # Restart Frappe services
    bench restart
    
    # Restart Nginx
    sudo systemctl restart nginx
    
    # Restart Redis
    sudo systemctl restart redis-server
    
    success "Services restarted"
}

# Main deployment function
main() {
    log "Starting WCFCB Assistant CRM Omnichannel Deployment"
    log "Site: $SITE_NAME"
    log "Environment: $ENVIRONMENT"
    
    check_prerequisites
    install_dependencies
    install_python_packages
    setup_ssl
    configure_nginx
    update_app
    setup_environment
    setup_monitoring
    restart_services
    run_tests
    
    success "Deployment completed successfully!"
    
    log "Next steps:"
    log "1. Configure channel credentials in Assistant CRM Settings"
    log "2. Test webhook endpoints with your channel providers"
    log "3. Monitor logs at /tmp/omnichannel_health.json"
    log "4. Access the application at https://$SITE_NAME"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "test")
        run_tests
        ;;
    "monitor")
        cd "$BENCH_DIR"
        python3 monitor_omnichannel.py
        ;;
    "restart")
        restart_services
        ;;
    *)
        echo "Usage: $0 [deploy|test|monitor|restart] [site_name] [environment]"
        echo "  deploy   - Full deployment (default)"
        echo "  test     - Run integration tests only"
        echo "  monitor  - Run health check"
        echo "  restart  - Restart services"
        exit 1
        ;;
esac
