import { useNavigate } from 'react-router-dom'
import { BookOpen, MessageCircle, PenTool, Network, ArrowRight, Sparkles } from 'lucide-react'
import './LandingPage.css'

const FEATURES = [
  {
    icon: BookOpen,
    title: '수집',
    desc: '웹에서 읽은 글, 메모, PDF를 한 곳에 모으세요. AI가 자동으로 분류하고 요약합니다.',
  },
  {
    icon: MessageCircle,
    title: '대화',
    desc: '저장한 기억을 바탕으로 AI와 깊이 있는 대화를 나누세요. 맥락을 이해하는 지적 동반자.',
  },
  {
    icon: PenTool,
    title: '회고',
    desc: '하루를 돌아보며 저널을 작성하세요. AI가 성찰 질문과 인사이트를 제공합니다.',
  },
  {
    icon: Network,
    title: '발견',
    desc: '기억들 사이의 숨겨진 연결을 3D 그래프로 시각화하고 새로운 통찰을 발견하세요.',
  },
]

const TECH_STACK = [
  { name: 'React', color: '#61DAFB' },
  { name: 'TypeScript', color: '#3178C6' },
  { name: 'FastAPI', color: '#009688' },
  { name: 'LangGraph', color: '#FF6F00' },
  { name: 'Supabase', color: '#3ECF8E' },
  { name: 'pgvector', color: '#336791' },
]

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="landing-page">
      {/* Hero */}
      <section className="landing-hero">
        <div className="landing-hero-content">
          <div className="landing-logo">
            <Sparkles size={28} />
            <span>Memoir</span>
          </div>
          <h1 className="landing-headline">
            당신의 기억을 지키는<br />AI 파트너
          </h1>
          <p className="landing-subtext">
            읽고, 생각하고, 깨달은 것들을 AI와 함께 정리하세요.
            <br />
            흩어진 지식이 연결되고, 잊힌 기억이 되살아납니다.
          </p>
          <div className="landing-cta-group">
            <button
              className="landing-cta"
              onClick={() => navigate('/login')}
              type="button"
            >
              시작하기 <ArrowRight size={18} />
            </button>
            <button
              className="landing-cta-secondary"
              onClick={() => navigate('/demo')}
              type="button"
            >
              바로 체험하기
            </button>
          </div>
        </div>
        <div className="landing-hero-glow" />
      </section>

      {/* Features */}
      <section className="landing-features">
        <h2 className="landing-section-title">당신의 두 번째 뇌</h2>
        <div className="landing-feature-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="landing-feature-card">
              <div className="landing-feature-icon">
                <f.icon size={24} />
              </div>
              <h3>{f.title}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Tech Stack */}
      <section className="landing-tech">
        <h2 className="landing-section-title">Built with</h2>
        <div className="landing-tech-list">
          {TECH_STACK.map((t) => (
            <span key={t.name} className="landing-tech-badge" style={{ borderColor: t.color }}>
              <span className="landing-tech-dot" style={{ backgroundColor: t.color }} />
              {t.name}
            </span>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>&copy; 2025 Memoir. All rights reserved.</p>
      </footer>
    </div>
  )
}
