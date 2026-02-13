import { useCallback, useEffect, useState } from 'react'
import { API_BASE } from '../api/client'

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  return Uint8Array.from(rawData, (char) => char.charCodeAt(0))
}

export function usePushNotifications() {
  const [isSupported, setIsSupported] = useState(false)
  const [isSubscribed, setIsSubscribed] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    setIsSupported('serviceWorker' in navigator && 'PushManager' in window)
  }, [])

  useEffect(() => {
    if (!isSupported) return
    navigator.serviceWorker.ready.then(async (reg) => {
      const sub = await reg.pushManager.getSubscription()
      setIsSubscribed(!!sub)
    })
  }, [isSupported])

  const subscribe = useCallback(async () => {
    if (!isSupported) return false
    setIsLoading(true)

    try {
      // Service Worker 등록
      const reg = await navigator.serviceWorker.register('/sw.js')
      await navigator.serviceWorker.ready

      // VAPID 공개키 조회
      const keyRes = await fetch(`${API_BASE}/settings/push/vapid-key`)
      if (!keyRes.ok) throw new Error('VAPID 키 조회 실패')
      const { publicKey } = await keyRes.json()

      // Push 구독
      const subscription = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey) as BufferSource,
      })

      const subJson = subscription.toJSON()

      // 백엔드에 구독 정보 전송
      const keys = Object.keys(localStorage).filter(
        (k) => k.startsWith('sb-') && k.endsWith('-auth-token'),
      )
      const tokenData = keys.length > 0 ? JSON.parse(localStorage.getItem(keys[0]) || '{}') : null
      const accessToken = tokenData?.access_token

      await fetch(`${API_BASE}/settings/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          endpoint: subJson.endpoint,
          p256dh: subJson.keys?.p256dh || '',
          auth: subJson.keys?.auth || '',
        }),
      })

      setIsSubscribed(true)
      return true
    } catch (err) {
      console.error('푸시 구독 실패:', err)
      return false
    } finally {
      setIsLoading(false)
    }
  }, [isSupported])

  const unsubscribe = useCallback(async () => {
    if (!isSupported) return
    const reg = await navigator.serviceWorker.ready
    const sub = await reg.pushManager.getSubscription()
    if (sub) {
      await sub.unsubscribe()
      setIsSubscribed(false)
    }
  }, [isSupported])

  return { isSupported, isSubscribed, isLoading, subscribe, unsubscribe }
}
