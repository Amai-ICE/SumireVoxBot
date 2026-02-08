#!/bin/bash

# SumireVox セットアップスクリプト
# このスクリプトはgit cloneされたプロジェクトディレクトリで実行してください

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# ========== 関数定義 ==========

write_colored_output() {
    local message="$1"
    local color="$2"

    case "$color" in
        red)
            echo -e "${RED}${message}${NC}"
            ;;
        green)
            echo -e "${GREEN}${message}${NC}"
            ;;
        yellow)
            echo -e "${YELLOW}${message}${NC}"
            ;;
        blue)
            echo -e "${BLUE}${message}${NC}"
            ;;
        cyan)
            echo -e "${CYAN}${message}${NC}"
            ;;
        gray)
            echo -e "${GRAY}${message}${NC}"
            ;;
        *)
            echo -e "${message}"
            ;;
    esac
}

write_header() {
    echo ""
    write_colored_output "╔═══════════════════════════════════════╗" cyan
    write_colored_output "║   SumireVox Setup & Installation      ║" cyan
    write_colored_output "║          Auto Setup Script             ║" cyan
    write_colored_output "╚═══════════════════════════════════════╝" cyan
    echo ""
}

test_docker_installed() {
    if ! command -v docker &> /dev/null; then
        return 1
    fi
    if ! command -v docker-compose &> /dev/null; then
        return 1
    fi
    return 0
}

test_project_directory() {
    if [ ! -f ".env.template" ]; then
        write_colored_output "❌ .env.template not found!" red
        write_colored_output "This script should be run from the SumireVox project root directory." yellow
        write_colored_output "Please ensure you've cloned the repository and are in the correct directory." yellow
        exit 1
    fi
}

new_docker_compose_file() {
    local bot_count=$1

    cat > docker-compose.yml << 'EOF'
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
EOF

    for ((i = 1; i <= bot_count; i++)); do
        cat >> docker-compose.yml << EOF

  bot${i}:
    <<: *bot-template
    container_name: sumire_vox_bot_${i}
    env_file:
      - .env.bot${i}
EOF
    done

    cat >> docker-compose.yml << 'EOF'

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
EOF
}

update_env_file() {
    local env_file=$1
    local token=$2

    # Discord Token の更新
    sed -i "s/DISCORD_TOKEN=.*/DISCORD_TOKEN=${token}/" "$env_file"

    # Docker 環境用の設定
    sed -i "s/VOICEVOX_HOST=.*/VOICEVOX_HOST=voicevox_engine/" "$env_file"
    sed -i "s/POSTGRES_HOST=.*/POSTGRES_HOST=db/" "$env_file"

    # WEB_ENABLED を false に設定
    sed -i "s/WEB_ENABLED=.*/WEB_ENABLED=false/" "$env_file"
}

# ========== メイン処理 ==========

write_header

# Step 1: プロジェクトディレクトリの検証
write_colored_output "[Step 1/5] Verifying project directory..." yellow
test_project_directory
PROJECT_PATH=$(pwd)
write_colored_output "✓ Project directory verified: ${PROJECT_PATH}" green
echo ""

# Step 2: Docker のインストール確認
write_colored_output "[Step 2/5] Checking Docker installation..." yellow
if ! test_docker_installed; then
    write_colored_output "❌ Docker is not installed." red
    write_colored_output "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop" yellow
    exit 1
else
    write_colored_output "✓ Docker is properly configured" green
    docker --version | write_colored_output "$(cat)" green
    docker-compose --version | write_colored_output "$(cat)" green
fi
echo ""

# Step 3: ボット台数の指定
write_colored_output "[Step 3/5] Configuring bot instances..." yellow
if [ -z "$BOT_COUNT" ] || [ "$BOT_COUNT" -le 0 ]; then
    read -p "How many bot instances do you want to create? (default: 1): " BOT_COUNT_INPUT
    BOT_COUNT=${BOT_COUNT_INPUT:-1}

    # 正の整数か確認
    if ! [[ "$BOT_COUNT" =~ ^[0-9]+$ ]] || [ "$BOT_COUNT" -le 0 ]; then
        write_colored_output "❌ Invalid number. Setting to 1" red
        BOT_COUNT=1
    fi
fi
write_colored_output "✓ Will create ${BOT_COUNT} bot instance(s)" green
echo ""

# Step 4: docker-compose.yml の生成
write_colored_output "[Step 4/5] Generating docker-compose.yml..." yellow

new_docker_compose_file "$BOT_COUNT"
write_colored_output "✓ docker-compose.yml generated with ${BOT_COUNT} bot(s)" green
echo ""

# Step 5: .env ファイルの生成
write_colored_output "[Step 5/5] Creating .env files for bot instances..." yellow

for ((i = 1; i <= BOT_COUNT; i++)); do
    ENV_FILE=".env.bot${i}"

    # .env.template からコピー
    cp ".env.template" "$ENV_FILE"

    # Discord Token の入力
    write_colored_output "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" cyan
    read -p "Enter Discord Token for bot instance ${i}: " TOKEN
    write_colored_output "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" cyan

    if [ -z "$TOKEN" ]; then
        write_colored_output "❌ Discord Token cannot be empty!" red
        exit 1
    fi

    # .env ファイルの更新
    update_env_file "$ENV_FILE" "$TOKEN"
    write_colored_output "✓ Created ${ENV_FILE}" green
done
echo ""

# Step 6: 必要なディレクトリの作成
write_colored_output "[Step 6/5] Creating necessary directories..." yellow
for dir in postgres_data voicevox_config logs temp assets; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
done
write_colored_output "✓ Directories created" green
echo ""

# Docker コンテナの起動
write_colored_output "🐳 Starting Docker containers..." yellow

read -p "Start Docker containers now? (y/n, default: y): " START_DOCKER_INPUT
START_DOCKER=${START_DOCKER_INPUT:-y}

if [ "$START_DOCKER" = "y" ] || [ "$START_DOCKER" = "Y" ]; then
    write_colored_output "Building Docker images and starting containers..." yellow

    if docker-compose up -d; then
        write_colored_output "✓ Docker containers started successfully!" green
        echo ""

        # サービスの稼働確認を待機
        write_colored_output "Waiting for services to start..." yellow
        sleep 5

        write_colored_output "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" cyan
        write_colored_output "Service Status:" cyan
        write_colored_output "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" cyan
        docker-compose ps

        echo ""
        write_colored_output "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" cyan
        write_colored_output "✓ Setup Complete!" green
        write_colored_output "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" cyan
        echo ""

        write_colored_output "📍 Bot Instances:" cyan
        for ((i = 1; i <= BOT_COUNT; i++)); do
            write_colored_output "  Bot ${i} - Container: sumire_vox_bot_${i}" yellow
        done

        echo ""
        write_colored_output "📍 Service Endpoints:" cyan
        write_colored_output "VoiceVOX Engine: http://localhost:50021" yellow
        write_colored_output "Database: localhost:5432" yellow

        echo ""
        write_colored_output "💡 Useful Commands:" cyan
        write_colored_output "View logs: docker-compose logs -f" gray
        write_colored_output "View specific bot logs: docker-compose logs -f bot1" gray
        write_colored_output "Stop containers: docker-compose down" gray
        write_colored_output "Restart services: docker-compose restart" gray
    else
        write_colored_output "❌ Failed to start Docker containers" red
        exit 1
    fi
else
    write_colored_output "Skipped starting Docker containers" yellow
    write_colored_output "To start later, run: docker-compose up -d" gray
fi

echo ""
write_colored_output "✓ Installation completed successfully!" green
echo ""