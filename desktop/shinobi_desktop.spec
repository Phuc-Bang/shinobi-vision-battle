# -*- mode: python ; coding: utf-8 -*-

import glob
import os

from PyInstaller.utils.hooks import collect_dynamic_libs


project_root = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [
    (os.path.join(project_root, "frontend", "assets"), "frontend/assets"),
]

for model_path in glob.glob(os.path.join(project_root, "backend", "*.task")):
    datas.append((model_path, "backend"))

hiddenimports = [
    "mediapipe",
    "mediapipe.tasks",
    "mediapipe.tasks.c",
    "mediapipe.tasks.python",
    "mediapipe.tasks.python.core",
    "mediapipe.tasks.python.vision",
    "mediapipe.tasks.python.vision.hand_landmarker",
    "mediapipe.tasks.python.vision.pose_landmarker",
]

binaries = []
binaries += collect_dynamic_libs("mediapipe")

libmediapipe_path = os.path.join(
    project_root,
    "desktop",
    ".venv",
    "Lib",
    "site-packages",
    "mediapipe",
    "tasks",
    "c",
    "libmediapipe.dll",
)
if os.path.exists(libmediapipe_path):
    binaries.append((libmediapipe_path, "mediapipe/tasks/c"))


a = Analysis(
    [os.path.join(project_root, "desktop", "main.py")],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShinobiVisionBattle",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ShinobiVisionBattle",
)
