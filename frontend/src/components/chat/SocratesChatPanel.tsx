import { ChevronDown } from 'lucide-react'
import type { UseSocratesChatReturn } from '../../hooks/useSocratesChat'
import ChatEmptyState from './ChatEmptyState'
import ChatMessageList from './ChatMessageList'
import ChatInputBar from './ChatInputBar'
import './SocratesChatPanel.css'

interface SocratesChatPanelProps {
  chat: UseSocratesChatReturn
  showHeader?: boolean
  className?: string
}

export default function SocratesChatPanel({ chat, showHeader = false, className = '' }: SocratesChatPanelProps) {
  const {
    messages, input, setInput, isLoading, isLoadingHistory,
    briefing, expandedRefs, feedbacks, showScrollBtn, hasBriefingContent,
    messagesEndRef, messagesContainerRef, textareaRef,
    handleSendMessage, handleFeedback, scrollToBottom,
    handleMessagesScroll, adjustTextareaHeight, handleKeyDown,
    toggleRefExpand, sendMessageDirect,
  } = chat

  return (
    <div className={`socrates-chat-panel ${className}`}>
      {showHeader && (
        <div className="socrates-chat-panel__header">
          <h3>Socrates</h3>
          <p>당신의 지적 동반자</p>
        </div>
      )}

      <div className="socrates-chat-panel__messages-wrapper">
        <div
          className="chat-messages"
          ref={messagesContainerRef}
          onScroll={handleMessagesScroll}
          aria-live="polite"
          aria-label="대화 메시지"
        >
          {isLoadingHistory ? (
            <div className="chat-empty">
              <div className="loading-spinner"></div>
              <p>대화 기록을 불러오는 중...</p>
            </div>
          ) : messages.length === 0 ? (
            <ChatEmptyState
              briefing={briefing}
              hasBriefingContent={hasBriefingContent}
              onSuggestedQuestion={sendMessageDirect}
            />
          ) : (
            <ChatMessageList
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
            className="chat-scroll-bottom-btn"
            onClick={scrollToBottom}
            title="맨 아래로"
            type="button"
          >
            <ChevronDown size={20} />
          </button>
        )}
      </div>

      <ChatInputBar
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
