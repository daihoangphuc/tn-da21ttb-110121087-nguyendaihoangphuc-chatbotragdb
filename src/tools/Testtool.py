import os
import argparse
import requests
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if USE_GEMINI:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage


class WebSearchAgent:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        if USE_GEMINI:
            self.llm = ChatGoogleGenerativeAI(
                model=LLM_MODEL_NAME, temperature=0, google_api_key=GOOGLE_API_KEY
            )

    def query(self, question: str) -> dict:
        try:
            if SERPER_API_KEY:
                search_results = self.search_with_serper(question)
            elif TAVILY_API_KEY:
                search_results = self.search_with_tavily(question)
            else:
                return {
                    "success": False,
                    "error": "No API key found in environment variables.",
                }

            if not search_results["success"]:
                return search_results

            if USE_GEMINI:
                prompt = self.build_search_prompt(question, search_results["data"])
                response = self.llm.invoke([HumanMessage(content=prompt)])
                return {"success": True, "response": response.content}
            else:
                return {"success": True, "response": search_results["response"]}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_with_serper(self, query: str) -> dict:
        if self.verbose:
            print("🔎 Using Serper API...")

        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY}
        payload = {"q": query}

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "organic" not in data:
            return {"success": False, "error": "No results from Serper."}

        results = data["organic"][:5]
        result_text = ""
        for item in results:
            result_text += f"- {item.get('title')}\n  {item.get('link')}\n  {item.get('snippet')}\n\n"

        return {"success": True, "response": result_text, "data": results}

    def search_with_tavily(self, query: str) -> dict:
        if self.verbose:
            print("🔎 Using Tavily API...")

        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
        }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "results" not in data:
            return {"success": False, "error": "No results from Tavily."}

        results = data["results"][:5]
        result_text = ""
        for item in results:
            result_text += f"- {item.get('title')}\n  {item.get('url')}\n  {item.get('content')}\n\n"

        return {"success": True, "response": result_text, "data": results}

    def build_search_prompt(self, query: str, web_results: List[dict]) -> str:
        prompt = f"""Dưới đây là một số kết quả tìm kiếm liên quan đến truy vấn "{query}". Hãy tóm tắt câu trả lời từ các nguồn này và trích dẫn nguồn cụ thể (URL) trong mỗi ý quan trọng.

"""
        for idx, result in enumerate(web_results, start=1):
            title = result.get("title", "")
            link = result.get("link") or result.get("url", "")
            snippet = result.get("snippet") or result.get("content", "")
            prompt += f"[{idx}] {title}\nURL: {link}\n{snippet}\n\n"

        prompt += f"""
Dựa trên các tài liệu và URL ở trên, hãy trả lời câu hỏi: "{query}"

👉 Lưu ý:
- Mỗi ý chính nên kèm theo URL gốc tương ứng.
- KHÔNG bịa thông tin. Nếu không đủ dữ liệu, hãy nói rõ.
"""
        return prompt


def main():
    parser = argparse.ArgumentParser(description="Simple Web Search Agent")
    parser.add_argument("--query", "-q", type=str, help="Query to search")
    parser.add_argument("--batch", "-b", type=str, help="File with list of queries")
    parser.add_argument("--output", "-o", type=str, help="File to save results")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    agent = WebSearchAgent(verbose=args.verbose)

    if args.batch:
        batch_process(agent, args.batch, args.output)
    elif args.query:
        single_query(agent, args.query, args.output)
    else:
        interactive_mode(agent)


def single_query(agent: WebSearchAgent, query: str, output_file: Optional[str] = None):
    print(f"\n🔍 Query: {query}")
    result = agent.query(query)

    if result["success"]:
        print("\n📚 RESULT:")
        print(result["response"])

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Query: {query}\n\n{result['response']}")
    else:
        print(f"\n❌ ERROR: {result['error']}")


def batch_process(
    agent: WebSearchAgent, file_path: str, output_file: Optional[str] = None
):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]

        results = []
        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{len(queries)}] 🔍 {query}")
            result = agent.query(query)
            if result["success"]:
                results.append(
                    f"Query [{i+1}]: {query}\n{result['response']}\n" + "-" * 80 + "\n"
                )
            else:
                results.append(
                    f"Query [{i+1}]: {query}\nERROR: {result['error']}\n"
                    + "-" * 80
                    + "\n"
                )

        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                f.writelines(results)
            print(f"\n✅ Results saved to {output_file}")
        else:
            print("\n".join(results))

    except Exception as e:
        print(f"❌ Error: {e}")


def interactive_mode(agent: WebSearchAgent):
    print("\n=== Web Search Agent Interactive Mode ===")
    print("Type 'exit' to quit\n")

    while True:
        query = input("🔍 Your question: ")
        if query.lower() in ["exit", "quit"]:
            print("👋 Bye!")
            break
        if not query.strip():
            continue

        result = agent.query(query)
        if result["success"]:
            print("\n📚 RESULT:")
            print(result["response"])
        else:
            print(f"\n❌ ERROR: {result['error']}")


if __name__ == "__main__":
    main()
