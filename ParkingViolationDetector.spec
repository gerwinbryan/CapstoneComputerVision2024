# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\Dominic\\PycharmProjects\\pythonProject1\\project\\models', 'models'), ('C:\\Users\\Dominic\\PycharmProjects\\pythonProject1\\yolov8\\PaddleOCR\\tools', 'tools'), ('C:\\Users\\Dominic\\miniconda3\\envs\\pythonProject1\\Lib\\site-packages\\paddle\\libs', 'paddle/libs'), ('C:\\Users\\Dominic\\PycharmProjects\\pythonProject1\\yolov8\\PaddleOCR\\ppocr', 'ppocr')]
binaries = []
hiddenimports = ['paddleocr', 'paddle', 'ultralytics', 'cv2', 'numpy', 'PIL', 'skimage', 'shapely', 'pyclipper', 'lanms']
tmp_ret = collect_all('paddleocr')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('paddle')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ultralytics')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
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
    name='ParkingViolationDetector',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
    name='ParkingViolationDetector',
)
