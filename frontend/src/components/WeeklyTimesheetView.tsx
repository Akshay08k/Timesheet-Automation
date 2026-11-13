import React, { useState, useEffect } from 'react';
import type { TimesheetEntry, WeeklyReview, ActivityItem, ManualActivity } from '../types';
import { api } from '../api/client';
import { ActivityDrawer } from './ActivityDrawer';
import { ManualActivityModal } from './ManualActivityModal';
import {
  Sparkles,
  RefreshCw,
  Send,
  GitCommit,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
} from 'lucide-react';

interface WeeklyTimesheetViewProps {
  selectedMonday: string;
}

const PROJECTS = [
  {
    name: 'VCC - VCQMS Enhancements and InspectionDB',
    area: 'Rysun Project Management\\VC - VCQMS',
  },
  {
    name: 'VCC - RMA Modernization',
    area: 'Rysun Project Management\\VCC - RMA Modernization',
  },
];

export const WeeklyTimesheetView: React.FC<WeeklyTimesheetViewProps> = ({ selectedMonday }) => {
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [generatingAll, setGeneratingAll] = useState(false);
  const [submittingAll, setSubmittingAll] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Active drawer states
  const [activeDateForActivities, setActiveDateForActivities] = useState<string | null>(null);
  const [dayActivities, setDayActivities] = useState<ActivityItem[]>([]);
  const [activeDateForManual, setActiveDateForManual] = useState<string | null>(null);
  const [manualActivities, setManualActivities] = useState<ManualActivity[]>([]);

  // Regenerate prompt popover state
  const [activeRegenDate, setActiveRegenDate] = useState<string | null>(null);
  const [customPrompt, setCustomPrompt] = useState('');
  const [regenLoading, setRegenLoading] = useState(false);

  // Load weekly review
  const loadReview = async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const data = await api.getWeeklyReview(selectedMonday);
      setReview(data);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to load weekly timesheets' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReview();
  }, [selectedMonday]);

  // Synchronize client activity from Azure DevOps
  const handleSyncClientActivity = async () => {
    if (!review) return;
    setSyncing(true);
    setStatusMessage({ type: 'info', text: 'Syncing commits and pull requests from Client Azure DevOps...' });
    try {
      const res = await api.syncActivities(review.week_start, review.week_end);
      setStatusMessage({
        type: 'success',
        text: `Sync complete: Found ${res.total_found} events (${res.commits} commits, ${res.pull_requests} PRs). ${res.new_added} new items saved.`,
      });
      loadReview();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Client sync failed' });
    } finally {
      setSyncing(false);
    }
  };

  // Generate Gemini summaries for all 5 days in a single API call
  const handleGenerateAllSummaries = async () => {
    if (!review) return;
    setGeneratingAll(true);
    setStatusMessage({ type: 'info', text: 'Google Gemini API is analyzing commit history and generating timesheet summaries...' });
    try {
      const updatedReview = await api.generateWeeklySummary(review.week_start);
      setReview(updatedReview);
      setStatusMessage({
        type: 'success',
        text: 'All 5 daily summaries generated successfully via Google Gemini API!',
      });
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'AI generation failed' });
    } finally {
      setGeneratingAll(false);
    }
  };

  // Single Day Gemini summary generation / regeneration
  const handleGenerateSingle = async (dateStr: string, customInstruction?: string) => {
    setRegenLoading(true);
    try {
      await api.generateDailySummary(dateStr, customInstruction);
      setActiveRegenDate(null);
      setCustomPrompt('');
      loadReview();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Gemini generation failed' });
    } finally {
      setRegenLoading(false);
    }
  };

  // Ref for debounced API updates per draftId
  const debounceTimers = React.useRef<{ [key: string]: ReturnType<typeof setTimeout> }>({});

  useEffect(() => {
    return () => {
      Object.values(debounceTimers.current).forEach(clearTimeout);
    };
  }, []);

  // Update draft field with immediate optimistic UI update + debounced network persist
  const handleUpdateField = (
    draftId: number,
    patch: Partial<TimesheetEntry>,
    debounceMs: number = 0
  ) => {
    // 1. Immediately update UI state so text displays synchronously with zero lag
    setReview((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        entries: prev.entries.map((e) => (e.id === draftId ? { ...e, ...patch } : e)),
      };
    });

    // 2. Debounce server persistence
    const timerKey = `${draftId}_${Object.keys(patch)[0]}`;
    if (debounceTimers.current[timerKey]) {
      clearTimeout(debounceTimers.current[timerKey]);
    }

    const saveToServer = async () => {
      try {
        await api.updateTimesheetDraft(draftId, patch);
      } catch (err: any) {
        setStatusMessage({ type: 'error', text: err.message || 'Failed to update entry' });
      }
    };

    if (debounceMs > 0) {
      debounceTimers.current[timerKey] = setTimeout(saveToServer, debounceMs);
    } else {
      saveToServer();
    }
  };

  // Open Activity Drawer
  const handleOpenActivities = async (dateStr: string) => {
    setActiveDateForActivities(dateStr);
    try {
      const items = await api.getActivities(dateStr);
      setDayActivities(items);
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleExclude = async (actId: number) => {
    try {
      const updated = await api.toggleExcludeActivity(actId);
      setDayActivities((prev) => prev.map((a) => (a.id === actId ? updated : a)));
    } catch (err) {
      console.error(err);
    }
  };

  // Open Manual Activity Modal
  const handleOpenManual = async (dateStr: string) => {
    setActiveDateForManual(dateStr);
    try {
      const items = await api.getManualActivities(dateStr);
      setManualActivities(items);
    } catch (err) {
      console.error(err);
    }
  };

  // Submit Single Day to Rysun
  const handleSubmitSingleDay = async (draftId: number, force = false) => {
    const entry = review?.entries.find((e) => e.id === draftId);
    if (entry && (!entry.task_summary || !entry.task_summary.trim())) {
      setStatusMessage({
        type: 'error',
        text: `Cannot submit ${entry.date_str} (${entry.day_of_week}): Task Summary is empty. Azure DevOps requires a Task Summary. Please write a description or generate one with Gemini AI first.`,
      });
      return;
    }

    if (entry && entry.submission_status === 'submitted' && !force) {
      const confirmUpdate = window.confirm(
        `Resource Timesheet #${entry.ry_workitem_id || ''} for ${entry.date_str} is already submitted. Do you want to update it in Rysun Azure DevOps with this point-wise README format summary?`
      );
      if (!confirmUpdate) return;
      force = true;
    }

    try {
      const res = await api.submitSingleDay(draftId, force);
      if (res.status === 'already_submitted') {
        const confirmUpdate = window.confirm(
          `A Resource Timesheet work item (#${res.workitem_id}) already exists for this date in Rysun. Do you want to update it with your current approved summary?`
        );
        if (confirmUpdate) {
          handleSubmitSingleDay(draftId, true);
        }
      } else if (res.status === 'created' || res.status === 'updated') {
        setStatusMessage({ type: 'success', text: res.message });
        loadReview();
      } else {
        setStatusMessage({ type: 'error', text: res.message });
        loadReview();
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Submission failed' });
    }
  };

  // Submit Approved Entries for the Week
  const handleSubmitApprovedWeek = async () => {
    if (!review) return;
    const approvedEntries = review.entries.filter((e) => e.is_user_approved);
    if (approvedEntries.length === 0) {
      alert('Please check "Approve entry" on the days you wish to submit or update.');
      return;
    }

    const emptySummaryEntry = approvedEntries.find((e) => !e.task_summary || !e.task_summary.trim());
    if (emptySummaryEntry) {
      setStatusMessage({
        type: 'error',
        text: `Cannot submit approved week: ${emptySummaryEntry.date_str} (${emptySummaryEntry.day_of_week}) has an empty Task Summary. Azure DevOps requires a Task Summary on every timesheet. Please fill it in or generate it before submitting.`,
      });
      return;
    }

    const hasAlreadySubmitted = approvedEntries.some((e) => e.submission_status === 'submitted');
    const confirmMessage = hasAlreadySubmitted
      ? `Submit / update ${approvedEntries.length} approved daily timesheets to Rysun Azure DevOps (including updating submitted entries with your current point-wise README summaries)?`
      : `Submit ${approvedEntries.length} approved daily timesheets to Rysun Azure DevOps?`;

    const confirmSubmit = window.confirm(confirmMessage);
    if (!confirmSubmit) return;

    setSubmittingAll(true);
    try {
      const results = await api.submitWeek(
        approvedEntries.map((e) => e.id),
        hasAlreadySubmitted
      );
      const createdCount = results.filter((r) => r.status === 'created' || r.status === 'updated').length;
      setStatusMessage({
        type: 'success',
        text: `Successfully processed ${createdCount}/${results.length} timesheets in Rysun Azure DevOps!`,
      });
      loadReview();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Batch submission failed' });
    } finally {
      setSubmittingAll(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Controls & Weekly Action Bar */}
      <div className="bg-white rounded-xl shadow-xs border border-slate-200 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Weekly Timesheet Review</h1>
            <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 text-slate-700 rounded-md border border-slate-200">
              Mon--Fri ({review?.week_start} to {review?.week_end})
            </span>
          </div>
          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500 font-medium">
            <span>Total Hours: <strong className="text-slate-900">{review?.total_hours || 0} hrs</strong></span>
            <span>•</span>
            <span>Approved: <strong className="text-blue-600">{review?.approved_count || 0} / 5</strong></span>
            <span>•</span>
            <span>Submitted: <strong className="text-emerald-700">{review?.submitted_count || 0} / 5</strong></span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleSyncClientActivity}
            disabled={syncing}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 rounded-lg shadow-2xs transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-600 ${syncing ? 'animate-spin' : ''}`} />
            Sync Client Activity
          </button>

          <button
            onClick={handleGenerateAllSummaries}
            disabled={generatingAll}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg shadow-xs transition"
          >
            <Sparkles className={`w-3.5 h-3.5 ${generatingAll ? 'animate-spin' : ''}`} />
            Generate Summaries (Gemini API)
          </button>

          <button
            onClick={handleSubmitApprovedWeek}
            disabled={submittingAll}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 rounded-lg shadow-xs transition"
          >
            <Send className="w-3.5 h-3.5" />
            Submit Approved to Rysun
          </button>
        </div>
      </div>

      {/* Status Banners */}
      {statusMessage && (
        <div
          className={`px-4 py-3 rounded-lg text-xs font-medium flex items-center justify-between border ${
            statusMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : statusMessage.type === 'error'
              ? 'bg-rose-50 text-rose-800 border-rose-200'
              : 'bg-blue-50 text-blue-800 border-blue-200'
          }`}
        >
          <span>{statusMessage.text}</span>
          <button onClick={() => setStatusMessage(null)} className="font-bold underline ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* 5 Daily Timesheet Cards */}
      {loading && !review ? (
        <div className="p-12 text-center text-slate-400">Loading daily timesheets...</div>
      ) : (
        <div className="space-y-4">
          {review?.entries.map((entry) => {
            const isSubmitted = entry.submission_status === 'submitted';
            return (
              <div
                key={entry.id}
                className={`bg-white rounded-xl border transition-all ${
                  isSubmitted
                    ? 'border-emerald-200 shadow-2xs'
                    : entry.is_user_approved
                    ? 'border-blue-400 shadow-xs'
                    : 'border-slate-200 shadow-2xs'
                }`}
              >
                {/* Day Header */}
                <div className="px-5 py-3.5 bg-slate-50/70 border-b border-slate-200 rounded-t-xl flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="font-bold text-sm text-slate-900">{entry.day_of_week}</div>
                    <span className="text-xs font-medium text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                      {entry.date_str}
                    </span>

                    {/* Submission status pill */}
                    {isSubmitted ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 bg-emerald-100/70 border border-emerald-300 px-2 py-0.5 rounded-full">
                        <CheckCircle2 className="w-3 h-3" /> Submitted in Rysun {entry.ry_workitem_id && `(#${entry.ry_workitem_id})`}
                      </span>
                    ) : entry.existing_rysun_item ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-800 bg-amber-50 border border-amber-300 px-2 py-0.5 rounded-full">
                        <AlertCircle className="w-3.5 h-3.5" /> Exists in Rysun (#{entry.existing_rysun_item.id})
                      </span>
                    ) : (
                      <span className="text-[11px] font-semibold text-slate-500 bg-slate-200/60 px-2 py-0.5 rounded-full">
                        Draft
                      </span>
                    )}
                  </div>

                  {/* Top Right: Special day flags + Hours */}
                  <div className="flex items-center gap-4 text-xs">
                    {/* Flags */}
                    <div className="flex items-center gap-3">
                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={entry.ph}
                          onChange={(e) => handleUpdateField(entry.id, { ph: e.target.checked })}
                          className="rounded text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                        />
                        <span className="text-slate-600 font-medium">PH</span>
                      </label>

                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={entry.leave}
                          onChange={(e) => handleUpdateField(entry.id, { leave: e.target.checked })}
                          className="rounded text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                        />
                        <span className="text-slate-600 font-medium">Leave</span>
                      </label>

                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={entry.half_day}
                          onChange={(e) => handleUpdateField(entry.id, { half_day: e.target.checked })}
                          className="rounded text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                        />
                        <span className="text-slate-600 font-medium">Half Day</span>
                      </label>

                      <label className="flex items-center gap-1 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={entry.wfh}
                          onChange={(e) => handleUpdateField(entry.id, { wfh: e.target.checked })}
                          className="rounded text-blue-600 focus:ring-blue-500 w-3.5 h-3.5"
                        />
                        <span className="text-slate-600 font-medium">WFH</span>
                      </label>
                    </div>

                    {/* Hours Input */}
                    <div className="flex items-center gap-1.5 pl-3 border-l border-slate-300">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max="24"
                        value={entry.hours}
                        onChange={(e) => handleUpdateField(entry.id, { hours: parseFloat(e.target.value) || 0 }, 400)}
                        className="w-14 text-xs font-bold text-center px-1 py-1 border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                      />
                      <span className="text-slate-500 font-medium">hrs</span>
                    </div>
                  </div>
                </div>

                {/* Day Body */}
                <div className="p-5 space-y-4">
                  {/* Project & Area mapping */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div>
                      <label className="block text-slate-500 font-semibold mb-1">Project</label>
                      <select
                        value={entry.project_name}
                        onChange={(e) => {
                          const chosen = PROJECTS.find((p) => p.name === e.target.value);
                          handleUpdateField(entry.id, {
                            project_name: e.target.value,
                            area_path: chosen ? chosen.area : entry.area_path,
                          });
                        }}
                        className="w-full text-xs px-2.5 py-1.5 bg-white border border-slate-300 rounded focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                      >
                        {Array.from(new Set([...PROJECTS.map((p) => p.name), ...(entry.project_name ? [entry.project_name] : [])])).map((pName) => (
                          <option key={pName} value={pName}>
                            {pName}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-slate-500 font-semibold mb-1">Rysun Area Path</label>
                      <input
                        type="text"
                        value={entry.area_path}
                        readOnly
                        className="w-full text-xs px-2.5 py-1.5 bg-slate-100 border border-slate-200 text-slate-600 rounded select-all font-mono"
                      />
                    </div>
                  </div>

                  {/* Task Summary Area */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-bold text-slate-800">Task Summary</label>
                        <span className="text-[11px] text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded font-semibold flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-indigo-600" />
                          Gemini 2.5 Flash
                        </span>
                      </div>

                      {/* Quick Evidence & Manual Buttons */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleOpenActivities(entry.date_str)}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 hover:text-blue-600 bg-slate-100 hover:bg-blue-50 px-2.5 py-1 rounded transition"
                        >
                          <GitCommit className="w-3.5 h-3.5 text-blue-600" />
                          Activity Explorer
                        </button>

                        <button
                          onClick={() => handleOpenManual(entry.date_str)}
                          className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-600 hover:text-emerald-700 bg-slate-100 hover:bg-emerald-50 px-2.5 py-1 rounded transition"
                        >
                          <Plus className="w-3.5 h-3.5 text-emerald-600" />
                          Add Non-Code Work
                        </button>
                      </div>
                    </div>

                    <textarea
                      rows={6}
                      value={entry.task_summary ?? ''}
                      onChange={(e) => handleUpdateField(entry.id, { task_summary: e.target.value }, 800)}
                      placeholder="Daily timesheet summary for Rysun Resource Timesheet (Markdown / README format with - bullet points)..."
                      className="w-full text-xs px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:outline-hidden leading-relaxed font-sans"
                    />

                    {/* Detailed Bullets (if generated) */}
                    {entry.detailed_bullets && entry.detailed_bullets.length > 0 && (
                      <div className="mt-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                        <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-1">
                          Key Work Bullets (Derived from Commits)
                        </span>
                        <ul className="list-disc list-inside space-y-0.5 text-xs text-slate-700">
                          {entry.detailed_bullets.map((b, i) => (
                            <li key={i}>{b}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Regenerate with instructions popover */}
                  {activeRegenDate === entry.date_str && (
                    <div className="bg-indigo-50/70 border border-indigo-200 rounded-lg p-3 space-y-2 text-xs">
                      <div className="font-semibold text-indigo-950 flex items-center gap-1">
                        <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                        Custom Gemini Prompt Guidance (Optional)
                      </div>
                      <input
                        type="text"
                        value={customPrompt}
                        onChange={(e) => setCustomPrompt(e.target.value)}
                        placeholder="e.g. Focus on VCQMS backend bugfixes and include review remarks..."
                        className="w-full text-xs px-2.5 py-1.5 bg-white border border-indigo-300 rounded focus:ring-2 focus:ring-indigo-500 focus:outline-hidden"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setActiveRegenDate(null)}
                          className="px-2.5 py-1 text-slate-600 hover:bg-slate-200 rounded"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleGenerateSingle(entry.date_str, customPrompt)}
                          disabled={regenLoading}
                          className="px-3 py-1 font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded shadow-2xs"
                        >
                          {regenLoading ? 'Regenerating...' : 'Regenerate Now'}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Footer actions: Approve & Submit Day */}
                  <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-800">
                      <input
                        type="checkbox"
                        checked={entry.is_user_approved}
                        onChange={(e) => handleUpdateField(entry.id, { is_user_approved: e.target.checked })}
                        className="rounded text-blue-600 focus:ring-blue-500 w-4 h-4"
                      />
                      <span>Confirm & Approve Day</span>
                    </label>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setActiveRegenDate(activeRegenDate === entry.date_str ? null : entry.date_str)}
                        className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded hover:bg-indigo-50 transition font-medium"
                      >
                        <Sparkles className="w-3 h-3" />
                        Regenerate
                      </button>

                      <button
                        onClick={() => handleSubmitSingleDay(entry.id)}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white rounded-md transition shadow-2xs ${
                          isSubmitted
                            ? 'bg-amber-600 hover:bg-amber-700'
                            : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                      >
                        <Send className="w-3 h-3" />
                        {isSubmitted ? 'Update in Rysun' : 'Submit Day to Rysun'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Activity Drawer */}
      {activeDateForActivities && (
        <ActivityDrawer
          isOpen={Boolean(activeDateForActivities)}
          onClose={() => setActiveDateForActivities(null)}
          dateStr={activeDateForActivities}
          activities={dayActivities}
          onToggleExclude={handleToggleExclude}
        />
      )}

      {/* Manual Activities Modal */}
      {activeDateForManual && (
        <ManualActivityModal
          isOpen={Boolean(activeDateForManual)}
          onClose={() => setActiveDateForManual(null)}
          dateStr={activeDateForManual}
          activities={manualActivities}
          onActivitiesChanged={async () => {
            if (activeDateForManual) {
              const items = await api.getManualActivities(activeDateForManual);
              setManualActivities(items);
            }
          }}
        />
      )}
    </div>
  );
};
