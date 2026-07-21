FROM python:3.12-slim

# git e necessario em runtime: source_resolver.py clona repositorios via `git clone`
# quando a tool recebe repositorio_git em vez de caminho_projeto.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY README.md ./

RUN uv sync --frozen --no-dev

ENV DOC_AGENT_TRANSPORT=streamable-http
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["uv", "run", "doc-agent"]
