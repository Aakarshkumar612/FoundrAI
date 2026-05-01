import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";
import type { Upload } from "@/shared/types";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

export function UploadPage() {
  const inputRef                = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult]     = useState<Upload | null>(null);
  const [error, setError]       = useState("");

  async function handleFile(file: File) {
    setResult(null); setError(""); setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      setResult(await api.upload<Upload>("/upload/financials", form));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <motion.div className="p-8 max-w-2xl" initial="hidden" animate="visible"
      variants={{ visible:{transition:{staggerChildren:0.08}} }}>

      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Upload Document</h1>
        <p className="mt-1 text-sm text-[#6B6560]">
          Extracted and indexed into RAG — seeds AI responses and Monte Carlo simulations.
        </p>
      </motion.div>

      {/* Drop zone */}
      <motion.div variants={fadeUp}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); const f=e.dataTransfer.files[0]; if(f) handleFile(f); }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-2xl border-2 border-dashed px-8 py-16 text-center transition-all ${
          dragging ? "border-[#D97757] bg-[#D97757]/5" : "border-[#1e1c1a] hover:border-[#2a2520] hover:bg-[#0d0c0b]"
        }`}>
        <input ref={inputRef} type="file" hidden
          accept=".csv,.xlsx,.xls,.pdf,.docx,.jpg,.jpeg,.png,.webp,.txt"
          onChange={e => { const f=e.target.files?.[0]; if(f) handleFile(f); }} />
        <div className="text-4xl mb-3 text-[#6B6560]">⬆</div>
        <p className="text-sm font-medium text-[#A89F95]">Drop your file here or click to browse</p>
        <p className="mt-1 text-xs text-[#6B6560]">CSV, Excel, PDF, Word, JPG/PNG, TXT — up to 50 MB</p>
      </motion.div>

      {uploading && (
        <motion.div variants={fadeUp} initial="hidden" animate="visible"
          className="mt-5 flex items-center gap-3 rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] px-5 py-3">
          <Spinner size={16} />
          <p className="text-sm text-[#A89F95]">Extracting text, indexing into RAG, analysing metrics…</p>
        </motion.div>
      )}

      {result && (
        <motion.div variants={fadeUp} initial="hidden" animate="visible"
          className="mt-5 rounded-2xl border border-[#4CAF84]/30 bg-[#4CAF84]/5 p-5">
          <p className="text-sm font-semibold text-[#4CAF84] mb-3">Upload complete</p>
          <div className="space-y-1.5 text-xs text-[#A89F95]">
            <p><span className="text-[#6B6560]">File:</span> {result.filename}</p>
            <p><span className="text-[#6B6560]">Type:</span> {result.file_type}</p>
            {result.row_count != null && <p><span className="text-[#6B6560]">Rows:</span> {result.row_count}</p>}
            {result.columns && result.columns.length > 0 && (
              <p><span className="text-[#6B6560]">Columns:</span> {result.columns.join(", ")}</p>
            )}
            <p>
              <span className="text-[#6B6560]">Simulation seed:</span>{" "}
              {result.is_financial
                ? <span className="text-[#4CAF84]">Financial columns detected — direct seed</span>
                : <span className="text-[#D97757]">AI-extracted metrics seed</span>}
            </p>
            <p className="mt-2 font-mono text-[#6B6560] text-[10px] break-all">ID: {result.upload_id}</p>
          </div>
        </motion.div>
      )}

      {error && (
        <motion.div variants={fadeUp} initial="hidden" animate="visible"
          className="mt-5 rounded-2xl border border-red-900/40 bg-red-950/20 px-5 py-3">
          <p className="text-sm text-red-400">{error}</p>
        </motion.div>
      )}
    </motion.div>
  );
}
