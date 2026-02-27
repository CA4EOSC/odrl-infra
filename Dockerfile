# Stage 1: Build Frontend
FROM node:20-alpine as frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

# Stage 2: Backend & Runtime
FROM ruby:3.2-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential libsodium-dev libssl-dev zlib1g-dev pkg-config git jq bash curl python3 python3-pip openssh-client && \
    rm -rf /var/lib/apt/lists/* && \
    gem install httparty ed25519 multibases multihashes multicodecs optparse rbnacl simple_dag uri 'json-canonicalization:1.0.0' 'securerandom:0.1.1' && \
    gem update

# Copy and install local OYDID gem source
COPY oydid/ruby-gem /usr/src/oydid-gem
WORKDIR /usr/src/oydid-gem
RUN gem build oydid.gemspec && gem install oydid-*.gem

# Install Python dependencies
# Added aiofiles for FastAPI StaticFiles
RUN pip3 install --no-cache-dir pytest fastapi uvicorn google-auth requests rdflib aiofiles qdrant-client fastembed --break-system-packages

# Setup OYDID CLI
COPY oydid/cli/oydid.rb /usr/local/bin/oydid
RUN chmod 755 /usr/local/bin/oydid

# Copy test script and API app
COPY tests /usr/src/app/tests
COPY app /usr/src/app/app

# Copy Frontend Build Artifacts
# Copy to a location outside /usr/src/app to avoid volume masking
COPY --from=frontend-build /app/dist /frontend_dist

WORKDIR /usr/src/app

# Default command matches docker-compose, but useful if run standalone
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
