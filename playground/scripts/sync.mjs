// 把 tone-front 里的 RagChat 组件复制过来：组件只维护一份（在 tone-front 里），这里只是预览
import { cpSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '../../tone-front/src/components/HelperChatBoot/RagChat');
const dst = resolve(here, '../src/RagChat');

rmSync(dst, { recursive: true, force: true });
cpSync(src, dst, { recursive: true });
console.log(`synced RagChat: ${src} -> ${dst}`);
