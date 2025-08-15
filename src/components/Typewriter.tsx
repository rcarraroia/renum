
'use client'
import { useEffect, useMemo, useRef, useState } from 'react'

type Props = { 
  texts: string[]
  speed?: number
  pause?: number
  loop?: boolean
}

export default function Typewriter({ texts, speed = 28, pause = 1200, loop = true }: Props) {
  const indexRef = useRef(0)
  const [output, setOutput] = useState('')
  const [phase, setPhase] = useState<'typing'|'pausing'|'deleting'>('typing')
  const current = useMemo(() => texts[indexRef.current % texts.length] || '', [texts])

  useEffect(() => {
    if (phase === 'typing') {
      if (output.length < current.length) {
        const t = setTimeout(() => setOutput(current.slice(0, output.length + 1)), speed)
        return () => clearTimeout(t)
      }
      setPhase('pausing')
    }
    if (phase === 'pausing') {
      const t = setTimeout(() => setPhase('deleting'), pause)
      return () => clearTimeout(t)
    }
    if (phase === 'deleting') {
      if (output.length > 0) {
        const t = setTimeout(() => setOutput(current.slice(0, output.length - 1)), Math.max(10, speed / 2))
        return () => clearTimeout(t)
      }
      indexRef.current = indexRef.current + 1
      if (!loop && indexRef.current >= texts.length) return
      setPhase('typing')
    }
  }, [phase, output, current, speed, pause, loop, texts.length])

  return (
    <span aria-live="polite" aria-atomic="true">
      {output}
      <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-0.5 animate-caret" 
            style={{ backgroundColor: 'hsl(var(--renum-fg))' }} />
    </span>
  )
}
