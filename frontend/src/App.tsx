import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import Spinner from './components/ui/Spinner'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import SessionPage from './pages/SessionPage'
import ResultsPage from './pages/ResultsPage'
import JoinPage from './pages/JoinPage'
import ChatPage from './pages/ChatPage'
import AnnouncementsPage from './pages/AnnouncementsPage'

function RootRedirect() {
  const { user, isLoading } = useAuth()
  if (isLoading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner size="lg" />
    </div>
  )
  return user ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/create" element={<HomePage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/session/:id" element={<SessionPage />} />
      <Route path="/session/:id/results" element={<ResultsPage />} />
      <Route path="/join/:code" element={<JoinPage />} />
      <Route path="/session/:id/chat" element={<ChatPage />} />
      <Route path="/session/:id/announcements" element={<AnnouncementsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
