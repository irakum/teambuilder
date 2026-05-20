import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Send, ArrowLeft, MessageSquare } from 'lucide-react'
import Layout from '../components/ui/Layout'
import Spinner from '../components/ui/Spinner'
import { apiClient } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

interface ChatListItem {
  channel: string
  title: string
  subtitle?: string
  last_message_at: string | null
}

interface ChatMessage {
  id: string
  channel: string
  sender_id: string
  sender_name: string
  sender_avatar?: string
  content: string
  created_at: string
}

interface ChatMeta {
  channel: string
  title: string
  subtitle?: string
  lastMessageAt: string | null
  unread: number
}

export default function ChatPage() {
  const { id: sessionId } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const { user } = useAuth()
  const [activeChannel, setActiveChannel] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatMeta, setChatMeta] = useState<Record<string, ChatMeta>>({})
  const [input, setInput] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: chats, isLoading } = useQuery({
    queryKey: ['chats', sessionId],
    queryFn: () => apiClient.get<ChatListItem[]>(`/sessions/${sessionId}/chats`).then(r => r.data),
    enabled: !!sessionId,
    staleTime: 0,
    refetchOnMount: true,
    refetchInterval: 10000, // оновлюємо кожні 10 секунд
  })

  // Зберігаємо час останнього прочитання в localStorage
  const getReadAt = (channel: string) =>
    localStorage.getItem(`read_at:${sessionId}:${channel}`) ?? null

  const markRead = (channel: string) => {
    localStorage.setItem(`read_at:${sessionId}:${channel}`, new Date().toISOString())
  }

  // Оновлюємо meta при кожному refetch — рахуємо unread по localStorage
  useEffect(() => {
    if (!chats) return
    setChatMeta(prev => {
      const next = { ...prev }
      chats.forEach(c => {
        const readAt = getReadAt(c.channel)
        const isActive = c.channel === activeChannel
        const hasUnread = !isActive && c.last_message_at && (
          !readAt || new Date(c.last_message_at) > new Date(readAt)
        )
        // Зберігаємо ws unread якщо він більший
        const wsUnread = prev[c.channel]?.unread ?? 0
        next[c.channel] = {
          channel: c.channel,
          title: c.title,
          subtitle: c.subtitle,
          lastMessageAt: c.last_message_at,
          unread: isActive ? 0 : (hasUnread ? Math.max(wsUnread, 1) : wsUnread),
        }
      })
      return next
    })
  }, [chats, activeChannel])

  // Автоматично відкриваємо перший чат
  useEffect(() => {
    if (chats && chats.length > 0 && !activeChannel) {
      setActiveChannel(chats[0].channel)
    }
  }, [chats])

  // При відкритті каналу — скидаємо лічильник і зберігаємо час прочитання
  useEffect(() => {
    if (!activeChannel) return
    markRead(activeChannel)
    setChatMeta(prev => ({
      ...prev,
      [activeChannel]: { ...prev[activeChannel], unread: 0 },
    }))
  }, [activeChannel])

  // WebSocket підключення
  useEffect(() => {
    if (!activeChannel || !sessionId || !user?.id) return

    const jwt = localStorage.getItem('jwt_token')
    if (!jwt) return

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setMessages([])

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${protocol}//${window.location.host}/api/ws/${sessionId}?token=${jwt}&channel=${encodeURIComponent(activeChannel)}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'history') {
        setMessages(data.messages)
        // Оновлюємо lastMessageAt з history
        if (data.messages.length > 0) {
          const last = data.messages[data.messages.length - 1]
          setChatMeta(prev => ({
            ...prev,
            [activeChannel]: {
              ...prev[activeChannel],
              lastMessageAt: last.created_at,
              unread: 0,
            },
          }))
        }
      } else if (data.type === 'message') {
        const msg: ChatMessage = data.message
        setMessages(prev => [...prev, msg])
        // Оновлюємо meta — якщо чужий канал то +unread
        setChatMeta(prev => {
          const ch = msg.channel === 'general' ? 'general'
            : msg.team_id ? `team:${msg.team_id}`
            : msg.participant_id ? `support:${msg.participant_id}`
            : activeChannel
          const isActive = ch === activeChannel
          const current = prev[ch] || {}
          return {
            ...prev,
            [ch]: {
              ...current,
              lastMessageAt: msg.created_at,
              unread: isActive ? 0 : (current.unread || 0) + 1,
            },
          }
        })
      }
    }

    ws.onerror = () => console.error('WebSocket error')

    return () => { ws.close() }
  }, [activeChannel, sessionId, user?.id])

  // Скрол вниз
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(() => {
    const content = input.trim()
    if (!content || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ content }))
    setInput('')
  }, [input])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Сортуємо чати по lastMessageAt (останні зверху)
  const sortedChats = Object.values(chatMeta).sort((a, b) => {
    if (!a.lastMessageAt && !b.lastMessageAt) return 0
    if (!a.lastMessageAt) return 1
    if (!b.lastMessageAt) return -1
    return new Date(b.lastMessageAt).getTime() - new Date(a.lastMessageAt).getTime()
  })

  const activeChat = chatMeta[activeChannel ?? '']

  const formatTime = (iso: string) => new Date(iso).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })
  const formatDate = (iso: string) => new Date(iso).toLocaleDateString('uk-UA', { day: 'numeric', month: 'long' })

  const groupedMessages = messages.reduce<{ date: string; msgs: ChatMessage[] }[]>((acc, msg) => {
    const date = formatDate(msg.created_at)
    const last = acc[acc.length - 1]
    if (last && last.date === date) { last.msgs.push(msg) }
    else { acc.push({ date, msgs: [msg] }) }
    return acc
  }, [])

  if (isLoading) return (
    <Layout><div className="flex justify-center pt-20"><Spinner size="lg" /></div></Layout>
  )

  return (
    <Layout>
      <div className="flex gap-4 h-[calc(100vh-120px)]">

        {/* Sidebar */}
        <div className="w-72 flex-shrink-0 flex flex-col card overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
            <button
              className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-1"
              onClick={() => navigate(`/session/${sessionId}`)}
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Назад
            </button>
            <h2 className="font-semibold text-gray-900 text-sm">Чати</h2>
          </div>
          <div className="flex-1 overflow-y-auto">
            {sortedChats.length === 0 ? (
              <div className="text-center py-8 text-gray-400 text-sm px-4">
                <MessageSquare className="h-6 w-6 mx-auto mb-2 opacity-40" />
                Немає доступних чатів
              </div>
            ) : (
              <ul className="divide-y divide-gray-50">
                {sortedChats.map(chat => (
                  <li key={chat.channel}>
                    <button
                      className={`w-full text-left px-4 py-3 transition-colors ${
                        activeChannel === chat.channel
                          ? 'bg-primary-50 border-r-2 border-primary-500'
                          : chat.unread > 0
                          ? 'bg-blue-50 hover:bg-blue-100'
                          : 'hover:bg-gray-50'
                      }`}
                      onClick={() => setActiveChannel(chat.channel)}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className={`text-sm leading-tight truncate ${
                            activeChannel === chat.channel
                              ? 'text-primary-700 font-medium'
                              : chat.unread > 0
                              ? 'text-gray-900 font-semibold'
                              : 'text-gray-900 font-medium'
                          }`}>
                            {chat.title}
                          </p>
                          {chat.subtitle && (
                            <p className="text-xs text-gray-400 mt-0.5">{chat.subtitle}</p>
                          )}
                          {chat.lastMessageAt && (
                            <p className={`text-xs mt-0.5 ${chat.unread > 0 ? 'text-primary-500 font-medium' : 'text-gray-400'}`}>
                              {formatTime(chat.lastMessageAt)}
                            </p>
                          )}
                        </div>
                        {chat.unread > 0 && (
                          <span className="flex-shrink-0 mt-0.5 inline-flex items-center justify-center min-w-[20px] h-5 px-1 rounded-full bg-primary-500 text-white text-xs font-bold">
                            {chat.unread > 99 ? '99+' : chat.unread}
                          </span>
                        )}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Chat panel */}
        <div className="flex-1 flex flex-col card overflow-hidden">
          {!activeChannel ? (
            <div className="flex-1 flex items-center justify-center text-gray-400">
              <div className="text-center">
                <MessageSquare className="h-10 w-10 mx-auto mb-3 opacity-30" />
                <p>Оберіть чат зліва</p>
              </div>
            </div>
          ) : (
            <>
              <div className="px-5 py-3 border-b border-gray-100 bg-gray-50 flex-shrink-0">
                <h3 className="font-semibold text-gray-900 text-sm">{activeChat?.title}</h3>
                {activeChat?.subtitle && <p className="text-xs text-gray-400">{activeChat.subtitle}</p>}
              </div>

              <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {messages.length === 0 ? (
                  <div className="text-center text-gray-400 text-sm pt-8">
                    Повідомлень ще немає. Напишіть перше!
                  </div>
                ) : (
                  groupedMessages.map(group => (
                    <div key={group.date}>
                      <div className="flex items-center gap-3 my-3">
                        <div className="flex-1 h-px bg-gray-100" />
                        <span className="text-xs text-gray-400">{group.date}</span>
                        <div className="flex-1 h-px bg-gray-100" />
                      </div>
                      <div className="space-y-3">
                        {group.msgs.map(msg => {
                          const isMe = msg.sender_id === user?.id
                          return (
                            <div key={msg.id} className={`flex gap-2 ${isMe ? 'flex-row-reverse' : ''}`}>
                              {msg.sender_avatar ? (
                                <img src={msg.sender_avatar} alt={msg.sender_name}
                                  className="w-7 h-7 rounded-full flex-shrink-0 mt-1" />
                              ) : (
                                <div className="w-7 h-7 rounded-full bg-gray-200 flex-shrink-0 mt-1 flex items-center justify-center text-xs text-gray-500">
                                  {msg.sender_name[0]}
                                </div>
                              )}
                              <div className={`max-w-[70%] flex flex-col ${isMe ? 'items-end' : 'items-start'}`}>
                                {!isMe && (
                                  <span className="text-xs text-gray-400 mb-1 ml-1">{msg.sender_name}</span>
                                )}
                                <div className={`px-3 py-2 rounded-2xl text-sm ${
                                  isMe ? 'bg-primary-500 text-white rounded-tr-sm' : 'bg-gray-100 text-gray-900 rounded-tl-sm'
                                }`}>
                                  {msg.content}
                                </div>
                                <span className="text-xs text-gray-400 mt-1 mx-1">{formatTime(msg.created_at)}</span>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  ))
                )}
                <div ref={bottomRef} />
              </div>

              <div className="px-4 py-3 border-t border-gray-100 flex-shrink-0">
                <div className="flex gap-2 items-end">
                  <textarea
                    className="input flex-1 resize-none min-h-[40px] max-h-[120px]"
                    placeholder="Написати повідомлення..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                  />
                  <button
                    className="btn-primary flex-shrink-0 h-10"
                    onClick={sendMessage}
                    disabled={!input.trim()}
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>
                <p className="text-xs text-gray-400 mt-1">Enter — надіслати, Shift+Enter — новий рядок</p>
              </div>
            </>
          )}
        </div>
      </div>
    </Layout>
  )
}
