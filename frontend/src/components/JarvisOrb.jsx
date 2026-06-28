import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { MeshDistortMaterial } from '@react-three/drei'
import * as THREE from 'three'

const COLORS = {
  idle:      '#00c8ff',
  listening: '#00f0ff',
  thinking:  '#ffaa00',
  speaking:  '#00ff88',
  alert:     '#ff4400',
}

const RING_CONFIGS = [
  { radius: 1.9, tube: 0.018, baseRotation: [Math.PI / 2, 0, 0],          speed:  0.35 },
  { radius: 2.1, tube: 0.012, baseRotation: [Math.PI / 4, Math.PI / 5, 0], speed: -0.28 },
  { radius: 2.3, tube: 0.009, baseRotation: [0, Math.PI / 3, Math.PI / 4], speed:  0.20 },
]

export function JarvisOrb({ state = 'idle' }) {
  // All material refs for imperative updates in useFrame
  const coreRef        = useRef()
  const innerRef       = useRef()
  const wireRef        = useRef()
  const distortMatRef  = useRef()
  const innerMatRef    = useRef()
  const lightRef       = useRef()
  const ringRefs       = [useRef(), useRef(), useRef()]
  const ringMatRefs    = [useRef(), useRef(), useRef()]
  const pulseRef       = useRef()
  const pulseMatRef    = useRef()
  const pointsRef      = useRef()
  const pointsMatRef   = useRef()

  // Lerped color state (no React re-renders, lives in useFrame)
  const lerpedColor = useRef(new THREE.Color(COLORS.idle))
  const targetColor = useRef(new THREE.Color(COLORS.idle))
  const pulseScale  = useRef(1.0)

  // Track state changes without re-renders
  const stateRef = useRef(state)
  if (stateRef.current !== state) {
    stateRef.current = state
    targetColor.current.set(COLORS[state] ?? COLORS.idle)
  }

  // Particle positions — fixed sphere distribution
  const particlePositions = useMemo(() => {
    const count = 2800
    const arr = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi   = Math.acos(2 * Math.random() - 1)
      const r     = 2.4 + Math.random() * 1.3
      arr[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      arr[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      arr[i * 3 + 2] = r * Math.cos(phi)
    }
    return arr
  }, [])

  useFrame(({ clock }, delta) => {
    const t  = clock.getElapsedTime()
    const st = stateRef.current

    // Lerp color towards target
    lerpedColor.current.lerp(targetColor.current, delta * 5)
    const c = lerpedColor.current

    // State-dependent pulse speed
    const pulseSpeed = st === 'listening' ? 3.5 : st === 'alert' ? 6 : st === 'thinking' ? 2 : 1.5
    const orbScale   = 1 + 0.065 * Math.sin(t * pulseSpeed)

    // Core sphere
    if (coreRef.current)   coreRef.current.scale.setScalar(orbScale)
    if (innerRef.current)  innerRef.current.scale.setScalar(orbScale * 1.04)

    // Update distort material
    if (distortMatRef.current) {
      const mat = distortMatRef.current
      mat.emissive.set(c)
      mat.emissiveIntensity = st === 'alert' ? 1.2 : st === 'speaking' ? 0.9 : st === 'listening' ? 0.8 : 0.45
      mat.distort = st === 'thinking' ? 0.55 : 0.28
    }

    // Inner glow
    if (innerMatRef.current) {
      innerMatRef.current.emissive.set(c)
      innerMatRef.current.emissiveIntensity = 1.8 + 0.6 * Math.sin(t * pulseSpeed * 1.3)
    }

    // Wireframe
    if (wireRef.current) {
      wireRef.current.material.color.set(c)
      wireRef.current.material.opacity = 0.1 + 0.06 * Math.sin(t * 1.8)
    }

    // Point light
    if (lightRef.current) {
      lightRef.current.color.set(c)
      const baseIntensity = st === 'alert' ? 9 : st === 'speaking' ? 7 : st === 'listening' ? 6 : 3.5
      lightRef.current.intensity = baseIntensity + 1.5 * Math.sin(t * pulseSpeed)
    }

    // Orbital rings
    const ringSpeedMult = st === 'thinking' ? 2.2 : st === 'listening' ? 1.6 : 1
    RING_CONFIGS.forEach((cfg, i) => {
      const ring    = ringRefs[i].current
      const ringMat = ringMatRefs[i].current
      if (ring) {
        ring.rotation.z += delta * cfg.speed * ringSpeedMult
        ring.rotation.x += delta * cfg.speed * ringSpeedMult * 0.4
      }
      if (ringMat) {
        ringMat.color.set(c)
        ringMat.emissive.set(c)
        ringMat.emissiveIntensity = 0.9 + 0.3 * Math.sin(t * 2 + i)
      }
    })

    // Expanding pulse ring
    const pulseSpeedRate = st === 'speaking' ? 1.6 : st === 'listening' ? 0.9 : 0.5
    pulseScale.current += delta * pulseSpeedRate
    if (pulseScale.current > 3.8) pulseScale.current = 1.0

    if (pulseRef.current) {
      const s = pulseScale.current
      pulseRef.current.scale.setScalar(s)
    }
    if (pulseMatRef.current) {
      const t2 = (pulseScale.current - 1) / 2.8
      pulseMatRef.current.opacity = Math.max(0, 0.4 * (1 - t2))
      pulseMatRef.current.emissive.set(c)
      pulseMatRef.current.color.set(c)
    }

    // Particle cloud
    if (pointsRef.current) {
      pointsRef.current.rotation.y += delta * 0.045
      pointsRef.current.rotation.x += delta * 0.012
    }
    if (pointsMatRef.current) {
      pointsMatRef.current.color.set(c)
      pointsMatRef.current.opacity = st === 'idle' ? 0.35 : 0.55
    }
  })

  return (
    <group>
      {/* Dynamic point light (color + intensity updated in useFrame) */}
      <pointLight ref={lightRef} color="#00c8ff" intensity={3.5} distance={14} />
      {/* Subtle ambient fill */}
      <pointLight color="#001133" intensity={0.8} distance={25} position={[0, 6, 2]} />

      {/* Inner bright core glow */}
      <mesh ref={innerRef}>
        <sphereGeometry args={[0.65, 32, 32]} />
        <meshStandardMaterial
          ref={innerMatRef}
          color="#ffffff"
          emissive="#00c8ff"
          emissiveIntensity={1.8}
          transparent
          opacity={0.18}
        />
      </mesh>

      {/* Main distorted sphere */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[1.2, 64, 64]} />
        <MeshDistortMaterial
          ref={distortMatRef}
          color="#00c8ff"
          emissive="#00c8ff"
          emissiveIntensity={0.45}
          distort={0.28}
          speed={2.5}
          transparent
          opacity={0.62}
        />
      </mesh>

      {/* Wireframe grid overlay — creates Jarvis holographic grid look */}
      <mesh ref={wireRef}>
        <sphereGeometry args={[1.215, 18, 18]} />
        <meshBasicMaterial
          color="#00c8ff"
          wireframe
          transparent
          opacity={0.1}
        />
      </mesh>

      {/* Three orbital rings */}
      {RING_CONFIGS.map((cfg, i) => (
        <mesh key={i} ref={ringRefs[i]} rotation={cfg.baseRotation}>
          <torusGeometry args={[cfg.radius, cfg.tube, 8, 120]} />
          <meshStandardMaterial
            ref={ringMatRefs[i]}
            color="#00c8ff"
            emissive="#00c8ff"
            emissiveIntensity={0.9}
            transparent
            opacity={0.72}
          />
        </mesh>
      ))}

      {/* Expanding energy pulse ring */}
      <mesh ref={pulseRef}>
        <torusGeometry args={[1.6, 0.007, 4, 80]} />
        <meshStandardMaterial
          ref={pulseMatRef}
          color="#00c8ff"
          emissive="#00c8ff"
          emissiveIntensity={2.5}
          transparent
          opacity={0.35}
        />
      </mesh>

      {/* Particle cloud */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            args={[particlePositions, 3]}
          />
        </bufferGeometry>
        <pointsMaterial
          ref={pointsMatRef}
          color="#00c8ff"
          size={0.013}
          sizeAttenuation
          transparent
          opacity={0.4}
        />
      </points>
    </group>
  )
}
