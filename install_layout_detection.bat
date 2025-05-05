@echo off
echo === Cai dat Layout Parser don gian ===
call venv\Scripts\activate

echo Cap nhat pip...
python -m pip install --upgrade pip

echo Cai dat cac goi co ban can thiet...
pip install opencv-python PyMuPDF pdf2image pytesseract Pillow layoutparser numpy

echo Tao thu muc cho model cache...
mkdir model_cache 2>nul

echo.
echo === Hoan thanh ===
echo Da cai dat layoutparser co ban. He thong se su dung phuong phap layout don gian.
echo.
echo Huong dan su dung:
echo 1. Dat ENABLE_LAYOUT_DETECTION=true trong file .env
echo 2. Khoi dong lai API
echo.
echo Khi gap loi voi detection model, he thong se tu dong chuyen sang phuong phap
echo xu ly don gian, moi trang PDF se duoc coi la mot khoi van ban duy nhat.

pause 