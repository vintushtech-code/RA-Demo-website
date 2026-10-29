/**
 * GuardianTree FP — Services Page Interactive Controller
 * Handles showcase panel switching, multi-service side-by-side comparison drawer/matrix modal,
 * filter & keyword search, detail modal view, and dynamic advisory recommendation calculation.
 */

const serviceKeys = ['portfolio-strategy', 'retirement-planning', 'institutional-treasury', 'fiduciary-services'];

function getConsultationBaseUrl() {
    return window.CONSULTATION_URL || '/consultation/';
}

function showService(key, scrollToSection = false) {
    const panels = document.querySelectorAll('.showcase-panel');
    const dots = document.querySelectorAll('.showcase-dot');
    const index = serviceKeys.indexOf(key);
    if (index === -1) return;

    panels.forEach((panel) => {
        const isActive = panel.dataset.serviceKey === key;
        panel.classList.toggle('active', isActive);
    });

    dots.forEach((dot) => {
        const isActive = dot.dataset.serviceKey === key;
        dot.classList.toggle('active', isActive);
    });

    const url = new URL(window.location.href);
    url.searchParams.set('service', key);
    window.history.replaceState({}, '', url);

    if (scrollToSection) {
        const showcase = document.getElementById('service-showcase');
        if (showcase) {
            requestAnimationFrame(() => {
                showcase.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        }
    }
}

function moveService(direction) {
    const activeKey = document.querySelector('.showcase-panel.active')?.dataset.serviceKey || serviceKeys[0];
    const currentIndex = serviceKeys.indexOf(activeKey);
    const nextIndex = (currentIndex + direction + serviceKeys.length) % serviceKeys.length;
    showService(serviceKeys[nextIndex]);
}

// Services Comparison Functionality
let selectedServices = [];
const comparisonData = {
    architecture: {
        name: "Bespoke Financial Architecture",
        target: "$1M+ Portfolios / Family Wealth",
        objective: "Forensic wealth structuring & tax shielding",
        deliverables: ["Forensic global balance sheet audit", "Asset-backed leverage optimization", "Offshore & domestic trust integration", "Quarterly wealth projection models"],
        access: "Managing Partner & Senior Desk",
        taxReduction: "High (Up to 40% liability reduction)"
    },
    portfolio: {
        name: "Active Wealth Cultivation",
        target: "Growth Seekers / Active Portfolios",
        objective: "Quantitative multi-asset growth & private credit/PE",
        deliverables: ["Discretionary quantitative equity models", "Access to PE syndicates & direct deals", "Algorithmic risk buffers & hedging", "Real-time institutional portal access"],
        access: "Discretionary Portfolio Manager",
        taxReduction: "Medium (Tax-loss harvesting integrated)"
    },
    retirement: {
        name: "Optimized Retirement Trajectories",
        target: "Pre-retirement Executives & Business Owners",
        objective: "Guaranteed, tax-free longevity income design",
        deliverables: ["Tax-sheltered distribution strategy", "Healthcare cost shielding", "Executive pension roll-overs", "Enduring legacy transfer buffers"],
        access: "Retirement Strategy Advisor",
        taxReduction: "High (Maximized distribution tax shielding)"
    },
    legacy: {
        name: "Strategic Corporate & Legacy Counsel",
        target: "Family Enterprises & Corporate Founders",
        objective: "Succession mapping, phantom stock, and office charters",
        deliverables: ["M&A exit valuation roadmap", "Executive equity phantom stock design", "Family Office Charter & Constitution", "Donor-Advised Funds (DAF) setup"],
        access: "Full Retained Advisory Council",
        taxReduction: "High (Dynasty & CRT shielding)"
    },
    tax: {
        name: "Tax Mitigation & Estate Shielding",
        target: "Asset Protection & High Tax Exposure",
        objective: "Cross-border tax minimization and estate trust shield",
        deliverables: ["Irrevocable Dynasty Trust setup", "Multi-jurisdictional tax audit", "Legal liability asset protection", "Charitable Remainder Trust (CRT) implementation"],
        access: "Fiduciary Trust Attorney & Tax Partner",
        taxReduction: "Extreme (Maximum multi-jurisdictional reduction)"
    },
    alternatives: {
        name: "Private Equity & Alternative Assets",
        target: "Accredited Investors & Family Offices",
        objective: "Direct co-investment in non-public yield assets",
        deliverables: ["Direct private equity syndications", "High-yield private credit pools (8-12%)", "Prime commercial real estate syndicates", "Pre-IPO venture capital rounds"],
        access: "Alternatives Placement Desk",
        taxReduction: "Medium (Capital gains deferrals)"
    },
    advisory: {
        name: "Strategic Corporate Advisory",
        target: "Enterprises, Mid-Caps, and Startups",
        objective: "Corporate capital structure and transaction advisory",
        deliverables: ["Buy-side & sell-side M&A consulting", "Capital structure optimization", "Distressed asset restructuring", "Forensic due diligence audits"],
        access: "Senior Investment Banker",
        taxReduction: "Transactional (Corporate tax structuring)"
    },
    family: {
        name: "Family & Next-Gen Financial Literacy",
        target: "Heirs & Community Youth",
        objective: "Governance retreats and wealth stewardship workshops",
        deliverables: ["Next-generation family retreats", "Interactive wealth workshops", "Mentorship access", "Entrepreneurial grant incubators"],
        access: "Community Engagement Partner",
        taxReduction: "N/A"
    }
};

function handleCompareSelect(checkbox, event) {
    if (event) event.stopPropagation();
    const serviceId = checkbox.getAttribute('data-service-id');
    if (checkbox.checked) {
        if (selectedServices.length >= 3) {
            checkbox.checked = false;
            alert("You can select up to 3 services to compare side-by-side.");
            return;
        }
        selectedServices.push(serviceId);
    } else {
        selectedServices = selectedServices.filter(id => id !== serviceId);
    }
    updateComparisonDrawer();
}

function updateComparisonDrawer() {
    const drawer = document.getElementById('comparison-drawer');
    const countText = document.getElementById('compare-count-text');
    if (!drawer) return;

    if (selectedServices.length > 0) {
        drawer.classList.add('active');
        if (countText) countText.innerText = `${selectedServices.length} of 3 selected`;
    } else {
        drawer.classList.remove('active');
    }
}

function clearComparison() {
    selectedServices = [];
    document.querySelectorAll('.compare-select').forEach(cb => cb.checked = false);
    updateComparisonDrawer();
}

function openComparisonModal() {
    if (selectedServices.length === 0) return;
    const wrapper = document.getElementById('compare-table-wrapper');
    if (!wrapper) return;

    let html = `<table class="compare-table" role="table" aria-label="Side-by-side Service Comparison Matrix"><thead><tr><th scope="col" class="compare-row-header">Attribute</th>`;

    selectedServices.forEach(id => {
        const service = comparisonData[id];
        html += `<th scope="col" class="compare-col-service">${service.name}</th>`;
    });
    html += `</tr></thead><tbody>`;

    // Row 1: Target Client
    html += `<tr><th scope="row" class="compare-row-header">Target Client</th>`;
    selectedServices.forEach(id => {
        html += `<td>${comparisonData[id].target}</td>`;
    });
    html += `</tr>`;

    // Row 2: Strategic Objective
    html += `<tr><th scope="row" class="compare-row-header">Strategic Objective</th>`;
    selectedServices.forEach(id => {
        html += `<td>${comparisonData[id].objective}</td>`;
    });
    html += `</tr>`;

    // Row 3: Key Deliverables
    html += `<tr><th scope="row" class="compare-row-header">Key Deliverables</th>`;
    selectedServices.forEach(id => {
        html += `<td><ul style="list-style: none; padding-left: 0; margin: 0;">`;
        comparisonData[id].deliverables.forEach(item => {
            html += `<li style="margin-bottom: 6px; color: #FFFFFF;"><span style="color: #F5D77F; margin-right: 6px;">✓</span> ${item}</li>`;
        });
        html += `</ul></td>`;
    });
    html += `</tr>`;

    // Row 4: Fiduciary Access
    html += `<tr><th scope="row" class="compare-row-header">Fiduciary Access</th>`;
    selectedServices.forEach(id => {
        html += `<td>${comparisonData[id].access}</td>`;
    });
    html += `</tr>`;

    // Row 5: Tax Optimization
    html += `<tr><th scope="row" class="compare-row-header">Tax Optimization</th>`;
    selectedServices.forEach(id => {
        html += `<td>${comparisonData[id].taxReduction}</td>`;
    });
    html += `</tr>`;

    // Row 6: Action Button
    html += `<tr><th scope="row" class="compare-row-header">Action</th>`;
    const consultationBase = getConsultationBaseUrl();
    selectedServices.forEach(id => {
        html += `<td>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <button class="btn-gold-sm" style="width: 100%; text-align: center; font-size: 0.8rem; padding: 8px 12px; border-radius: 6px;" onclick="closeComparisonModal(); openModal('${id}')">VIEW SYSTEM DETAILS</button>
                    <a href="${consultationBase}" class="btn-glass" style="width: 100%; text-align: center; font-size: 0.8rem; padding: 8px 12px; border-radius: 6px;" onclick="closeComparisonModal()">REQUEST EVALUATION</a>
                </div>
            </td>`;
    });
    html += `</tr>`;

    html += `</tbody></table>`;
    wrapper.innerHTML = html;

    const modal = document.getElementById('compare-modal');
    if (modal) {
        modal.classList.add('active');
        if (typeof announceToScreenReader === 'function') {
            announceToScreenReader(`Service Comparison Modal opened comparing ${selectedServices.length} services.`);
        }
        if (typeof speechEnabled !== 'undefined' && speechEnabled && typeof speakText === 'function') {
            speakText(`Service Comparison Matrix opened with ${selectedServices.length} services.`);
        }
    }
}

function closeComparisonModal() {
    const modal = document.getElementById('compare-modal');
    if (modal) modal.classList.remove('active');
}

// Filtering Functionality
function filterServices() {
    const activePill = document.querySelector('.filter-pill.active');
    const activeCategory = activePill ? activePill.getAttribute('data-category') : 'all';
    const searchInput = document.getElementById('service-search');
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const serviceCards = document.querySelectorAll('.service-card');

    serviceCards.forEach(card => {
        const cardCategories = card.getAttribute('data-category') || '';
        const cardText = card.innerText.toLowerCase();

        const matchesCategory = (activeCategory === 'all') || cardCategories.includes(activeCategory);
        const matchesSearch = query === '' || cardText.includes(query);

        if (matchesCategory && matchesSearch) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}

// Service Modal Details
const serviceDetails = {
    architecture: {
        title: "Bespoke Financial Architecture",
        badge: "WEALTH ARCHITECTURE",
        desc: "Our flagship structural planning mandate engineered for individuals and families managing over $1M in liquid assets. We audit your global balance sheet to eliminate tax friction, restructure liabilities, and align liquid cash flow with generational goals.",
        deliverables: [
            "Full forensic balance sheet & tax liability audit",
            "Asset-backed leverage & liquidity structuring",
            "Offshore & domestic trust integration",
            "Quarterly wealth projection modeling"
        ]
    },
    portfolio: {
        title: "Active Wealth Cultivation",
        badge: "PORTFOLIO GROWTH",
        desc: "Institutional discretionary asset management deploying quantitative multi-asset strategies across equities, global bonds, private equity, and structured alternative debt. Designed to outperform benchmark indices while preserving principal.",
        deliverables: [
            "Discretionary portfolio mandate execution",
            "Access to private equity syndicates & direct co-investments",
            "Algorithmic risk hedging & downside buffers",
            "Real-time institutional performance portal access"
        ]
    },
    retirement: {
        title: "Optimized Retirement Trajectories",
        badge: "RETIREMENT & LONGEVITY",
        desc: "Guaranteed income trajectory design for executives and business owners transitioning out of active operations. We construct non-correlated income cash flow streams immune to market drawdowns.",
        deliverables: [
            "Tax-sheltered distribution strategy",
            "Longevity insurance & healthcare cost shielding",
            "Executive pension rollover & consolidation",
            "Legacy transfer buffer creation"
        ]
    },
    legacy: {
        title: "Strategic Corporate & Legacy Counsel",
        badge: "CORPORATE & SUCCESSION",
        desc: "Comprehensive advisory for family enterprises and founders. We design governance structures, succession plans, and philanthropic endowments that ensure legacy continuity across generations.",
        deliverables: [
            "Business valuation & succession roadmap",
            "Executive retention & equity phantom stock design",
            "Family Office Charter & Constitution development",
            "Donor-Advised Funds & Private Foundation setup"
        ]
    },
    tax: {
        title: "Tax Mitigation & Estate Shielding",
        badge: "TAX & ESTATE SHIELDING",
        desc: "Advanced multi-jurisdictional tax optimization strategies that safeguard capital against estate tax friction, capital gains spikes, and regulatory vulnerability.",
        deliverables: [
            "Irrevocable Dynasty Trust structuring",
            "Cross-border tax compliance & shielding",
            "Asset protection against legal liabilities",
            "Charitable Remainder Trust (CRT) implementation"
        ]
    },
    alternatives: {
        title: "Private Equity & Alternative Assets",
        badge: "ALTERNATIVE VENTURES",
        desc: "Exclusive co-investment opportunities in private credit markets, prime commercial real estate syndicates, venture capital rounds, and physical commodity vaults.",
        deliverables: [
            "Access to institutional private placement memos",
            "High-yield private debt pools (8-12% target return)",
            "Tier-1 commercial real estate syndications",
            "Pre-IPO venture capital allocations"
        ]
    },
    advisory: {
        title: "Strategic Corporate Advisory",
        badge: "FINANCE ADVISORY",
        desc: "Expert-led strategic financial advisory guiding enterprises through complex mergers, acquisitions, capital structuring, and critical financial transitions.",
        deliverables: [
            "Buy-side and sell-side M&A advisory",
            "Capital structure optimization",
            "Distressed asset restructuring",
            "Comprehensive financial due diligence"
        ]
    },
    family: {
        title: "Family & Next-Gen Financial Literacy",
        badge: "COMMUNITY & YOUTH",
        desc: "Curriculum-based financial stewardship programs designed to equip heirs and community youth with practical capital management skills and executive leadership principles.",
        deliverables: [
            "Next-generation family governance retreats",
            "Interactive wealth stewardship workshops",
            "Oasis Youth Center mentorship access",
            "Entrepreneurial grant funding incubators"
        ]
    }
};

function openModal(key) {
    const detail = serviceDetails[key];
    if (!detail) return;
    const modalBody = document.getElementById('modal-body-content');
    if (!modalBody) return;

    const serviceMap = {
        architecture: 'investment',
        portfolio: 'investment',
        retirement: 'retirement',
        legacy: 'wealth_management',
        tax: 'tax_planning',
        alternatives: 'investment',
        advisory: 'general',
        family: 'wealth_management'
    };
    const serviceKey = serviceMap[key] || 'financial_planning';
    const consultationUrl = `${getConsultationBaseUrl()}?service=${serviceKey}`;

    modalBody.innerHTML = `
        <span class="card-badge" style="margin-bottom: 12px; display: inline-block;">${detail.badge}</span>
        <h2 style="font-size: 2.2rem; font-family: var(--font-heading); margin-bottom: 16px; color: var(--color-heading-text);">${detail.title}</h2>
        <p style="color: var(--color-text-muted); font-size: 1.05rem; line-height: 1.7; margin-bottom: 24px;">${detail.desc}</p>
        <h4 style="color: var(--color-gold-light); font-size: 1rem; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">Key Advisory Deliverables:</h4>
        <ul style="list-style: none; margin-bottom: 30px;">
            ${detail.deliverables.map(item => `<li style="color: var(--color-text-main); margin-bottom: 10px; font-size: 0.95rem;"><span style="color: var(--color-gold-light); margin-right: 8px;">✓</span> ${item}</li>`).join('')}
        </ul>
        <div style="text-align: right;">
            <a href="${consultationUrl}" class="btn-gold-sm" style="display: inline-block; text-decoration: none; padding: 0.75rem 1.75rem; background: linear-gradient(135deg, #0B192C, #1E293B); border: 1px solid #D4AF37; color: #FFF9D2; border-radius: var(--radius-pill); font-weight: 700;">BOOK CONSULTATION FOR THIS SERVICE →</a>
        </div>
    `;
    const modal = document.getElementById('service-modal');
    if (modal) modal.classList.add('active');
}

function closeModal() {
    const modal = document.getElementById('service-modal');
    if (modal) modal.classList.remove('active');
}

function getConsultationRecommendation(profile, objective) {
    const recommendation = {
        service: 'financial_planning',
        label: 'Comprehensive Financial Planning',
        subject: 'Wealth Architecture & Advisory Blueprint',
        message: 'Request an advisory session focused on portfolio architecture, tax-efficient wealth transfer, and long-term capital preservation.',
        title: 'Bespoke Wealth Architecture & Tax Shield',
        desc: 'Our foundational comprehensive mandate integrating asset allocation, cash flow optimization, and tax-efficient distribution.',
        features: [
            '1-on-1 Managing Partner',
            'Quarterly Financial Audit',
            'Bespoke Asset Allocation'
        ]
    };

    if (profile === 'fo' || objective === 'tax') {
        recommendation.service = 'tax_planning';
        recommendation.label = 'Tax Optimization & Fiscal Structuring';
        recommendation.subject = 'Family Office Trust & Tax Shield Strategy';
        recommendation.message = 'Request an advisory session focused on cross-border trust structuring, dynasty trust design, and tax mitigation strategies.';
        recommendation.title = 'Family Office Sovereign Trust & Tax Shield';
        recommendation.desc = 'Tailored for multi-generational holdings and family offices requiring cross-border trust structuring, tax elimination strategies, and legacy governance.';
        recommendation.features = [
            'Dedicated Senior Family Officer',
            'Irrevocable Dynasty Trust',
            'Offshore Sovereign Defense'
        ];
    } else if (objective === 'growth') {
        recommendation.service = 'investment';
        recommendation.label = 'Investment & Multi-Asset Portfolio Strategy';
        recommendation.subject = 'Active Multi-Asset Growth Advisory';
        recommendation.message = 'Request an advisory session focused on private equity access, multi-asset growth allocation, and quantitative risk management.';
        recommendation.title = 'Active Multi-Asset Portfolio Cultivation';
        recommendation.desc = 'Optimized for aggressive capital growth using quantitative equity models, private equity syndicates, and structured high-yield debt.';
        recommendation.features = [
            'Private Market Co-Investment',
            'Algorithmic Downside Buffer',
            'Real-Time Portfolio Portal'
        ];
    } else if (objective === 'succession' || profile === 'corp') {
        recommendation.service = 'wealth_management';
        recommendation.label = 'Private Wealth Management & Family Office';
        recommendation.subject = 'Corporate Succession & Legacy Advisory';
        recommendation.message = 'Request an advisory session focused on succession planning, founder liquidity, and family office governance.';
        recommendation.title = 'Corporate Succession & Founder Liquidity Mandate';
        recommendation.desc = 'Engineered for business founders preparing for M&A exit, phantom equity distribution, and successor leadership transition.';
        recommendation.features = [
            'M&A Valuation & Exit Strategy',
            'Executive Equity Phantom Plan',
            'Heir Leadership Bootcamp'
        ];
    } else if (objective === 'preservation') {
        recommendation.service = 'fixed_deposit';
        recommendation.label = 'Fixed Deposit & High-Yield Preservation';
        recommendation.subject = 'Preservation & Structured Wealth Protection';
        recommendation.message = 'Request an advisory session focused on capital preservation, high-yield preservation instruments, and wealth protection protocols.';
        recommendation.title = 'Preservation & Wealth Protection Blueprint';
        recommendation.desc = 'Designed for clients prioritizing capital preservation, risk reduction, and structured wealth protection across market cycles.';
        recommendation.features = [
            'Preservation Strategy Design',
            'Risk-Shielded Allocation',
            'Tax-Efficient Capital Defense'
        ];
    }

    return recommendation;
}

function getConsultationUrl(recommendation) {
    const baseUrl = getConsultationBaseUrl();
    const params = new URLSearchParams();
    params.set('service', recommendation.service);
    params.set('subject', recommendation.subject);
    params.set('message', recommendation.message);
    return `${baseUrl}?${params.toString()}`;
}

function calculateRecommendation() {
    const profileEl = document.getElementById('calc-profile');
    const objEl = document.getElementById('calc-objective');
    if (!profileEl || !objEl) return;

    const profile = profileEl.value;
    const obj = objEl.value;
    const titleEl = document.getElementById('rec-title');
    const descEl = document.getElementById('rec-desc');
    const featsEl = document.getElementById('rec-features');
    const serviceLabelEl = document.getElementById('rec-service-label');
    const buttonLink = document.getElementById('apply-advisory-link');

    const recommendation = getConsultationRecommendation(profile, obj);

    if (titleEl) titleEl.innerText = recommendation.title;
    if (descEl) descEl.innerText = recommendation.desc;
    if (featsEl) featsEl.innerHTML = recommendation.features.map(feature => `<span>• ${feature}</span>`).join('');
    if (serviceLabelEl) {
        serviceLabelEl.innerText = `Recommended Service: ${recommendation.label}`;
    }
    if (buttonLink) {
        buttonLink.href = getConsultationUrl(recommendation);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Initial service showcase activation
    const searchParams = new URLSearchParams(window.location.search);
    const hasServiceParam = searchParams.has('service');
    const initialKey = searchParams.get('service') || serviceKeys[0];
    const validKey = serviceKeys.includes(initialKey) ? initialKey : serviceKeys[0];
    showService(validKey, hasServiceParam);

    document.querySelector('.showcase-nav.prev')?.addEventListener('click', () => moveService(-1));
    document.querySelector('.showcase-nav.next')?.addEventListener('click', () => moveService(1));

    // Touch swipe gesture support for interactive showcase carousel on mobile
    const showcaseShell = document.querySelector('.showcase-shell');
    if (showcaseShell) {
        let touchStartX = 0;
        let touchStartY = 0;

        showcaseShell.addEventListener('touchstart', (e) => {
            if (!e.changedTouches || e.changedTouches.length === 0) return;
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });

        showcaseShell.addEventListener('touchend', (e) => {
            if (!e.changedTouches || e.changedTouches.length === 0) return;
            const diffX = e.changedTouches[0].screenX - touchStartX;
            const diffY = e.changedTouches[0].screenY - touchStartY;

            if (Math.abs(diffX) > 40 && Math.abs(diffX) > Math.abs(diffY)) {
                if (diffX < 0) {
                    moveService(1); // Swipe left -> next slide
                } else {
                    moveService(-1); // Swipe right -> prev slide
                }
            }
        }, { passive: true });
    }

    document.querySelectorAll('.showcase-dot').forEach((dot) => {
        dot.addEventListener('click', () => showService(dot.dataset.serviceKey, true));
    });

    document.querySelectorAll('.service-menu-link').forEach((link) => {
        link.addEventListener('click', (event) => {
            event.preventDefault();
            const key = link.dataset.serviceKey;
            const url = new URL(link.href);
            url.searchParams.set('service', key);
            window.history.pushState({}, '', url);
            showService(key, true);
        });
    });

    // Filtering listeners
    const filterPills = document.querySelectorAll('.filter-pill');
    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            filterServices();
        });
    });

    const searchInput = document.getElementById('service-search');
    if (searchInput) {
        searchInput.addEventListener('input', filterServices);
    }

    // Modal background click listeners
    const compareModal = document.getElementById('compare-modal');
    if (compareModal) {
        compareModal.addEventListener('click', (e) => {
            if (e.target.classList.contains('compare-modal-overlay')) {
                closeComparisonModal();
            }
        });
    }

    const serviceModal = document.getElementById('service-modal');
    if (serviceModal) {
        serviceModal.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                closeModal();
            }
        });
    }

    // Initial recommendation calculation
    calculateRecommendation();
});
