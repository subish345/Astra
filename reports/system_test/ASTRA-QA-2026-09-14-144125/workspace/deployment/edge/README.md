# ASTRA-EA: Edge Compute Deployment Package

This directory contains specifications and platform runbooks for deploying ASTRA-EA onto edge compute hardware (e.g. ARM64 SBCs, NVIDIA Jetson, industrial x86 mini-PCs).

## Target Edge Architectures
1. **ARM64 (aarch64):**
   - 4–8 cores @ 1.8+ GHz
   - 4GB – 8GB LPDDR4 RAM
   - ONNX Runtime INT8 with ARM NEON acceleration
2. **NVIDIA Jetson (Orin / Xavier):**
   - TensorRT FP16/INT8 execution provider
   - Unified memory architecture
3. **x86_64 Industrial Embedded:**
   - Intel Core i5/i7 low-power U-series or AMD Ryzen Embedded
   - OpenVINO / ONNX execution provider

## Deployment Execution
```bash
./deployment/scripts/install_edge.sh
astra edge doctor
astra physical-test --profile view_left
```
