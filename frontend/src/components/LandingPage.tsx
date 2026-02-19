import { useNavigate } from 'react-router-dom'
import { ArrowRight, BookOpen, MessageCircle, PenTool, Network } from 'lucide-react'
import './LandingPage.css'

const FEATURES = [
  {
    icon: BookOpen,
    title: '읽은 것, 바로 저장',
    desc: '기사, 메모, 생각을 한 곳에 모으면 AI가 알아서 정리해줘요.',
  },
  {
    icon: MessageCircle,
    title: '내 기억과 대화',
    desc: '저장한 내용을 기반으로 AI가 답해줘요. 진짜 나를 아는 비서처럼.',
  },
  {
    icon: PenTool,
    title: '하루 돌아보기',
    desc: '오늘 하루를 저널로 기록하면, AI가 생각을 정리하는 질문을 던져줘요.',
  },
  {
    icon: Network,
    title: '연결된 지식 발견',
    desc: '흩어진 기억 사이에서 숨겨진 연결고리를 찾아드려요.',
  },
]

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="landing-page">
      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <img
            src="/favicon.png"
            alt="Memoir"
            className="landing-logo-img"
          />
          <h1 className="landing-headline">
            기억을 모으면,<br />나만의 지식이 됩니다
          </h1>
          <p className="landing-subtext">
            매일 읽고, 생각하고, 느낀 것들 — 그냥 흘려보내지 마세요.
            <br />
            Memoir가 당신의 기억을 지키고, 연결하고, 되살려 드려요.
          </p>
          <div className="landing-cta-group">
            <button
              className="landing-cta"
              onClick={() => navigate('/login')}
              type="button"
            >
              무료로 시작하기 <ArrowRight size={18} />
            </button>
            <button
              className="landing-cta-secondary"
              onClick={() => navigate('/demo')}
              type="button"
            >
              먼저 둘러보기
            </button>
          </div>
        </div>
        <div className="landing-hero-glow" />
      </section>

      {/* Features */}
      <section className="landing-features">
        <h2 className="landing-section-title">이렇게 도와드려요</h2>
        <div className="landing-feature-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing-feature-card">
              <div className="landing-feature-icon">
                <f.icon size={28} />
              </div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>&copy; 2025 Memoir</p>
      </footer>
    </div>
  )
}
