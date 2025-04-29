from typing import List, Dict, Any, Optional
import json
import re

from src.llm import GeminiLLM
from src.utils import measure_time


class QueryDecomposer:
    """Lớp phân tích và phân rã truy vấn phức tạp thành các truy vấn đơn giản hơn"""

    def __init__(self):
        """Khởi tạo query decomposer với LLM"""
        self.llm = GeminiLLM()

        # System prompt để hướng dẫn LLM về cách phân rã truy vấn
        self.system_prompt = """
        Bạn là một hệ thống trí tuệ nhân tạo chuyên phân tích và phân rã câu hỏi phức tạp thành các câu hỏi đơn giản hơn.
        Nhiệm vụ của bạn là:
        1. Phân tích câu hỏi gốc và xác định xem nó có phức tạp hay không
        2. Nếu câu hỏi đơn giản (chỉ hỏi về một khía cạnh), giữ nguyên và trả về chính câu hỏi đó
        3. Nếu câu hỏi phức tạp, phân rã thành 2-4 câu hỏi đơn giản, mỗi câu hỏi tập trung vào một khía cạnh
        4. Đảm bảo các câu hỏi phân rã có thể được kết hợp lại để trả lời câu hỏi gốc
        5. Trả về kết quả dưới dạng JSON với cấu trúc:
           {
             "is_complex": true/false,
             "sub_queries": ["câu hỏi 1", "câu hỏi 2", ...]
           }
        """

        # Các mẫu để nhận diện câu hỏi phức tạp
        self.complex_patterns = [
            r"so sánh|compare",
            r"khác nhau|differences between",
            r"giống nhau|similarities",
            r"ưu điểm và nhược điểm|pros and cons",
            r"vừa.*vừa|both.*and",
            r"không chỉ.*mà còn|not only.*but also",
            r"ngoài.*còn có|besides.*also",
            r"và|and",
            r"hoặc|or",
            r"lần lượt|in sequence",
            r"thứ nhất.*thứ hai|first.*second",
            r"một mặt.*mặt khác|on one hand.*on the other",
            r"trước.*sau|before.*after",
            r"nguyên nhân.*kết quả|cause.*effect",
            r"làm thế nào|how to",
            r"tại sao|why",
        ]

    def _is_complex_query(self, query: str) -> bool:
        """Kiểm tra xem một truy vấn có phức tạp hay không

        Args:
            query: Câu truy vấn cần kiểm tra

        Returns:
            True nếu truy vấn phức tạp, False nếu không
        """
        # Kiểm tra độ dài (truy vấn dài thường phức tạp)
        if len(query.split()) > 15:
            return True

        # Kiểm tra các pattern chỉ ra truy vấn phức tạp
        for pattern in self.complex_patterns:
            if re.search(pattern, query.lower()):
                return True

        # Kiểm tra số lượng dấu câu
        punctuation_count = len(re.findall(r"[,;:]", query))
        if punctuation_count >= 2:
            return True

        # Kiểm tra số lượng dấu hỏi (có thể hỏi nhiều câu hỏi)
        question_count = len(re.findall(r"\?", query))
        if question_count >= 2:
            return True

        return False

    @measure_time
    def decompose_query(self, query: str) -> Dict[str, Any]:
        """Phân rã truy vấn phức tạp thành các truy vấn đơn giản hơn

        Args:
            query: Câu truy vấn cần phân rã

        Returns:
            Dict chứa kết quả phân rã
        """
        print(f"⏳ Đang phân tích và phân rã truy vấn: '{query}'")

        # Kiểm tra nhanh xem truy vấn có phức tạp không
        is_complex = self._is_complex_query(query)

        if not is_complex:
            print("ℹ️ Truy vấn đơn giản, không cần phân rã")
            return {"is_complex": False, "sub_queries": [query]}

        # Xây dựng prompt cho LLM
        prompt = f"""
        {self.system_prompt}
        
        Phân tích và phân rã câu hỏi sau: "{query}"
        
        Trả về kết quả dưới dạng JSON. Chỉ trả về đúng định dạng JSON, không có giải thích hay ghi chú.
        """

        # Gọi LLM để phân rã truy vấn
        try:
            response = self.llm.generate_text(prompt)

            # Trích xuất phần JSON từ kết quả
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Nếu không có định dạng markdown code block, thử lấy toàn bộ kết quả
                json_str = response.strip()

            # Parse JSON
            result = json.loads(json_str)

            # Đảm bảo kết quả có đúng format
            if "is_complex" not in result or "sub_queries" not in result:
                raise ValueError("Kết quả không đúng định dạng")

            print(
                f"✅ Đã phân rã truy vấn thành {len(result['sub_queries'])} truy vấn con"
            )
            return result

        except Exception as e:
            print(f"⚠️ Lỗi khi phân rã truy vấn: {str(e)}")
            # Trả về kết quả mặc định
            return {"is_complex": True, "sub_queries": [query]}

    def generate_query_plan(self, query: str) -> Dict[str, Any]:
        """Tạo kế hoạch truy vấn cho truy vấn phức tạp

        Args:
            query: Câu truy vấn gốc

        Returns:
            Dict chứa kế hoạch truy vấn
        """
        # Phân rã truy vấn
        decomposed = self.decompose_query(query)

        # Nếu truy vấn là đơn giản, không cần kế hoạch
        if not decomposed["is_complex"]:
            return {
                "original_query": query,
                "is_complex": False,
                "sub_queries": decomposed["sub_queries"],
                "execution_plan": "direct",
                "reasoning_required": False,
            }

        # Xác định xem có cần suy luận nhiều bước không
        reasoning_required = len(decomposed["sub_queries"]) > 2

        # Tạo kế hoạch truy vấn
        plan = {
            "original_query": query,
            "is_complex": True,
            "sub_queries": decomposed["sub_queries"],
            "execution_plan": "sequential" if reasoning_required else "parallel",
            "reasoning_required": reasoning_required,
        }

        return plan


