FROM python:3.12.3-slim

WORKDIR /code

# Install necessary system dependencies
RUN apt-get update && apt-get install -yq \
    curl \
    libnss3 \
    --no-install-recommends

COPY ./requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

# Install Playwright 
# RUN curl -fsSL https://playwright.dev/python/sh | python -
RUN playwright install --with-deps chromium

COPY config.toml ./config.toml
COPY . .

# create a folder in the container
RUN mkdir -p /response-logs


# 
# CMD ["uvicorn", "main:app", "--reload"]
CMD ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--workers", "4", "--port", "80"]