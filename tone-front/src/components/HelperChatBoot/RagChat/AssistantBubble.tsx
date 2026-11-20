import React from 'react';
import { Button, Spin, Tooltip, Typography } from 'antd';
import { renderAnswer } from './markdown';
import { BotBubble, FollowUps, SourceItem } from './styles';
import type { AssistantMessage, SourceRef } from './types';

interface Props {
    message: AssistantMessage;
    onAsk: (question: string) => void; // 点击推荐追问
    onRetry: (id: string) => void;
    disabled: boolean; // 有问题正在回答时，追问按钮先禁用
}

const sourceLabel = (s: SourceRef) => (s.section ? `${s.title} › ${s.section}` : s.title);

function sourceHref(raw: string): string | undefined {
    if (!raw.trim()) return undefined;
    try {
        const url = new URL(raw, window.location.href);
        return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined;
    } catch {
        return undefined;
    }
}

const AssistantBubble: React.FC<Props> = ({ message, onAsk, onRetry, disabled }) => {
    const [active, setActive] = React.useState<number | null>(null);
    const listRef = React.useRef<HTMLDivElement>(null);
    const { reply } = message;

    const html = React.useMemo(
        () => (reply ? renderAnswer(reply.answer, reply.sources.length) : ''),
        [reply],
    );

    // 点击正文里的 [n]：滚动到第 n 个来源并高亮 1.5 秒
    const handleAnswerClick = (e: React.MouseEvent<HTMLDivElement>) => {
        const target = (e.target as HTMLElement).closest('[data-cite]');
        if (!target) return;
        const idx = Number(target.getAttribute('data-cite'));
        setActive(idx);
        listRef.current
            ?.querySelector(`[data-source="${idx}"]`)
            ?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        window.setTimeout(() => setActive(null), 1500);
    };

    if (message.status === 'loading') {
        return (
            <BotBubble>
                <Spin size="small" /> <Typography.Text type="secondary">正在检索文档并生成回答…</Typography.Text>
            </BotBubble>
        );
    }

    if (message.status === 'error' || !reply) {
        return (
            <BotBubble>
                <Typography.Text type="danger">{message.error || '出错了'}</Typography.Text>{' '}
                <Typography.Link onClick={() => onRetry(message.id)}>重试</Typography.Link>
            </BotBubble>
        );
    }

    return (
        <BotBubble>
            {reply.warning && (
                <Typography.Text type="warning" style={{ fontSize: 12 }}>
                    {reply.warning}
                </Typography.Text>
            )}

            {/* renderAnswer 内部已经用 DOMPurify 清洗过，可以安全地插入 */}
            <div className="rag-answer" onClick={handleAnswerClick} dangerouslySetInnerHTML={{ __html: html }} />

            {reply.sources.length > 0 && (
                <div ref={listRef}>
                    <div className="rag-label">参考来源</div>
                    {reply.sources.map((s) => (
                        <Tooltip key={s.chunk_id} title={s.snippet} placement="left" mouseEnterDelay={0.5}>
                            <SourceItem
                                href={sourceHref(s.url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                data-source={s.index}
                                $cited={s.cited}
                                $active={active === s.index}
                            >
                                <span className="idx">[{s.index}]</span>
                                <span className="text">{sourceLabel(s)}</span>
                            </SourceItem>
                        </Tooltip>
                    ))}
                </div>
            )}

            {reply.follow_ups.length > 0 && (
                <>
                    <div className="rag-label">你可能还想问</div>
                    <FollowUps>
                        {reply.follow_ups.map((q) => (
                            <Button key={q} size="small" disabled={disabled} onClick={() => onAsk(q)}>
                                {q}
                            </Button>
                        ))}
                    </FollowUps>
                </>
            )}

            <div className="rag-meta">
                {reply.mode} 检索 · {reply.latency_ms} ms{reply.llm_used ? '' : ' · 未使用大模型'}
                {reply.query && reply.query !== message.question && (
                    <div>按「{reply.query}」检索（结合了上文）</div>
                )}
            </div>
        </BotBubble>
    );
};

export default AssistantBubble;
