# 
FROM python:3.12.3-slim

# 
WORKDIR /code

# Install necessary system dependencies
RUN apt-get update && apt-get install -yq \
    curl \
    libnss3 \
    --no-install-recommends

# 
COPY ./requirements.txt ./

# 
RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

# RUN apt update
# RUN apt-get install ffmpeg -y
# RUN ffmpeg -version

# Install Playwright
# RUN curl -fsSL https://playwright.dev/python/sh | python -
RUN playwright install --with-deps chromium

# 
COPY . .
# COPY ./src ./src

# 
# CMD ["uvicorn", "main:app", "--reload"]
CMD ["uvicorn", "main:app", "--proxy-headers", "--host", "0.0.0.0", "--workers", "4", "--port", "80"]