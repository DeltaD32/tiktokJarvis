import { useState, useRef, useEffect } from 'react'

export function FloatWindow({ title, subtitle, x, y, z, onClose, onFocus, onDragMove, children, width, height, maxWidth, maxHeight }) {
  const dragRef = useRef(null)

  useEffect(() => {
    const onMove = (e) => {
      if (!dragRef.current) return
      const nx = Math.max(8, Math.min(window.innerWidth - 90, e.clientX - dragRef.current.ox))
      const ny = Math.max(60, Math.min(window.innerHeight - 60, e.clientY - dragRef.current.oy))
      onDragMove?.(nx, ny)
    }
    const onUp = () => { dragRef.current = null }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [onDragMove])

  const handleMouseDown = (e) => {
    e.preventDefault()
    onFocus?.()
    dragRef.current = { ox: e.clientX - x, oy: e.clientY - y }
  }

  return (
    <div
      className="float-window"
      style={{
        left: x, top: y, zIndex: z,
        width: width || 'auto',
        maxWidth: maxWidth || '90vw',
        height: height || 'auto',
        maxHeight: maxHeight || '74vh',
      }}
    >
      <div className="float-header" onMouseDown={handleMouseDown}>
        <div className="float-dots">
          <div /><div /><div /><div /><div /><div />
        </div>
        <div className="float-title">{title}</div>
        {subtitle && <div className="float-subtitle">{subtitle}</div>}
        <button className="float-close" onClick={onClose}>-</button>
      </div>
      {children}
    </div>
  )
}
