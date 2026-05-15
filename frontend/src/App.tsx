import { Routes, Route, Navigate } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SessionPage from './pages/SessionPage'
import ResultsPage from './pages/ResultsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/session/:id" element={<SessionPage />} />
      <Route path="/session/:id/results" element={<ResultsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
