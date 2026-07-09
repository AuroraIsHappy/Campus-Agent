# ---- Stage 1: Hermes base (clone + install hermes-agent, not on PyPI) ----
FROM python:3.13-slim AS hermes-base
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl build-essential && rm -rf /var/lib/apt/lists/*
# Clone hermes-agent at a pinned tag + install (local build, not PyPI)
ARG HERMES_VERSION=0.18.0
RUN git clone --depth 1 --branch v${HERMES_VERSION} \
    https://github.com/NousResearch/hermes-agent.git /opt/hermes-agent \
    || git clone --depth 1 https://github.com/NousResearch/hermes-agent.git /opt/hermes-agent
WORKDIR /opt/hermes-agent
RUN pip install --no-cache-dir -e .

# ---- Stage 2: Campus backend + frontend build ----
FROM hermes-base AS campus-build
WORKDIR /app
# Install campus Python deps
COPY student-secretary-agent/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Copy campus code
COPY student-secretary-agent/ ./
# Build frontend
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /app/frontend
RUN npm install && npm run build

# ---- Stage 3: Final runtime image ----
FROM python:3.13-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    git nodejs && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# Copy installed packages from build stage
COPY --from=campus-build /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=campus-build /usr/local/bin /usr/local/bin
# Copy hermes-agent (needed at runtime for hermes_cli imports)
COPY --from=campus-build /opt/hermes-agent /opt/hermes-agent
ENV PYTHONPATH="/opt/hermes-agent:${PYTHONPATH}"
# Copy campus app + built frontend
COPY --from=campus-build /app /app
# Copy skills directory (campus-authored skills)
COPY student-secretary-agent/skills ./skills

ENV CAMPUS_HOME=/data/.campus
ENV CAMPUS_ENV=prod
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "campus.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
