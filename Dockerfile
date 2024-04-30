# 
FROM python:3.12.3-slim

# 
WORKDIR /code

# 
COPY ./requirements.txt ./

# 
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 
COPY ./src ./src

# 
CMD ["uvicorn", "main:app", "--reload"]
# CMD ["uvicorn", "app.main:app", "--proxy-headers", "--host", "0.0.0.0", "--port", "80"]