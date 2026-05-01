import { useEffect } from "react";

export const useIntersectionObserver = (selector = ".reveal", options = {}) => {
  useEffect(() => {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("active");
        }
      });
    }, {
      threshold: 0.1,
      ...options
    });

    const elements = document.querySelectorAll(selector);
    elements.forEach((el) => {
      if (el instanceof Element) {
        observer.observe(el);
      }
    });

    return () => {
      elements.forEach((el) => {
        if (el instanceof Element) {
          observer.unobserve(el);
        }
      });
      observer.disconnect();
    };
  }, [selector, options]);
};
