#!/bin/bash

# AIDE ML Enterprise Setup Script

set -e

echo "🚀 Setting up AIDE ML Enterprise..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys!"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs uploads workspaces

# Backend setup
echo "🔧 Setting up backend..."
pip install -e .
pip install -r backend/requirements.txt

# Initialize database
echo "💾 Initializing database..."
python -c "import asyncio; from backend.database import init_db; asyncio.run(init_db())"

# Frontend setup
echo "🎨 Setting up frontend..."
cd frontend

if [ ! -d node_modules ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

if [ ! -f .env ]; then
    echo "📝 Creating frontend .env file..."
    cp .env.example .env
fi

cd ..

echo "✅ Setup complete!"
echo ""
echo "To start the application:"
echo "  Backend:  cd backend && uvicorn main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo ""
echo "Or use Docker Compose:"
echo "  docker-compose up --build"
