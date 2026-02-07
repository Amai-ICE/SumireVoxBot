
# SumireVox セットアップスクリプト
# このスクリプトはgit cloneされたプロジェクトディレクトリで実行してください

param(
    [int]$BotCount = 0,
    [switch]$SkipDockerCheck = $false,
    [switch]$SkipStartDocker = $false
)

# エラーハンドリング
$ErrorActionPreference = "Stop"

# ========== 関数定義 ==========

function Write-ColoredOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Header {
    Write-Host ""
    Write-ColoredOutput "╔═══════════════════════════════════════╗" -Color Cyan
    Write-ColoredOutput "║   SumireVox Setup & Installation      ║" -Color Cyan
    Write-ColoredOutput "║          Auto Setup Script             ║" -Color Cyan
    Write-ColoredOutput "╚═══════════════════════════════════════╝" -Color Cyan
    Write-Host ""
}

function Test-DockerInstalled {
    try {
        $null = docker --version 2>$null
        $null = docker-compose --version 2>$null
        return $true
    } catch {
        return $false
    }
}

function Test-ProjectDirectory {
    if (-not (Test-Path ".env.template")) {
        Write-ColoredOutput "❌ .env.template not found!" -Color Red
        Write-ColoredOutput "This script should be run from the SumireVox project root directory." -Color Yellow
        Write-ColoredOutput "Please ensure you've cloned the repository and are in the correct directory." -Color Yellow
        exit 1
    }
}

function New-DockerComposeFile {
    param([int]$BotCount)

    $yaml = @"
version: "3.8"

x-bot-template: &bot-template
  build: .
  volumes:
    - .:/app
  depends_on:
    - db
    - voicevox_engine
  networks:
    - sumire_vox_network
  restart: unless-stopped

services:
"@

    for ($i = 1; $i -le $BotCount; $i++) {
        $yaml += @"

  bot$($i):
    <<: *bot-template
    container_name: sumire_vox_bot_$($i)
    env_file:
      - .env.bot$($i)
"@
    }

    $yaml += @"

  voicevox_engine:
    image: voicevox/voicevox_engine:cpu-ubuntu20.04-latest
    container_name: voicevox_engine
    ports:
      - "50021:50021"
    restart: unless-stopped
    volumes:
      - ./voicevox_config:/root/.local/share/voicevox_engine
    networks:
      - sumire_vox_network

  db:
    image: postgres:15
    container_name: sumire_vox_db
    restart: always
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: sumire_vox
    ports:
      - "5432:5432"
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
    networks:
      - sumire_vox_network

networks:
  sumire_vox_network:
    driver: bridge
"@

    return $yaml
}

function Update-EnvFile {
    param(
        [string]$EnvFilePath,
        [string]$Token
    )

    $content = Get-Content $EnvFilePath -Raw

    # Discord Token の更新
    $content = $content -replace 'DISCORD_TOKEN=.*', "DISCORD_TOKEN=$Token"

    # Docker 環境用の設定
    $content = $content -replace 'VOICEVOX_HOST=.*', "VOICEVOX_HOST=voicevox_engine"
    $content = $content -replace 'POSTGRES_HOST=.*', "POSTGRES_HOST=db"

    # WEB_PORT の設定（WEB_ENABLEDがfalseになっていることを前提）
    $content = $content -replace 'WEB_ENABLED=.*', "WEB_ENABLED=false"

    Set-Content -Path $EnvFilePath -Value $content
}

function Backup-File {
    param([string]$FilePath)

    if (Test-Path $FilePath) {
        $backupPath = "$FilePath.backup"
        Copy-Item $FilePath $backupPath -Force | Out-Null
        Write-ColoredOutput "⚠️  Backed up existing file to $backupPath" -Color Yellow
        return $true
    }
    return $false
}

# ========== メイン処理 ==========

Write-Header

# Step 1: プロジェクトディレクトリの検証
Write-ColoredOutput "[Step 1/5] Verifying project directory..." -Color Yellow
Test-ProjectDirectory
$projectPath = Get-Location
Write-ColoredOutput "✓ Project directory verified: $projectPath" -Color Green
Write-Host ""

# Step 2: Docker のインストール確認
Write-ColoredOutput "[Step 2/5] Checking Docker installation..." -Color Yellow
if (-not (Test-DockerInstalled) -and -not $SkipDockerCheck) {
    Write-ColoredOutput "❌ Docker is not installed." -Color Red
    Write-ColoredOutput "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" -Color Yellow
    exit 1
} else {
    Write-ColoredOutput "✓ Docker is properly configured" -Color Green
    docker --version | Write-ColoredOutput -Color Green
    docker-compose --version | Write-ColoredOutput -Color Green
}
Write-Host ""

