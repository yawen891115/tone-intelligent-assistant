/**
 * 智能问答（RAG）的数据类型，和后端 backend/rag/api.py 里的 Pydantic 模型一一对应。
 */

export type RetrievalMode = 'hybrid' | 'dense' | 'sparse';

/** 一条参考来源：回答里的 [index] 就指向它 */
export interface SourceRef {
    index: number;
    chunk_id: string;
    doc_id: string;
    title: string;
    section: string;
    url: string;
    snippet: string;
    score: number;
    cited: boolean; // 回答正文里有没有引用它
}

/** 后端 /api/assistant/chat 返回的 data */
export interface AssistantReply {
    answer: string; // Markdown
    sources: SourceRef[];
    follow_ups: string[]; // 可点击的推荐追问
    query: string; // 实际用于检索的语句（多轮追问会被改写成独立问题）
    mode: RetrievalMode;
    latency_ms: number;
    llm_used: boolean;
    warning?: string | null;
}

/** T-One 接口统一的外层格式 */
export interface ApiEnvelope<T> {
    code: number;
    msg: string;
    data: T;
}

export interface ChatTurn {
    role: 'user' | 'assistant';
    content: string;
}

export interface ChatRequest {
    question: string;
    history?: ChatTurn[];
    mode?: RetrievalMode;
    top_k?: number;
}

/** 界面上的一条消息：用户消息 或 助手消息（有加载中 / 成功 / 失败三种状态） */
export interface UserMessage {
    id: string;
    role: 'user';
    text: string;
    time: number;
}

export interface AssistantMessage {
    id: string;
    role: 'assistant';
    time: number;
    question: string; // 对应的问题，重试时要用
    status: 'loading' | 'done' | 'error';
    reply?: AssistantReply;
    error?: string;
}

export type ChatMessage = UserMessage | AssistantMessage;
