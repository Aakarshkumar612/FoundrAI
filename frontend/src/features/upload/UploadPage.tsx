import { useRef, useState } from "react";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import type { Upload } from "@/shared/types";
import { 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  ArrowRight, 
  ShieldCheck,
  BrainCircuit,
  Database
} from "lucide-react";
import { Link } from "react-router-dom";

export function UploadPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState<Upload | null>(null);
  const [error, setError] = useState("");

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true); setError(""); setSuccess(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await api.upload<Upload>("/upload/financials", formData);
      setSuccess(res);
      setFile(null);
    } catch (err: any) {
      setError(err.message || "Upload failed. Verify CSV format.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-12 animate-fade-up">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-white/5 border border-white/10 text-[#6366f1] mb-2 shadow-lg">
          <UploadCloud size={32} />
        </div>
        <h1 className="text-4xl font-bold text-white tracking-tight">Expand Your <span className="gradient-text">Intelligence</span></h1>
        <p className="text-[#94a3b8] max-w-lg mx-auto leading-relaxed">
          Upload your financial CSVs or strategy documents to ground your AI advisor in real business context.
        </p>
      </div>

      <div className="grid md:grid-cols-5 gap-8">
        {/* Upload Form */}
        <div className="md:col-span-3">
          <form onSubmit={handleUpload} className="glass-card p-10 space-y-8 relative overflow-hidden">
            <div 
              className={`border-2 border-dashed rounded-2xl p-12 text-center transition-all cursor-pointer group ${
                file ? 'border-[#6366f1] bg-[#6366f1]/5' : 'border-white/10 hover:border-white/20'
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input 
                type="file" ref={fileInputRef} hidden accept=".csv,.xlsx,.pdf,.docx"
                onChange={e => setFile(e.target.files?.[0] || null)}
              />
              <div className="w-16 h-16 rounded-full bg-white/5 mx-auto flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                {file ? <FileText className="text-[#6366f1]" size={32} /> : <UploadCloud className="text-[#4b5563]" size={32} />}
              </div>
              <div className="space-y-2">
                <p className="text-lg font-bold text-white">{file ? file.name : "Select Document"}</p>
                <p className="text-xs text-[#94a3b8] uppercase tracking-[0.2em] font-bold">CSV, PDF, Excel, or Word (Max 50MB)</p>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              <button 
                type="submit" disabled={!file || loading}
                className="w-full py-4 rounded-xl bg-gradient-to-r from-[#6366f1] to-[#a855f7] font-bold text-white hover:scale-[1.02] transition-all flex items-center justify-center gap-2 shadow-lg shadow-[#6366f1]/20 disabled:opacity-50"
              >
                {loading ? <Spinner size={20} /> : <>Commence Indexing <ArrowRight size={18} /></>}
              </button>
              
              {error && (
                <div className="flex items-center gap-3 p-4 rounded-xl bg-red-400/10 border border-red-400/20 text-red-400 text-xs">
                  <AlertCircle size={16} /> {error}
                </div>
              )}

              {success && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-[#3ECF8E]/10 border border-[#3ECF8E]/20 text-[#3ECF8E] text-xs font-bold">
                    <CheckCircle2 size={16} /> Document successfully indexed into RAG.
                  </div>
                  <Link to="/query" className="flex items-center justify-between p-4 rounded-xl glass-card border-[#3ECF8E]/40 group">
                    <span className="text-xs font-bold text-white">Analyze with AI Advisor</span>
                    <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                  </Link>
                </div>
              )}
            </div>
          </form>
        </div>

        {/* Guidance */}
        <div className="md:col-span-2 space-y-6">
          <div className="glass-card p-6 space-y-4">
             <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#3ECF8E]">
                <ShieldCheck size={20} />
             </div>
             <h3 className="text-sm font-bold text-white uppercase tracking-wider">Privacy first</h3>
             <p className="text-xs text-[#94a3b8] leading-relaxed">
               Your documents are processed locally, encoded into vectors, and stored with unique tenant IDs. No other users can access your knowledge base.
             </p>
          </div>

          <div className="glass-card p-6 space-y-4">
             <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#8b5cf6]">
                <BrainCircuit size={20} />
             </div>
             <h3 className="text-sm font-bold text-white uppercase tracking-wider">Metric Extraction</h3>
             <p className="text-xs text-[#94a3b8] leading-relaxed">
               For financial CSVs, our engine automatically detects columns like Revenue and CAC to feed the Monte Carlo simulation engine.
             </p>
          </div>

          <div className="glass-card p-6 space-y-4">
             <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#06b6d4]">
                <Database size={20} />
             </div>
             <h3 className="text-sm font-bold text-white uppercase tracking-wider">ColBERT Pipeline</h3>
             <p className="text-xs text-[#94a3b8] leading-relaxed">
               Using late-interaction retrieval ensures that even complex semantic nuances in your strategy are understood by our agent swarm.
             </p>
          </div>
        </div>
      </div>
    </div>
  );
}
