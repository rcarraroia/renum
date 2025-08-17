# Renum - Multi-Agent Orchestration Platform

A modern platform for orchestrating teams of specialized AI agents, built with FastAPI backend and React frontend.

## 🏗️ Architecture

- **Backend**: FastAPI with Clean Architecture (Python 3.11+)
- **Frontend**: React 18 + TypeScript + Vite
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **Real-time**: WebSocket connections
- **Deployment**: Docker containers

## 📁 Project Structure

```
renum/
├── apps/api/                 # FastAPI Backend
│   ├── app/                  # Application code
│   │   ├── api/v1/          # API endpoints
│   │   ├── domain/          # Domain models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── infra/           # Infrastructure
│   ├── migrations/          # Database migrations
│   └── tests/               # Backend tests
├── src/                     # React Frontend
│   ├── components/          # React components
│   ├── pages/               # Page components
│   ├── hooks/               # Custom hooks
│   └── lib/                 # Utilities
├── docs/                    # Documentation
├── .kiro/specs/            # Feature specifications
└── .github/workflows/      # CI/CD pipelines
```

## 🚀 Quick Start

### Backend Setup

1. **Navigate to API directory**:
   ```bash
   cd apps/api
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Set up environment**:
   ```bash
   cp .env.production.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Run database migrations**:
   ```bash
   cd migrations
   python run_migrations.py
   ```

5. **Start the server**:
   ```bash
   python start_server.py
   ```

### Frontend Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Start development server**:
   ```bash
   npm run dev
   ```

## 🗄️ Database Migrations

The project uses a custom migration system for Supabase:

```bash
cd apps/api/migrations
python run_migrations.py
```

### Migration Files:
- `001_multi_agent_system_schema.sql` - Core database schema
- `002_rls_policies.sql` - Row Level Security policies
- `003_triggers_and_functions.sql` - Database triggers and functions
- `004_initial_data.sql` - Initial system data

## 🔧 Development

### Backend Development

The backend follows Clean Architecture principles:

- **Domain Layer**: Business entities and rules
- **Use Cases Layer**: Application business logic
- **Infrastructure Layer**: External concerns (database, APIs)
- **Interface Layer**: Controllers and presenters

### Frontend Development

Built with modern React patterns:

- **Components**: Reusable UI components with shadcn/ui
- **Hooks**: Custom hooks for state management
- **Services**: API communication layer
- **Types**: TypeScript definitions

## 🧪 Testing

### Backend Tests
```bash
cd apps/api
pytest
```

### Frontend Tests
```bash
npm test
```

## 📦 Deployment

### Production Deployment

1. **Build Docker images**:
   ```bash
   docker-compose -f docker-compose.production.yml build
   ```

2. **Deploy**:
   ```bash
   ./deploy-production.sh
   ```

### Environment Variables

Required environment variables:

```env
# Supabase
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📚 Documentation

- [Backend API Documentation](apps/api/README.md)
- [Database Schema](apps/api/migrations/README.md)
- [Feature Specifications](.kiro/specs/)

## 🔗 Links

- **Lovable Project**: https://lovable.dev/projects/0feda7ea-0168-4ffc-94ca-1bd5c008937b
- **Repository**: This repository
- **Documentation**: [docs/](docs/)

## 📄 License

This project is licensed under the MIT License.