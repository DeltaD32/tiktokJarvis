import { useState } from 'react'

function InlineParser({ text }) {
  const parts = []
  let remaining = text
  let key = 0

  while (remaining.length > 0) {
    // Bold **...**
    const boldMatch = remaining.match(/^\*\*(.+?)\*\*/)
    if (boldMatch) {
      parts.push(<strong key={key++}>{boldMatch[1]}</strong>)
      remaining = remaining.slice(boldMatch[0].length)
      continue
    }
    // Inline code `...`
    const codeMatch = remaining.match(/^`([^`]+)`/)
    if (codeMatch) {
      parts.push(<code key={key++} style={inlineCodeStyle}>{codeMatch[1]}</code>)
      remaining = remaining.slice(codeMatch[0].length)
      continue
    }
    // Italic *...*
    const italicMatch = remaining.match(/^\*(.+?)\*/)
    if (italicMatch) {
      parts.push(<em key={key++}>{italicMatch[1]}</em>)
      remaining = remaining.slice(italicMatch[0].length)
      continue
    }
    // Link [text](url)
    const linkMatch = remaining.match(/^\[([^\]]+)\]\(([^)]+)\)/)
    if (linkMatch) {
      parts.push(
        <a key={key++} href={linkMatch[2]} target="_blank" rel="noopener noreferrer"
          style={{ color: 'var(--accent)', textDecoration: 'underline' }}>
          {linkMatch[1]}
        </a>
      )
      remaining = remaining.slice(linkMatch[0].length)
      continue
    }
    // Plain text up to next special char
    const nextSpecial = remaining.search(/[\*\`\[]/)
    if (nextSpecial === -1) {
      parts.push(<span key={key++}>{remaining}</span>)
      break
    }
    if (nextSpecial > 0) {
      parts.push(<span key={key++}>{remaining.slice(0, nextSpecial)}</span>)
      remaining = remaining.slice(nextSpecial)
    } else {
      // Special char at position 0 but no match — treat as literal
      parts.push(<span key={key++}>{remaining[0]}</span>)
      remaining = remaining.slice(1)
    }
  }

  return <>{parts}</>
}

const inlineCodeStyle = {
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: '0.9em',
  background: 'rgba(255,255,255,0.06)',
  padding: '1px 5px',
  borderRadius: 3,
  color: 'var(--accent)',
}

const preStyle = {
  background: 'rgba(0,0,0,0.3)',
  border: '1px solid var(--border)',
  borderRadius: 8,
  padding: '10px 12px',
  margin: '8px 0',
  overflow: 'auto',
  maxHeight: 300,
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 11,
  lineHeight: 1.5,
  color: 'var(--text)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  position: 'relative',
}

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  margin: '8px 0',
  fontSize: 10,
}

const thStyle = {
  background: 'rgba(0,240,255,0.08)',
  border: '1px solid var(--border)',
  padding: '4px 8px',
  textAlign: 'left',
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 9,
  letterSpacing: '0.05em',
  color: 'var(--accent)',
}

const tdStyle = {
  border: '1px solid var(--border)',
  padding: '3px 8px',
  color: 'var(--text)',
}

const blockquoteStyle = {
  borderLeft: '2px solid var(--accent)',
  padding: '4px 12px',
  margin: '6px 0',
  background: 'rgba(0,240,255,0.03)',
  borderRadius: '0 6px 6px 0',
  color: 'var(--text-dim)',
  fontSize: '0.95em',
}

export function RichMessage({ content, maxHeight }) {
  const [iframeVisible, setIframeVisible] = useState({})
  if (!content) return null

  const lines = content.split('\n')
  const elements = []
  let i = 0
  let inCodeBlock = false
  let codeLines = []
  let codeLang = ''
  let inTable = false
  let tableRows = []
  let tableAligns = []
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block toggle
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <CodeBlock key={key++} lang={codeLang} code={codeLines.join('\n')} />
        )
        codeLines = []
        codeLang = ''
        inCodeBlock = false
      } else {
        inCodeBlock = true
        codeLang = line.trim().slice(3).trim()
      }
      i++
      continue
    }

    if (inCodeBlock) {
      codeLines.push(line)
      i++
      continue
    }

    // Table detection
    if (line.includes('|') && line.trim().startsWith('|')) {
      if (!inTable) {
        inTable = true
        tableRows = []
        tableAligns = []
      }
      const cells = line.split('|').filter(c => c.trim()).map(c => c.trim())
      // Check if this is a separator row (e.g. |---|---|)
      if (cells.every(c => /^:?-{2,}:?$/.test(c))) {
        tableAligns = cells.map(c => {
          if (c.startsWith(':') && c.endsWith(':')) return 'center'
          if (c.endsWith(':')) return 'right'
          return 'left'
        })
      } else {
        tableRows.push(cells)
      }
      // Look ahead: is next line a table row?
      const nextLine = lines[i + 1]
      if (!nextLine || !nextLine.includes('|')) {
        // End of table
        if (tableRows.length > 0) {
          elements.push(
            <Table key={key++} rows={tableRows} aligns={tableAligns} />
          )
        }
        inTable = false
        tableRows = []
        tableAligns = []
      }
      i++
      continue
    } else if (inTable) {
      // Table ended mid-way
      if (tableRows.length > 0) {
        elements.push(<Table key={key++} rows={tableRows} aligns={tableAligns} />)
      }
      inTable = false
      tableRows = []
      tableAligns = []
      // Don't increment i — reprocess this line
    }

    // Blockquote
    if (line.trim().startsWith('>')) {
      const content = line.replace(/^>\s?/, '')
      elements.push(
        <div key={key++} style={blockquoteStyle}>
          <InlineParser text={content} />
        </div>
      )
      i++
      continue
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) {
      elements.push(<hr key={key++} style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '8px 0' }} />)
      i++
      continue
    }

    // Heading
    const headingMatch = line.match(/^(#{1,3})\s+(.+)/)
    if (headingMatch) {
      const level = headingMatch[1].length
      const sizes = { 1: 15, 2: 13, 3: 12 }
      const colors = { 1: 'var(--accent)', 2: 'var(--text)', 3: 'var(--text-dim)' }
      elements.push(
        <div key={key++} style={{ fontSize: sizes[level] || 12, fontWeight: 700, color: colors[level] || 'var(--text)', margin: '8px 0 4px' }}>
          <InlineParser text={headingMatch[2]} />
        </div>
      )
      i++
      continue
    }

    // Bullet list
    const bulletMatch = line.match(/^(\s*)[-*]\s+(.+)/)
    if (bulletMatch) {
      const indent = bulletMatch[1].length
      elements.push(
        <div key={key++} style={{ paddingLeft: 12 + indent * 8, margin: '1px 0', fontSize: 11, lineHeight: 1.5 }}>
          <span style={{ color: 'var(--accent)', marginRight: 6 }}>•</span>
          <InlineParser text={bulletMatch[2]} />
        </div>
      )
      i++
      continue
    }

    // Numbered list
    const numMatch = line.match(/^(\s*)\d+\.\s+(.+)/)
    if (numMatch) {
      const indent = numMatch[1].length
      const num = elements.filter(el => el && el.key && el.key.toString().startsWith('nl')).length + 1
      elements.push(
        <div key={key++} style={{ paddingLeft: 12 + indent * 8, margin: '1px 0', fontSize: 11, lineHeight: 1.5 }}>
          <span style={{ color: 'var(--accent)', marginRight: 6, fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>{num}.</span>
          <InlineParser text={numMatch[2]} />
        </div>
      )
      i++
      continue
    }

    // URL detection — standalone URLs become preview iframes
    const urlMatch = line.trim().match(/^(https?:\/\/[^\s]+)$/)
    if (urlMatch) {
      const url = urlMatch[1]
      const show = iframeVisible[url]
      elements.push(
        <div key={key++} style={{ margin: '4px 0' }}>
          <a href={url} target="_blank" rel="noopener noreferrer"
            style={{ color: 'var(--accent)', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>
            {url}
          </a>
          <button
            className="chip"
            onClick={() => setIframeVisible(prev => ({ ...prev, [url]: !prev[url] }))}
            style={{ fontSize: 8, marginLeft: 8, padding: '1px 6px' }}
          >
            {show ? 'hide preview' : 'preview'}
          </button>
          {show && (
            <div style={{ marginTop: 4, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)', maxHeight: 300 }}>
              <iframe src={url} style={{ width: '100%', height: 300, border: 'none', background: '#fff' }}
                sandbox="allow-scripts allow-same-origin" title="URL preview" />
            </div>
          )}
        </div>
      )
      i++
      continue
    }

    // Empty line
    if (line.trim() === '') {
      elements.push(<div key={key++} style={{ height: 4 }} />)
      i++
      continue
    }

    // Regular paragraph
    elements.push(
      <div key={key++} style={{ fontSize: 11, lineHeight: 1.5, color: 'var(--text)' }}>
        <InlineParser text={line} />
      </div>
    )
    i++
  }

  // Close any open code block
  if (inCodeBlock && codeLines.length > 0) {
    elements.push(
      <CodeBlock key={key++} lang={codeLang} code={codeLines.join('\n')} />
    )
  }

  // Close open table
  if (inTable && tableRows.length > 0) {
    elements.push(<Table key={key++} rows={tableRows} aligns={tableAligns} />)
  }

  return (
    <div style={{ maxHeight: maxHeight || 'none', overflow: maxHeight ? 'auto' : 'visible' }}>
      {elements}
    </div>
  )
}

function CodeBlock({ lang, code }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {})
  }
  return (
    <div style={preStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, opacity: 0.5 }}>
        <span style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: 'var(--accent)' }}>
          {lang || 'code'}
        </span>
        <button className="chip" onClick={copy} style={{ fontSize: 8, padding: '1px 6px' }}>
          {copied ? 'copied!' : 'copy'}
        </button>
      </div>
      <code>{code}</code>
    </div>
  )
}

function Table({ rows, aligns }) {
  if (rows.length === 0) return null
  const header = rows[0]
  const body = rows.slice(1)
  return (
    <div style={{ overflow: 'auto', maxWidth: '100%' }}>
      <table style={tableStyle}>
        <thead>
          <tr>
            {header.map((cell, i) => (
              <th key={i} style={{ ...thStyle, textAlign: aligns[i] || 'left' }}>
                <InlineParser text={cell} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, ri) => (
            <tr key={ri}>
              {row.map((cell, ci) => (
                <td key={ci} style={{ ...tdStyle, textAlign: aligns[ci] || 'left' }}>
                  <InlineParser text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
