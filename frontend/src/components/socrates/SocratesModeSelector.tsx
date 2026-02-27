import type { SocratesMode } from '../../types'
import { SOCRATES_MODE_LABELS } from '../../types'

interface SocratesModeSelectorProps {
  selectedMode: SocratesMode
  onModeChange: (mode: SocratesMode) => void
  availableModes?: SocratesMode[]
}

export default function SocratesModeSelector({
  selectedMode,
  onModeChange,
  availableModes,
}: SocratesModeSelectorProps) {
  const modes = availableModes ?? (Object.keys(SOCRATES_MODE_LABELS) as SocratesMode[])

  return (
    <div className="socrates-mode-selector">
      {modes.map((mode) => {
        const { label, icon } = SOCRATES_MODE_LABELS[mode]
        const isActive = selectedMode === mode
        return (
          <button
            key={mode}
            type="button"
            className={`socrates-mode-chip${isActive ? ' socrates-mode-chip--active' : ''}`}
            onClick={() => onModeChange(isActive ? 'default' : mode)}
            title={SOCRATES_MODE_LABELS[mode].description}
          >
            <span className="socrates-mode-chip__icon">{icon}</span>
            {label}
          </button>
        )
      })}
    </div>
  )
}
