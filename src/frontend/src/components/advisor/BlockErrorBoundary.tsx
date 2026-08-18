import { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  blockType: string
}

interface State {
  hasError: boolean
  message: string
}

export class BlockErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, message: '' }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, message: error.message }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`BlockErrorBoundary [${this.props.blockType}]:`, error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '12px 16px',
          background: 'var(--bg-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '13px',
          color: 'var(--text-muted)',
        }}>
          Could not display this result ({this.props.blockType}).
        </div>
      )
    }
    return this.props.children
  }
}
