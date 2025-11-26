#!/bin/bash
# PR Validation Script
# Runs health checks and integration tests to verify everything works before merging

set -e  # Exit on error

echo "🔍 Running PR validation tests..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if services are running
echo "📋 Checking if services are running..."

check_service() {
    local name=$1
    local url=$2
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is running"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not running"
        return 1
    fi
}

SERVICES_OK=true

if ! check_service "Qdrant" "http://localhost:6333/health"; then
    SERVICES_OK=false
fi

if ! check_service "Ollama" "http://localhost:11434/api/tags"; then
    SERVICES_OK=false
fi

if ! check_service "API" "http://localhost:8000/health"; then
    SERVICES_OK=false
fi

if [ "$SERVICES_OK" = false ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Some services are not running.${NC}"
    echo "Start them with: cd deploy && docker compose up -d"
    echo "Wait for services to be healthy, then run this script again."
    exit 1
fi

echo ""
echo "🧪 Running health check and integration tests..."
echo ""

# Run health check tests (excluding slow tests)
if pytest tests/test_health_integration.py -v -m "not slow"; then
    echo ""
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    echo ""
    echo "To run full integration tests (including slow tests), run:"
    echo "  pytest tests/test_health_integration.py -v"
    exit 0
else
    echo ""
    echo -e "${RED}❌ Health checks failed!${NC}"
    echo "Please fix the issues before merging."
    exit 1
fi

