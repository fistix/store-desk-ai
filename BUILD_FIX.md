# Quick Fix for Docker Build Issues

## Option 1: Use Minimal Requirements (Recommended for now)
```bash
# Use minimal requirements without STT
cp storedesk-ai/requirements.minimal.txt storedesk-ai/requirements.txt

# Build and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## Option 2: Try with setuptools fix
```bash
# Update requirements with setuptools first
echo "setuptools>=65.5.0" >> storedesk-ai/requirements.txt

# Try build again
docker-compose -f docker-compose.prod.yml build storedesk-ai
```

## Option 3: Disable STT temporarily
```bash
# Edit storedesk-ai/main.py and comment out STT import
# Then build without whisper dependencies
```

## Option 4: Use Pre-built Images (Fastest)
```bash
# Skip local build and use working images
docker-compose -f docker-compose.yml up -d
```

## After Build Success

Once the core services are running, you can:
1. Add STT functionality later
2. Test the AI assistant without voice input
3. Gradually add STT back when build issues are resolved

## Current Status
- ✅ All NodeJS services build fine
- ✅ Redis builds fine  
- ✅ Frontend builds fine
- ⚠️ Python AI service has STT dependency issues

The system will work perfectly for text-based AI assistance without STT!
