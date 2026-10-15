import shutil
import importlib
import sys
from pathlib import Path

checks = []

def is_tool_installed(tool_name: str, fallback_paths: list[str] | None = None) -> bool:
    if shutil.which(tool_name) is not None:
        return True
    if fallback_paths:
        for p in fallback_paths:
            if Path(p).exists():
                return True
    return False

# System tools
checks.append(('soffice (LibreOffice)', is_tool_installed('soffice', [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
])))
checks.append(('tesseract (OCR)', is_tool_installed('tesseract', [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
])))

# Python packages
pkgs = ['docx', 'python_docx', 'pptx', 'reportlab', 'PyPDF2', 'PIL', 'docx2pdf', 'comtypes', 'win32com']
# Mapping to import names
imports = {
    'docx': 'docx',
    'python_docx': 'docx',
    'pptx': 'pptx',
    'reportlab': 'reportlab',
    'PyPDF2': 'PyPDF2',
    'PIL': 'PIL',
    'docx2pdf': 'docx2pdf',
    'comtypes': 'comtypes',
    'win32com': 'win32com'
}

for key in pkgs:
    name = imports.get(key, key)
    try:
        spec = importlib.util.find_spec(name)
        ok = spec is not None
    except Exception:
        ok = False
    checks.append((f'Python package: {name}', ok))

print('Environment check for Mark-L document conversions')
print('Python executable:', sys.executable)
print()
ok_all = True
for desc, ok in checks:
    print(f"- {desc}: {'OK' if ok else 'MISSING'}")
    ok_all = ok_all and ok

print()
if ok_all:
    print('All recommended tools and packages are present.')
else:
    print('Some tools or packages are missing. See suggestions below to install them:')
    print()
    if not shutil.which('soffice'):
        print('Install LibreOffice and ensure `soffice` is on your PATH. Download: https://www.libreoffice.org/download/download/')
    if not shutil.which('tesseract'):
        print('Install Tesseract OCR if you need scanned PDF OCR: https://github.com/tesseract-ocr/tesseract')
    print('\nInstall Python packages into the interpreter you run Mark-L with:')
    print('  pip install python-docx python-pptx reportlab PyPDF2 Pillow docx2pdf comtypes pywin32')

print('\nNote: For best fidelity DOCX/PPTX->PDF conversion on Windows, install Microsoft Office or LibreOffice. COM automation requires Word/PowerPoint installed.')
