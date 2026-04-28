FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Create .env file if it doesn't exist
RUN if [ ! -f .env ]; then echo "PORT=4010" > .env; fi

EXPOSE 4010

# Use nodemon for development hot reloading
RUN npm install -g nodemon

CMD ["nodemon", "app.js"]
