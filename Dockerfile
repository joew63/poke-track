FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

COPY config.example.yaml .env.example ./

CMD ["python", "-m", "poke_track.main"]
