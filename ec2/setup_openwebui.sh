#!/bin/bash
# OpenWebUI Setup Script
# Run after setup_ollama.sh

set -e

echo "=== Installing OpenWebUI ==="

# Option A: Docker (recommended)
if command -v docker &> /dev/null; then
    echo "Using Docker installation..."
    docker run -d \
        -p 8080:8080 \
        -v open-webui:/app/backend/data \
        --name open-webui \
        --restart unless-stopped \
        -e OLLAMA_BASE_URL=http://<EC2_PRIVATE_IP>:11434 \
        ghcr.io/open-webui/open-webui:main

    echo "OpenWebUI (Docker) installed successfully"
else
    # Option B: pip
    echo "Using pip installation..."
    pip install open-webui

    # Create systemd service
    sudo cp openwebui.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable openwebui
    sudo systemctl start openwebui

    echo "OpenWebUI (pip) installed successfully"
fi

echo "=== OpenWebUI setup complete ==="
echo "OpenWebUI available at http://<ec2-public-ip>:8080"