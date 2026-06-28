import { motion } from 'framer-motion'

const OVERLAY = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit:    { opacity: 0 },
}

const BOX = {
  initial: { scale: 0.85, opacity: 0, y: 20 },
  animate: { scale: 1, opacity: 1, y: 0, transition: { type: 'spring', stiffness: 420, damping: 26 } },
  exit:    { scale: 0.9, opacity: 0, y: -10, transition: { duration: 0.18 } },
}

export function ConfirmationDialog({ request, onConfirm, onDeny }) {
  return (
    <motion.div
      className="confirm-overlay"
      variants={OVERLAY}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      <motion.div className="confirm-box" variants={BOX}>
        <div className="confirm-icon">⚠</div>
        <div className="confirm-title">Authorization Required</div>
        <div className="confirm-desc">{request.description}</div>
        <div className="confirm-actions">
          <button className="confirm-deny" onClick={onDeny}>Deny</button>
          <button className="confirm-approve" onClick={onConfirm}>Authorize</button>
        </div>
      </motion.div>
    </motion.div>
  )
}
