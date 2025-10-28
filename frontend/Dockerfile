FROM node:18-alpine

WORKDIR /app

# Copy lockfile too (if present) for reproducible installs
COPY package*.json ./

# Be tolerant to older peer deps like react-meta-tags@1.0.1 needing React 16
RUN if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --legacy-peer-deps ; \
    else \
      npm install --legacy-peer-deps ; \
    fi

# Now copy the rest and build
COPY . ./
RUN npm run build