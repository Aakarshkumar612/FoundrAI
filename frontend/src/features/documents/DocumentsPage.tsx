import { useEffect, useState } from "react";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import { Files, Trash2, Calendar, FileType, Database, Plus, Search } from "lucide-react";
import { Link } from "react-router-dom";

interface Upload {
  id: string;
  filename: string;
  file_type: string;
  row_count: number | null;
  created_at: string;
}

export function DocumentsPage() {
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => { loadUploads(); }, []);

  async function loadUploads() {
    try {
      const res = await api.get<{uploads: Upload[]}>("/founders/uploads");
      setUploads(res.uploads);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }

  async function deleteUpload(id: string) {
    if (!window.confirm("Delete this document from RAG index?")) return;
    setDeletingId(id);
    try {
      await api.delete(`/founders/uploads/${id}`);
      setUploads(uploads.filter(u => u.id !== id));
    } catch (err) { alert("Delete failed"); }
    finally { setDeletingId(null); }
  }

  const filtered = uploads.filter(u => u.filename.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-8 animate-fade-up">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#8b5cf6]">
              <Files size={20} />
            </div>
            <h1 className="text-3xl font-bold text-white">Document <span className="gradient-text">Library</span></h1>
          </div>
          <p className="text-[#94a3b8]">Manage your private knowledge base and financial data</p>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
            <input 
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              className="w-full md:w-64 bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white focus:border-[#6366f1] focus:outline-none transition-colors text-sm"
              placeholder="Search files..."
            />
          </div>
          <Link to="/upload" className="flex items-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-sm hover:scale-105 transition-all shadow-lg shadow-[#6366f1]/20 text-white">
            <Plus size={18} /> Upload
          </Link>
        </div>
      </div>

      {loading ? <div className="flex justify-center py-20"><Spinner size={32} /></div> : (
        <div className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-white/5 bg-white/[0.02]">
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Document Name</th>
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Classification</th>
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Insights</th>
                  <th className="px-8 py-5 text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Indexed At</th>
                  <th className="px-8 py-5 text-right text-[10px] font-bold uppercase tracking-[0.2em] text-[#4b5563]">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filtered.length === 0 && (
                  <tr><td colSpan={5} className="px-8 py-20 text-center text-[#94a3b8] text-sm">No documents found. Start by uploading a financial CSV or strategy PDF.</td></tr>
                )}
                {filtered.map(u => (
                  <tr key={u.id} className="hover:bg-white/[0.01] transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-white font-bold group-hover:border-[#6366f1]/40 transition-colors">
                          <FileType size={18} className="text-[#6366f1]" />
                        </div>
                        <span className="text-sm font-bold text-white leading-none">{u.filename}</span>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className={`px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-widest ${u.file_type === 'financial' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'}`}>
                        {u.file_type}
                      </span>
                    </td>
                    <td className="px-8 py-5">
                      <div className="flex items-center gap-2 text-sm text-white font-medium">
                        <Database size={14} className="text-[#94a3b8]" /> {u.row_count || 'RAG Chunks'}
                      </div>
                    </td>
                    <td className="px-8 py-5 text-sm text-[#94a3b8] font-medium">
                      <div className="flex items-center gap-2">
                        <Calendar size={14} /> {new Date(u.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-8 py-5 text-right">
                      <button 
                        onClick={() => deleteUpload(u.id)} disabled={deletingId === u.id}
                        className="p-2 rounded-lg bg-white/5 hover:bg-red-500/10 text-[#4b5563] hover:text-red-400 transition-all"
                      >
                        {deletingId === u.id ? <Spinner size={14} /> : <Trash2 size={16} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
