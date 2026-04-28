#!/bin/bash

echo "Generating package-lock.json files..."

# Generate for backend
cd backend
npm install
cd ..

# Generate for frontend  
cd frontend
npm install
cd ..

echo "Package-lock.json files generated successfully!"
