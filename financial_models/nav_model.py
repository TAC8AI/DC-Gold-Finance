"""
Institutional-style corporate NAV modeling across mining peers.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from data_ingestion.data_normalizer import DataNormalizer
from scenario_engine.npv_calculator import NPVCalculator
from utils.logger import setup_logger

logger = setup_logger(__name__)


class CorporateNAVModel:
    """Build apples-to-apples project and corporate NAV comparisons."""

    def __init__(self):
        self.normalizer = DataNormalizer()
        self.npv_calculator = NPVCalculator()
        self.companies_config = self.normalizer.companies_config.get("companies", {})
        self.assumptions_config = self.normalizer.assumptions_config or {}
        self.nav_assumptions = self._load_nav_assumptions()

    def _load_nav_assumptions(self) -> Dict[str, Any]:
        """Load NAV assumptions from assumptions.yaml with robust defaults."""
        defaults = {
            "default_discount_rate": 0.08,
            "secondary_discount_rate": 0.05,
            "use_stage_risking": True,
            "risk_positive_npv_only": True,
            "exclude_sunk_capex_for_producers": True,
            "default_stage_probability": 0.5,
            "stage_probabilities": {
                "exploration": 0.25,
                "pea": 0.35,
                "pfs": 0.50,
                "fs": 0.65,
                "permitting": 0.60,
                "construction": 0.80,
                "production": 1.00,
            },
            "corporate_adjustments": {},
        }

        nav_config = self.assumptions_config.get("nav_model", {})
        if isinstance(nav_config, dict):
            defaults.update({k: v for k, v in nav_config.items() if k != "stage_probabilities"})
            stage_map = dict(defaults["stage_probabilities"])
            stage_map.update(nav_config.get("stage_probabilities", {}) or {})
            defaults["stage_probabilities"] = stage_map

        return defaults

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        """Convert value to float safely."""
        try:
            if value is None:
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _stage_probability(self, stage: str) -> float:
        """Return stage-based probability factor."""
        stage_key = str(stage or "").strip().lower()
        stage_probabilities = self.nav_assumptions.get("stage_probabilities", {})
        probability = self._safe_float(
            stage_probabilities.get(stage_key),
            self._safe_float(self.nav_assumptions.get("default_stage_probability"), 0.5),
        )
        return max(0.0, min(1.0, probability))

    def _infer_mine_life_years(self, project: Dict[str, Any]) -> int:
        """Infer mine life when not explicitly provided."""
        configured_life = int(self._safe_float(project.get("mine_life_years"), 0))
        if configured_life > 0:
            return configured_life

        annual_prod = self._safe_float(project.get("annual_production_oz"), 0)
        lom_oz = self._safe_float(project.get("life_of_mine_gold_oz"), 0)
        if annual_prod > 0 and lom_oz > 0:
            inferred = int(round(lom_oz / annual_prod))
            if inferred > 0:
                return inferred

        return 10

    def _project_nav(
        self,
        project: Dict[str, Any],
        gold_price: float,
        discount_rate: float,
        use_stage_risking: bool,
    ) -> Dict[str, Any]:
        """Calculate project NAV including stage-risked expected value."""
        stage = str(project.get("stage", "exploration")).lower()
        annual_prod_oz = self._safe_float(project.get("annual_production_oz"), 0)
        aisc_per_oz = self._safe_float(project.get("aisc_per_oz"), 0)
        start_year = int(self._safe_float(project.get("production_start_year"), datetime.now().year))
        mine_life_years = self._infer_mine_life_years(project)
        ownership_pct = self._safe_float(project.get("ownership_pct"), 100.0)
        ownership_factor = max(0.0, ownership_pct) / 100.0

        current_year = datetime.now().year
        if stage == "production" and start_year < current_year:
            start_year = current_year

        initial_capex_millions = self._safe_float(project.get("initial_capex_millions"), 0)
        exclude_sunk = bool(self.nav_assumptions.get("exclude_sunk_capex_for_producers", True))
        if exclude_sunk and stage == "production":
            initial_capex_millions = 0.0

        if annual_prod_oz <= 0 or aisc_per_oz <= 0 or mine_life_years <= 0:
            return {
                "project_name": project.get("name", "Unknown"),
                "stage": stage,
                "modeled": False,
                "reason": "Missing required production/cost/life inputs",
                "annual_production_oz": annual_prod_oz,
                "aisc_per_oz": aisc_per_oz,
                "start_year": start_year,
                "mine_life_years": mine_life_years,
                "initial_capex_millions": initial_capex_millions,
                "ownership_pct": ownership_pct,
                "unrisked_nav": 0.0,
                "risked_nav": 0.0,
                "stage_probability": self._stage_probability(stage),
            }

        npv, _ = self.npv_calculator.calculate_project_npv(
            gold_price=gold_price,
            annual_production_oz=annual_prod_oz,
            aisc_per_oz=aisc_per_oz,
            discount_rate=discount_rate,
            initial_capex=initial_capex_millions * 1_000_000,
            start_year=start_year,
            mine_life_years=mine_life_years,
        )

        stage_probability = self._stage_probability(stage)
        unrisked_nav = self._safe_float(npv, 0.0) * ownership_factor

        if use_stage_risking:
            if bool(self.nav_assumptions.get("risk_positive_npv_only", True)):
                risked_base = max(0.0, unrisked_nav)
            else:
                risked_base = unrisked_nav
            risked_nav = risked_base * stage_probability
        else:
            risked_nav = unrisked_nav

        return {
            "project_name": project.get("name", "Unknown"),
            "stage": stage,
            "modeled": True,
            "annual_production_oz": annual_prod_oz,
            "aisc_per_oz": aisc_per_oz,
            "start_year": start_year,
            "mine_life_years": mine_life_years,
            "initial_capex_millions": initial_capex_millions,
            "ownership_pct": ownership_pct,
            "margin_per_oz": gold_price - aisc_per_oz,
            "unrisked_nav": unrisked_nav,
            "risked_nav": risked_nav,
            "stage_probability": stage_probability,
        }

    def _corporate_adjustment(self, ticker: str) -> Dict[str, float]:
        """Return configured corporate-level NAV bridge adjustments."""
        config = self.nav_assumptions.get("corporate_adjustments", {}).get(ticker, {})
        non_operating_assets = self._safe_float(config.get("non_operating_assets_millions"), 0) * 1_000_000
        other_liabilities = self._safe_float(config.get("other_liabilities_millions"), 0) * 1_000_000
        environmental_liabilities = self._safe_float(config.get("environmental_liabilities_millions"), 0) * 1_000_000
        stream_royalty_burden = self._safe_float(config.get("stream_royalty_burden_millions"), 0) * 1_000_000
        net_adjustment = non_operating_assets - other_liabilities - environmental_liabilities - stream_royalty_burden
        return {
            "non_operating_assets": non_operating_assets,
            "other_liabilities": other_liabilities,
            "environmental_liabilities": environmental_liabilities,
            "stream_royalty_burden": stream_royalty_burden,
            "net_adjustment": net_adjustment,
        }

    def calculate_company_nav(
        self,
        ticker: str,
        gold_price: float,
        discount_rate: Optional[float] = None,
        use_stage_risking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Calculate corporate NAV for one ticker.

        Returns both project NAV stack and corporate bridge metrics.
        """
        normalized = self.normalizer.get_normalized_company_data(ticker)
        if "error" in normalized:
            return {"ticker": ticker, "error": normalized["error"]}

        company_cfg = self.companies_config.get(ticker, {})
        projects_cfg = company_cfg.get("projects", {})

        discount = (
            self._safe_float(discount_rate, 0.0)
            if discount_rate is not None
            else self._safe_float(self.nav_assumptions.get("default_discount_rate"), 0.08)
        )
        use_risking = (
            bool(use_stage_risking)
            if use_stage_risking is not None
            else bool(self.nav_assumptions.get("use_stage_risking", True))
        )

        project_results: List[Dict[str, Any]] = []
        for project in projects_cfg.values():
            project_results.append(
                self._project_nav(
                    project=project,
                    gold_price=gold_price,
                    discount_rate=discount,
                    use_stage_risking=use_risking,
                )
            )

        unrisked_project_nav = sum(p.get("unrisked_nav", 0.0) for p in project_results)
        risked_project_nav = sum(p.get("risked_nav", 0.0) for p in project_results)
        selected_project_nav = risked_project_nav if use_risking else unrisked_project_nav

        market_cap = self._safe_float(normalized.get("market", {}).get("market_cap"), 0)
        shares_outstanding = self._safe_float(normalized.get("market", {}).get("shares_outstanding"), 0)
        current_price = self._safe_float(normalized.get("market", {}).get("current_price"), 0)
        cash = self._safe_float(normalized.get("cash", {}).get("total_cash"), 0)
        debt = self._safe_float(normalized.get("cash", {}).get("total_debt"), 0)
        enterprise_value = market_cap + debt - cash

        adjustments = self._corporate_adjustment(ticker)
        corporate_nav = selected_project_nav + cash - debt + adjustments["net_adjustment"]
        corporate_nav_unrisked = unrisked_project_nav + cash - debt + adjustments["net_adjustment"]
        corporate_nav_risked = risked_project_nav + cash - debt + adjustments["net_adjustment"]

        nav_per_share = corporate_nav / shares_outstanding if shares_outstanding > 0 else 0.0
        p_nav = market_cap / corporate_nav if corporate_nav > 0 else None
        ev_nav = enterprise_value / selected_project_nav if selected_project_nav > 0 else None
        implied_upside_pct = (corporate_nav / market_cap - 1) * 100 if market_cap > 0 else 0.0

        return {
            "ticker": ticker,
            "company_name": normalized.get("name", ticker),
            "gold_price": gold_price,
            "discount_rate": discount,
            "use_stage_risking": use_risking,
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "shares_outstanding": shares_outstanding,
            "current_price": current_price,
            "cash": cash,
            "debt": debt,
            "project_nav_unrisked": unrisked_project_nav,
            "project_nav_risked": risked_project_nav,
            "project_nav_selected": selected_project_nav,
            "corporate_nav": corporate_nav,
            "corporate_nav_unrisked": corporate_nav_unrisked,
            "corporate_nav_risked": corporate_nav_risked,
            "corporate_adjustment": adjustments["net_adjustment"],
            "adjustments_detail": adjustments,
            "nav_per_share": nav_per_share,
            "p_nav": p_nav,
            "ev_nav": ev_nav,
            "implied_upside_pct": implied_upside_pct,
            "project_breakdown": project_results,
            "modeled_projects": sum(1 for p in project_results if p.get("modeled")),
            "total_projects": len(project_results),
            "analysis_time": datetime.now().isoformat(),
        }

    def compare_companies(
        self,
        tickers: List[str],
        gold_price: float,
        discount_rate_primary: Optional[float] = None,
        discount_rate_secondary: Optional[float] = None,
        use_stage_risking: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Return peer NAV comparison tables and project-level drilldown."""
        primary_rate = (
            self._safe_float(discount_rate_primary, 0)
            if discount_rate_primary is not None
            else self._safe_float(self.nav_assumptions.get("default_discount_rate"), 0.08)
        )
        secondary_rate = (
            self._safe_float(discount_rate_secondary, 0)
            if discount_rate_secondary is not None
            else self._safe_float(self.nav_assumptions.get("secondary_discount_rate"), 0.05)
        )

        summaries_primary: Dict[str, Dict[str, Any]] = {}
        summaries_secondary: Dict[str, Dict[str, Any]] = {}
        rows: List[Dict[str, Any]] = []
        project_rows: List[Dict[str, Any]] = []

        for ticker in tickers:
            primary = self.calculate_company_nav(
                ticker=ticker,
                gold_price=gold_price,
                discount_rate=primary_rate,
                use_stage_risking=use_stage_risking,
            )
            secondary = self.calculate_company_nav(
                ticker=ticker,
                gold_price=gold_price,
                discount_rate=secondary_rate,
                use_stage_risking=use_stage_risking,
            )

            if "error" in primary:
                logger.warning("NAV comparison skipped for %s: %s", ticker, primary.get("error"))
                continue

            summaries_primary[ticker] = primary
            summaries_secondary[ticker] = secondary

            p_nav_primary = primary.get("p_nav")
            p_nav_secondary = secondary.get("p_nav")
            corporate_nav_primary = self._safe_float(primary.get("corporate_nav"), 0)
            corporate_nav_secondary = self._safe_float(secondary.get("corporate_nav"), 0)

            rows.append(
                {
                    "Ticker": ticker,
                    "Company": primary.get("company_name", ticker),
                    "Price": primary.get("current_price", 0),
                    "Shares (M)": self._safe_float(primary.get("shares_outstanding"), 0) / 1_000_000,
                    "Market Cap ($M)": self._safe_float(primary.get("market_cap"), 0) / 1_000_000,
                    f"Project NAV @{int(primary_rate * 100)}% ($M)": self._safe_float(primary.get("project_nav_selected"), 0) / 1_000_000,
                    f"Corporate NAV @{int(primary_rate * 100)}% ($M)": corporate_nav_primary / 1_000_000,
                    f"NAV/Share @{int(primary_rate * 100)}%": primary.get("nav_per_share", 0),
                    f"P/NAV @{int(primary_rate * 100)}% (x)": p_nav_primary,
                    f"EV/NAV @{int(primary_rate * 100)}% (x)": primary.get("ev_nav"),
                    f"Corporate NAV @{int(secondary_rate * 100)}% ($M)": corporate_nav_secondary / 1_000_000,
                    f"NAV/Share @{int(secondary_rate * 100)}%": secondary.get("nav_per_share", 0),
                    f"P/NAV @{int(secondary_rate * 100)}% (x)": p_nav_secondary,
                    f"Implied Upside @{int(primary_rate * 100)}%": primary.get("implied_upside_pct", 0),
                    "Cash ($M)": self._safe_float(primary.get("cash"), 0) / 1_000_000,
                    "Debt ($M)": self._safe_float(primary.get("debt"), 0) / 1_000_000,
                    "Corporate Adj ($M)": self._safe_float(primary.get("corporate_adjustment"), 0) / 1_000_000,
                    "Modeled Projects": primary.get("modeled_projects", 0),
                    "Total Projects": primary.get("total_projects", 0),
                }
            )

            for project in primary.get("project_breakdown", []):
                project_rows.append(
                    {
                        "Ticker": ticker,
                        "Project": project.get("project_name", "Unknown"),
                        "Stage": str(project.get("stage", "unknown")).title(),
                        "Modeled": "Yes" if project.get("modeled") else "No",
                        "Ownership (%)": self._safe_float(project.get("ownership_pct"), 0),
                        "Annual Gold (oz/yr)": self._safe_float(project.get("annual_production_oz"), 0),
                        "AISC ($/oz)": self._safe_float(project.get("aisc_per_oz"), 0),
                        "Start Year": int(self._safe_float(project.get("start_year"), 0)),
                        "Mine Life (yrs)": int(self._safe_float(project.get("mine_life_years"), 0)),
                        "Capex Used ($M)": self._safe_float(project.get("initial_capex_millions"), 0),
                        "Stage Probability": self._safe_float(project.get("stage_probability"), 0),
                        f"Unrisked NAV @{int(primary_rate * 100)}% ($M)": self._safe_float(project.get("unrisked_nav"), 0) / 1_000_000,
                        f"Risked NAV @{int(primary_rate * 100)}% ($M)": self._safe_float(project.get("risked_nav"), 0) / 1_000_000,
                    }
                )

        summary_df = pd.DataFrame(rows)
        project_df = pd.DataFrame(project_rows)

        primary_pnav_col = f"P/NAV @{int(primary_rate * 100)}% (x)"
        peer_stats = {
            "median_p_nav": None,
            "mean_p_nav": None,
            "count_positive_nav": 0,
            "primary_pnav_col": primary_pnav_col,
        }

        if not summary_df.empty and primary_pnav_col in summary_df.columns:
            valid = summary_df[summary_df[primary_pnav_col].notna() & (summary_df[primary_pnav_col] > 0)].copy()
            peer_stats["count_positive_nav"] = len(valid)
            if not valid.empty:
                peer_stats["median_p_nav"] = float(valid[primary_pnav_col].median())
                peer_stats["mean_p_nav"] = float(valid[primary_pnav_col].mean())

                ranking = valid[["Ticker", primary_pnav_col]].copy()
                ranking["P/NAV Percentile (Lower Better)"] = (
                    ranking[primary_pnav_col].rank(method="min", pct=True, ascending=True) * 100
                )
                summary_df = summary_df.merge(
                    ranking[["Ticker", "P/NAV Percentile (Lower Better)"]],
                    on="Ticker",
                    how="left",
                )
            else:
                summary_df["P/NAV Percentile (Lower Better)"] = None

        return {
            "summary_df": summary_df,
            "project_df": project_df,
            "primary_results": summaries_primary,
            "secondary_results": summaries_secondary,
            "peer_stats": peer_stats,
            "assumptions": {
                "gold_price": gold_price,
                "discount_rate_primary": primary_rate,
                "discount_rate_secondary": secondary_rate,
                "use_stage_risking": (
                    bool(use_stage_risking)
                    if use_stage_risking is not None
                    else bool(self.nav_assumptions.get("use_stage_risking", True))
                ),
                "stage_probabilities": self.nav_assumptions.get("stage_probabilities", {}),
                "exclude_sunk_capex_for_producers": bool(
                    self.nav_assumptions.get("exclude_sunk_capex_for_producers", True)
                ),
            },
            "analysis_time": datetime.now().isoformat(),
        }
