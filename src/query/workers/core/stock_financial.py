"""定义四个财报接口各自独立的数据更新 Worker。"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from query.utils import TIME_COLUMN, logger
from query.utils.ts_api import get_company_types, get_pro

from .base import StockWorker

FLOW_SUFFIXES = ("ttm", "1", "2", "3", "4")
BALANCE_FACTORS = tuple(
    """
    cap_rese undistr_porfit surplus_rese special_rese money_cap
    trad_asset notes_receiv accounts_receiv oth_receiv prepayment div_receiv
    int_receiv inventories amor_exp nca_within_1y sett_rsrv loanto_oth_bank_fi
    premium_receiv reinsur_receiv reinsur_res_receiv pur_resale_fa oth_cur_assets
    total_cur_assets fa_avail_for_sale htm_invest lt_eqt_invest invest_real_estate
    time_deposits oth_assets lt_rec fix_assets cip const_materials fixed_assets_disp
    produc_bio_assets oil_and_gas_assets intan_assets r_and_d goodwill lt_amor_exp
    defer_tax_assets decr_in_disbur oth_nca total_nca cash_reser_cb depos_in_oth_bfi
    prec_metals deriv_assets rr_reins_une_prem rr_reins_outstd_cla rr_reins_lins_liab
    rr_reins_lthins_liab refund_depos ph_pledge_loans refund_cap_depos
    indep_acct_assets client_depos client_prov transac_seat_fee invest_as_receiv
    total_assets lt_borr st_borr cb_borr depos_ib_deposits loan_oth_bank trading_fl
    notes_payable acct_payable adv_receipts sold_for_repur_fa comm_payable
    payroll_payable taxes_payable int_payable div_payable oth_payable acc_exp
    deferred_inc st_bonds_payable payable_to_reinsurer rsrv_insur_cont
    acting_trading_sec acting_uw_sec non_cur_liab_due_1y oth_cur_liab total_cur_liab
    bond_payable lt_payable specific_payables estimated_liab defer_tax_liab
    defer_inc_non_cur_liab oth_ncl total_ncl depos_oth_bfi deriv_liab depos
    agency_bus_liab oth_liab prem_receiv_adva depos_received ph_invest
    reser_une_prem reser_outstd_claims reser_lins_liab reser_lthins_liab
    indept_acc_liab pledge_borr indem_payable policy_div_payable total_liab
    treasury_share ordin_risk_reser forex_differ invest_loss_unconf minority_int
    total_hldr_eqy_exc_min_int total_hldr_eqy_inc_min_int total_liab_hldr_eqy
    lt_payroll_payable oth_comp_income oth_eqt_tools oth_eqt_tools_p_shr
    lending_funds acc_receivable st_fin_payable payables hfs_assets hfs_sales
    cost_fin_assets fair_value_fin_assets contract_assets contract_liab
    accounts_receiv_bill accounts_pay oth_rcv_total fix_assets_total cip_total
    oth_pay_total long_pay_total debt_invest oth_debt_invest
    """.split()
)
INCOME_RAW_FACTORS = tuple(
    """
    basic_eps diluted_eps total_revenue revenue int_income prem_earned comm_income n_commis_income
    n_oth_income n_oth_b_income prem_income out_prem une_prem_reser reins_income
    n_sec_tb_income n_sec_uw_income n_asset_mg_income oth_b_income
    fv_value_chg_gain invest_income ass_invest_income forex_gain total_cogs oper_cost
    int_exp comm_exp biz_tax_surchg sell_exp admin_exp fin_exp assets_impair_loss
    prem_refund compens_payout reser_insur_liab div_payt reins_exp oper_exp
    compens_payout_refu insur_reser_refu reins_cost_refund other_bus_cost
    operate_profit non_oper_income non_oper_exp nca_disploss total_profit income_tax
    n_income n_income_attr_p minority_gain oth_compr_income t_compr_income
    compr_inc_attr_p compr_inc_attr_m_s ebit ebitda insurance_exp undist_profit
    distable_profit rd_exp fin_exp_int_exp fin_exp_int_inc transfer_surplus_rese
    transfer_housing_imprest transfer_oth adj_lossgain withdra_legal_surplus
    withdra_legal_pubfund withdra_biz_devfund withdra_rese_fund withdra_oth_ersu
    workers_welfare distr_profit_shrhder prfshare_payable_dvd comshare_payable_dvd
    capit_comstock_div continued_net_profit
    """.split()
)
CASHFLOW_RAW_FACTORS = tuple(
    """
    net_profit finan_exp c_fr_sale_sg recp_tax_rends n_depos_incr_fi
    n_incr_loans_cb n_inc_borr_oth_fi prem_fr_orig_contr n_incr_insured_dep
    n_reinsur_prem n_incr_disp_tfa ifc_cash_incr n_incr_disp_faas
    n_incr_loans_oth_bank n_cap_incr_repur c_fr_oth_operate_a c_inf_fr_operate_a
    c_paid_goods_s c_paid_to_for_empl c_paid_for_taxes n_incr_clt_loan_adv
    n_incr_dep_cbob c_pay_claims_orig_inco pay_handling_chrg pay_comm_insur_plcy
    oth_cash_pay_oper_act st_cash_out_act n_cashflow_act oth_recp_ral_inv_act
    c_disp_withdrwl_invest c_recp_return_invest n_recp_disp_fiolta n_recp_disp_sobu
    stot_inflows_inv_act c_pay_acq_const_fiolta c_paid_invest n_disp_subs_oth_biz
    oth_pay_ral_inv_act n_incr_pledge_loan stot_out_inv_act n_cashflow_inv_act
    c_recp_borrow proc_issue_bonds oth_cash_recp_ral_fnc_act stot_cash_in_fnc_act
    free_cashflow c_prepay_amt_borr c_pay_dist_dpcp_int_exp incl_dvd_profit_paid_sc_ms
    oth_cashpay_ral_fnc_act stot_cashout_fnc_act n_cash_flows_fnc_act
    eff_fx_flu_cash n_incr_cash_cash_equ c_cash_equ_beg_period c_cash_equ_end_period
    c_recp_cap_contrib incl_cash_rec_saims uncon_invest_loss prov_depr_assets
    depr_fa_coga_dpba amort_intang_assets lt_amort_deferred_exp decr_deferred_exp
    incr_acc_exp loss_disp_fiolta loss_scr_fa loss_fv_chg invest_loss
    decr_def_inc_tax_assets incr_def_inc_tax_liab decr_inventories decr_oper_payable
    incr_oper_payable others im_net_cashflow_oper_act conv_debt_into_cap
    conv_copbonds_due_within_1y fa_fnc_leases im_n_incr_cash_equ
    net_dism_capital_add net_cash_rece_sec credit_impa_loss use_right_asset_dep
    oth_loss_asset end_bal_cash beg_bal_cash end_bal_cash_equ beg_bal_cash_equ
    """.split()
)
INDICATOR_FACTORS = tuple(
    """
    eps dt_eps total_revenue_ps revenue_ps capital_rese_ps surplus_rese_ps
    undist_profit_ps extra_item profit_dedt gross_margin current_ratio quick_ratio
    cash_ratio ar_turn ca_turn fa_turn assets_turn op_income fcff fcfe
    current_exint noncurrent_exint interestdebt netdebt tangible_asset working_capital
    networking_capital invest_capital retained_earnings diluted2_eps bps ocfps
    retainedps cfps ebit_ps fcff_ps fcfe_ps netprofit_margin grossprofit_margin
    cogs_of_sales expense_of_sales profit_to_gr saleexp_to_gr adminexp_of_gr
    finaexp_of_gr impai_ttm gc_of_gr op_of_gr ebit_of_gr roe roe_waa roe_dt roa npta
    roic roe_yearly roa2_yearly debt_to_assets assets_to_eqt dp_assets_to_eqt
    ca_to_assets nca_to_assets tbassets_to_totalassets int_to_talcap
    eqt_to_talcapital currentdebt_to_debt longdeb_to_debt ocf_to_shortdebt
    debt_to_eqt eqt_to_debt eqt_to_interestdebt tangibleasset_to_debt
    tangasset_to_intdebt tangibleasset_to_netdebt ocf_to_debt turn_days roa_yearly
    roa_dp fixed_assets profit_to_op q_saleexp_to_gr q_gc_to_gr q_roe q_dt_roe
    q_npta q_ocf_to_sales basic_eps_yoy dt_eps_yoy cfps_yoy op_yoy ebt_yoy
    netprofit_yoy dt_netprofit_yoy ocf_yoy roe_yoy bps_yoy assets_yoy eqt_yoy tr_yoy
    or_yoy q_sales_yoy q_op_qoq equity_yoy
    """.split()
)
INCOME_STOCK_FACTORS = (
    "undist_profit", "distable_profit", "distr_profit_shrhder",
)
INCOME_SPECIAL_FACTORS = ("basic_eps", "diluted_eps")
INCOME_FLOW_FACTORS = tuple(
    factor for factor in INCOME_RAW_FACTORS
    if factor not in (*INCOME_STOCK_FACTORS, *INCOME_SPECIAL_FACTORS)
)
CASHFLOW_STOCK_FACTORS = (
    "c_cash_equ_beg_period", "c_cash_equ_end_period",
    "end_bal_cash", "beg_bal_cash", "end_bal_cash_equ", "beg_bal_cash_equ",
)
CASHFLOW_FLOW_FACTORS = tuple(
    factor for factor in CASHFLOW_RAW_FACTORS if factor not in CASHFLOW_STOCK_FACTORS
)
# 存量只输出原值；每股收益保留累计季报，不用金额流量公式拼接TTM。
INCOME_FACTORS = tuple(
    f"{factor}_{suffix}"
    for factor in INCOME_FLOW_FACTORS
    for suffix in FLOW_SUFFIXES
) + tuple(
    f"{factor}_{quarter}"
    for factor in INCOME_SPECIAL_FACTORS
    for quarter in (1, 2, 3, 4)
) + INCOME_STOCK_FACTORS + INCOME_SPECIAL_FACTORS
CASHFLOW_FACTORS = tuple(
    f"{factor}_{suffix}"
    for factor in CASHFLOW_FLOW_FACTORS
    for suffix in FLOW_SUFFIXES
) + CASHFLOW_STOCK_FACTORS
# 查询层只对这些按公告日存储的财报字段执行前向填充。
FINANCIAL_FACTORS = frozenset(
    (*BALANCE_FACTORS, *INCOME_FACTORS, *CASHFLOW_FACTORS, *INDICATOR_FACTORS)
)


def first_shoot(
        data: pd.DataFrame,
        end_date_col: str = "end_date",
        ann_date_col: str = "f_ann_date",
        factors: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """逐字段接受报告期不倒退的有效值；同报告期修订允许更新，状态仅在内存中。"""
    if data.empty:
        return data.copy()
    if factors is None:
        factors = tuple(name for name in data if name not in {
            end_date_col, ann_date_col, "ann_date", "f_ann_date", "end_type",
            "ts_code", "report_type", "comp_type", "update_flag",
        })
    ordered = data.sort_values([ann_date_col, end_date_col], kind="stable")
    latest: dict[str, pd.Timestamp] = {}
    records = []
    for published, reports in ordered.groupby(ann_date_col, sort=True):
        record = {ann_date_col: published, end_date_col: reports[end_date_col].max()}
        for _, report in reports.iterrows():
            period = report[end_date_col]
            for factor in factors:
                value = pd.to_numeric(report.get(factor), errors="coerce")
                if pd.notna(value) and np.isfinite(value) and period >= latest.get(factor, pd.Timestamp.min):
                    record[factor] = float(value)
                    latest[factor] = period
        records.append(record)
    return pd.DataFrame(records).reindex(columns=[ann_date_col, end_date_col, *factors])


def process_flow(
        data: pd.DataFrame,
        factors: tuple[str, ...],
        ann_date_col: str = "f_ann_date",
        end_date_col: str = "end_date",
        end_type_col: str = "end_type",
        *,
        stock_factors: tuple[str, ...] = (),
        quarter_factors: tuple[str, ...] = (),
) -> pd.DataFrame:
    """每个公告时点计算一次TTM，仅用当时已知且两年内ffill的累计原料。

    季报后缀分别维护报告期，保留累计口径，不把半年/前三季度改成单季差分。
    年报TTM等于当年累计；其余为本期累计+上年年报-上年同期，任一缺失即NULL。
    存量只保留原值，非可加字段只保留原值和累计季报；均不生成TTM。
    两年限制仅裁剪TTM原料，不清空逐字段报告期状态；不读取未来公告或修订。
    """
    reported_factors = tuple(dict.fromkeys((*factors, *stock_factors, *quarter_factors)))
    generated = [f"{factor}_{suffix}" for factor in factors for suffix in FLOW_SUFFIXES]
    generated.extend(f"{factor}_{quarter}" for factor in quarter_factors for quarter in (1, 2, 3, 4))
    generated.extend((*stock_factors, *quarter_factors))
    columns = list(data.columns) + [name for name in generated if name not in data]
    if data.empty:
        return data.reindex(columns=columns).copy()
    ordered = data.sort_values([ann_date_col, end_date_col], kind="stable")
    latest: dict[tuple[str, int], pd.Timestamp] = {}
    current_periods: dict[str, pd.Timestamp] = {}
    known: dict[tuple[str, pd.Timestamp], tuple[float, pd.Timestamp]] = {}
    current_period = pd.Timestamp.min
    records = []
    for published, reports in ordered.groupby(ann_date_col, sort=True):
        cutoff = published-pd.DateOffset(years=2)
        known = {key: value for key, value in known.items() if value[1] >= cutoff}
        current_period = max(current_period, reports[end_date_col].max())
        record = reports.iloc[-1].to_dict()
        for factor in reported_factors:
            if factor in record:
                record[factor] = np.nan
        for _, report in reports.iterrows():
            period = report[end_date_col]
            report_quarter = int(report[end_type_col])
            for factor in reported_factors:
                value = pd.to_numeric(report.get(factor), errors="coerce")
                if pd.isna(value) or not np.isfinite(value):
                    continue
                key = factor, report_quarter
                if factor not in stock_factors and period >= latest.get(key, pd.Timestamp.min):
                    record[f"{factor}_{report_quarter}"] = float(value)
                    latest[key] = period
                    if factor in factors:
                        known[factor, period] = float(value), published
                if period >= current_periods.get(factor, pd.Timestamp.min):
                    current_periods[factor] = period
                    if factor in record:
                        record[factor] = float(value)
        for factor in factors:
            current = known.get((factor, current_period), (np.nan, published))[0]
            if current_period.quarter == 4:
                result = current
            else:
                annual_period = pd.Timestamp(current_period.year-1, 12, 31)
                prior_period = current_period-pd.DateOffset(years=1)
                annual = known.get((factor, annual_period), (np.nan, published))[0]
                prior = known.get((factor, prior_period), (np.nan, published))[0]
                result = current+annual-prior
            record[f"{factor}_ttm"] = result if np.isfinite(result) else np.nan
        records.append(record)
    return pd.DataFrame(records).reindex(columns=columns)


def prepare(
        df: pd.DataFrame,
        ann_date_col: str,
        *,
        comp_type: str | None = None,
) -> pd.DataFrame:
    """按实际公告日保留历史，先选更新标记，再选较晚的原公告版本。

    同版本存在不同公司口径时，只有数值冲突组才使用供应商行业对应的口径。
    不全局过滤历史口径，不混入母公司、单季或调整报表，不按返回顺序选值。
    """
    data = df.reset_index(drop=True).copy()
    data[ann_date_col] = pd.to_datetime(data[ann_date_col], errors="coerce")
    if ann_date_col != "ann_date" and "ann_date" in data:
        announced = pd.to_datetime(data["ann_date"], errors="coerce")
        data[ann_date_col] = data[ann_date_col].fillna(announced)
        data[ann_date_col] = data[ann_date_col].where(
            announced.isna() | data[ann_date_col].ge(announced), announced,
        )
    data["end_date"] = pd.to_datetime(data["end_date"], errors="coerce")
    if data[[ann_date_col, "end_date"]].isna().any().any():
        raise ValueError("财报存在无效公告日期或报告期")
    data["end_type"] = data["end_date"].dt.strftime("%m%d").map({"0331": 1, "0630": 2, "0930": 3, "1231": 4})
    data = data.dropna(subset=["end_type"])
    if "report_type" in data:
        data["report_type"] = data["report_type"].astype("string").str.strip()
        # 1为默认合并报表；母公司、单季及调整口径不能混入同一累计序列。
        data = data[data.report_type.eq("1")].copy()
    if data.empty:
        return data.reset_index(drop=True)
    groups = [ann_date_col, "end_date"]
    if "ts_code" in data:
        groups.append("ts_code")
    if "update_flag" in data:
        flags = data["update_flag"].astype("string").str.strip()
        invalid = flags.notna() & ~flags.isin(("", "0", "1"))
        if invalid.any():
            raise ValueError("财报update_flag只能为0、1或空值")
        latest = flags.eq("1").fillna(False)
        has_latest = latest.groupby([data[name] for name in groups], dropna=False).transform("any")
        data = data.loc[latest | ~has_latest].copy()
        data["update_flag"] = flags.loc[data.index].fillna("")
    if ann_date_col != "ann_date" and "ann_date" in data:
        announced = pd.to_datetime(data["ann_date"], errors="coerce").fillna(data[ann_date_col])
        newest = announced.groupby([data[name] for name in groups], dropna=False).transform("max")
        data = data.loc[announced.eq(newest)].copy()
    metadata = {"ts_code", "ann_date", "f_ann_date", "end_date", "end_type",
                "report_type", "comp_type", "update_flag"}
    values = [name for name in data if name not in metadata]
    candidates = data[values].apply(pd.to_numeric, errors="coerce")
    candidates = candidates.where(np.isfinite(candidates))
    conflicts = candidates.groupby([data[name] for name in groups], dropna=False).nunique().gt(1)
    if conflicts.any().any() and comp_type is not None and "comp_type" in data:
        preferred = data["comp_type"].astype("string").str.strip().eq(comp_type).fillna(False)
        has_preferred = preferred.groupby([data[name] for name in groups], dropna=False).transform("any")
        conflicted = conflicts.any(axis=1).reindex(pd.MultiIndex.from_frame(data[groups])).to_numpy()
        discarded = conflicted & has_preferred & ~preferred
        if discarded.any():
            for key, reports in data.loc[conflicted & has_preferred].groupby(groups, dropna=False, sort=True):
                fields = conflicts.loc[key].loc[lambda row: row].index.tolist()
                logger.warning(
                    f"财报重复口径消歧：分组={dict(zip(groups, key))}，"
                    f"候选公司类型={sorted(reports.comp_type.astype(str).unique())}，"
                    f"采用行业对应公司类型={comp_type}，冲突字段={fields}"
                )
            data = data.loc[~discarded].copy()
            candidates = candidates.loc[data.index]
            conflicts = candidates.groupby([data[name] for name in groups], dropna=False).nunique().gt(1)
    if conflicts.any().any():
        details = [
            {**dict(zip(groups, key)), "fields": row.index[row].tolist()}
            for key, row in conflicts.loc[conflicts.any(axis=1)].iterrows()
        ]
        raise ValueError(f"财报同版本仍有冲突，无法按公司口径消歧：{details}")
    # 只合并同一优先级版本的相同值或互补缺失，不从已淘汰版本回补空字段。
    data = pd.concat([data.drop(columns=values), candidates], axis=1).copy()
    for name in ("ann_date", "comp_type", "update_flag"):
        if name in data and name != ann_date_col:
            data[name] = data[name].astype("string").fillna("")
    order = groups + [name for name in ("ann_date", "comp_type", "update_flag") if name in data and name not in groups]
    data = data.sort_values(order, kind="stable")
    data = data.groupby(groups, dropna=False, sort=False).first().reset_index()
    return data.sort_values([ann_date_col, "end_date"], kind="stable").reset_index(drop=True)


def fetch_financial(
        worker: StockWorker,
        endpoint: Callable[..., pd.DataFrame],
        endpoint_name: str,
        code: str,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp,
        ann_date_col: str,
        flow_factors: tuple[str, ...] | None = None,
        stock_factors: tuple[str, ...] = (),
        quarter_factors: tuple[str, ...] = (),
) -> pd.DataFrame:
    """回放截至截止日的全部历史重建内存报告期，只输出本次区间，不持久化状态。"""
    fields = ["ts_code", "ann_date", ann_date_col, "end_date", "update_flag"]
    params = {"ts_code": code, "end_date": end_date.strftime("%Y%m%d")}
    if endpoint_name != "fina_indicator":
        fields.extend(("report_type", "comp_type"))
        params["report_type"] = "1"
    fields.extend(worker.factors if flow_factors is None else (*flow_factors, *stock_factors, *quarter_factors))
    params["fields"] = ",".join(dict.fromkeys(fields))
    # 报告期水位不能随两年TTM原料过期；增量同样需要早期历史，不能只回看一两年。
    response = worker.paginator.fetch(
        endpoint,
        params=params,
        page_size=100,
        context=f"{worker}[{code}].{endpoint_name}",
        stop_on_short=False,
    )
    if response.empty:
        return worker.EMPTY
    response = response.copy()
    published = pd.to_datetime(response[ann_date_col], errors="coerce")
    if ann_date_col != "ann_date" and "ann_date" in response:
        announced = pd.to_datetime(response["ann_date"], errors="coerce")
        published = published.fillna(announced)
        published = published.where(announced.isna() | published.ge(announced), announced)
    # 两个公告日期取较晚者为可用时点，未来版本必须在选择前排除。
    response = response[published.le(end_date) | published.isna()]
    if response.empty:
        return worker.EMPTY
    comp_type = get_company_types().get(code) if endpoint_name != "fina_indicator" else None
    data = prepare(response, ann_date_col, comp_type=comp_type)
    if data.empty:
        return worker.EMPTY
    if flow_factors is not None:
        data = process_flow(data, flow_factors, ann_date_col=ann_date_col,
                            stock_factors=stock_factors, quarter_factors=quarter_factors)
    else:
        data = first_shoot(data, ann_date_col=ann_date_col, factors=worker.factors)
    data = data.rename(columns={ann_date_col: TIME_COLUMN})[
        [TIME_COLUMN, *worker.factors]
    ]
    return worker.melt(
        code,
        data,
        start_date=start_date,
        end_date=end_date,
    )


class StockBalanceSheetWorker(StockWorker):
    """通过 balancesheet 接口更新资产负债表。"""

    def __str__(self) -> str:
        """返回资产负债表 Worker 标识。"""
        return "<StockBalanceSheetWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回资产负债表因子。"""
        return BALANCE_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """获取一只股票的资产负债表。"""
        return fetch_financial(
            self,
            get_pro().balancesheet,
            "balancesheet",
            code,
            start_date,
            end_date,
            "f_ann_date",
        )


