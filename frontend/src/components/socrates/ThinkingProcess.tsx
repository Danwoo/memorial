import { useState } from 'react';
import { AgentStep, AgentStepStatus, getToolLabel } from '../../types/agentStep';

interface ThinkingProcessProps {
  steps: AgentStep[];
  isThinking: boolean;
  className?: string;
}

function StepIcon({ status }: { status: AgentStepStatus }) {
  if (status === 'done') {
    return <span className="thinking-step-icon thinking-step-icon--done">✓</span>;
  }
  if (status === 'active') {
    return <span className="thinking-step-icon thinking-step-icon--active" />;
  }
  if (status === 'error') {
    return <span className="thinking-step-icon thinking-step-icon--error">✗</span>;
  }
  return <span className="thinking-step-icon thinking-step-icon--pending" />;
}

export function ThinkingProcess({
  steps,
  isThinking,
  className = '',
}: ThinkingProcessProps) {
  const [expanded, setExpanded] = useState(false);

  if (!isThinking && steps.length === 0) return null;

  const activeStep = steps.find((s) => s.status === 'active');
  const doneCount = steps.filter((s) => s.status === 'done').length;

  return (
    <div className={`thinking-process ${className}`}>
      <button
        className="thinking-process__header"
        onClick={() => setExpanded((v) => !v)}
        type="button"
      >
        {isThinking && <span className="thinking-process__spinner" />}
        <span className="thinking-process__title">
          {isThinking
            ? activeStep
              ? `${getToolLabel(activeStep.tool)} 중...`
              : '생각하고 있습니다...'
            : `${doneCount}개 단계 완료`}
        </span>
        <span className="thinking-process__toggle">
          {expanded ? '▲' : '▼'}
        </span>
      </button>

      {expanded && steps.length > 0 && (
        <ul className="thinking-process__steps">
          {steps.map((step) => (
            <li key={step.id} className={`thinking-step thinking-step--${step.status}`}>
              <StepIcon status={step.status} />
              <span className="thinking-step__label">
                {getToolLabel(step.tool)}
              </span>
              {step.detail && step.status === 'done' && (
                <span className="thinking-step__detail">{step.detail}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
