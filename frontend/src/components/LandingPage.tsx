import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BookOpen,
  Pencil,
  Network,
  Bot,
  Sparkles,
  Check,
  ChevronRight,
  Link as LinkIcon,
  FileText,
} from 'lucide-react'
import AuthModal from './AuthModal'
import { useIsMobile } from '../hooks/useMediaQuery'
import './LandingPage.css'

interface Feature {
  icon: typeof BookOpen
  title: string
  body: string
  accent: string
  accentBg: string
}

const FEATURES: Feature[] = [
  {
    icon: BookOpen,
    title: '읽은 것, 바로 저장',
    body: 'URL · PDF · 메모를 한 곳에 모아두세요. AI가 핵심을 추출하고 자동으로 태그를 달아드려요.',
    accent: 'var(--feature-scrap)',
    accentBg: 'var(--feature-scrap-bg)',
  },
  {
    icon: Pencil,
    title: '하루를 짧게 적기',
    body: '리치 텍스트 에디터에 한 줄이면 충분해요. 매일 다른 성찰 질문이 글쓰기를 도와줘요.',
    accent: 'var(--feature-diary)',
    accentBg: 'var(--feature-diary-bg)',
  },
  {
    icon: Network,
    title: '연결된 지식 발견',
    body: '다이어리와 스크랩이 어떻게 이어지는지 마인드맵으로 한눈에. AI가 클러스터를 찾아드려요.',
    accent: 'var(--feature-mindmap)',
    accentBg: 'var(--feature-mindmap-bg)',
  },
  {
    icon: Bot,
    title: '내 기억과 대화',
    body: 'Socrates에게 질문하세요. 내가 저장한 글만 검색해서 맥락 있는 답변을 만들어줘요.',
    accent: 'var(--accent-primary)',
    accentBg: 'var(--accent-bg)',
  },
]

const STEPS = [
  { n: '01', title: '저장하세요', body: '읽은 글, 떠오른 생각, 책 한 페이지. 한 번 클릭이면 끝나요.' },
  { n: '02', title: '연결됩니다', body: 'AI가 엔티티와 관계를 자동으로 추출해서 지식 그래프를 만들어요.' },
  { n: '03', title: '꺼내 쓰세요', body: 'Socrates에게 물어보면, 내 노트만 검색해서 맥락 있는 답변을 드려요.' },
]

const MINDMAP_BULLETS = [
  '엔티티와 관계를 자동 추출',
  '클러스터 색상 모드로 주제별 보기',
  '허브 노드 · 외로운 노트 인사이트',
]

