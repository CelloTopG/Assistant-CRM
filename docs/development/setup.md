# Development Setup Guide

This guide provides comprehensive instructions for setting up a local development environment for WCFCB Assistant CRM.

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04+, macOS 10.15+, or Windows 10+ (with WSL2)
- **Python**: 3.8 to 3.11 (3.10 recommended)
- **Node.js**: 16.x or 18.x
- **Git**: Latest version
- **Database**: MariaDB 10.6+ or PostgreSQL 13+

### Development Tools
- **Code Editor**: VS Code (recommended) with Python and JavaScript extensions
- **Terminal**: Bash or Zsh
- **API Testing**: Postman or Insomnia
- **Database Client**: DBeaver or phpMyAdmin

## Environment Setup

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
# Update package lists
sudo apt update

# Install Python and development tools
sudo apt install -y python3.10 python3.10-dev python3.10-venv python3-pip
sudo apt install -y git curl wget build-essential

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install MariaDB
sudo apt install -y mariadb-server mariadb-client

# Install Redis
sudo apt install -y redis-server
```

#### macOS
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.10 node@18 mariadb redis git

# Start services
brew services start mariadb
brew services start redis
```

#### Windows (WSL2)
```bash
# Install WSL2 and Ubuntu 20.04 from Microsoft Store
# Then follow Ubuntu instructions above
```

### 2. Configure Database

#### MariaDB Setup
```bash
# Secure MariaDB installation
sudo mysql_secure_installation

# Create development database
sudo mysql -u root -p
```

```sql
-- Create database
CREATE DATABASE assistant_crm_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER 'assistant_crm_dev'@'localhost' IDENTIFIED BY 'dev_password';
GRANT ALL PRIVILEGES ON assistant_crm_dev.* TO 'assistant_crm_dev'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Install Frappe Bench

#### Install Bench CLI
```bash
# Install bench
pip3 install frappe-bench

# Verify installation
bench --version
```

#### Initialize Bench
```bash
# Create bench directory
bench init --frappe-branch version-14 frappe-bench-dev
cd frappe-bench-dev

# Create development site
bench new-site assistant-crm.local --db-name assistant_crm_dev --db-user assistant_crm_dev --db-password dev_password

# Set as default site
bench use assistant-crm.local
```

## Assistant CRM Development Setup

### 1. Clone and Install App

#### Clone Repository
```bash
# Clone from your fork or main repository
git clone https://github.com/your-username/assistant_crm.git apps/assistant_crm

# Or get app using bench
bench get-app https://github.com/your-username/assistant_crm.git
```

#### Install App
```bash
# Install app on site
bench --site assistant-crm.local install-app assistant_crm

# Run migrations
bench --site assistant-crm.local migrate

# Build assets
bench build --app assistant_crm
```

### 2. Development Configuration

#### Create Development Environment File
```bash
# Create .env.ai file in bench root
nano .env.ai
```

```bash
# Development Environment Configuration
# AI Configuration
google_gemini_api_key=your_development_gemini_api_key
gemini_model=gemini-1.5-pro

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=assistant_crm_dev
DB_USER=assistant_crm_dev
DB_PASSWORD=dev_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Development Settings
DEBUG=true
LOG_LEVEL=DEBUG
DEVELOPMENT_MODE=true

# External Services (Development)
NGROK_SUBDOMAIN=your-ngrok-subdomain

# Test Data
USE_TEST_DATA=true
MOCK_EXTERNAL_APIS=true
```

#### Configure Development Settings
```bash
# Enable developer mode
bench --site assistant-crm.local set-config developer_mode 1
bench --site assistant-crm.local set-config server_script_enabled 1

# Enable debug mode
bench --site assistant-crm.local set-config debug 1

# Set up email for development (optional)
bench --site assistant-crm.local set-config mail_server "localhost"
bench --site assistant-crm.local set-config mail_port 1025
```

### 3. Install Development Dependencies

#### Python Development Packages
```bash
# Install development requirements
pip3 install -r apps/assistant_crm/requirements-dev.txt

