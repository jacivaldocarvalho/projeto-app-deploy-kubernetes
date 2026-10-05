@echo off
setlocal
set "RENDER_CREATED="
cd /d "%~dp0"
if errorlevel 1 exit /b 1
where docker >nul 2>&1
if errorlevel 1 (
    echo Required tool not found: docker
    exit /b 1
)
where git >nul 2>&1
if errorlevel 1 (
    echo Required tool not found: git
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
git rev-parse --verify HEAD >nul 2>&1
if errorlevel 1 exit /b 1
for /f "delims=" %%S in ('git status --porcelain --untracked-files^=normal') do (
    echo Commit all repository changes before building a commit-tagged deployment.
    exit /b 1
)
for /f "delims=" %%H in ('git rev-parse --verify HEAD') do set "IMAGE_TAG=%%H"
if not defined IMAGE_TAG exit /b 1
set "BACKEND_IMAGE=jncarvalho/projeto-backend:%IMAGE_TAG%"
set "DATABASE_IMAGE=jncarvalho/projeto-database:%IMAGE_TAG%"
set "RENDER_DIR=%TEMP%\projeto-deploy-%RANDOM%-%RANDOM%"
if exist "%RENDER_DIR%" exit /b 1
mkdir "%RENDER_DIR%"
if errorlevel 1 exit /b 1
set "RENDER_CREATED=1"
copy /y deployment.yml "%RENDER_DIR%\deployment.yml" >nul
if errorlevel 1 goto :failure
copy /y services.yml "%RENDER_DIR%\services.yml" >nul
if errorlevel 1 goto :failure
(
    echo apiVersion: kustomize.config.k8s.io/v1beta1
    echo kind: Kustomization
    echo resources:
    echo   - deployment.yml
    echo   - services.yml
    echo images:
    echo   - name: jncarvalho/projeto-backend
    echo     newTag: "%IMAGE_TAG%"
    echo   - name: jncarvalho/projeto-database
    echo     newTag: "%IMAGE_TAG%"
) > "%RENDER_DIR%\kustomization.yaml"
if errorlevel 1 goto :failure
kubectl kustomize "%RENDER_DIR%" > "%RENDER_DIR%\rendered.yml"
if errorlevel 1 goto :failure

echo Building application images for commit %IMAGE_TAG%...
docker build -f backend/dockerfile -t "%BACKEND_IMAGE%" .
if errorlevel 1 goto :failure
docker build -f database/dockerfile -t "%DATABASE_IMAGE%" .
if errorlevel 1 goto :failure

echo Pushing application images...
docker push "%BACKEND_IMAGE%"
if errorlevel 1 goto :failure
docker push "%DATABASE_IMAGE%"
if errorlevel 1 goto :failure

echo Configuring database credentials...
kubectl get secret application-database >nul 2>&1
if errorlevel 1 (
    kubectl create secret generic application-database --from-env-file=.env
    if errorlevel 1 goto :failure
) else (
    echo Secret already exists. Rotate credentials explicitly if needed.
)

echo Applying Kubernetes resources...
kubectl apply -f "%RENDER_DIR%\rendered.yml"
if errorlevel 1 goto :failure

echo Waiting for application deployments...
kubectl rollout status deployment/mysql --timeout=600s
if errorlevel 1 goto :failure
kubectl rollout status deployment/php --timeout=300s
if errorlevel 1 goto :failure
if defined RENDER_CREATED rmdir /s /q "%RENDER_DIR%"
exit /b 0

:failure
if defined RENDER_CREATED rmdir /s /q "%RENDER_DIR%"
exit /b 1
