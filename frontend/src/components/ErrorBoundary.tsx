import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary-icon">&#x26A0;&#xFE0F;</div>
          <h2>문제가 발생했습니다</h2>
          <p>예기치 않은 오류가 발생했습니다. 새로고침하거나 잠시 후 다시 시도해주세요.</p>
          {this.state.error && (
            <div className="error-boundary-details">
              {this.state.error.message}
            </div>
          )}
          <button className="btn btn-primary" onClick={this.handleReload} type="button">
            새로고침
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
