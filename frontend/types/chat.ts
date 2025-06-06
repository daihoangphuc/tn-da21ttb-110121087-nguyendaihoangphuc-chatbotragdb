export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    id: string;
    title: string;
    page: string;
    relevance: number;
  }>;
  citations?: Array<{
    id: string;
    text: string;
    sourceId: string;
  }>;
} 