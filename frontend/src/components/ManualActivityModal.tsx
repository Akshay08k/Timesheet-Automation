import React, { useState } from 'react';
import type { ManualActivity } from '../types';
import { api } from '../api/client';
import { X, Plus, Trash2, Clock } from 'lucide-react';

interface ManualActivityModalProps {
  isOpen: boolean;
  onClose: () => void;
  dateStr: string;
  activities: ManualActivity[];
  onActivitiesChanged: () => void;
}

const CATEGORIES = [
  'Meeting',
  'Client Discussion',
  'Team Discussion',
  'Debugging & Investigation',
  'Code Review',
  'Documentation',
  'Requirement Analysis',
  'Deployment / Release',
  'Other',
];

export const ManualActivityModal: React.FC<ManualActivityModalProps> = ({
  isOpen,
  onClose,
  dateStr,
  activities,
  onActivitiesChanged,
}) => {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState<number>(1.0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await api.createManualActivity({
        date_str: dateStr,
        category,
        description,
        duration_hours: Number(duration),
      });
      setDescription('');
      onActivitiesChanged();
    } catch (err: any) {
      setError(err.message || 'Failed to add activity');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteManualActivity(id);
      onActivitiesChanged();
    } catch (err: any) {
      setError(err.message || 'Failed to delete activity');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">Manual Non-Code Activities ({dateStr})</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-5">
          {/* Add form */}
          <form onSubmit={handleAdd} className="space-y-3 bg-slate-50 p-4 rounded-lg border border-slate-200">
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Log Non-Code Work</h4>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full text-xs px-2.5 py-1.5 bg-white border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">Duration (Hours)</label>
                <input
                  type="number"
                  step="0.25"
                  min="0.25"
                  max="24"
                  value={duration}
                  onChange={(e) => setDuration(parseFloat(e.target.value))}
                  className="w-full text-xs px-2.5 py-1.5 bg-white border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">Activity Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                placeholder="e.g. Sprint planning meeting with Visual Comfort team to discuss RMA tickets..."
                required
                className="w-full text-xs px-2.5 py-1.5 bg-white border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-hidden resize-none"
              />
            </div>

            {error && <div className="text-xs text-rose-600">{error}</div>}

            <button
              type="submit"
              disabled={loading || !description.trim()}
              className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded transition"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Activity
            </button>
          </form>

          {/* List existing */}
          <div>
            <h4 className="text-xs font-bold text-slate-800 mb-2">Existing Manual Entries ({activities.length})</h4>
            {activities.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No manual activities logged for this day.</p>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {activities.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-start justify-between gap-3 p-2.5 border border-slate-200 rounded-lg bg-white text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 text-[11px]">
                          {a.category}
                        </span>
                        <span className="text-slate-500 font-medium">{a.duration_hours} hrs</span>
                      </div>
                      <p className="text-slate-800">{a.description}</p>
                    </div>
                    <button
                      onClick={() => handleDelete(a.id)}
                      className="text-slate-400 hover:text-rose-600 p-1 transition"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium bg-white border border-slate-300 rounded hover:bg-slate-100 transition"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
