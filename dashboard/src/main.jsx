import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

// App will be imported in Plan 02
function Placeholder() {
  return <div className="p-4 text-gray-700">GigAI Dashboard loading...</div>
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Placeholder />
  </React.StrictMode>
)
