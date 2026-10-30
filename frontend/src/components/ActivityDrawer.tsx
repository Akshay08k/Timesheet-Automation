import React from 'react';
import type { ActivityItem } from '../types';
import { X, GitCommit, GitPullRequest, EyeOff, Eye, ExternalLink } from 'lucide-react';

interface ActivityDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  dateStr: string;
  activities: ActivityItem[];
  onToggleExclude: (activityId: number) => void;
}

export const ActivityDrawer: React.FC<ActivityDrawerProps> = ({
  isOpen,
  onClose,
  dateStr,
  activities,
  onToggleExclude,
}) => {
  if (!isOpen) return null;

  const commits = activities.filter((a) => a.source_type === 'commit');
  const prs = activities.filter((a) => a.source_type === 'pull_request');

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs">
      <div className="bg-white w-full max-w-lg h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div>
            <h3 className="font-bold text-sm text-slate-900">Activity Explorer</h3>
            <p className="text-xs text-slate-500">Evidence for {dateStr} ({activities.length} total events)</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 flex-1 overflow-y-auto space-y-6">
          {/* Commits Section */}
          <div>
            <div className="flex items-center gap-1.5 mb-2.5">
              <GitCommit className="w-4 h-4 text-blue-600" />
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Git Commits ({commits.length})
              </h4>
            </div>

            {commits.length === 0 ? (
              <p className="text-xs text-slate-400 italic bg-slate-50 p-3 rounded-md">No commits recorded for this date.</p>
            ) : (
              <div className="space-y-2">
                {commits.map((c) => (
                  <div
                    key={c.id}
                    className={`border rounded-lg p-3 transition ${
                      c.is_excluded
                        ? 'bg-slate-50/70 border-slate-200 opacity-60'
                        : 'bg-white border-slate-200 hover:border-blue-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <code className="text-[11px] font-mono px-1.5 py-0.5 bg-slate-100 rounded text-slate-700 font-semibold">
                            {c.external_id.slice(0, 8)}
                          </code>
                          <span className="text-[11px] font-medium text-slate-500 bg-slate-50 px-2 py-0.5 rounded border border-slate-200">
                            {c.repository}
                          </span>
                        </div>
                        <p className="text-xs text-slate-900 font-medium leading-relaxed">{c.title}</p>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {c.url && (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1 text-slate-400 hover:text-blue-600 rounded transition"
                            title="Open in Azure DevOps"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <button
                          onClick={() => onToggleExclude(c.id)}
                          className={`p-1 rounded text-xs transition ${
                            c.is_excluded
                              ? 'text-amber-600 hover:bg-amber-50'
                              : 'text-slate-400 hover:text-slate-700 hover:bg-slate-100'
                          }`}
                          title={c.is_excluded ? 'Include in AI Summary' : 'Exclude from AI Summary'}
                        >
                          {c.is_excluded ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pull Requests Section */}
          <div>
            <div className="flex items-center gap-1.5 mb-2.5">
              <GitPullRequest className="w-4 h-4 text-purple-600" />
              <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Pull Requests ({prs.length})
              </h4>
            </div>

            {prs.length === 0 ? (
              <p className="text-xs text-slate-400 italic bg-slate-50 p-3 rounded-md">No pull requests recorded for this date.</p>
            ) : (
              <div className="space-y-2">
                {prs.map((p) => (
                  <div key={p.id} className="border border-slate-200 rounded-lg p-3 bg-white">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[11px] font-mono font-bold text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200">
                            PR #{p.external_id}
                          </span>
                          <span className="text-[11px] text-slate-500">{p.repository}</span>
                        </div>
                        <p className="text-xs text-slate-900 font-medium">{p.title}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs text-slate-500">
          <span>Excluded items are skipped when running Gemini AI summarization.</span>
          <button
            onClick={onClose}
            className="px-3 py-1.5 bg-white border border-slate-300 font-medium rounded hover:bg-slate-100 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
