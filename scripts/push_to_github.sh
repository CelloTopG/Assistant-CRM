#!/bin/bash

# WCFCB Assistant CRM - GitHub Repository Setup Script
# Run this script after creating the repository on GitHub

echo "🚀 Setting up WCFCB Assistant CRM repository..."

# Set the correct remote URL (replace with your actual repository URL)
echo "📡 Configuring remote repository..."
git remote set-url origin https://github.com/QuantumSolver/assistant_crm.git

# Verify remote configuration
echo "🔍 Verifying remote configuration..."
git remote -v

# Push to GitHub
echo "📤 Pushing to GitHub..."
git push -u origin main

# Verify the push was successful
if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "🔗 Your documentation is now available at:"
    echo "   https://github.com/QuantumSolver/assistant_crm"
    echo ""
    echo "📚 Share this documentation URL with your supervisor:"
    echo "   https://github.com/QuantumSolver/assistant_crm/tree/main/docs"
    echo ""
    echo "📋 Direct links for quick access:"
    echo "   • Main Documentation: https://github.com/QuantumSolver/assistant_crm/blob/main/docs/README.md"
    echo "   • Installation Guide: https://github.com/QuantumSolver/assistant_crm/blob/main/docs/user-guide/installation.md"
    echo "   • Architecture: https://github.com/QuantumSolver/assistant_crm/blob/main/docs/technical/architecture.md"
    echo "   • API Reference: https://github.com/QuantumSolver/assistant_crm/blob/main/docs/api/chat-api.md"
    echo "   • Production Deployment: https://github.com/QuantumSolver/assistant_crm/blob/main/docs/deployment/production.md"
else
    echo "❌ Push failed. Please check your GitHub authentication."
    echo "💡 You may need to:"
    echo "   1. Set up a Personal Access Token"
    echo "   2. Configure Git credentials"
    echo "   3. Check repository permissions"
fi
