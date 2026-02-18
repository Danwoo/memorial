import { useState } from 'react'
import { PenLine, Calendar } from 'lucide-react'
import { DEMO_JOURNAL_DATES, DEMO_JOURNALS } from '../../data/demo-data'
import { useToast } from '../../contexts/ToastContext'
import '../JournalView.css'

export default function DemoJournalView() {
  const toast = useToast()
  const [selectedDate, setSelectedDate] = useState(DEMO_JOURNAL_DATES[0])
  const journal = DEMO_JOURNALS[selectedDate]

  const handleEdit = () => {
    toast.info('데모 모드에서는 수정할 수 없습니다. 회원가입 후 이용해주세요!')
  }

  return (
    <div className="journal-view">
      {/* 날짜 패널 */}
      <div className="journal-dates-panel">
        <h2 className="journal-dates-title"><Calendar size={18} /> 저널 날짜</h2>
        <div className="journal-date-list">
          {DEMO_JOURNAL_DATES.map(date => (
            <button
              key={date}
              className={`journal-date-item ${date === selectedDate ? 'active' : ''}`}
              onClick={() => setSelectedDate(date)}
            >
              <span className="date-label">{new Date(date + 'T00:00:00').toLocaleDateString('ko-KR', { month: 'short', day: 'numeric', weekday: 'short' })}</span>
              {DEMO_JOURNALS[date]?.mood && <span className="date-mood">{DEMO_JOURNALS[date].mood}</span>}
            </button>
          ))}
        </div>
      </div>

      {/* 에디터 패널 */}
      <div className="journal-editor-panel">
        <div className="journal-editor-header">
          <h1><PenLine size={22} /> {new Date(selectedDate + 'T00:00:00').toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })}</h1>
        </div>
        {journal ? (
          <div className="journal-content" onClick={handleEdit} style={{ cursor: 'pointer', whiteSpace: 'pre-wrap', padding: 16, lineHeight: 1.8 }}>
            {journal.content}
          </div>
        ) : (
          <div className="journal-empty">
            <p>이 날짜에는 아직 저널이 없습니다.</p>
          </div>
        )}
      </div>

      {/* AI 패널 */}
      <div className="journal-ai-panel">
        <h3>AI 회고 질문</h3>
        <div className="journal-questions">
          <div className="journal-question-card">오늘 가장 인상 깊었던 학습 내용은 무엇인가요?</div>
          <div className="journal-question-card">이전에 알고 있던 것과 연결되는 점이 있나요?</div>
          <div className="journal-question-card">내일 더 탐구하고 싶은 주제가 있나요?</div>
        </div>
      </div>
    </div>
  )
}
