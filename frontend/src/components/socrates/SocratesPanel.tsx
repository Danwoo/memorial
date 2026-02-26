import { ChevronDown } from 'lucide-react'
import type { UseSocratesChatReturn } from '../../hooks/useSocratesChat'
import SocratesEmptyState from './SocratesEmptyState'
import SocratesMessageList from './SocratesMessageList'
import SocratesInputBar from './SocratesInputBar'
import './SocratesPanel.css'

interface SocratesPanelProps {
  chat: UseSocratesChatReturn
  showHeader?: boolean
  className?: string
}

export default function SocratesPanel({ chat, showHeader = false, className = '' }: SocratesPanelProps) {
  const {
    messages, input, setInput, isLoading, isLoadingHistory,
    briefing, expandedRefs, feedbacks, showScrollBtn, hasBriefingContent,
    messagesEndRef, messagesContainerRef, textareaRef,
    handleSendMessage, handleFeedback, scrollToBottom,
    handleMessagesScroll, adjustTextareaHeight, handleKeyDown,
    toggleRefExpand, sendMessageDirect,
  } = chat

  return (
    <div className={`socrates-panel ${className}`}>
      {showHeader && (
        <div className="socrates-panel__header">
          <h3>Socrates</h3>
          <p>당신의 지적 동반자</p>
        </div>
      )}

      <div className="socrates-panel__messages-wrapper">
        <div
          className="socrates-messages"
          ref={messagesContainerRef}
          onScroll={handleMessagesScroll}
          aria-live="polite"
          aria-label="대화 메시지"
        >
          {isLoadingHistory ? (
            <div className="socrates-empty">
              <div className="loading-spinner"></div>
              <p>대화 기록을 불러오는 중...</p>
            </div>
          ) : messages.length === 0 ? (
            <SocratesEmptyState
              briefing={briefing}
              hasBriefingContent={hasBriefingContent}
              onSuggestedQuestion={sendMessageDirect}
            />
          ) : (
            <SocratesMessageList
              messages={messages}
              expandedRefs={expandedRefs}
              feedbacks={feedbacks}
              onToggleRefExpand={toggleRefExpand}
              onFeedback={handleFeedback}
            />
          )}
          <div ref={messagesEndRef} />
        </div>

        {showScrollBtn && (
          <button
            className="socrates-scroll-bottom-btn"
            onClick={scrollToBottom}
            title="맨 아래로"
            type="button"
          >
            <ChevronDown size={20} />
          </button>
        )}
      </div>

      <SocratesInputBar
        input={input}
        isLoading={isLoading}
        textareaRef={textareaRef}
        onInputChange={setInput}
        onSend={handleSendMessage}
        onKeyDown={handleKeyDown}
        onAdjustHeight={adjustTextareaHeight}
      />
    </div>
  )
}
