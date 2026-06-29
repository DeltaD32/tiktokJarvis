import { useRef, useEffect } from 'react'

const STATE_COLORS = {
  idle:      [0, 240, 255],
  thinking:  [179, 136, 255],
  busy:      [255, 179, 0],
  alert:     [255, 90, 69],
  speaking:  [0, 240, 255],
  complete:  [70, 242, 176],
}

export function ParticleCanvas({ state, speaking, muted }) {
  const canvasRef = useRef(null)
  const stateRef = useRef(state)
  const speakingRef = useRef(speaking)
  const rafRef = useRef(0)

  useEffect(() => { stateRef.current = state }, [state])
  useEffect(() => { speakingRef.current = speaking }, [speaking])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')

    // Particle system state
    let ring = [0, 240, 255]
    let scale = 1
    let cyf = 0.47
    let galPhase = 0
    let spin = 0
    let swirl = 0.18
    let turb = 1
    let voiceAmp = 0
    let lastT = performance.now() / 1000

    // Sun corona — fibonacci shell
    const pts = []
    const N = 150
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2
      const rr = Math.sqrt(Math.max(0, 1 - y * y))
      const phi = i * 2.399963229728653
      pts.push([Math.cos(phi) * rr, y, Math.sin(phi) * rr])
    }

    // Galaxy disk — spiral arms
    const gal = []
    const GN = 460, arms = 3
    for (let i = 0; i < GN; i++) {
      const rnd = Math.random()
      const r = 0.52 + Math.pow(rnd, 0.62) * 1.18
      const armAng = ((i % arms) / arms) * Math.PI * 2
      const ang = armAng + r * 2.15 + (Math.random() - 0.5) * 0.7
      gal.push({
        r, ang,
        z: (Math.random() - 0.5) * 0.17 * (1.7 - r),
        spd: 0.85 / Math.sqrt(r),
        size: 0.4 + Math.random() * 1.15,
        ph: Math.random() * 6.283,
        tw: 0.5 + Math.random() * 0.7,
      })
    }

    // Knowledge cloud
    const cloud = []
    for (let i = 0; i < 70; i++) {
      cloud.push({
        r: 1.5 + Math.random() * 1.5,
        ang: Math.random() * 6.283,
        z: (Math.random() - 0.5) * 0.7,
        size: 0.6 + Math.random() * 1.4,
        tw: 0.3 + Math.random() * 0.5,
        ph: Math.random() * 6.283,
      })
    }

    const draw = () => {
      const rect = canvas.getBoundingClientRect()
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      const w = rect.width, h = rect.height
      if (w > 0 && canvas.width !== Math.round(w * dpr)) {
        canvas.width = Math.round(w * dpr)
        canvas.height = Math.round(h * dpr)
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.clearRect(0, 0, w, h)

      const st = stateRef.current
      const work = st !== 'idle'
      scale += ((work ? 0.6 : 1) - scale) * 0.06
      cyf += ((work ? 0.43 : 0.47) - cyf) * 0.06

      const tg = STATE_COLORS[st] || STATE_COLORS.idle
      for (let i = 0; i < 3; i++) ring[i] += (tg[i] - ring[i]) * 0.06
      const [r, g, b] = ring.map(Math.round)
      const col = (a) => `rgba(${r},${g},${b},${a})`

      const cx = w / 2, cy = h * cyf
      const R = Math.min(w, h) * 0.40 * scale
      const t = performance.now() / 1000
      let dt = t - lastT; lastT = t
      if (dt > 0.1) dt = 0.1
      const busy = st === 'busy' || st === 'thinking'
      const alert = st === 'alert'

      // Voice amplitude
      let ampT = 0
      if (speakingRef.current) {
        const word = Math.sin(t * 1.9 + 0.4) * 0.5 + 0.5
        const syl = (Math.sin(t * 12.5) * 0.5 + 0.5) * (Math.sin(t * 27.3 + 1.1) * 0.5 + 0.5)
        ampT = (0.2 + 0.8 * syl) * (0.3 + 0.7 * word)
      }
      voiceAmp += (ampT - voiceAmp) * 0.3
      const amp = voiceAmp

      // Motion
      const swirlT = alert ? 1.5 : busy ? 0.92 : 0.2
      const turbT = alert ? 3.4 : busy ? 2.1 : 1.0
      swirl += (swirlT - swirl) * 0.05
      turb += (turbT - turb) * 0.05
      galPhase += dt * swirl
      spin += dt * (0.12 + swirl * 0.18)

      const tilt = 1.02 + Math.sin(t * 0.08) * 0.07
      const ct = Math.cos(tilt), stt = Math.sin(tilt)
      const diskSpin = t * 0.045

      // Ambient glow
      const gr = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * (1.6 + amp * 0.4))
      gr.addColorStop(0, col(0.16 + amp * 0.12))
      gr.addColorStop(0.45, col(0.05))
      gr.addColorStop(1, col(0))
      ctx.fillStyle = gr
      ctx.beginPath(); ctx.arc(cx, cy, R * (1.6 + amp * 0.4), 0, 7); ctx.fill()

      // Knowledge cloud
      for (let i = 0; i < cloud.length; i++) {
        const gg = cloud[i]
        const a = gg.ang + galPhase * 0.18 + diskSpin
        const x = Math.cos(a) * gg.r, zc = Math.sin(a) * gg.r
        const z2 = gg.z * stt + zc * ct, y2 = gg.z * ct - zc * stt
        const persp = 1 / (1.6 - z2 * 0.55), depth = (z2 + 1) / 2
        const tw = 0.5 + 0.5 * Math.sin(t * gg.tw + gg.ph)
        ctx.fillStyle = col(0.05 * depth * tw)
        ctx.beginPath()
        ctx.arc(cx + x * R * persp, cy + y2 * R * persp, gg.size * (R / 240), 0, 7)
        ctx.fill()
      }

      // Galaxy disk
      const shimmer = turb + amp * 1.6
      for (let i = 0; i < gal.length; i++) {
        const gg = gal[i]
        const a = gg.ang + galPhase * gg.spd + diskSpin
        const x = Math.cos(a) * gg.r, zc = Math.sin(a) * gg.r
        const y = gg.z + Math.sin(t * gg.tw + gg.ph) * 0.018 * shimmer
        const z2 = y * stt + zc * ct, y2 = y * ct - zc * stt
        const persp = 1 / (1.6 - z2 * 0.55), depth = (z2 + 1) / 2
        const tw = 0.62 + 0.38 * Math.sin(t * 2.2 * gg.tw + gg.ph)
        const size = gg.size * (0.45 + depth * 1.05) * (R / 175)
        ctx.fillStyle = col((0.12 + depth * 0.5) * tw)
        ctx.beginPath()
        ctx.arc(cx + x * R * persp, cy + y2 * R * persp, Math.max(0.35, size), 0, 7)
        ctx.fill()
      }

      // Sun corona
      const cosY = Math.cos(spin), sinY = Math.sin(spin)
      const cosX = Math.cos(0.5), sinX = Math.sin(0.5)
      const SR = R * 0.4
      const jit = (alert ? 1.8 : busy ? 0.8 : 0.18) * (R / 175) * (1 + amp * 1.4)
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i]
        const x = p[0] * cosY - p[2] * sinY
        const z = p[0] * sinY + p[2] * cosY
        const y2 = p[1] * cosX - z * sinX
        const z2 = p[1] * sinX + z * cosX
        const persp = 1 / (1.7 - z2 * 0.6), depth = (z2 + 1) / 2
        ctx.fillStyle = col(0.1 + depth * 0.55)
        ctx.beginPath()
        ctx.arc(
          cx + x * SR * persp + Math.sin(t * 3 + i) * jit,
          cy + y2 * SR * persp + Math.cos(t * 2.4 + i * 1.3) * jit,
          Math.max(0.4, (0.5 + depth) * (R / 200)), 0, 7
        )
        ctx.fill()
      }

      // Orbital ring
      ctx.lineWidth = 1.1
      ctx.strokeStyle = col(0.16)
      ctx.beginPath()
      for (let k = 0; k <= 64; k++) {
        const a = (k / 64) * Math.PI * 2
        const zc = Math.sin(a) * 1.32
        const z2 = zc * ct, y2 = -zc * stt
        const persp = 1 / (1.6 - z2 * 0.55)
        const X = cx + Math.cos(a) * 1.32 * R * persp, Y = cy + y2 * R * persp
        if (k === 0) ctx.moveTo(X, Y); else ctx.lineTo(X, Y)
      }
      ctx.stroke()

      // Voice halo
      if (amp > 0.015) {
        ctx.strokeStyle = col(0.55 * amp); ctx.lineWidth = 2
        ctx.beginPath(); ctx.arc(cx, cy, R * (0.46 + amp * 0.5), 0, 7); ctx.stroke()
        ctx.strokeStyle = col(0.25 * amp); ctx.lineWidth = 1.4
        ctx.beginPath(); ctx.arc(cx, cy, R * (0.46 + amp * 0.9), 0, 7); ctx.stroke()
      }

      // Bright core
      const basePulse = busy || alert ? Math.abs(Math.sin(t * (alert ? 4.4 : 2.5))) * 0.4 : 0.12 * Math.sin(t * 2)
      const pr = R * 0.06 * (1 + basePulse + amp * 1.15)
      const cgr = ctx.createRadialGradient(cx, cy, 0, cx, cy, pr * (3.2 + amp * 1.6))
      cgr.addColorStop(0, col(0.95))
      cgr.addColorStop(0.4, col(0.5))
      cgr.addColorStop(1, col(0))
      ctx.fillStyle = cgr
      ctx.beginPath(); ctx.arc(cx, cy, pr * (3.2 + amp * 1.6), 0, 7); ctx.fill()
      ctx.fillStyle = col(1)
      ctx.beginPath(); ctx.arc(cx, cy, Math.max(1.5, pr), 0, 7); ctx.fill()

      rafRef.current = requestAnimationFrame(draw)
    }

    rafRef.current = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(rafRef.current)
  }, [])

  return <canvas ref={canvasRef} className="canvas-layer" />
}
