import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { supabase } from "@/shared/auth/supabase";
import { Spinner } from "@/shared/components/Spinner";

const fadeUp = { hidden:{opacity:0,y:16}, visible:{opacity:1,y:0,transition:{duration:0.4,ease:[0.22,1,0.36,1]}} };

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

  return (
    <motion.div className="p-8 max-w-4xl" initial="hidden" animate="visible" variants={{ visible:{transition:{staggerChildren:0.08}} }}>
      <motion.div variants={fadeUp} className="mb-8">
        <h1 className="text-2xl font-bold text-[#F5F0EB]">Market Intelligence</h1>
        <p className="mt-1 text-sm text-[#6B6560]">Global startup news ingested every 6 hours and embedded into your RAG pipeline.</p>
      </motion.div>

      {loading ? <Spinner size={24} /> : (
        <div className="space-y-4">
          {articles.length === 0 && <p className="text-sm text-[#6B6560]">No articles ingested yet.</p>}
          {articles.map(article => (
             <motion.a key={article.id} href={article.url} target="_blank" rel="noopener noreferrer" variants={fadeUp}
               className="block rounded-2xl border border-[#1e1c1a] bg-[#0d0c0b] p-6 hover:border-[#D97757]/40 transition-colors group">
               <h2 className="text-lg font-semibold text-[#F5F0EB] mb-2 group-hover:text-[#D97757] transition-colors">{article.title}</h2>
               <div className="flex items-center gap-4 text-xs text-[#6B6560] mb-3">
                 <span className="bg-[#161412] px-2 py-1 rounded-md">{article.source}</span>
                 <span>{new Date(article.published_date).toLocaleDateString()}</span>
               </div>
               <div className="flex flex-wrap gap-2 mt-2">
                 {article.topics?.map(t => (
                   <span key={t} className="text-[10px] uppercase tracking-wider text-[#A89F95] border border-[#2a2520] rounded-full px-2 py-0.5">{t}</span>
                 ))}
               </div>
             </motion.a>
          ))}
        </div>
      )}
    </motion.div>
  );
}
