# AIDE ML - Enterprise Edition

> **The Machine Learning Engineering Agent - Refactored for Production**

A fully refactored, enterprise-ready version of AIDE ML with modern architecture, featuring a React + TypeScript frontend and FastAPI backend.

## 🚀 What's New in 2.0

### Architecture Improvements
- **Frontend**: Modern React + TypeScript with Tailwind CSS
- **Backend**: FastAPI with async/await support
- **Real-time Updates**: WebSocket integration for live experiment monitoring
- **Database**: SQLAlchemy with SQLite for persistent experiment history
- **Containerization**: Docker and Docker Compose for easy deployment

### Key Features
- 🎨 **Modern UI**: Clean, professional interface with real-time progress tracking
- 📊 **Interactive Visualizations**: Charts and graphs for experiment metrics
- 💾 **Persistent Storage**: All experiments and results saved to database
- 🔄 **Real-time Updates**: Live status updates via WebSocket
- 📁 **File Management**: Easy upload and management of datasets
- 🐳 **Docker Ready**: One-command deployment with Docker Compose
- 📈 **Metrics Dashboard**: Comprehensive experiment monitoring and analysis

## 📋 Prerequisites

- Python 3.10+
- Node.js 18+
- Docker and Docker Compose (optional, for containerized deployment)

## 🛠️ Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd aideml
   cp .env.example .env
   # Edit .env and add your API keys
   ```

2. **Build and Run**
   ```bash
   docker-compose up --build
   ```

3. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Option 2: Local Development

#### Backend Setup

1. **Install Dependencies**
   ```bash
   # Install AIDE ML
   pip install -e .
   
   # Install backend dependencies
   pip install -r backend/requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

3. **Run Backend**
   ```bash
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit if needed (defaults should work for local development)
   ```

3. **Run Frontend**
   ```bash
   npm run dev
   ```

4. **Access the Application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000

## 📖 Usage Guide

### Creating an Experiment

1. **Navigate to Dashboard**
   - Open http://localhost:3000 in your browser

2. **Create New Experiment**
   - Click "New Experiment" button
   - Fill in experiment details:
     - Name: Descriptive name for your experiment
     - Goal: What you want the model to achieve
     - Evaluation Metric: How to measure performance (e.g., RMSE, Accuracy)
     - Number of Steps: Improvement iterations (1-100)
     - LLM Model: Choose your preferred model

3. **Upload Dataset**
   - Upload CSV, TXT, JSON, or MD files
   - Multiple files can be uploaded

4. **Run Experiment**
   - Click "Create & Run Experiment"
   - Monitor progress in real-time
   - View live logs and metrics

### Monitoring Experiments

- **Dashboard**: Overview of all experiments with status indicators
- **Real-time Progress**: Live progress bars and step tracking
- **Metrics Visualization**: Interactive charts showing performance over time
- **Code Review**: View and download generated solution code
- **Logs**: Real-time execution logs via WebSocket

## 🏗️ Architecture

### Backend (FastAPI)
```
backend/
├── api/              # API endpoints
│   └── experiments.py
├── core/             # Core configuration
│   └── config.py
├── database/         # Database setup
│   └── base.py
├── models/           # SQLAlchemy models
│   └── experiment.py
├── schemas/          # Pydantic schemas
│   └── experiment.py
├── services/         # Business logic
│   └── experiment_service.py
└── main.py          # Application entry point
```

### Frontend (React + TypeScript)
```
frontend/
├── src/
│   ├── components/   # Reusable UI components
│   │   └── ui/      # Base UI components
│   ├── pages/       # Page components
│   │   ├── Dashboard.tsx
│   │   ├── NewExperiment.tsx
│   │   └── ExperimentDetail.tsx
│   ├── services/    # API clients
│   │   ├── api.ts
│   │   └── websocket.ts
│   ├── types/       # TypeScript types
│   └── utils/       # Utility functions
└── index.html       # HTML template
```

## 🔧 Configuration

### Environment Variables

#### Backend (.env)
```env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite+aiosqlite:///./aide.db
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

#### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000
```

## 🐳 Docker Deployment

### Production Deployment

1. **Build Images**
   ```bash
   docker-compose build
   ```

2. **Run Services**
   ```bash
   docker-compose up -d
   ```

3. **View Logs**
   ```bash
   docker-compose logs -f
   ```

4. **Stop Services**
   ```bash
   docker-compose down
   ```

## 🔒 Security Considerations

- Set strong `SECRET_KEY` in production
- Use HTTPS in production environments
- Implement authentication for multi-user scenarios
- Regularly update dependencies
- Review and restrict CORS origins

## 📊 API Documentation

Access interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

- `POST /api/v1/experiments/` - Create experiment
- `GET /api/v1/experiments/` - List experiments
- `GET /api/v1/experiments/{id}` - Get experiment details
- `POST /api/v1/experiments/{id}/upload` - Upload files
- `POST /api/v1/experiments/{id}/run` - Run experiment
- `WS /api/v1/experiments/ws/{id}` - WebSocket for real-time updates

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Original AIDE ML algorithm and research team
- FastAPI and React communities
- All contributors and users

## 📧 Support

For questions and support:
- GitHub Issues: [Create an issue](https://github.com/WecoAI/aideml/issues)
- Documentation: [Read the docs](https://docs.weco.ai)

---

**Built with ❤️ by the AIDE ML Team**
