export default function LoadingOverlay() {
  return (
    <div className="loading-overlay">
      <div className="loading-content">
        <p className="loading-text">Loading</p>
        <div className="loading-dots">
          <span className="dot" />
          <span className="dot" />
          <span className="dot" />
        </div>
      </div>
    </div>
  )
}