class MultiStepReasoner:
    """Lớp thực hiện suy luận nhiều bước cho các câu hỏi phức tạp"""

    def __init__(self, retriever=None):
        """Khởi tạo MultiStepReasoner

        Args:
            retriever: Đối tượng retriever để truy xuất tài liệu (nếu cần)
        """
        self.llm = GeminiLLM()
        self.retriever = retriever
        self.decomposer = QueryDecomposer()

    @measure_time
    def answer_with_reasoning(
        self, query: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trả lời câu hỏi phức tạp bằng cách suy luận nhiều bước

        Args:
            query: Câu hỏi phức tạp
            context: Context sẵn có (nếu không cung cấp sẽ tự động truy xuất)

        Returns:
            Dict chứa kết quả trả lời
        """
        print(f"⏳ Đang thực hiện suy luận nhiều bước cho câu hỏi: '{query}'")

        # 1. Phân rã truy vấn và tạo kế hoạch
        query_plan = self.decomposer.generate_query_plan(query)

        # 2. Nếu truy vấn đơn giản, xử lý trực tiếp
        if not query_plan["is_complex"]:
            print(f"ℹ️ Câu hỏi đơn giản, xử lý trực tiếp")
            # Truy xuất tài liệu nếu chưa có context
            if context is None and self.retriever:
                docs = self.retriever.retrieve(query)
                context = "\n\n".join([doc.page_content for doc in docs])

            # Tạo câu trả lời
            answer = self._generate_answer(query, context)
            return {"answer": answer, "reasoning_steps": [], "is_complex": False}

        # 3. Xử lý truy vấn phức tạp
        sub_queries = query_plan["sub_queries"]
        reasoning_steps = []

        # 3.1 Xử lý từng sub-query
        for i, sub_query in enumerate(sub_queries):
            print(f"⏳ Đang xử lý sub-query {i+1}/{len(sub_queries)}: '{sub_query}'")

            # Truy xuất tài liệu cho sub-query
            if self.retriever:
                sub_docs = self.retriever.retrieve(sub_query)
                sub_context = "\n\n".join([doc.page_content for doc in sub_docs])
            else:
                sub_context = context

            # Tạo câu trả lời cho sub-query
            sub_answer = self._generate_answer(sub_query, sub_context)

            # Thêm vào reasoning_steps
            reasoning_steps.append(
                {"step": i + 1, "sub_query": sub_query, "sub_answer": sub_answer}
            )

        # 3.2 Tổng hợp kết quả
        # Tạo prompt tổng hợp
        synthesis_prompt = self._create_synthesis_prompt(query, reasoning_steps)

        # Gọi LLM để tổng hợp
        final_answer = self.llm.generate_text(synthesis_prompt)

        # Làm sạch kết quả
        final_answer = final_answer.strip()

        print(f"✅ Đã hoàn thành suy luận nhiều bước")

        return {
            "answer": final_answer,
            "reasoning_steps": reasoning_steps,
            "is_complex": True,
        }

    def _generate_answer(self, query: str, context: str) -> str:
        """Tạo câu trả lời cho một câu hỏi từ context

        Args:
            query: Câu hỏi
            context: Context chứa thông tin

        Returns:
            Câu trả lời
        """
        prompt = f"""
        Dựa trên thông tin sau đây, hãy trả lời câu hỏi một cách đầy đủ và chính xác.
        
        Câu hỏi: {query}
        
        Thông tin:
        {context}
        
        Câu trả lời:
        """

        return self.llm.generate_text(prompt)

    def _create_synthesis_prompt(
        self, query: str, reasoning_steps: List[Dict[str, Any]]
    ) -> str:
        """Tạo prompt để tổng hợp các bước suy luận

        Args:
            query: Câu hỏi gốc
            reasoning_steps: Các bước suy luận

        Returns:
            Prompt tổng hợp
        """
        steps_text = ""
        for step in reasoning_steps:
            steps_text += f"Bước {step['step']}: {step['sub_query']}\nKết quả: {step['sub_answer']}\n\n"

        prompt = f"""
        Bạn cần tổng hợp các kết quả từ nhiều bước suy luận thành một câu trả lời hoàn chỉnh.
        
        Câu hỏi gốc: {query}
        
        Dưới đây là kết quả từ các bước suy luận:
        {steps_text}
        
        Hãy tổng hợp thông tin và đưa ra câu trả lời hoàn chỉnh cho câu hỏi gốc. Trả lời nên mạch lạc, rõ ràng và đầy đủ.
        Đảm bảo kết hợp thông tin từ tất cả các bước suy luận một cách hợp lý.
        
        Câu trả lời tổng hợp:
        """

        return prompt
