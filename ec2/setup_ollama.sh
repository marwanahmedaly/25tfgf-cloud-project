#!/bin/bash
# EC2 Ollama Setup Script
# Run on Ubuntu 22.04 EC2 instance with GPU (g4dn.xlarge)

set -e

echo "=== Installing Ollama ==="
curl -fsSL https://ollama.com/install.sh | sh
ollama --version

echo "=== Creating Ollama systemd service ==="
sudo cp ollama.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama --no-pager

echo "=== Ollama installation complete ==="
echo "Ollama API available at http://localhost:11434"