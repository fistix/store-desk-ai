# Development Workflow

## 🚀 Quick Development Setup

### **Method 1: Local Development (Recommended)**
```bash
# Install dependencies locally
cd storedesk-ai
pip install -r requirements.txt

# Run with hot reloading
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### **Method 2: Docker with Volume Mount**
```bash
# Use dev compose for hot reloading
docker compose -f docker-compose.dev.yml --env-file .env.production up --build

# For subsequent changes (no rebuild needed)
docker compose -f docker-compose.dev.yml restart storedesk-ai
```

## 🔄 Development vs Production

| Feature | Development | Production |
|----------|-------------|-------------|
| **Code Changes** | ✅ Hot reload | ❌ Rebuild required |
| **Package Downloads** | ✅ Once | ✅ Cached |
| **Speed** | ⚡ Instant | 🐢 Slow rebuild |
| **Isolation** | ❌ Local env | ✅ Containerized |

## 📁 File Structure

```
storedesk-ai/
├── docker-compose.prod.yml    # Production (no hot reload)
├── docker-compose.dev.yml    # Development (hot reload)
├── .dockerignore           # Exclude from build context
└── README_DEV.md           # This file
```

## 🛠️ Development Commands

### **Local Development** (Fastest)
```bash
# Install dependencies
pip install -r requirements.txt

# Start with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or with more workers for testing
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --workers 1
```

### **Docker Development** (Medium)
```bash
# First time (builds with cache)
docker compose -f docker-compose.dev.yml --env-file .env.production up --build

# Subsequent changes (no rebuild)
docker compose -f docker-compose.dev.yml restart storedesk-ai

# View logs
docker compose -f docker-compose.dev.yml logs -f storedesk-ai
```

### **Production Build** (Slowest)
```bash
# Only for deployment
docker compose -f docker-compose.prod.yml --env-file .env.production up --build
```

## 🎯 Best Practices

### **For Code Changes**:
1. **Use local development** - fastest iteration
2. **Test locally** before deploying
3. **Use Docker dev** only if environment issues

### **For Testing**:
1. **Local**: Quick feedback loop
2. **Docker dev**: Closer to production
3. **Docker prod**: Final verification

### **Package Management**:
- **Local**: Packages install once, persist
- **Docker dev**: Cache persists in volume
- **Docker prod**: Cache in layers

## 🔧 Environment Setup

### **Required Environment Variables** (.env.production):
```env
# Google Gemini API
GOOGLE_API_KEY=your_gemini_key

# OpenAI API (optional)
OPENAI_API_KEY=your_openai_key

# Redis
REDIS_URL=redis://redis:6379

# Other settings
DEBUG=true
LOG_LEVEL=INFO
```

## 🐛 Troubleshooting

### **Hot Reload Not Working**:
```bash
# Check if running in reload mode
ps aux | grep uvicorn

# Should show: --reload flag
```

### **Docker Volume Issues**:
```bash
# Check volume mount
docker compose -f docker-compose.dev.yml config

# Rebuild if needed
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml up --build
```

### **Package Installation Issues**:
```bash
# Clear pip cache
pip cache purge

# Reinstall locally
pip install -r requirements.txt --force-reinstall
```
