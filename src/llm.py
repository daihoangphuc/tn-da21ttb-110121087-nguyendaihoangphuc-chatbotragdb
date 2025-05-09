from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

# Load biến môi trường từ .env
load_dotenv()


class GeminiLLM:
    """Lớp quản lý mô hình ngôn ngữ lớn Gemini"""

    def __init__(self, api_key=None):
        """Khởi tạo mô hình Gemini"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY không được cung cấp")

        # Cấu hình google.generativeai
        genai.configure(api_key=self.api_key)

        # Khởi tạo LangChain wrapper
        self.model = ChatGoogleGenerativeAI(
            model=os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash"),
            google_api_key=self.api_key,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
            top_p=float(os.getenv("LLM_TOP_P", "0.85")),
            max_output_tokens=int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")),
        )

        # Lưu thông tin model
        self.model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")

        # Danh sách các định dạng cần xác nhận trong phản hồi
        self.format_patterns = {
            "code_block": (r"```([\w-]*)\n([\s\S]*?)```", "```{}\n{}\n```"),
            "headings": (r"^(#+)\s+(.*?)$", "{} {}"),
            "tables": (
                r"\|\s*(.*?)\s*\|[\s\S]*?\|\s*[-:]+\s*\|[\s\S]*?\|",
                "Table format correct",
            ),
            "lists": (r"^\s*[-*+]\s+(.*?)$", "- {}"),
            "numbered_lists": (r"^\s*(\d+)[.)]\s+(.*?)$", "{}. {}"),
            "bold": (r"\*\*(.*?)\*\*", "**{}**"),
            "italic": (r"\*(.*?)\*", "*{}*"),
            "blockquote": (r"^>\s+(.*?)$", "> {}"),
        }

    def preprocess_prompt(self, prompt):
        """Tiền xử lý prompt trước khi gửi đến LLM để đảm bảo định dạng nhất quán"""
        # Chỉ xử lý prompt dạng văn bản
        if isinstance(prompt, str):
            # Thêm nhắc nhở về chuẩn định dạng nếu chưa có
            format_reminder = """
            HÃY TRẢ LỜI THEO ĐÚNG ĐỊNH DẠNG MARKDOWN:
            1. Sử dụng ## cho tiêu đề chính và ### cho tiêu đề phụ
            2. Đặt mã SQL trong ```sql và ```, mã khác trong ```language và ```
            3. Sử dụng **in đậm** cho thuật ngữ quan trọng
            4. Sử dụng bảng Markdown khi cần liệt kê và so sánh dữ liệu có cấu trúc
            5. Sử dụng danh sách có dấu gạch đầu dòng (-) hoặc số (1. 2. 3.)
            """

            if "```sql" not in prompt and "Markdown" not in prompt:
                prompt += format_reminder

        return prompt

    def postprocess_response(self, response):
        """Hậu xử lý phản hồi từ LLM để đảm bảo định dạng nhất quán"""
        if not hasattr(response, "content"):
            return response

        content = response.content

        # Đảm bảo các khối mã SQL đúng định dạng
        import re

        # Chuẩn hóa các khối mã không có chỉ định ngôn ngữ
        content = re.sub(r"```\s*\n", "```text\n", content)

        # Đảm bảo các khối mã SQL được định dạng đúng
        sql_blocks = re.findall(r"```(?:sql)?\s*\n(.*?)\n```", content, re.DOTALL)
        for sql_block in sql_blocks:
            # Tìm các truy vấn SQL không có chú thích
            if "--" not in sql_block and "SELECT" in sql_block.upper():
                lines = sql_block.split("\n")
                formatted_lines = []
                for line in lines:
                    line = line.strip()
                    # Thêm chú thích cho các mệnh đề SQL chính nếu chưa có
                    for clause in [
                        "SELECT",
                        "FROM",
                        "WHERE",
                        "GROUP BY",
                        "HAVING",
                        "ORDER BY",
                        "JOIN",
                    ]:
                        if line.upper().startswith(clause) and "--" not in line:
                            line = f"{line} -- Mệnh đề {clause}"
                    formatted_lines.append(line)

                # Thay thế khối mã gốc bằng khối đã định dạng
                content = content.replace(sql_block, "\n".join(formatted_lines))

        # Đảm bảo có tiêu đề chính
        if not re.search(r"^##\s+", content, re.MULTILINE):
            # Tìm dòng đầu tiên có nghĩa để làm tiêu đề
            first_meaningful_line = next(
                (
                    line
                    for line in content.split("\n")
                    if line.strip() and not line.startswith(">")
                ),
                "",
            )
            if first_meaningful_line:
                content = f"## {first_meaningful_line}\n\n" + content.replace(
                    first_meaningful_line, "", 1
                )

        # Đảm bảo bảng Markdown được định dạng đúng
        table_patterns = re.findall(
            r"\|.*\|(?:\s*[\r\n]+\|[-:| ]+\|)?", content, re.MULTILINE
        )
        for table_pattern in table_patterns:
            # Kiểm tra xem bảng có dòng ngăn cách tiêu đề và nội dung không
            if "|---" not in table_pattern and "|:-" not in table_pattern:
                lines = table_pattern.split("\n")
                if len(lines) >= 1:
                    header_line = lines[0]
                    column_count = header_line.count("|") - 1
                    separator_line = "|" + "---|" * column_count

                    # Chèn dòng ngăn cách vào sau dòng tiêu đề
                    new_table = (
                        header_line
                        + "\n"
                        + separator_line
                        + "\n"
                        + "\n".join(lines[1:])
                    )
                    content = content.replace(table_pattern, new_table)

        # Đặt nội dung đã xử lý vào response
        response.content = content

        return response

    def invoke(self, prompt):
        """Gọi mô hình LLM với prompt"""
        processed_prompt = self.preprocess_prompt(prompt)
        response = self.model.invoke(processed_prompt)
        return self.postprocess_response(response)

    async def invoke_streaming(self, prompt):
        """Gọi mô hình LLM với prompt và trả về kết quả dạng streaming"""
        processed_prompt = self.preprocess_prompt(prompt)

        # Sử dụng trực tiếp genai API thay vì langchain wrapper để streaming
        model = genai.GenerativeModel(self.model_name)

        # Chuẩn bị nội dung từ prompt (chuyển từ langchain format sang genai format)
        if hasattr(processed_prompt, "to_messages"):
            # Là một chuỗi messages trong langchain
            messages = processed_prompt.to_messages()
            content = []

            for message in messages:
                role = "user" if message.type == "human" else "model"
                content.append({"role": role, "parts": [{"text": message.content}]})
        else:
            # Là text prompt đơn giản
            content = [{"role": "user", "parts": [{"text": processed_prompt}]}]

        # Gọi model streaming
        stream = await model.generate_content_async(
            content,
            stream=True,
            generation_config={
                "temperature": float(os.getenv("LLM_TEMPERATURE", "0")),
                "top_p": float(os.getenv("LLM_TOP_P", "0.85")),
                "max_output_tokens": int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "2048")),
            },
        )

        # Trả về từng phần response qua generator
        full_response = ""

        async for chunk in stream:
            if hasattr(chunk, "candidates") and chunk.candidates:
                if (
                    hasattr(chunk.candidates[0], "content")
                    and chunk.candidates[0].content.parts
                ):
                    text_chunk = chunk.candidates[0].content.parts[0].text
                    full_response += text_chunk

                    # Áp dụng xử lý cục bộ để đảm bảo định dạng
                    if (
                        "```" in text_chunk
                        and "```" not in full_response[: -len(text_chunk)]
                    ):
                        # Bắt đầu khối mã, kiểm tra nếu không có chỉ định ngôn ngữ
                        if "```\n" in text_chunk:
                            text_chunk = text_chunk.replace("```\n", "```text\n")

                    yield text_chunk
