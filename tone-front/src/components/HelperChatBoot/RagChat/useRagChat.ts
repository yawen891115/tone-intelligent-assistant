import { useCallback, useEffect, useRef, useState } from 'react';
import { askAssistant } from './service';
import type { AssistantMessage, ChatMessage, ChatTurn, RetrievalMode } from './types';

let seq = 0;
const uid = () => `${Date.now().toString(36)}-${(seq += 1)}`;

/** 把已经完成的对话整理成 history，只带最近 2 轮，让大模型能理解"它""这个"指的是什么 */
export function toHistory(messages: ChatMessage[]): ChatTurn[] {
    const turns: ChatTurn[] = [];
    messages.forEach((m) => {
        if (m.role === 'assistant' && m.status === 'done' && m.reply) {
            turns.push({ role: 'user', content: m.question }, { role: 'assistant', content: m.reply.answer.slice(0, 1000) });
        }
    });
    return turns.slice(-4);
}

/**
 * 聊天状态管理：messages 列表 + 三个动作
 *   ask(问题)     发送问题（推荐追问被点击时也是调用它）
 *   retry(消息id) 某条回答失败后重试
 *   clear()       清空对话
 */
export function useRagChat(options: { mode?: RetrievalMode; topK?: number } = {}) {
    const { mode = 'hybrid', topK = 5 } = options;
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const messagesRef = useRef<ChatMessage[]>(messages);
    messagesRef.current = messages; // 回调里读最新的 messages，避免闭包拿到旧值
    const abortRef = useRef<AbortController | null>(null);

    useEffect(() => () => abortRef.current?.abort(), []); // 组件卸载时取消还没回来的请求

    const isLoading = (list: ChatMessage[]) =>
        list.some((m) => m.role === 'assistant' && m.status === 'loading');

    const run = useCallback(
        async (botId: string, question: string, history: ChatTurn[]) => {
            const controller = new AbortController();
            abortRef.current = controller;
            const patch = (p: Partial<AssistantMessage>) =>
                setMessages((prev) =>
                    prev.map((m) => (m.id === botId ? ({ ...m, ...p } as AssistantMessage) : m)),
                );
            try {
                const reply = await askAssistant({ question, history, mode, top_k: topK }, controller.signal);
                patch({ status: 'done', reply });
            } catch (e) {
                const err = e as Error;
                if (err.name === 'AbortError') return;
                patch({ status: 'error', error: err.message || '请求失败' });
            } finally {
                if (abortRef.current === controller) abortRef.current = null;
            }
        },
        [mode, topK],
    );

    const ask = useCallback(
        (text: string) => {
            const question = text.trim();
            if (!question || abortRef.current || isLoading(messagesRef.current)) return; // 上一个问题还没回答完，先不发
            const history = toHistory(messagesRef.current);
            const botId = uid();
            const now = Date.now();
            setMessages((prev) => [
                ...prev,
                { id: uid(), role: 'user', text: question, time: now },
                { id: botId, role: 'assistant', status: 'loading', question, time: now },
            ]);
            run(botId, question, history);
        },
        [run],
    );

    const retry = useCallback(
        (botId: string) => {
            const list = messagesRef.current;
            const idx = list.findIndex((m) => m.id === botId);
            const msg = list[idx];
            if (!msg || msg.role !== 'assistant' || abortRef.current || isLoading(list)) return;
            setMessages((prev) =>
                prev.map((m) => (m.id === botId ? { ...msg, status: 'loading', error: undefined } : m)),
            );
            run(botId, msg.question, toHistory(list.slice(0, Math.max(0, idx - 1))));
        },
        [run],
    );

    const clear = useCallback(() => {
        abortRef.current?.abort();
        abortRef.current = null;
        setMessages([]);
    }, []);

    return { messages, loading: isLoading(messages), ask, retry, clear };
}
