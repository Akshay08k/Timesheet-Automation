import React from 'react';
import type { User, AdoCredential } from '../types';
import { Calendar, CheckCircle2, AlertCircle, LogOut, Link2, Sparkles, Clock } from 'lucide-react';

interface NavbarProps {
  user: User;
  credentials: AdoCredential[];
  onOpenConnections: () => void;
  onLogout: () => void;
  selectedMonday: string;
  onWeekChange: (mondayStr: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  credentials,
  onOpenConnections,
  onLogout,
  selectedMonday,
  onWeekChange,
}) => {
  const clientCred = credentials.find((c) => c.provider === 'client' && c.is_valid);
  const rysunCred = credentials.find((c) => c.provider === 'rysun' && c.is_valid);

  const handlePrevWeek = () => {
    const d = new Date(selectedMonday);
    d.setDate(d.getDate() - 7);
    onWeekChange(d.toISOString().split('T')[0]);
  };

  const handleNextWeek = () => {
    const d = new Date(selectedMonday);
    d.setDate(d.getDate() + 7);
    onWeekChange(d.toISOString().split('T')[0]);
  };

  const handleThisWeek = () => {
    const today = new Date();
    const day = today.getDay();
    const diff = today.getDate() - day + (day === 0 ? -6 : 1);
    const mon = new Date(today.setDate(diff));
    onWeekChange(mon.toISOString().split('T')[0]);
  };

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 text-white p-2 rounded-lg flex items-center justify-center shadow-xs">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">DevTimesheet</span>
              <span className="inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                <Sparkles className="w-3 h-3 text-indigo-600" />
                Gemini AI
              </span>
            </div>
            <p className="text-xs text-slate-500">Azure DevOps & Timesheet Automation</p>
          </div>
        </div>

        {/* Week Selector */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button
            onClick={handlePrevWeek}
            className="px-2 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-white rounded transition"
            title="Previous Week"
          >
            ← Prev
          </button>
          <div className="flex items-center gap-2 px-3 py-1 text-sm font-semibold text-slate-800">
            <Calendar className="w-4 h-4 text-blue-600" />
            <span>Week of {selectedMonday}</span>
          </div>
          <button
            onClick={handleNextWeek}
            className="px-2 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-white rounded transition"
            title="Next Week"
          >
            Next →
          </button>
          <button
            onClick={handleThisWeek}
            className="ml-2 px-2.5 py-1 text-xs font-semibold bg-white text-blue-600 border border-slate-200 rounded shadow-2xs hover:bg-blue-50 transition"
          >
            Current
          </button>
        </div>

        {/* Right Section: Connections & User Profile */}
        <div className="flex items-center gap-4">
          {/* ADO Connection Pills */}
          <button
            onClick={onOpenConnections}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition text-xs"
          >
            <Link2 className="w-4 h-4 text-slate-500" />
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600 font-medium">Client:</span>
              {clientCred ? (
                <span className="inline-flex items-center text-emerald-700 font-semibold gap-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                </span>
              ) : (
                <span className="inline-flex items-center text-amber-600 font-medium gap-0.5">
                  <AlertCircle className="w-3.5 h-3.5" /> Disconnected
                </span>
              )}
            </div>
            <span className="text-slate-300">|</span>
            <div className="flex items-center gap-1.5">
              <span className="text-slate-600 font-medium">Rysun:</span>
              {rysunCred ? (
                <span className="inline-flex items-center text-emerald-700 font-semibold gap-0.5">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                </span>
              ) : (
                <span className="inline-flex items-center text-amber-600 font-medium gap-0.5">
                  <AlertCircle className="w-3.5 h-3.5" /> Disconnected
                </span>
              )}
            </div>
          </button>

          {/* User Profile & Logout */}
          <div className="flex items-center gap-2 border-l border-slate-200 pl-4">
            <div className="text-right">
              <div className="text-xs font-bold text-slate-800">{user.full_name}</div>
              <div className="text-[11px] text-slate-500">{user.timezone}</div>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
