import React, { useState, useEffect } from 'react';

const Counter = ({ value, label }) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = parseInt(value);
    if (start === end) return;

    let totalMiliseconds = 2000;
    let incrementTime = (totalMiliseconds / end);

    let timer = setInterval(() => {
      start += 1;
      setCount(start);
      if (start === end) clearInterval(timer);
    }, incrementTime);

    return () => clearInterval(timer);
  }, [value]);

  return (
    <div className="flex flex-col items-center">
      <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">{count}+</div>
      <div className="text-xs uppercase tracking-widest text-muted font-semibold">{label}</div>
    </div>
  );
};

export const StatsBar = () => {
  return (
    <section className="py-12 border-y border-white/5 bg-white/[0.02]">
      <div className="max-w-7xl mx-auto px-6 grid grid-cols-2 md:grid-cols-4 gap-12 reveal">
        <Counter value="10" label="AI Specialist Agents" />
        <Counter value="10000" label="Stochastic Simulations" />
        <Counter value="25" label="Integrated Data Sources" />
        <Counter value="500" label="Tokens per Second" />
      </div>
    </section>
  );
};
