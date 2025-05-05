@echo off
echo === Cai dat Layout Detection - EfficientDet ===
call venv\Scripts\activate

echo Cap nhat pip...
python -m pip install --upgrade pip

echo Cai dat PyTorch va TorchVision (can thiet cho EfficientDet)...
pip install torch>=1.10.0 torchvision>=0.11.0 torchaudio

echo Cai dat cac goi co ban...
pip install opencv-python PyMuPDF pdf2image pytesseract Pillow 

echo Cai dat LayoutParser voi EfficientDet backend...
pip install layoutparser[effdet]

echo.
echo === Hoan thanh ===
echo Cac goi can thiet da duoc cai dat. Vui long kiem tra bang cach chay python test_layout_detection.py
echo Hay dam bao ENABLE_LAYOUT_DETECTION=true trong file .env.

pause 