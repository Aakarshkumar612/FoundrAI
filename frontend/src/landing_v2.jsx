import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from "@/shared/auth/supabase";
import { useIntersectionObserver } from './hooks/useIntersectionObserver';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { StatsBar } from './components/StatsBar';
import { Features } from './components/Features';
import { HowItWorks } from './components/HowItWorks';
import { TechStack } from './components/TechStack';
import { CTA } from './components/CTA';
import { Footer } from './components/Footer';

export const LandingPageV2 = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);

  // Activate scroll-triggered reveal animations
  useIntersectionObserver('.reveal');

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => {
      if (data.user) {
        navigate("/dashboard");
      } else {
        setLoading(false);
      }
    });
  }, [navigate]);

  if (loading) return null;

  return (
    <div className="relative min-h-screen bg-[#0a0a0f] text-white selection:bg-[#6366f1]/30 overflow-x-hidden">
      {/* Background elements */}
      <div className="fixed inset-0 bg-dots opacity-[0.03] pointer-events-none" />
      
      <Navbar />
      <Hero />
      <StatsBar />
      <Features />
      <HowItWorks />
      <TechStack />
      <CTA />
      <Footer />
    </div>
  );
};
