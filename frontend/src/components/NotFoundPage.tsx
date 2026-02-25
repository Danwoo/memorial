import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      gap: 'var(--space-lg)',
      color: 'var(--text-secondary)',
      padding: 'var(--space-2xl)',
      textAlign: 'center',
    }}>
      <span style={{ fontSize: '3rem', opacity: 0.4 }}>404</span>
      <p style={{ fontSize: '1rem', margin: 0 }}>
        페이지를 찾을 수 없습니다
      </p>
      <Link
        to="/dashboard"
        className="btn btn-primary"
        style={{ textDecoration: 'none', padding: '8px 20px', fontSize: '0.875rem' }}
      >
        홈으로 돌아가기
      </Link>
    </div>
  )
}
