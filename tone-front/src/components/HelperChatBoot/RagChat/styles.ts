import styled from 'styled-components';

/** 面板内容区是 400 × 412（外框 500 高，减去标题栏 48、标签栏 40），和原来的「常见问题」一样大 */
export const Wrapper = styled.div`
    width: 400px;
    height: 412px;
    display: flex;
    flex-direction: column;
    background-color: #f0f3f6;
`;

export const MessageList = styled.div`
    position: relative; /* 让子元素的 offsetTop 以它为基准，自动滚动要用 */
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
`;

export const UserBubble = styled.div`
    align-self: flex-end;
    max-width: 300px;
    background-color: #205ce8;
    color: #fff;
    border-radius: 10px 0 10px 10px;
    padding: 9px 14px;
    font-size: 14px;
    line-height: 22px;
    word-break: break-all;
`;

export const BotBubble = styled.div`
    align-self: flex-start;
    width: 340px;
    background-color: #fff;
    border-radius: 0 10px 10px 10px;
    padding: 12px 14px;
    font-size: 14px;
    line-height: 22px;
    color: rgba(0, 0, 0, 0.85);

    .rag-answer {
        word-break: break-word;
        p {
            margin: 0 0 6px;
        }
        ol,
        ul {
            padding-left: 20px;
            margin: 0 0 6px;
        }
        pre {
            background: #f5f5f5;
            padding: 8px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
            margin: 4px 0 8px;
        }
        code {
            background: #f5f5f5;
            padding: 0 4px;
            border-radius: 3px;
            font-size: 12px;
        }
        pre code {
            padding: 0;
        }
    }

    .rag-cite {
        background: transparent;
        border: 0;
        padding: 0;
        font-size: 0.75em;
        vertical-align: super;
        color: #205ce8;
        cursor: pointer;
        font-weight: 500;
        margin: 0 1px;
    }

    .rag-label {
        margin-top: 10px;
        margin-bottom: 4px;
        font-size: 12px;
        font-weight: 500;
        color: rgba(0, 0, 0, 0.45);
    }

    .rag-meta {
        margin-top: 8px;
        font-size: 12px;
        color: #bfbfbf;
    }
`;

export const SourceItem = styled.a<{ $cited: boolean; $active: boolean }>`
    display: flex;
    gap: 4px;
    padding: 2px 4px;
    border-radius: 4px;
    font-size: 12px;
    line-height: 20px;
    color: ${({ $cited }) => ($cited ? '#205ce8' : 'rgba(0, 0, 0, 0.45)')} !important;
    background-color: ${({ $active }) => ($active ? '#e6f0ff' : 'transparent')};
    transition: background-color 0.3s;

    .idx {
        flex-shrink: 0;
    }
    .text {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    &:hover .text {
        text-decoration: underline;
    }
`;

export const FollowUps = styled.div`
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;

    button {
        height: auto;
        max-width: 100%;
        white-space: normal;
        text-align: left;
        border-radius: 12px;
        font-size: 12px;
        padding: 2px 10px;
    }
`;

export const InputBar = styled.div`
    height: 48px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 12px 0 16px;
    background-color: #fff;
    border-radius: 0 0 10px 10px;

    .ant-input {
        height: 32px;
        border-radius: 16px;
        background-color: #f0f2f5;
        border-color: transparent;
    }
    .ant-input:focus {
        box-shadow: none;
        border-color: #205ce8;
    }
`;