export default function LandingPage() {
  const [authOpen, setAuthOpen] = useState(false)
  const openAuth = () => setAuthOpen(true)
  const closeAuth = () => setAuthOpen(false)

  return (
    <div className="landing-page">
      <TopNav onSignIn={openAuth} />
      <Hero onSignIn={openAuth} />
      <FeatureGrid />
      <HowItWorks />
      <MindmapShowcase />
      <FinalCta onSignIn={openAuth} />
      <Footer />
      <AuthModal open={authOpen} onClose={closeAuth} />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Top nav
// ─────────────────────────────────────────────────────────────────────
function TopNav({ onSignIn }: { onSignIn: () => void }) {
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  return (
    <nav className="landing-nav">
      <a href="#top" className="landing-nav-brand">
        <img src="/logos/logo-final.svg" width={28} height={28} alt="" />
        <span>Memoir</span>
      </a>
      <div className="landing-nav-actions">
        {!isMobile && (
          <>
            <a className="landing-nav-link" href="#features">기능</a>
            <a className="landing-nav-link" href="#how">어떻게 작동하나요</a>
            <button type="button" className="landing-nav-ghost" onClick={() => navigate('/demo')}>
              둘러보기
            </button>
          </>
        )}
        <button type="button" className="landing-nav-primary" onClick={onSignIn}>
          로그인
        </button>
      </div>
    </nav>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Hero
// ─────────────────────────────────────────────────────────────────────
function Hero({ onSignIn }: { onSignIn: () => void }) {
  const navigate = useNavigate()
  return (
    <section className="landing-hero" id="top">
      <div className="landing-hero-glow" aria-hidden="true" />

      <div className="landing-hero-inner">
        <a href="#how" className="landing-hero-eyebrow">
          <span className="landing-hero-eyebrow-tag">새 기능</span>
          <span>마인드맵에서 클러스터를 자동으로 찾아드려요</span>
          <ChevronRight size={12} />
        </a>

        <h1 className="landing-hero-headline">
          기억을 모으면,<br />
          <span className="landing-hero-accent-wrap">
            <span className="landing-hero-accent">나만의 지식</span>
            <svg
              className="landing-hero-underline"
              viewBox="0 0 200 12"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path
                d="M 4 8 Q 50 2, 100 6 T 196 5"
                fill="none"
                stroke="var(--accent-primary)"
                strokeWidth="2.5"
                strokeLinecap="round"
                opacity="0.6"
              />
            </svg>
          </span>이 됩니다
        </h1>

        <p className="landing-hero-subtext">
          매일 읽고, 생각하고, 느낀 것들을 그냥 흘려보내지 마세요.<br />
          Memoir가 당신의 기억을 지키고, 연결하고, 되살려 드려요.
        </p>

        <div className="landing-hero-ctas">
          <button type="button" className="landing-cta-primary" onClick={onSignIn}>
            30초 만에 시작하기
            <ChevronRight size={16} />
          </button>
          <button type="button" className="landing-cta-secondary" onClick={() => navigate('/demo')}>
            <Sparkles size={15} />
            데모 둘러보기
          </button>
        </div>

        <div className="landing-hero-trust">
          <span><Check size={12} color="var(--color-success)" /> 카드 없이 시작</span>
          <span className="landing-hero-trust-dot" />
          <span><Check size={12} color="var(--color-success)" /> 카카오·구글 로그인</span>
          <span className="landing-hero-trust-dot" />
          <span><Check size={12} color="var(--color-success)" /> 한국 서버에 저장</span>
        </div>
      </div>

      <div className="landing-hero-screenshot">
        <div className="landing-hero-browser-chrome">
          <span className="landing-hero-browser-dot" style={{ background: '#FF5F57' }} />
          <span className="landing-hero-browser-dot" style={{ background: '#FEBC2E' }} />
          <span className="landing-hero-browser-dot" style={{ background: '#28C840' }} />
          <div className="landing-hero-browser-url">memoir-knowledge.vercel.app</div>
        </div>
        <img
          src="/screenshots/calendar-screenshot.png"
          alt="Memoir 캘린더 뷰"
          loading="lazy"
        />
      </div>
    </section>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Feature grid
// ─────────────────────────────────────────────────────────────────────
function FeatureGrid() {
  return (
    <section className="landing-section" id="features">
      <SectionHeader
        eyebrow="기능"
        title="당신의 기억, 정리되고 살아납니다"
        sub="네 가지 도구가 매끄럽게 연결돼요. 따로 쓰지 않아도 자연스럽게 흐름이 만들어져요."
      />
      <div className="landing-feature-grid">
        {FEATURES.map((f) => (
          <article key={f.title} className="landing-feature-card">
            <div
              className="landing-feature-icon"
              style={{ background: f.accentBg, color: f.accent }}
            >
              <f.icon size={22} />
            </div>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

// ─────────────────────────────────────────────────────────────────────
// How it works
// ─────────────────────────────────────────────────────────────────────
function HowItWorks() {
  return (
    <section className="landing-section landing-section-tinted" id="how">
      <SectionHeader
        eyebrow="작동 방식"
        title="저장 → 연결 → 꺼내쓰기"
        sub="복잡한 정리 규칙은 필요 없어요. Memoir가 알아서 구조를 만들어드려요."
      />
      <div className="landing-steps-grid">
        {STEPS.map((s, i) => (
          <article key={s.n} className="landing-step-card">
            <div className="landing-step-tag">STEP {s.n}</div>
            <StepIllustration index={i} />
            <h3>{s.title}</h3>
            <p>{s.body}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

function StepIllustration({ index }: { index: number }) {
  if (index === 0) {
    const chips = [
      { icon: LinkIcon, label: '도둑맞은 집중력 — 핵심 정리', meta: 'brunch.co.kr' },
      { icon: FileText, label: '교토 가을 단풍 명소 8곳.pdf', meta: 'PDF · 4쪽' },
      { icon: Pencil, label: '오랜만에 산책하니 좋네', meta: '다이어리' },
    ]
    return (
      <div className="landing-step-chips">
        {chips.map((c, i) => (
          <div key={i} className="landing-step-chip">
            <c.icon size={14} color="var(--accent-primary)" />
            <div className="landing-step-chip-text">
              <span className="landing-step-chip-label">{c.label}</span>
              <span className="landing-step-chip-meta">{c.meta}</span>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (index === 1) {
    return (
      <svg className="landing-step-network" viewBox="0 0 240 140" aria-hidden="true">
        <g stroke="var(--border-primary)" strokeWidth="1" fill="none" opacity="0.6">
          <line x1="60" y1="40" x2="120" y2="80" />
          <line x1="180" y1="40" x2="120" y2="80" />
          <line x1="60" y1="110" x2="120" y2="80" />
          <line x1="180" y1="110" x2="120" y2="80" />
          <line x1="60" y1="40" x2="180" y2="40" />
          <line x1="60" y1="110" x2="180" y2="110" />
        </g>
        <circle cx="120" cy="80" r="12" fill="var(--accent-primary)" opacity="0.95" />
        <circle cx="60" cy="40" r="8" fill="var(--feature-mindmap)" />
        <circle cx="180" cy="40" r="8" fill="var(--feature-scrap)" />
        <circle cx="60" cy="110" r="8" fill="var(--feature-diary)" />
        <circle cx="180" cy="110" r="8" fill="var(--accent-primary)" />
      </svg>
    )
  }

  return (
    <div className="landing-step-chat">
      <div className="landing-step-chat-user">오늘 읽은 글 중 기억남는 한 줄?</div>
      <div className="landing-step-chat-ai">
        "집중은 시간 관리가 아니라 주의 관리"라는 문장이 가장 기억에 남으셨어요.
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Mindmap showcase
// ─────────────────────────────────────────────────────────────────────
function MindmapShowcase() {
  return (
    <section className="landing-section landing-showcase">
      <div className="landing-showcase-text">
        <div className="landing-eyebrow">마인드맵</div>
        <h2 className="landing-showcase-title">내 머릿속이 한눈에 보입니다</h2>
        <p className="landing-showcase-body">
          다이어리와 스크랩에서 사람·개념·도구를 자동으로 추출해서, 서로 어떻게 이어지는지 3D 그래프로 보여줘요.
          AI가 비슷한 주제를 묶어주고, 외로운 노트를 다시 찾아드려요.
        </p>
        <ul className="landing-showcase-list">
          {MINDMAP_BULLETS.map((t) => (
            <li key={t}>
              <span className="landing-showcase-check">
                <Check size={12} />
              </span>
              {t}
            </li>
          ))}
        </ul>
      </div>
      <div className="landing-showcase-image">
        <img src="/screenshots/mindmap-screenshot.png" alt="Memoir 마인드맵" loading="lazy" />
      </div>
    </section>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Final CTA
// ─────────────────────────────────────────────────────────────────────
function FinalCta({ onSignIn }: { onSignIn: () => void }) {
  const navigate = useNavigate()
  return (
    <section className="landing-final-section">
      <div className="landing-final-card">
        <h2>오늘의 기억부터 모아볼까요?</h2>
        <p>30초면 충분해요. 카드 없이, 카카오나 구글로 바로 시작하세요.</p>
        <div className="landing-final-ctas">
          <button type="button" className="landing-final-primary" onClick={onSignIn}>
            지금 시작하기
          </button>
          <button type="button" className="landing-final-secondary" onClick={() => navigate('/demo')}>
            먼저 둘러보기
          </button>
        </div>
      </div>
    </section>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Footer
// ─────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer className="landing-footer">
      <div className="landing-footer-inner">
        <div className="landing-footer-brand">
          <img src="/logos/logo-final.svg" width={20} height={20} alt="" />
          <span>Memoir</span>
          <span className="landing-footer-copy">· © 2026</span>
        </div>
        <div className="landing-footer-links">
          <a href="#">이용약관</a>
          <a href="#">개인정보처리방침</a>
          <a href="#">도움말</a>
          <a href="mailto:hello@memoir.app">문의</a>
        </div>
      </div>
    </footer>
  )
}

// ─────────────────────────────────────────────────────────────────────
// Shared
// ─────────────────────────────────────────────────────────────────────
function SectionHeader({ eyebrow, title, sub }: { eyebrow: string; title: string; sub?: string }) {
  return (
    <div className="landing-section-header">
      <div className="landing-eyebrow">{eyebrow.toUpperCase()}</div>
      <h2>{title}</h2>
      {sub && <p>{sub}</p>}
    </div>
  )
}
