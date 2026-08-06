FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    NEUROPA_DATA_DIR=/data

COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project
COPY neuropa ./neuropa
RUN uv sync --frozen --no-dev

VOLUME ["/data"]
EXPOSE 8474
CMD ["uv", "run", "neuropa", "--lan", "--port", "8474"]
