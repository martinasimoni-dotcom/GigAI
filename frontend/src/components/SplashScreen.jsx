import { useEffect, useState } from 'react'

export default function SplashScreen({ onEnter }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const t = requestAnimationFrame(() => setVisible(true))
    return () => cancelAnimationFrame(t)
  }, [])

  return (
    <div
      onClick={onEnter}
      style={{
        width: '100vw',
        height: '100vh',
        background: '#355182',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        gap: '24px',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(16px)',
        transition: 'opacity 0.6s ease, transform 0.6s ease',
      }}
    >
      <img
        src="/logo.png"
        alt="GIGAI"
        style={{ height: '200px', width: 'auto' }}
      />
      <span style={{
        color: '#FFFFFF',
        fontSize: '24px',
        fontWeight: 700,
        fontFamily: 'var(--font-family)',
      }}>
        Hi, Martina!
      </span>
    </div>
  )
}
