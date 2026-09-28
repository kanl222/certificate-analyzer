from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


project_root = Path(SPECPATH).parents[1]
entry_point = project_root / "src" / "certificate_analyzer" / "__main__.py"

hidden_imports = collect_submodules("certificate_analyzer") + [
    "pkg_resources",
    "servicemanager",
    "win32event",
    "win32service",
    "win32serviceutil",
    "win32timezone",
]

analysis = Analysis(
    [str(entry_point)],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

gui = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="CertificateAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

cli = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="certificate-analyzer-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

bundle = COLLECT(
    gui,
    cli,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="CertificateAnalyzer",
)
