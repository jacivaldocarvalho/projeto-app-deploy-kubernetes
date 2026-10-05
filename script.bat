@echo off
setlocal
cd /d "%~dp0"
if errorlevel 1 exit /b 1
where docker >nul 2>&1
if errorlevel 1 (
    echo Required tool not found: docker
    exit /b 1
)
where kubectl >nul 2>&1
if errorlevel 1 (
    echo Required tool not found: kubectl
    exit /b 1
)
if not exist .env (
    echo Copy .env.example to .env and configure database credentials first.
    exit /b 1
)
for %%K in (MYSQL_ROOT_PASSWORD MYSQL_DATABASE MYSQL_USER MYSQL_PASSWORD) do (
    findstr /r /c:"^%%K=..*" .env >nul
    if errorlevel 1 (
        echo Missing or empty setting in .env: %%K
        exit /b 1
    )
)
findstr /b /c:"MYSQL_ROOT_PASSWORD=replace-with-" /c:"MYSQL_PASSWORD=replace-with-" .env >nul
if not errorlevel 1 (
    echo Replace the example passwords in .env before deployment.
    exit /b 1
)
findstr /x /c:"MYSQL_USER=root" .env >nul
if not errorlevel 1 (
    echo MYSQL_USER must be a dedicated application user, not root.
    exit /b 1
)
echo Building application images...
docker build -f backend/dockerfile -t jncarvalho/projeto-backend:1.0 .
if errorlevel 1 exit /b 1
docker build -f database/dockerfile -t jncarvalho/projeto-database:1.0 .
if errorlevel 1 exit /b 1
echo Pushing application images...
docker push jncarvalho/projeto-backend:1.0
if errorlevel 1 exit /b 1
docker push jncarvalho/projeto-database:1.0
if errorlevel 1 exit /b 1
echo Configuring database credentials...
kubectl get secret application-database >nul 2>&1
if errorlevel 1 (
    kubectl create secret generic application-database --from-env-file=.env
    if errorlevel 1 exit /b 1
) else (
    echo Secret already exists. Rotate credentials explicitly if needed.
)
echo Applying Kubernetes resources...
kubectl apply -f services.yml
if errorlevel 1 exit /b 1
kubectl apply -f deployment.yml
if errorlevel 1 exit /b 1
echo Waiting for application deployments...
kubectl rollout status deployment/mysql --timeout=180s
if errorlevel 1 exit /b 1
kubectl rollout status deployment/php --timeout=180s
if errorlevel 1 exit /b 1
