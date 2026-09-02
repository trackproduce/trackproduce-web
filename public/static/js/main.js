"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const cards = Array.from(document.querySelectorAll(".card"));
    const filters = Array.from(document.querySelectorAll(".filter"));

    /* ---------- Header: solidify on scroll ---------- */
    const header = document.getElementById("site-header");
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 40);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    /* ---------- Mobile nav (hamburger) ---------- */
    const navToggle = document.getElementById("nav-toggle");
    const nav = document.getElementById("site-nav");
    const navBackdrop = document.getElementById("nav-backdrop");
    const setNav = (open) => {
        nav.classList.toggle("is-open", open);
        navBackdrop.classList.toggle("is-open", open);
        navBackdrop.hidden = !open;
        navToggle.setAttribute("aria-expanded", String(open));
        // Both labels are editable copy: the template renders them into data-label-*
        // (see app/registry.py, "Menú"), so this file holds no user-facing text.
        navToggle.setAttribute(
            "aria-label",
            open ? navToggle.dataset.labelClose : navToggle.dataset.labelOpen
        );
    };
    navToggle.addEventListener("click", () => setNav(nav.classList.contains("is-open") ? false : true));
    navBackdrop.addEventListener("click", () => setNav(false));
    nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => setNav(false)));
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && nav.classList.contains("is-open")) setNav(false);
    });

    /* ---------- Scroll reveal ---------- */
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const revealEls = Array.from(
        document.querySelectorAll(".section__title, .services li, .card")
    );
    if (!reduceMotion && "IntersectionObserver" in window) {
        revealEls.forEach((el) => el.classList.add("reveal"));
        const io = new IntersectionObserver(
            (entries, obs) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        obs.unobserve(entry.target);
                    }
                });
            },
            { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
        );
        revealEls.forEach((el) => io.observe(el));
    }

    /* ---------- Category filter ---------- */
    filters.forEach((btn) => {
        btn.addEventListener("click", () => {
            filters.forEach((b) => {
                b.classList.remove("is-active");
                b.setAttribute("aria-pressed", "false");
            });
            btn.classList.add("is-active");
            btn.setAttribute("aria-pressed", "true");
            const f = btn.dataset.filter;
            cards.forEach((card) => {
                const show = f === "all" || card.dataset.cat === f;
                card.classList.toggle("is-hidden", !show);
            });
        });
    });

    /* ---------- Hover-to-play for video cards ---------- */
    cards.forEach((card) => {
        if (card.dataset.type !== "video") return;
        const video = card.querySelector("video");
        if (!video) return;
        const ensureSrc = () => {
            if (!video.src) video.src = card.dataset.src;
        };
        card.addEventListener("mouseenter", () => {
            ensureSrc();
            video.play().catch(() => {});
        });
        card.addEventListener("mouseleave", () => {
            video.pause();
        });
    });

    /* ---------- Lightbox ---------- */
    const lightbox = document.getElementById("lightbox");
    const stage = lightbox.querySelector(".lightbox__stage");
    const btnClose = lightbox.querySelector(".lightbox__close");
    const btnPrev = lightbox.querySelector(".lightbox__prev");
    const btnNext = lightbox.querySelector(".lightbox__next");
    let current = -1;

    const visibleCards = () => cards.filter((c) => !c.classList.contains("is-hidden"));

    const render = (index) => {
        const list = visibleCards();
        if (index < 0) index = list.length - 1;
        if (index >= list.length) index = 0;
        current = index;
        const card = list[index];
        stage.innerHTML = "";
        if (card.dataset.type === "video") {
            const v = document.createElement("video");
            v.src = card.dataset.src;
            v.controls = true;
            v.autoplay = true;
            v.loop = true;
            v.playsInline = true;
            stage.appendChild(v);
        } else {
            const img = document.createElement("img");
            img.src = card.dataset.src;
            img.alt = card.getAttribute("aria-label") || "";
            stage.appendChild(img);
        }
    };

    const open = (card) => {
        const list = visibleCards();
        const idx = list.indexOf(card);
        if (idx === -1) return;
        render(idx);
        lightbox.hidden = false;
        document.body.style.overflow = "hidden";
    };

    const close = () => {
        lightbox.hidden = true;
        stage.innerHTML = "";
        document.body.style.overflow = "";
        current = -1;
    };

    cards.forEach((card) => {
        card.addEventListener("click", () => open(card));
        card.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                open(card);
            }
        });
    });

    btnClose.addEventListener("click", close);
    btnPrev.addEventListener("click", () => render(current - 1));
    btnNext.addEventListener("click", () => render(current + 1));
    lightbox.addEventListener("click", (e) => {
        if (e.target === lightbox) close();
    });
    document.addEventListener("keydown", (e) => {
        if (lightbox.hidden) return;
        if (e.key === "Escape") close();
        else if (e.key === "ArrowLeft") render(current - 1);
        else if (e.key === "ArrowRight") render(current + 1);
    });
});
