#!/bin/bash

# PebbleMind Model Download Script
# Downloads required models for full functionality

set -e

echo "🤖 PebbleMind Model Downloader"
echo "================================"

# Create models directory
mkdir -p models

# Function to download with progress
download_with_progress() {
    local url=$1
    local output=$2
    local name=$3

    if [ -f "$output" ]; then
        echo "✅ $name already exists, skipping..."
        return
    fi

    echo "⬇️  Downloading $name..."
    if command -v wget &> /dev/null; then
        wget -q --show-progress "$url" -O "$output"
    elif command -v curl &> /dev/null; then
        curl -L -o "$output" "$url"
    else
        echo "❌ Neither wget nor curl found. Please install one of them."
        exit 1
    fi
}

# Download Qwen2.5 models (1.5B, 3B, 7B)
echo ""
echo "📥 Downloading LLM Models (Qwen2.5 Instruct)..."

# 1.5B Model (Ultra-light CPU)
echo "  Downloading 1.5B model (ultra-light)..."
QWEN_15B_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
download_with_progress "$QWEN_15B_URL" "models/qwen2.5-1.5b-instruct-q4_k_m.gguf" "Qwen2.5-1.5B GGUF Model"

# 3B Model (Balanced - Default)
echo "  Downloading 3B model (balanced - recommended)..."
QWEN_3B_URL="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf"
download_with_progress "$QWEN_3B_URL" "models/qwen2.5-3b-instruct-q4_k_m.gguf" "Qwen2.5-3B GGUF Model"

# 7B Model (High-quality with GPU offload)
echo "  Downloading 7B model (high-quality)..."
QWEN_7B_URL="https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m.gguf"
download_with_progress "$QWEN_7B_URL" "models/qwen2.5-7b-instruct-q4_k_m.gguf" "Qwen2.5-7B GGUF Model"

# Download BGE-small embedding model
echo ""
echo "📥 Downloading Embedding Model (BGE-small)..."
if command -v pip &> /dev/null && pip show huggingface_hub &> /dev/null; then
    echo "Using huggingface-cli to download BGE-small..."
    huggingface-cli download BAAI/bge-small-en-v1.5 --local-dir models/bge-small-en-v1.5 --quiet
else
    echo "⚠️  huggingface_hub not found. Install with: pip install huggingface_hub"
    echo "   Then run: huggingface-cli download BAAI/bge-small-en-v1.5 --local-dir models/bge-small-en-v1.5"
fi

# Download Whisper models
echo ""
echo "📥 Downloading Whisper Models..."
WHISPER_BASE_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main"

# Base English model
download_with_progress "${WHISPER_BASE_URL}/ggml-base.en.bin" "models/ggml-base.en.bin" "Whisper Base English"

# Tiny English model (faster, less accurate)
download_with_progress "${WHISPER_BASE_URL}/ggml-tiny.en.bin" "models/ggml-tiny.en.bin" "Whisper Tiny English"

# Download Piper voices
echo ""
echo "📥 Downloading Piper TTS Voices..."
PIPER_VOICES_URL="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

# Amy voice (low quality, fast)
download_with_progress "${PIPER_VOICES_URL}/en/en_US/amy/low/en_US-amy-low.onnx" "models/en_US-amy-low.onnx" "Piper Amy Low Voice"
download_with_progress "${PIPER_VOICES_URL}/en/en_US/amy/low/en_US-amy-low.onnx.json" "models/en_US-amy-low.onnx.json" "Piper Amy Low Config"

# Lessac voice (medium quality)
download_with_progress "${PIPER_VOICES_URL}/en/en_US/lessac/medium/en_US-lessac-medium.onnx" "models/en_US-lessac-medium.onnx" "Piper Lessac Medium Voice"
download_with_progress "${PIPER_VOICES_URL}/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" "models/en_US-lessac-medium.onnx.json" "Piper Lessac Medium Config"

echo ""
echo "🎉 Model download complete!"
echo ""
echo "📂 Models downloaded to: $(pwd)/models/"
echo ""
echo "📊 Qwen2.5 Model Strategy:"
echo "  • 1.5B Model: Ultra-light CPU usage, fastest responses"
echo "  • 3B Model:  Balanced quality/speed (default recommended)"
echo "  • 7B Model:  Highest quality, best with GPU offloading"
echo "  • All models use K-quantization (q4_K_M) for optimal CPU performance"
echo ""
echo "📋 Next steps:"
echo "1. Configure your preferred model size in pebblemind.yaml"
echo "2. Enable GPU offloading if you have compatible hardware"
echo "3. Run: pebblemind status"
echo "4. Try: pebblemind chat --interactive"
echo "5. Switch models anytime: pebblemind switch-model [1.5b|3b|7b]"
echo ""
echo "💡 Tips:"
echo "- Start with 3B model for best balance of quality and speed"
echo "- Use 1.5B on resource-constrained systems"
echo "- Enable GPU offloading for 7B model to get best performance"
echo "- All models support dynamic switching without restart"
