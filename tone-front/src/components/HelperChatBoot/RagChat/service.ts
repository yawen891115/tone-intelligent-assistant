import type { ApiEnvelope, AssistantReply, ChatRequest } from './types';

/**
 * 后端地址前缀。开发时由 config/proxy.ts 把 /api/assistant/ 转发到 RAG 服务（默认 localhost:8000），
 * 线上由 nginx 转发，所以这里写相对路径即可。
 */
export const ASSISTANT_API = '/api/assistant';

/** 用原生 fetch 而不是 umi request：支持 AbortController 取消，也方便组件在 tone-front 之外复用 */
export async function askAssistant(body: ChatRequest, signal?: AbortSignal): Promise<AssistantReply> {
    const res = await fetch(`${ASSISTANT_API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
        signal,
    });
    if (!res.ok) {
        throw new Error(
            res.status === 422 ? '问题长度需要在 1~500 字之间' : `助手服务暂时不可用（HTTP ${res.status}）`,
        );
    }
    const json = (await res.json()) as ApiEnvelope<AssistantReply>;
    if (json.code !== 200) {
        throw new Error(json.msg || '助手服务异常');
    }
    return json.data;
}
