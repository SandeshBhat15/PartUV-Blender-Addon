# PartUV - Blender Addon

[![Download Latest](https://img.shields.io/github/v/release/SandeshBhat15/PartUV-Blender-Addon?label=Download&style=for-the-badge&color=green)](https://github.com/SandeshBhat15/PartUV-Blender-Addon/releases/latest/download/PartUV-v1.0.0.zip)
[![Downloads](https://img.shields.io/github/downloads/SandeshBhat15/PartUV-Blender-Addon/total?color=blue)](https://github.com/SandeshBhat15/PartUV-Blender-Addon/releases)
[![Blender](https://img.shields.io/badge/Blender-4.2%2B%20%7C%205.x-orange)](https://www.blender.org/)

PartUV (SIGGRAPH Asia 2025) as the main UV unwrapping engine for Blender 4.2+ / 5.x, with xatlas and OptCuts as fallbacks. Auto-installs all requirements with live progress on the main page.

## Download

**[Download PartUV-v1.0.0.zip (Latest)](https://github.com/SandeshBhat15/PartUV-Blender-Addon/releases/latest/download/PartUV-v1.0.0.zip)** — 210KB, single file.

## Installation

1. Click **Download** above or go to `Releases` on the right and download `PartUV-v1.0.0.zip`.
2. In Blender: `Edit -> Preferences -> Extensions -> Install from Disk` (or drag the zip onto Blender).
3. Enable `PartUV`. It auto-starts downloading `PartUV AI` + `xatlas` in the background (2 sec delay). Watch `3D View -> N -> PartUV` for live progress.
4. When `Done - PartUV is ready`, use `3D View -> N -> PartUV -> Unwrap` (PartUV AI is default). Also available in `UV Editor -> N -> PartUV`.

No manual setup needed. The `PartUV -- One-Click` panel shows the same progress and lets you choose `Geometric Only` or `+ AI (~1.2GB)`.

## Features

- **PartUV AI** as primary engine (geometric fallback when checkpoint is missing)
- **xatlas 0.2.3** and **OptCuts 1.20.2** as fallbacks
- One-click install with live progress bar and auto-repair
- Works on Windows and Linux with NVIDIA GPU for AI mode

## Usage

1. Select one or more meshes.
2. In `3D View -> N -> PartUV`, choose `Priority` and `Engine` (PartUV is default when installed).
3. Click `Unwrap`. Results appear as `UVgami Unwrapped` collection; originals are hidden if `Transfer UVs` is off.

Use `Test PartUV` in the One-Click panel to quickly verify the install (creates a test Suzanne).

## Requirements

- Blender 4.2.0 or newer (5.x supported)
- Windows or Linux (PartUV is CUDA-based; macOS uses xatlas/OptCuts only)
- Internet access on first install to download engines
- NVIDIA GPU recommended for AI segmentation

## Acknowledgements

- PartUV: https://github.com/EricWang12/PartUV
- UVgami (upstream): https://github.com/danielboxer/UVgami
- PartField checkpoint: https://huggingface.co/mikaelaangel/partfield-ckpt

## License

GPL-3.0-or-later (UVgami) + MIT. PartUV wheel is CUDA and PartField checkpoint is NVIDIA non-commercial.
