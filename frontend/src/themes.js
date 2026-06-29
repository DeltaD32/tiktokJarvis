export const THEMES = {
  jarvis: {
    name: 'JARVIS',
    colors: {
      idle:     '0,240,255',
      thinking: '179,136,255',
      busy:     '255,179,0',
      alert:    '255,90,69',
      complete: '70,242,176',
    },
  },
  ultraviolet: {
    name: 'ULTRAVIOLET',
    colors: {
      idle:     '138,99,255',
      thinking: '186,85,211',
      busy:     '255,100,180',
      alert:    '255,60,60',
      complete: '0,230,200',
    },
  },
  solar: {
    name: 'SOLAR',
    colors: {
      idle:     '255,180,0',
      thinking: '255,120,0',
      busy:     '255,80,0',
      alert:    '255,40,40',
      complete: '180,255,0',
    },
  },
  forest: {
    name: 'FOREST',
    colors: {
      idle:     '0,230,120',
      thinking: '100,200,255',
      busy:     '255,200,0',
      alert:    '255,80,80',
      complete: '180,255,100',
    },
  },
  crimson: {
    name: 'CRIMSON',
    colors: {
      idle:     '255,80,80',
      thinking: '255,140,0',
      busy:     '255,180,0',
      alert:    '255,40,40',
      complete: '100,255,150',
    },
  },
}

export function applyTheme(themeName) {
  const theme = THEMES[themeName] || THEMES.jarvis
  const root = document.documentElement
  for (const [state, rgb] of Object.entries(theme.colors)) {
    root.style.setProperty(`--${state}-rgb`, rgb)
  }
  // Set current accent based on idle color
  root.style.setProperty('--accent-rgb', theme.colors.idle)
  root.style.setProperty('--accent', `rgb(${theme.colors.idle})`)
  localStorage.setItem('dela-theme', themeName)
}

export function getCurrentTheme() {
  return localStorage.getItem('dela-theme') || 'jarvis'
}
