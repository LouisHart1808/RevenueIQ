FROM python:3.13-slim
WORKDIR /workspace
RUN pip install --no-cache-dir uv==0.11.1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
COPY . .
ENV PATH="/workspace/.venv/bin:$PATH"
EXPOSE 8050
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "120", "app.main:server"]
