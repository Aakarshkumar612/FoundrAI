import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/shared/api/client";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

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

  useEffect(() => {
    loadUploads();
  }, []);

  async function loadUploads() {
    try {
      const res = await api.get<{uploads: Upload[]}>("/founders/uploads");
      setUploads(res.uploads);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function deleteUpload(id: string) {
    if (!window.confirm("Are you sure you want to delete this document? This will also remove it from the AI's knowledge base.")) return;
    setDeletingId(id);
    try {
      await api.delete(`/founders/uploads/${id}`);
      setUploads(uploads.filter(u => u.id !== id));
    } catch (err) {
      console.error(err);
      alert("Failed to delete document.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <motion.div className="p-8 max-w-4xl" initial="hidden" animate="visible" variants={{ visible:{transition:{staggerChildren:0.08}} }}>
      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Document Management</h1>
        <p className="mt-1 text-sm text-[#6B6560]">Manage the files you've uploaded to the AI's knowledge base.</p>
      </motion.div>

      {loading ? <Spinner size={24} /> : (
        <motion.div variants={fadeUp} className="rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] overflow-hidden">
          <table className="w-full text-left text-sm text-[#A89F95]">
            <thead className="bg-[#161412] text-xs uppercase tracking-wider text-[#6B6560]">
              <tr>
                <th className="px-6 py-4 font-medium">Filename</th>
                <th className="px-6 py-4 font-medium">Type</th>
                <th className="px-6 py-4 font-medium">Rows</th>
                <th className="px-6 py-4 font-medium">Uploaded</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e1c1a]">
              {uploads.length === 0 && (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-[#6B6560]">No documents uploaded yet.</td></tr>
              )}
              {uploads.map(u => (
                <tr key={u.id} className="hover:bg-[#161412]/50 transition-colors">
                  <td className="px-6 py-4 font-medium text-[#F5F0EB]">{u.filename}</td>
                  <td className="px-6 py-4 uppercase text-[10px]">{u.file_type}</td>
                  <td className="px-6 py-4">{u.row_count ?? "N/A"}</td>
                  <td className="px-6 py-4">{new Date(u.created_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 text-right">
                    <button onClick={() => deleteUpload(u.id)} disabled={deletingId === u.id} className="text-xs text-red-400 hover:text-red-300 disabled:opacity-50 transition-colors">
                      {deletingId === u.id ? "Deleting..." : "Delete"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}
    </motion.div>
  );
}
