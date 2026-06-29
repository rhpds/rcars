import '@patternfly/react-core/dist/styles/base.css'
import './styles/rcars-variables.css'
import './styles/rcars-dark-overrides.css'
import './styles/rcars-light-overrides.css'
import './styles/rcars-components.css'
import './styles/rcars-app.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
