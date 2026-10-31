"""初始化项目唯一的 Tushare 模块和进程内股票元数据。"""

from functools import cache
from typing import Any

import pandas as pd
import tushare as ts

from query.config import TUSHARE_TOKEN

from .logging import logger

_INDUSTRY_TO_SECTOR = {
    "煤炭开采": "能源",
    "石油加工": "能源",
    "石油开采": "能源",
    "石油贸易": "能源",
    "焦炭加工": "能源",
    "其他建材": "材料",
    "农药化肥": "材料",
    "化工原料": "材料",
    "化纤": "材料",
    "塑料": "材料",
    "小金属": "材料",
    "普钢": "材料",
    "染料涂料": "材料",
    "林业": "材料",
    "橡胶": "材料",
    "水泥": "材料",
    "特种钢": "材料",
    "玻璃": "材料",
    "矿物制品": "材料",
    "造纸": "材料",
    "钢加工": "材料",
    "铅锌": "材料",
    "铜": "材料",
    "铝": "材料",
    "陶瓷": "材料",
    "黄金": "材料",
    "专用机械": "工业",
    "仓储物流": "工业",
    "公共交通": "工业",
    "公路": "工业",
    "农用机械": "工业",
    "化工机械": "工业",
    "工程机械": "工业",
    "建筑工程": "工业",
    "批发业": "工业",
    "机场": "工业",
    "机床制造": "工业",
    "机械基件": "工业",
    "水运": "工业",
    "港口": "工业",
    "环境保护": "工业",
    "电器仪表": "工业",
    "电气设备": "工业",
    "空运": "工业",
    "纺织机械": "工业",
    "综合类": "工业",
    "航空": "工业",
    "船舶": "工业",
    "装修装饰": "工业",
    "路桥": "工业",
    "轻工机械": "工业",
    "运输设备": "工业",
    "铁路": "工业",
    "其他商业": "可选消费",
    "出版业": "可选消费",
    "商品城": "可选消费",
    "商贸代理": "可选消费",
    "家居用品": "可选消费",
    "家用电器": "可选消费",
    "广告包装": "可选消费",
    "影视音像": "可选消费",
    "摩托车": "可选消费",
    "文教休闲": "可选消费",
    "旅游景点": "可选消费",
    "旅游服务": "可选消费",
    "服饰": "可选消费",
    "汽车整车": "可选消费",
    "汽车服务": "可选消费",
    "汽车配件": "可选消费",
    "电器连锁": "可选消费",
    "百货": "可选消费",
    "纺织": "可选消费",
    "酒店餐饮": "可选消费",
    "乳制品": "日常消费",
    "农业综合": "日常消费",
    "啤酒": "日常消费",
    "日用化工": "日常消费",
    "渔业": "日常消费",
    "白酒": "日常消费",
    "种植业": "日常消费",
    "红黄酒": "日常消费",
    "超市连锁": "日常消费",
    "软饮料": "日常消费",
    "食品": "日常消费",
    "饲料": "日常消费",
    "中成药": "医疗保健",
    "化学制药": "医疗保健",
    "医疗保健": "医疗保健",
    "医药商业": "医疗保健",
    "生物制药": "医疗保健",
    "保险": "金融",
    "多元金融": "金融",
    "证券": "金融",
    "银行": "金融",
    "IT设备": "信息技术",
    "互联网": "信息技术",
    "元器件": "信息技术",
    "半导体": "信息技术",
    "通信设备": "信息技术",
    "软件服务": "信息技术",
    "电信运营": "电信服务",
    "供气供热": "公用事业",
    "新型电力": "公用事业",
    "水力发电": "公用事业",
    "水务": "公用事业",
    "火力发电": "公用事业",
    "全国地产": "房地产",
    "区域地产": "房地产",
    "园区开发": "房地产",
    "房产服务": "房地产",
}

StockMetadata = tuple[tuple[str, ...], pd.DataFrame, dict[str, str]]
_stock_metadata: StockMetadata | None = None


@cache
def get_pro() -> Any:
    """按需初始化并缓存项目唯一的 Tushare Pro 客户端。"""
    if not TUSHARE_TOKEN:
        raise RuntimeError("缺少 TUSHARE_TOKEN，无法初始化 Tushare Pro API")
    ts.set_token(TUSHARE_TOKEN)
    client = ts.pro_api(TUSHARE_TOKEN)
    if client is None:
        raise RuntimeError("Tushare Pro API 初始化失败")
    return client


def _load_stock_metadata() -> StockMetadata:
    """从 Tushare 加载全市场股票代码和行业映射。"""
    client = get_pro()
    stock_frames: list[pd.DataFrame] = []
    for status in ("L", "D", "P"):
        response = client.stock_basic(
            exchange="",
            list_status=status,
            fields="ts_code,industry",
        )
        if response is None:
            raise RuntimeError(f"stock_basic[{status}] 返回 None")
        if not isinstance(response, pd.DataFrame):
            raise TypeError(f"stock_basic[{status}] 返回值不是 DataFrame")
        required = {"ts_code", "industry"}
        if missing := required - set(response.columns):
            raise ValueError(
                f"stock_basic[{status}] 返回结果缺少列：{sorted(missing)}"
            )
        if not response.empty:
            stock_frames.append(response.loc[:, ["ts_code", "industry"]])

    if not stock_frames:
        raise RuntimeError("stock_basic 没有返回任何股票")

    stock_basic = pd.concat(stock_frames, ignore_index=True)
    stock_basic["ts_code"] = (
        stock_basic["ts_code"].astype("string").str.strip()
    )
    stock_basic["industry"] = (
        stock_basic["industry"].astype("string").str.strip()
    )
    stock_basic = (
        stock_basic.dropna(subset=["ts_code"])
        .loc[lambda frame: frame["ts_code"].ne("")]
        .drop_duplicates("ts_code", keep="first")
        .sort_values("ts_code")
        .reset_index(drop=True)
    )
    codes = tuple(stock_basic["ts_code"].astype(str))
    if not codes:
        raise RuntimeError("stock_basic 没有返回有效股票代码")

    stock_industries = stock_basic.rename(columns={"ts_code": "code"})
    code_to_industry = dict(
        zip(
            stock_industries["code"],
            stock_industries["industry"].map(_INDUSTRY_TO_SECTOR).fillna("工业"),
            strict=True,
        )
    )
    logger.success(f"Tushare Pro 初始化完成，共加载 {len(codes):,} 只股票")
    return codes, stock_industries, code_to_industry


def get_stock_metadata() -> StockMetadata:
    """首次读取时加载股票元数据，之后在当前 Python 进程中复用。"""
    global _stock_metadata
    if _stock_metadata is None:
        _stock_metadata = _load_stock_metadata()
    return _stock_metadata


def get_codes() -> tuple[str, ...]:
    """返回按需加载的全市场股票代码。"""
    return get_stock_metadata()[0]
