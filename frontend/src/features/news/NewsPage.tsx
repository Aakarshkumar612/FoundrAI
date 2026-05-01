import { useEffect, useState } from "react";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";
import { Newspaper, ExternalLink, Calendar, Globe, Search, Sparkles } from "lucide-react";

interface Article {
  id: string;
  title: string;
  source: string;
  published_date: string;
  url: string;
  topics: string[];
}

export function NewsPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const { data } = await supabase.from("news_articles")
          .select("id, title, source, published_date, url, topics")
          .order("published_date", { ascending: false })
          .limit(50);
        setArticles(data || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered = articles.filter(a => 
    a.title.toLowerCase().includes(search.toLowerCase()) || 
    a.source.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-fade-up">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-[#06b6d4]">
              <Newspaper size={20} />
            </div>
            <h1 className="text-3xl font-bold text-white">Market <span className="gradient-text">Intelligence</span></h1>
          </div>
          <p className="text-[#94a3b8]">Live global startup news ingested and embedded for RAG context</p>
        </div>

        <div className="relative w-full md:w-80">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[#4b5563]" size={18} />
          <input 
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-white focus:border-[#6366f1] focus:outline-none transition-colors text-sm"
            placeholder="Search intelligence..."
          />
        </div>
      </div>

      {loading ? <div className="flex justify-center py-20"><Spinner size={32} /></div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.length === 0 && (
            <div className="col-span-full py-20 text-center glass-card border-dashed">
              <Search className="mx-auto mb-4 text-[#4b5563]" size={48} />
              <p className="text-[#94a3b8]">No intelligence articles match your search.</p>
            </div>
          )}
          {filtered.map((a, i) => (
            <a 
              key={a.id} href={a.url} target="_blank" rel="noopener noreferrer"
              className="glass-card p-6 hover:border-[#6366f1]/40 transition-all group relative overflow-hidden flex flex-col justify-between"
            >
              <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                <ExternalLink size={16} className="text-[#6366f1]" />
              </div>
              
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <div className="px-2 py-1 rounded-md bg-[#6366f1]/10 border border-[#6366f1]/20 text-[#8b5cf6] text-[10px] font-bold uppercase tracking-wider">
                    {a.source}
                  </div>
                  <div className="flex items-center gap-1.5 text-[10px] text-[#4b5563] font-bold uppercase">
                    <Calendar size={12} /> {new Date(a.published_date).toLocaleDateString()}
                  </div>
                </div>
                <h3 className="text-lg font-bold text-white group-hover:text-[#6366f1] transition-colors leading-snug mb-4">{a.title}</h3>
              </div>

              <div className="flex flex-wrap gap-2 pt-4 border-t border-white/5">
                {(a.topics || []).map(t => (
                  <span key={t} className="text-[9px] uppercase font-bold tracking-tighter text-[#94a3b8] px-2 py-0.5 rounded-full bg-white/5 border border-white/5">
                    {t}
                  </span>
                ))}
                <div className="ml-auto flex items-center gap-1 text-[9px] font-bold text-[#3ECF8E] uppercase tracking-widest">
                  <Sparkles size={10} /> RAG Ready
                </div>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