# Install testing frameworks
pip3 install pytest pytest-cov black flake8 mypy
```

#### Node.js Development Packages
```bash
# Install frontend development tools
npm install -g eslint prettier @vue/cli

# Install app-specific packages
cd apps/assistant_crm
npm install
```

## Development Workflow

### 1. Start Development Server

#### Start Bench
```bash
# Start development server
bench start

# Or start individual services
bench serve --port 8000  # Web server
bench worker --queue default  # Background worker
bench schedule  # Scheduler
```

#### Access Development Site
- **Web Interface**: http://assistant-crm.local:8000
- **Admin Interface**: http://assistant-crm.local:8000/app
- **API Endpoints**: http://assistant-crm.local:8000/api/method/

### 2. Development Tools Setup

#### VS Code Configuration
Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreter": "./env/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "files.associations": {
    "*.py": "python",
    "*.js": "javascript",
    "*.json": "json"
  },
  "emmet.includeLanguages": {
    "jinja-html": "html"
  }
}
```

#### Git Hooks Setup
```bash
# Install pre-commit hooks
pip3 install pre-commit
cd apps/assistant_crm
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.15.0
    hooks:
      - id: eslint
        files: \.(js|jsx|ts|tsx)$
```

### 3. Testing Setup

#### Unit Testing
```bash
# Run Python tests
cd apps/assistant_crm
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=assistant_crm --cov-report=html
```

#### Integration Testing
```bash
# Run Frappe tests
bench --site assistant-crm.local run-tests --app assistant_crm

# Run specific test
bench --site assistant-crm.local run-tests --app assistant_crm --module assistant_crm.tests.test_chat_api
```

#### API Testing
```bash
# Test chat API
curl -X POST http://assistant-crm.local:8000/api/method/assistant_crm.api.chat.send_message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Anna!"}'

# Test system status
curl http://assistant-crm.local:8000/api/method/assistant_crm.api.chat.get_chat_status
```

## Development Best Practices

### 1. Code Organization

#### Directory Structure
```
apps/assistant_crm/
├── assistant_crm/
│   ├── api/                 # API endpoints
│   ├── services/            # Business logic services
│   ├── doctype/            # Frappe DocTypes
│   ├── public/             # Frontend assets
│   │   ├── js/             # JavaScript files
│   │   └── css/            # CSS files
│   ├── templates/          # Jinja templates
│   ├── tests/              # Test files
│   └── utils/              # Utility functions
├── docs/                   # Documentation
├── requirements.txt        # Python dependencies
└── package.json           # Node.js dependencies
```

#### Naming Conventions
- **Python Files**: `snake_case.py`
- **JavaScript Files**: `camelCase.js`
- **CSS Classes**: `kebab-case`
- **DocTypes**: `Title Case`
- **API Methods**: `snake_case`

### 2. Development Guidelines

#### Python Code Style
```python
# Use type hints
def send_message(message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Send a message to the AI assistant.
    
    Args:
        message: User's message content
        session_id: Optional session identifier
        
    Returns:
        Dictionary containing AI response and metadata
    """
    pass

# Use docstrings for all functions
# Follow PEP 8 style guide
# Use Black for code formatting
```

#### JavaScript Code Style
```javascript
// Use ES6+ features
const sendMessage = async (message, sessionId = null) => {
  try {
    const response = await fetch('/api/method/assistant_crm.api.chat.send_message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    
    return await response.json();
  } catch (error) {
    console.error('Error sending message:', error);
    throw error;
  }
};

// Use JSDoc for documentation
// Follow Airbnb JavaScript style guide
```

### 3. Debugging

#### Python Debugging
```python
# Use frappe.log_error for error logging
import frappe

try:
    # Your code here
    pass
except Exception as e:
    frappe.log_error(f"Error in function: {e}", "Assistant CRM Debug")
    raise

# Use pdb for interactive debugging
import pdb; pdb.set_trace()
```

#### JavaScript Debugging
```javascript
// Use console methods for debugging
console.log('Debug info:', data);
console.error('Error occurred:', error);
console.table(arrayData);

// Use browser developer tools
debugger; // Breakpoint for browser debugging
```

