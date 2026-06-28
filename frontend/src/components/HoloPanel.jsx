import { motion } from 'framer-motion'

const PANEL_VARIANTS = {
  initial: { x: '100%', opacity: 0 },
  animate: { x: 0, opacity: 1, transition: { type: 'spring', stiffness: 320, damping: 32 } },
  exit:    { x: '100%', opacity: 0, transition: { duration: 0.22 } },
}

export function HoloPanel({ title, message, onClose, children }) {
  return (
    <motion.div
      className="holo-panel"
      variants={PANEL_VARIANTS}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <div className="panel-header">
        <span className="panel-indicator" />
        <span className="panel-title">{title}</span>
        <button className="panel-close" onClick={onClose} aria-label="close">✕</button>
      </div>

      {message && (
        <div className="panel-message">{message}</div>
      )}

      <div className="panel-body">
        {children}
      </div>
    </motion.div>
  )
}
