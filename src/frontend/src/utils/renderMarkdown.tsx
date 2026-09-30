import React from 'react'

const escapeHtml = (s: string) =>
  s.replace(/&/g, '&amp;')
   .replace(/</g, '&lt;')
   .replace(/>/g, '&gt;')
   .replace(/"/g, '&quot;')
   .replace(/'/g, '&#39;')

const inlineMd = (s: string) =>
  escapeHtml(s)
   .replace(/\\([_*[\]()#])/g, '$1')
   .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
   .replace(/`([^`]+)`/g, '<code style="background:var(--bg-input);padding:1px 4px;border-radius:3px;font-size:12px">$1</code>')

export function renderMarkdown(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactElement[] = []
  let listItems: string[] = []
  let listOrdered = false

  const flushList = () => {
    if (listItems.length === 0) return
    const Tag = listOrdered ? 'ol' : 'ul'
    elements.push(
      <Tag key={`list-${elements.length}`} style={{ margin: '6px 0', paddingLeft: '20px', listStyle: listOrdered ? 'decimal' : 'disc' }}>
        {listItems.map((li, i) => <li key={i} style={{ marginBottom: '4px' }} dangerouslySetInnerHTML={{ __html: inlineMd(li) }} />)}
      </Tag>
    )
    listItems = []
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const bullet = line.match(/^[-–•]\s+(.*)/)
    const numbered = line.match(/^\d+\.\s+(.*)/)
    if (bullet) {
      if (listOrdered) flushList()
      listOrdered = false
      listItems.push(bullet[1])
      continue
    }
    if (numbered) {
      if (!listOrdered && listItems.length > 0) flushList()
      listOrdered = true
      listItems.push(numbered[1])
      continue
    }
    flushList()
    if (line.trim() === '') {
      elements.push(<div key={`br-${i}`} style={{ height: '8px' }} />)
    } else {
      elements.push(<p key={`p-${i}`} style={{ margin: '4px 0' }} dangerouslySetInnerHTML={{ __html: inlineMd(line) }} />)
    }
  }
  flushList()
  return <>{elements}</>
}
