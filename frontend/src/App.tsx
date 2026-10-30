import { useState, useEffect } from 'react';
import type { User, AdoCredential } from './types';
import { api } from './api/client';
import { Navbar } from './components/Navbar';
import { WeeklyTimesheetView } from './components/WeeklyTimesheetView';
import { ConnectionsModal } from './components/ConnectionsModal';
import { AuthView } from './components/AuthView';

function getMondayOfCurrentWeek(): string {
  const today = new Date();
  const day = today.getDay();
  const diff = today.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(today.setDate(diff));
  return monday.toISOString().split('T')[0];
}

export function App() {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('user');
    return saved ? JSON.parse(saved) : null;
  });
  const [credentials, setCredentials] = useState<AdoCredential[]>([]);
  const [isConnectionsOpen, setIsConnectionsOpen] = useState(false);
  const [selectedMonday, setSelectedMonday] = useState<string>(getMondayOfCurrentWeek());

  // Load credentials if user logged in
  const loadCredentials = async () => {
    if (!user) return;
    try {
      const data = await api.getCredentials();
      setCredentials(data);
    } catch (err) {
      console.error('Failed to load credentials:', err);
    }
  };

  useEffect(() => {
    if (user) {
      loadCredentials();
    }
  }, [user]);

  // Handle auth expiration event
  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
      setCredentials([]);
    };
    window.addEventListener('auth-expired', handleAuthExpired);
    return () => window.removeEventListener('auth-expired', handleAuthExpired);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setCredentials([]);
  };

  if (!user) {
    return <AuthView onAuthSuccess={(u) => setUser(u)} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <Navbar
        user={user}
        credentials={credentials}
        onOpenConnections={() => setIsConnectionsOpen(true)}
        onLogout={handleLogout}
        selectedMonday={selectedMonday}
        onWeekChange={(mon) => setSelectedMonday(mon)}
      />

      <main className="flex-1 pb-16">
        <WeeklyTimesheetView selectedMonday={selectedMonday} />
      </main>

      <ConnectionsModal
        isOpen={isConnectionsOpen}
        onClose={() => setIsConnectionsOpen(false)}
        credentials={credentials}
        onCredentialsUpdated={loadCredentials}
      />
    </div>
  );
}

export default App;