class StockIncomeWorker(StockWorker):
    """通过 income 接口更新利润表报告期值和 TTM 值。"""

    def __str__(self) -> str:
        """返回利润表 Worker 标识。"""
        return "<StockIncomeWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回利润表报告期和 TTM 因子。"""
        return INCOME_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """获取一只股票的利润表并计算报告期和 TTM 因子。"""
        return fetch_financial(
            self,
            get_pro().income,
            "income",
            code,
            start_date,
            end_date,
            "f_ann_date",
            INCOME_FLOW_FACTORS,
            INCOME_STOCK_FACTORS,
            INCOME_SPECIAL_FACTORS,
        )


class StockCashflowWorker(StockWorker):
    """通过 cashflow 接口更新现金流报告期值和 TTM 值。"""

    def __str__(self) -> str:
        """返回现金流量表 Worker 标识。"""
        return "<StockCashflowWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回现金流报告期和 TTM 因子。"""
        return CASHFLOW_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """获取一只股票的现金流量表并计算报告期和 TTM 因子。"""
        return fetch_financial(
            self,
            get_pro().cashflow,
            "cashflow",
            code,
            start_date,
            end_date,
            "f_ann_date",
            CASHFLOW_FLOW_FACTORS,
            CASHFLOW_STOCK_FACTORS,
        )


class StockFinaIndicatorWorker(StockWorker):
    """通过 fina_indicator 接口更新财务指标。"""

    def __str__(self) -> str:
        """返回财务指标 Worker 标识。"""
        return "<StockFinaIndicatorWorker>"

    @property
    def factors(self) -> tuple[str, ...]:
        """返回财务指标因子。"""
        return INDICATOR_FACTORS

    def fetch_one(
            self,
            code: str,
            *,
            start_date: pd.Timestamp,
            end_date: pd.Timestamp,
    ) -> pd.DataFrame:
        """获取一只股票的财务指标。"""
        return fetch_financial(
            self,
            get_pro().fina_indicator,
            "fina_indicator",
            code,
            start_date,
            end_date,
            "ann_date",
        )
