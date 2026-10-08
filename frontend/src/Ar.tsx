import type { ReactNode } from 'react'

// Arabic inside other text, isolated so its direction doesn't reorder the sentence
export const Ar = ({ children }: { children: ReactNode }) => (
  <bdi lang="ar" className="arabic">
    {children}
  </bdi>
)
