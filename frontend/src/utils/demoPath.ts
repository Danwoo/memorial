import { isDemoMode } from '../contexts/DemoContext'

export function demoPath(path: string): string {
  return isDemoMode() ? `/demo${path}` : path
}
