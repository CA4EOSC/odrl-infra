# Stage 1: Build Frontend
FROM node:20-alpine as frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_REDIRECT_URI
ARG VITE_ORCID_CLIENT_ID
ARG VITE_LOGO_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ENV VITE_REDIRECT_URI=$VITE_REDIRECT_URI
ENV VITE_ORCID_CLIENT_ID=$VITE_ORCID_CLIENT_ID
ENV VITE_LOGO_URL=$VITE_LOGO_URL
# Git version shown in the UI footer (the image has no .git); see bin/docker-build
ARG VITE_GIT_SHA
ARG VITE_GIT_BRANCH
ARG VITE_GIT_DATE
ARG VITE_GIT_DIRTY
ENV VITE_GIT_SHA=$VITE_GIT_SHA VITE_GIT_BRANCH=$VITE_GIT_BRANCH VITE_GIT_DATE=$VITE_GIT_DATE VITE_GIT_DIRTY=$VITE_GIT_DIRTY
RUN npm run build

# Stage 2: Backend & Runtime
FROM ruby:3.2-slim

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsodium-dev libssl-dev zlib1g-dev pkg-config git jq bash curl python3 python3-pip openssh-client && \
    rm -rf /var/lib/apt/lists/*

RUN gem install httparty ed25519 multibases multihashes multicodecs optparse rbnacl simple_dag uri 'json-canonicalization:1.0.0' 'securerandom:0.1.1'

# Copy and install local OYDID gem source
COPY oydid/ruby-gem /usr/src/oydid-gem
COPY oydid/LICENSE /usr/src/oydid-gem/LICENSE
WORKDIR /usr/src/oydid-gem
RUN gem build oydid.gemspec && gem install oydid-*.gem

# Install Python dependencies
# Added aiofiles for FastAPI StaticFiles, pyshacl for SHACL verification
RUN pip3 install --no-cache-dir pytest fastapi uvicorn google-auth requests rdflib aiofiles qdrant-client fastembed pyshacl --break-system-packages

# Setup OYDID CLI
COPY oydid/cli/oydid.rb /usr/local/bin/oydid
RUN chmod 755 /usr/local/bin/oydid

# Copy test script, CLI, and API app
COPY tests /usr/src/app/tests
COPY app /usr/src/app/app
COPY cli /usr/src/app/cli
COPY config /usr/src/app/config
COPY templates /usr/src/app/templates

# Copy Frontend Build Artifacts
# Copy to a location outside /usr/src/app to avoid volume masking
COPY --from=frontend-build /app/dist /frontend_dist

WORKDIR /usr/src/app

# Default command matches docker-compose, but useful if run standalone
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
