@echo off
echo === Kích hoạt môi trường ảo ===
call venv\Scripts\activate

echo === Nâng cấp pip lên phiên bản mới nhất ===
python -m pip install --upgrade pip

echo === Cài đặt từng gói thư viện riêng biệt ===
pip install qdrant-client
pip install sentence-transformers
pip install langchain
pip install langchain-google-genai
pip install google-generativeai
pip install python-dotenv
pip install pypdf
pip install docx2txt
pip install rank_bm25
pip install "unstructured[local-inference]"
pip install langchain-community
pip install langchain-text-splitters

echo.
echo === Cài đặt hoàn tất ===
echo.

pause 