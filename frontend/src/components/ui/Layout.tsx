import { Users } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 font-semibold text-gray-900 hover:text-primary-600">
            <Users className="h-5 w-5 text-primary-600" />
            TeamBuilder
          </Link>
        </div>
      </header>
      <main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">
        {children}
      </main>
    </div>
  )
}
