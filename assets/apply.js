/* 적용용 요청문. 템플릿에 값을 채울 뿐 외부 AI 를 부르지 않는다. 순수 함수 — node 시험이 같이 쓴다. */
import {FXN, titleOf} from './data.js';

export const ENVS = {
  chat: 'Claude 채팅 미리보기에서 바로 볼 수 있는 HTML 한 장 (외부 라이브러리는 CDN 으로)',
  code: 'Claude Code 로 만드는 프로젝트 파일 (실행 방법까지 알려 주기)',
  video: 'MP4 영상 파일로 내보낼 수 있는 구성 (Remotion 등, 렌더링 명령까지 알려 주기)'
};
export function buildRequest(r, o, uses) {
  const ed = r.ed || {}, g = ed.guide || {};
  const ref = g.brief || [titleOf(r), r.fx.filter(f => f !== 'etc').map(f => FXN[f]).join(', ')].filter(Boolean).join(' — ');
  const lines = [
    '다음 효과를 참고해서 내 용도에 맞게 새로 만들어 주세요.', '',
    '[참고한 효과]', ref, `(출처: @${r.author}${r.post_url ? ', ' + r.post_url : ''})`, '',
    `[내 용도] ${o.use || (uses[0] ? uses[0] : '자유롭게 정해 주세요')}`,
    `[들어갈 문구] ${o.text || '임의로 정해 주세요'}`,
    `[색상] ${o.color || '원본 분위기를 유지해 주세요'}`,
    `[실행 환경] ${ENVS[o.env] || ENVS.chat}`, '',
    '[조건]',
    '- 원본을 그대로 복제하지 말고, 위 용도와 문구에 맞게 구성을 바꿔 주세요.',
    '- 문구·색상·크기·속도처럼 바꾸기 쉬운 값은 맨 위에 변수로 모아 주세요.',
    '- 움직임 줄이기 설정(prefers-reduced-motion)에서는 정지 화면이나 단순한 전환을 보여 주세요.'
  ];
  if (!g.brief && r.prompt) {
    lines.push('', r.partial ? '[원본 프롬프트 — 일부만 공개됨, 빠진 부분은 알아서 채워 주세요]' : '[원본 프롬프트 — 기법 참고용]', r.prompt.slice(0, 1200) + (r.prompt.length > 1200 ? ' …' : ''));
  }
  return lines.join('\n');
}