# Step 3: ボット台数の指定
Write-ColoredOutput "[Step 3/5] Configuring bot instances..." -Color Yellow
if ($BotCount -le 0) {
    $BotCountInput = Read-Host "How many bot instances do you want to create? (default: 1)"
    $BotCount = if ($BotCountInput -eq "") { 1 } else { [int]$BotCountInput }

    if ($BotCount -le 0) {
        Write-ColoredOutput "❌ Invalid number. Setting to 1" -Color Red
        $BotCount = 1
    }
}
Write-ColoredOutput "✓ Will create $BotCount bot instance(s)" -Color Green
Write-Host ""

# Step 4: docker-compose.yml の生成
Write-ColoredOutput "[Step 4/5] Generating docker-compose.yml..." -Color Yellow
Backup-File "docker-compose.yml" | Out-Null

$dockerComposeContent = New-DockerComposeFile -BotCount $BotCount
Set-Content -Path "docker-compose.yml" -Value $dockerComposeContent
Write-ColoredOutput "✓ docker-compose.yml generated with $BotCount bot(s)" -Color Green
Write-Host ""

# Step 5: .env ファイルの生成
Write-ColoredOutput "[Step 5/5] Creating .env files for bot instances..." -Color Yellow

for ($i = 1; $i -le $BotCount; $i++) {
    $envFile = ".env.bot$i"

    # バックアップ
    Backup-File $envFile | Out-Null

    # .env.template からコピー
    Copy-Item ".env.template" $envFile -Force | Out-Null

    # Discord Token の入力
    Write-ColoredOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -Color Cyan
    $token = Read-Host "Enter Discord Token for bot instance $i"
    Write-ColoredOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -Color Cyan

    if ($token -eq "") {
        Write-ColoredOutput "❌ Discord Token cannot be empty!" -Color Red
        exit 1
    }

    # .env ファイルの更新
    Update-EnvFile -EnvFilePath $envFile -Token $token
    Write-ColoredOutput "✓ Created $envFile" -Color Green
}
Write-Host ""

# Step 6: 必要なディレクトリの作成
Write-ColoredOutput "[Step 6/5] Creating necessary directories..." -Color Yellow
$directories = @("postgres_data", "voicevox_config", "logs", "temp", "assets")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-ColoredOutput "✓ Directories created" -Color Green
Write-Host ""

# Docker コンテナの起動
Write-ColoredOutput "🐳 Starting Docker containers..." -Color Yellow

if (-not $SkipStartDocker) {
    $startDockerResponse = Read-Host "Start Docker containers now? (y/n, default: y)"
    if ($startDockerResponse -eq "n") {
        $SkipStartDocker = $true
    }
}

if (-not $SkipStartDocker) {
    Write-ColoredOutput "Building Docker images and starting containers..." -Color Yellow

    try {
        docker-compose up -d

        Write-ColoredOutput "✓ Docker containers started successfully!" -Color Green
        Write-Host ""

        # サービスの稼働確認を待機
        Write-ColoredOutput "Waiting for services to start..." -Color Yellow
        Start-Sleep -Seconds 5

        Write-ColoredOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -Color Cyan
        Write-ColoredOutput "Service Status:" -Color Cyan
        Write-ColoredOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -Color Cyan
        docker-compose ps

        Write-Host ""
        Write-ColoredOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -Color Cyan
        Write-ColoredOutput "✓ Setup Complete!" -Color Green
        Write-ColoredOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -Color Cyan
        Write-Host ""

        Write-ColoredOutput "📍 Bot Instances:" -Color Cyan
        for ($i = 1; $i -le $BotCount; $i++) {
            Write-ColoredOutput "  Bot $i - Container: sumire_vox_bot_$i" -Color Yellow
        }

        Write-Host ""
        Write-ColoredOutput "📍 Service Endpoints:" -Color Cyan
        Write-ColoredOutput "VoiceVOX Engine: http://localhost:50021" -Color Yellow
        Write-ColoredOutput "Database: localhost:5432" -Color Yellow

        Write-Host ""
        Write-ColoredOutput "💡 Useful Commands:" -Color Cyan
        Write-ColoredOutput "View logs: docker-compose logs -f" -Color Gray
        Write-ColoredOutput "View specific bot logs: docker-compose logs -f bot1" -Color Gray
        Write-ColoredOutput "Stop containers: docker-compose down" -Color Gray
        Write-ColoredOutput "Restart services: docker-compose restart" -Color Gray

    } catch {
        Write-ColoredOutput "❌ Failed to start Docker containers" -Color Red
        Write-ColoredOutput $_.Exception.Message -Color Red
        exit 1
    }
} else {
    Write-ColoredOutput "Skipped starting Docker containers" -Color Yellow
    Write-ColoredOutput "To start later, run: docker-compose up -d" -Color Gray
}

Write-Host ""
Write-ColoredOutput "✓ Installation completed successfully!" -Color Green
Write-Host ""