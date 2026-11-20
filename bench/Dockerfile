# Benchmark harness image. Standard library only: no pip install, no internet needed at build or run time.
# CI/CD: please pin the base image by digest when you wire this into the workflow.
FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
RUN groupadd --gid 10001 bench && useradd --uid 10001 --gid 10001 --create-home bench
WORKDIR /app
COPY harness.py prompts.jsonl /app/
USER 10001:10001
# -I: ignore PYTHON* variables and user site; -u: unbuffered, so `kubectl logs -f` shows progress.
ENTRYPOINT ["python", "-I", "-u", "/app/harness.py"]