#### Log Files
Monitor these log files during development:
```bash
# Frappe logs
tail -f logs/frappe.log

# Error logs
tail -f logs/error.log

# Custom app logs
tail -f logs/assistant_crm.log
```

## Testing and Quality Assurance

### 1. Automated Testing

#### Test Structure
```python
# tests/test_chat_api.py
import unittest
import frappe
from assistant_crm.api.chat import send_message

class TestChatAPI(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        self.test_message = "Hello Anna!"
        
    def test_send_message_success(self):
        """Test successful message sending."""
        response = send_message(self.test_message)
        self.assertTrue(response.get('success'))
        self.assertIn('response', response.get('data', {}))
        
    def test_send_message_empty(self):
        """Test sending empty message."""
        with self.assertRaises(frappe.ValidationError):
            send_message("")
            
    def tearDown(self):
        """Clean up after tests."""
        pass
```

#### Run Tests
```bash
# Run all tests
bench --site assistant-crm.local run-tests --app assistant_crm

# Run specific test file
bench --site assistant-crm.local run-tests --app assistant_crm --module tests.test_chat_api

# Run with coverage
bench --site assistant-crm.local run-tests --app assistant_crm --coverage
```

### 2. Code Quality Tools

#### Linting and Formatting
```bash
# Python linting
flake8 apps/assistant_crm/assistant_crm/

# Python formatting
black apps/assistant_crm/assistant_crm/

# JavaScript linting
eslint apps/assistant_crm/assistant_crm/public/js/

# JavaScript formatting
prettier --write apps/assistant_crm/assistant_crm/public/js/
```

#### Type Checking
```bash
# Python type checking
mypy apps/assistant_crm/assistant_crm/
```

## Deployment to Development Server

### 1. Ngrok Setup for Webhooks

#### Install Ngrok
```bash
# Install ngrok
npm install -g ngrok

# Or download from https://ngrok.com/download
```

#### Configure Ngrok
```bash
# Start ngrok tunnel
ngrok http 8000 --subdomain=your-subdomain

# Update webhook URLs in development
# WhatsApp: https://your-subdomain.ngrok.io/api/omnichannel/webhook/whatsapp
# Telegram: https://your-subdomain.ngrok.io/api/omnichannel/webhook/telegram
```

### 2. Development Deployment

#### Build and Deploy
```bash
# Build assets
bench build --app assistant_crm

# Clear cache
bench --site assistant-crm.local clear-cache

# Restart services
bench restart

# Update database
bench --site assistant-crm.local migrate
```

## Contributing Guidelines

### 1. Git Workflow

#### Branch Naming
- **Feature**: `feature/description-of-feature`
- **Bug Fix**: `bugfix/description-of-bug`
- **Hotfix**: `hotfix/critical-fix`
- **Documentation**: `docs/update-documentation`

#### Commit Messages
```
feat: add real-time typing indicators to chat interface

- Implement WebSocket connection for typing events
- Add typing indicator UI component
- Update chat service to handle typing events
- Add tests for typing functionality

Closes #123
```

### 2. Pull Request Process

#### Before Submitting PR
1. Run all tests and ensure they pass
2. Run linting and fix any issues
3. Update documentation if needed
4. Add tests for new functionality
5. Ensure code coverage doesn't decrease

#### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## Troubleshooting Development Issues

### Common Issues

#### 1. Import Errors
```bash
# Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Restart bench
bench restart
```

#### 2. Asset Build Errors
```bash
# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Rebuild assets
bench build --app assistant_crm --force
```

#### 3. Database Issues
```bash
# Reset database
bench --site assistant-crm.local reinstall

# Or restore from backup
bench --site assistant-crm.local restore backup_file.sql.gz
```

### Getting Help

1. Check the [Troubleshooting Guide](../user-guide/troubleshooting.md)
2. Review Frappe documentation: https://frappeframework.com/docs
3. Join the community: https://discuss.frappe.io/
4. Create an issue on GitHub with detailed error information

---

**Next**: [Contributing Guidelines](contributing.md) | [Testing Guide](testing.md)
