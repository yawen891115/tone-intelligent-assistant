import React from 'react';
import { Button, Input, Typography } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import AssistantBubble from './AssistantBubble';
import { useRagChat } from './useRagChat';
import { BotBubble, FollowUps, InputBar, MessageList, UserBubble, Wrapper } from './styles';
import type { RetrievalMode } from './types';

export interface RagChatProps {
    mode?: RetrievalMode;
    topK?: number;
    starterQuestions?: string[]; // 欢迎语下面的示例问题
}

const DEFAULT_STARTERS = [
    '怎么把自己的服务器接入 T-One？',
    '提交的测试一直在排队是怎么回事？',
    'tone-cli 有哪些常用命令？',
];

/**
 * T-One 答疑助手的「智能问答」标签页：
 *   基于帮助文档的混合检索（BM25 + 向量）回答问题，回答附带可点击的来源链接和推荐追问。
 */
const RagChat: React.FC<RagChatProps> = ({ mode = 'hybrid', topK = 5, starterQuestions = DEFAULT_STARTERS }) => {
    const { messages, loading, ask, retry } = useRagChat({ mode, topK });
    const [input, setInput] = React.useState('');
    const listRef = React.useRef<HTMLDivElement>(null);

    // 自动滚动：提问 / 加载中 → 滚到底部；回答完成 → 把刚才的问题滚到顶部，让用户从回答的开头读起
    React.useEffect(() => {
        const el = listRef.current;
        if (!el) return;
        const last = messages[messages.length - 1];
        const questions = el.querySelectorAll<HTMLElement>('[data-role="user"]');
        const lastQuestion = questions[questions.length - 1];
        if (last?.role === 'assistant' && last.status === 'done' && lastQuestion) {
            el.scrollTo({ top: lastQuestion.offsetTop - 12, behavior: 'smooth' });
        } else {
            el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
        }
    }, [messages]);

    const send = (text: string) => {
        if (!text.trim() || loading) return;
        ask(text);
        setInput('');
    };

    return (
        <Wrapper>
            <MessageList ref={listRef}>
                <BotBubble>
                    <div>你好，我是 T-One 智能助手，会根据平台帮助文档回答问题，并附上来源链接。可以试试：</div>
                    <FollowUps style={{ marginTop: 8 }}>
                        {starterQuestions.map((q) => (
                            <Button key={q} size="small" type="dashed" disabled={loading} onClick={() => send(q)}>
                                {q}
                            </Button>
                        ))}
                    </FollowUps>
                </BotBubble>

                {messages.map((m) =>
                    m.role === 'user' ? (
                        <UserBubble key={m.id} data-role="user">
                            {m.text}
                        </UserBubble>
                    ) : (
                        <AssistantBubble key={m.id} message={m} onAsk={send} onRetry={retry} disabled={loading} />
                    ),
                )}
            </MessageList>

            <InputBar>
                <Input
                    placeholder="输入问题，回车发送"
                    value={input}
                    maxLength={500}
                    onChange={(e) => setInput(e.target.value)}
                    onPressEnter={(e) => {
                        if (!e.nativeEvent.isComposing && e.nativeEvent.keyCode !== 229) send(input);
                    }}
                />
                <Typography.Link disabled={loading || !input.trim()} onClick={() => send(input)} aria-label="发送">
                    <SendOutlined style={{ fontSize: 18 }} />
                </Typography.Link>
            </InputBar>
        </Wrapper>
    );
};

export default RagChat;
