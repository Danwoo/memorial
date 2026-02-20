import type { ThemePreference } from '../../contexts/ThemeContext'
import type { User } from '../../types'

interface ProfileSectionProps {
  user: User | null
  email: string | null
  themePreference: ThemePreference
  setThemePreference: (pref: ThemePreference) => void
}

// 테마 선택 옵션 정의
const themeOptions: { value: ThemePreference; icon: JSX.Element; label: string }[] = [
  {
    value: 'light',
    label: '라이트',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
      </svg>
    ),
  },
  {
    value: 'dark',
    label: '다크',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
      </svg>
    ),
  },
  {
    value: 'system',
    label: '자동',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
    ),
  },
]

export default function ProfileSection({ user, email, themePreference, setThemePreference }: ProfileSectionProps) {
  return (
    <header className="settings-profile">
      <div className="profile-left">
        {user?.avatar_url ? (
          <img src={user.avatar_url} alt="" className="profile-avatar" referrerPolicy="no-referrer" />
        ) : (
          <div className="profile-avatar-placeholder">
            {(user?.full_name || user?.email || '?')[0].toUpperCase()}
          </div>
        )}
        <div className="profile-text">
          <h1 className="profile-name">{user?.full_name || '사용자'}</h1>
          <p className="profile-email">{email ?? user?.email ?? '-'}</p>
        </div>
      </div>
      <div className="theme-toggle-group">
        {themeOptions.map((opt) => (
          <button
            key={opt.value}
            className={`theme-btn ${themePreference === opt.value ? 'theme-btn--active' : ''}`}
            onClick={() => setThemePreference(opt.value)}
            title={opt.label}
            type="button"
          >
            {opt.icon}
          </button>
        ))}
      </div>
    </header>
  )
}
