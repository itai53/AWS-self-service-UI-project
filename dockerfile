FROM python:3.9-slim
RUN groupadd -g 1000 UI_user && useradd -m -u 1000 -g UI_user UI_user
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt 
COPY . .
# Set AWS credentials and SSH authentication file paths
ENV AWS_SHARED_CREDENTIALS_FILE=/UI_user/.aws/credentials   
ENV AWS_CONFIG_FILE=/UI_user/.aws/config
ENV SSH_AUTH_SOCK=/UI_user/.ssh
USER UI_user
EXPOSE 8000
ENTRYPOINT ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
