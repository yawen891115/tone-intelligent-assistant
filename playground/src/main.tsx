import React from 'react';
import ReactDOM from 'react-dom';
import { Radio, Typography } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import styled from 'styled-components';
import 'antd/dist/antd.css';
import RagChat from './RagChat';
import type { RetrievalMode } from './RagChat/types';

/* 模仿 T-One 右下角答疑助手面板的外框（400 × 500），方便直接看到组件嵌进去之后的效果 */
const Page = styled.div`
    min-height: 100vh;
    background: #f5f7fa;
    display: flex;
    gap: 32px;
    justify-content: center;
    align-items: flex-start;
    padding: 32px;
`;
const Panel = styled.div`
    width: 400px;
    height: 500px;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 0 6px 0 rgba(0, 0, 0, 0.12), 0 0 12px 5px rgba(0, 0, 0, 0.09);
    background: #f0f3f6;
`;
const Navbar = styled.div`
    height: 48px;
    background: #fff;
    border-bottom: 1px solid #d9d9d9;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 16px;
`;
const Tabs = styled.div`
    height: 40px;
    background: #fff;
    border-bottom: 1px solid #d9d9d9;
    display: flex;
    div {
        flex: 1;
        display: flex;
        justify-content: center;
        align-items: center;
        color: rgba(0, 0, 0, 0.45);
    }
    .active {
        color: #205ce8;
        font-weight: 500;
    }
`;

const App: React.FC = () => {
    const [mode, setMode] = React.useState<RetrievalMode>('hybrid');
    return (
        <Page>
            <div style={{ width: 260 }}>
                <Typography.Title level={4}>本地预览</Typography.Title>
                <Typography.Paragraph type="secondary">
                    右边是嵌进 T-One 答疑助手后的样子。切换检索模式可以直观对比三种检索的结果。
                </Typography.Paragraph>
                <Radio.Group value={mode} onChange={(e) => setMode(e.target.value)}>
                    <Radio.Button value="hybrid">hybrid</Radio.Button>
                    <Radio.Button value="dense">dense</Radio.Button>
                    <Radio.Button value="sparse">sparse</Radio.Button>
                </Radio.Group>
            </div>
            <Panel>
                <Navbar>
                    <Typography.Text strong>T-One答疑助手</Typography.Text>
                    <CloseOutlined style={{ color: '#BFBFBF' }} />
                </Navbar>
                <Tabs>
                    <div className="active">智能问答</div>
                    <div>常见问题</div>
                    <div>自助排查</div>
                </Tabs>
                <RagChat mode={mode} />
            </Panel>
        </Page>
    );
};

ReactDOM.render(<App />, document.getElementById('root'));
