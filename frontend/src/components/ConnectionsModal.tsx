import React, { useState } from 'react';
import type { AdoCredential } from '../types';
import { api } from '../api/client';
import { X, ShieldCheck, CheckCircle2, AlertCircle, RefreshCw, Globe } from 'lucide-react';

interface ConnectionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  credentials: AdoCredential[];
  onCredentialsUpdated: () => void;
}

export const ConnectionsModal: React.FC<ConnectionsModalProps> = ({
  isOpen,
  onClose,
  credentials,
  onCredentialsUpdated,
}) => {
  const clientCred = credentials.find((c) => c.provider === 'client');
  const rysunCred = credentials.find((c) => c.provider === 'rysun' || c.provider === 'mycompany');

  // Client form state
  const [clientOrg, setClientOrg] = useState(clientCred?.org_url || 'https://dev.azure.com/VisualComfortCo');
  const [clientPat, setClientPat] = useState('');
  const [clientLoading, setClientLoading] = useState(false);
  const [clientError, setClientError] = useState<string | null>(null);
  const [clientSuccess, setClientSuccess] = useState<string | null>(null);

  // Rysun form state
  const [rysunOrg, setRysunOrg] = useState(rysunCred?.org_url || 'https://dev.azure.com/Rysun');
  const [rysunPat, setRysunPat] = useState('');
  const [rysunLoading, setRysunLoading] = useState(false);
  const [rysunError, setRysunError] = useState<string | null>(null);
  const [rysunSuccess, setRysunSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSaveClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientLoading(true);
    setClientError(null);
    setClientSuccess(null);
    try {
      await api.saveCredential({
        provider: 'client',
        org_url: clientOrg,
        pat: clientPat,
      });
      setClientSuccess('Client Azure DevOps verified and securely connected!');
      setClientPat('');
      onCredentialsUpdated();
    } catch (err: any) {
      setClientError(err.message || 'Validation failed');
    } finally {
      setClientLoading(false);
    }
  };

  const handleSaveRysun = async (e: React.FormEvent) => {
    e.preventDefault();
    setRysunLoading(true);
    setRysunError(null);
    setRysunSuccess(null);
    try {
      await api.saveCredential({
        provider: 'rysun',
        org_url: rysunOrg,
        pat: rysunPat,
      });
      setRysunSuccess('Rysun Azure DevOps verified and securely connected!');
      setRysunPat('');
      onCredentialsUpdated();
    } catch (err: any) {
      setRysunError(err.message || 'Validation failed');
    } finally {
      setRysunLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">Azure DevOps Connections</h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-md hover:bg-slate-200 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="bg-blue-50/60 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
            <span className="font-bold">Encrypted at rest:</span> Your PATs are encrypted using AES-256-GCM before storage. They are never transmitted to browsers or logged.
          </div>

          {/* Card 1: Client Organization */}
          <div className="border border-slate-200 rounded-lg p-5 bg-white shadow-2xs">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">1. Client Azure DevOps Organization</h3>
                <p className="text-xs text-slate-500">Source of Git commits, PRs, and reviews.</p>
              </div>
              {clientCred?.is_valid ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full">
                  <AlertCircle className="w-3.5 h-3.5" /> Not Connected
                </span>
              )}
            </div>

            {clientCred?.resolved_identity_name && (
              <div className="mb-4 bg-slate-50 rounded-md p-2.5 text-xs text-slate-700 flex items-center justify-between border border-slate-100">
                <div>
                  <span className="font-semibold text-slate-900">Verified User:</span> {clientCred.resolved_identity_name} ({clientCred.resolved_identity_email || 'No email'})
                </div>
                <span className="text-[11px] text-slate-400">ID: {clientCred.resolved_identity_id?.slice(0, 8)}...</span>
              </div>
            )}

            <form onSubmit={handleSaveClient} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Organization URL</label>
                <div className="relative">
                  <Globe className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="url"
                    value={clientOrg}
                    onChange={(e) => setClientOrg(e.target.value)}
                    required
                    className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    placeholder="https://dev.azure.com/VisualComfortCo"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Client PAT (Scope: Code Read, Work Items Read)
                </label>
                <input
                  type="password"
                  value={clientPat}
                  onChange={(e) => setClientPat(e.target.value)}
                  placeholder={clientCred ? '••••••••••••••••••••••••••••••••' : 'Enter new Client PAT'}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>

              {clientError && <div className="text-xs text-rose-600 bg-rose-50 p-2 rounded-md">{clientError}</div>}
              {clientSuccess && <div className="text-xs text-emerald-700 bg-emerald-50 p-2 rounded-md">{clientSuccess}</div>}

              <button
                type="submit"
                disabled={clientLoading || !clientPat}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition"
              >
                {clientLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Validate & Connect Client
              </button>
            </form>
          </div>

          {/* Card 2: Rysun Organization */}
          <div className="border border-slate-200 rounded-lg p-5 bg-white shadow-2xs">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">2. Rysun Azure DevOps Organization</h3>
                <p className="text-xs text-slate-500">Destination for Resource Timesheet work items.</p>
              </div>
              {rysunCred?.is_valid ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full">
                  <AlertCircle className="w-3.5 h-3.5" /> Not Connected
                </span>
              )}
            </div>

            {rysunCred?.resolved_identity_name && (
              <div className="mb-4 bg-slate-50 rounded-md p-2.5 text-xs text-slate-700 flex items-center justify-between border border-slate-100">
                <div>
                  <span className="font-semibold text-slate-900">Verified User:</span> {rysunCred.resolved_identity_name} ({rysunCred.resolved_identity_email || 'No email'})
                </div>
                <span className="text-[11px] text-slate-400">ID: {rysunCred.resolved_identity_id?.slice(0, 8)}...</span>
              </div>
            )}

            <form onSubmit={handleSaveRysun} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Organization URL</label>
                <div className="relative">
                  <Globe className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="url"
                    value={rysunOrg}
                    onChange={(e) => setRysunOrg(e.target.value)}
                    required
                    className="w-full text-xs pl-9 pr-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                    placeholder="https://dev.azure.com/Rysun"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Rysun PAT (Scope: Work Items Read & Write)
                </label>
                <input
                  type="password"
                  value={rysunPat}
                  onChange={(e) => setRysunPat(e.target.value)}
                  placeholder={rysunCred ? '••••••••••••••••••••••••••••••••' : 'Enter new Rysun PAT'}
                  className="w-full text-xs px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                />
              </div>

              {rysunError && <div className="text-xs text-rose-600 bg-rose-50 p-2 rounded-md">{rysunError}</div>}
              {rysunSuccess && <div className="text-xs text-emerald-700 bg-emerald-50 p-2 rounded-md">{rysunSuccess}</div>}

              <button
                type="submit"
                disabled={rysunLoading || !rysunPat}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-md transition"
              >
                {rysunLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                Validate & Connect Rysun
              </button>
            </form>
          </div>
        </div>

        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold bg-white border border-slate-300 text-slate-700 hover:bg-slate-100 rounded-md transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
