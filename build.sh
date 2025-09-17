#!/bin/bash
# Render.com Build Script
# Ce script est exécuté automatiquement par Render lors du déploiement

echo "🚀 Starting Render.com build process..."
echo "Installing Python dependencies..."

# Installation des dépendances
pip install -r requirements.txt

echo "✅ Build completed successfully!"
echo "🤖 Discord Bot ready for deployment!"
