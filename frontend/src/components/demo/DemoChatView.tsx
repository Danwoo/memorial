import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Send, ThumbsUp, ThumbsDown, BookOpen } from 'lucide-react'
import { DEMO_SESSIONS, DEMO_CHAT_MESSAGES, DEMO_BRIEFING } from '../../data/demo-data'
import { useToast } from '../../contexts/ToastContext'
import '../ChatView.css'

export default function DemoChatView() {
  const { sessionId } = useParams()
  const toast = useToast()
  const [input, setInput] = useState('')

  const activeId = sessionId || DEMO_SESSIONS[0]?.id
  const messages = DEMO_CHAT_MESSAGES[activeId] || []
  const session = DEMO_SESSIONS.find(s => s.id === activeId)

  const handleSend = () => {
    toast.info('데모 모드에서는 메시지를 보낼 수 없습니다. 회원가입 후 이용해주세요!')
    setInput('')
  }

  return (
    <div className="chat-view">
      {messages.length === 0 ? (
        <div className="chat-empty">
          <div className="chat-empty-icon">💬</div>
          <h2>Socrates와 대화하기</h2>
          <p>저장한 기억을 바탕으로 깊이 있는 대화를 나눠보세요.</p>
          {DEMO_BRIEFING.suggested_question && (
            <button className="chat-suggestion-btn" onClick={handleSend}>
              {DEMO_BRIEFING.suggested_question}
            </button>
          )}
        </div>
      ) : (
        <div className="chat-messages">
          {session && <div className="chat-session-title">{session.title}</div>}
          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-message chat-message--${msg.role}`}>
              <div className="message-bubble">
                <div className="message-content">{msg.content}</div>
                {msg.references && msg.references.length > 0 && (
                  <div className="message-references">
                    {msg.references.map(ref => (
                      <span key={ref.id} className="reference-chip">
                        <BookOpen size={12} /> {ref.title}
                      </span>
                    ))}
                  </div>
                )}
                {msg.role === 'assistant' && (
                  <div className="message-feedback">
                    <button className="feedback-btn" onClick={() => toast.info('데모 모드입니다')} title="좋아요">
                      <ThumbsUp size={14} />
                    </button>
                    <button className="feedback-btn" onClick={() => toast.info('데모 모드입니다')} title="별로에요">
                      <ThumbsDown size={14} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="메시지를 입력하세요..."
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
          rows={1}
        />
        <button className="chat-send-btn" onClick={handleSend} disabled={!input.trim()}>
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
