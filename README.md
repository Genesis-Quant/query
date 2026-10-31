# Query

独立的 DolphinDB 因子查询 DSL 与数据更新工具。Python 模块为 `query`，发行包为 `query`。
核心代码提取自 Arena Runtime `eeebfe417aa999fa1e386cbd62b74326a5dab66c` 的查询及窄表 Workers；不依赖或加载 `arena-runtime`。

仅处理 `time / code / factor / value` 窄表，不包含分红、任意宽表、回测、报告或消息推送。

## 使用

```python
from query import DolphinSettings, FactorQuery, compile, create_session, execute_query

# 纯本地编译，不写入服务端模块目录。
script = compile()
settings = DolphinSettings.from_env()
session = create_session(settings)  # 连接成功后先执行已编译 DOS。
try:
    with execute_query({
        "start_date": "2026-04-30",
        "end_date": "2026-05-08",
        "lookback": "P110D",
        "lookforward": "P20D",
        "codes": ["600000.SH"],
        "factors": ["close"],
        "derivatives": {
            "next_close": {
                "type": "TS", "op": "unary.shift",
                "fields": {"col": "close"}, "params": {"periods": -1},
            },
        },
    }, session=session, settings=settings) as result:
        frame = result.data
finally:
    session.close()
```

不使用 `use query`，不需要服务端安装 `query.dos` 或 `common.dos`。底层 TA 算子仍使用 DolphinDB 自带的 `ta` 模块。
`lookback` / `lookforward` 是非负日历时长，默认 0；只扩大计算输入，数据和日历严格裁回原始闭区间。
空 `codes` 沿用全市场股票含义，通过 Tushare L/D/P 股票元数据取得候选；显式 codes 不访问 Tushare。
`source_data`、`computed_data`、`filtered_data` 保留原计算域，`.data` 和 `.calendar` 只包含输出域。
自建连接由结果关闭，借用连接只清理自己的结果对象，不关闭连接。查询允许指定窄表中的自定义因子；`available_factors()` 是 Worker 可产出字段目录，不是自定义表的限制。

## 固定证券字段 `factor@code`

普通字段 `close` 读取每一行证券自己的值；`close@000852.SH` 读取中证 1000 当天的值，并广播到请求截面的所有证券。既可放进 `factors` 直接输出，也可作为任意算符的字符串操作数：

```python
derivatives = {
    "index_return": {
        "type": "DIRECT", "op": "binary.div",
        "fields": {"left": "pct_chg@000852.SH", "right": 100.0},
    },
    "excess_return": {
        "type": "DIRECT", "op": "binary.sub",
        "fields": {
            "left": {
                "type": "TS", "op": "unary.pct_change",
                "fields": {"col": "close"}, "params": {"periods": 1},
            },
            "right": "index_return",
        },
    },
}
```

引用使用同一指定窄表和计算区间；外部证券不加入 `codes`，不增加面板行，也不参与 CS 排名。TS 窗口仍沿每只请求证券的完整日期轴计算，不跳过引用缺失日。`pct_chg` 按百分数存储，上例除以 100 转小数收益率。

引用在外部证券自己的时间线上沿用基础字段的默认填充，然后按日期广播：

- 行情、自定义字段：保留 NULL，不隐式前向填充。
- `is_st`：缺失填 0，不把某次 ST 状态前向延续。
- 财务字段：只把计算区间内的公告事件前向填充，区间前数据需通过 `lookback` 显式加载。
- 行业字段：只对计算区间内的行业事件前向填充，首次事件之前保持 NULL。
- `weight_...`：只使用计算区间内的快照，快照日未出现的证券填 0，快照之间前向填充；首次快照之前保持 NULL。

普通字段和 `factor@code` 都不读取计算起点前的历史记录或权重快照，不设置初始值。需要更多历史时显式扩大 `lookback`；它扩大的是计算区间，不改变输出区间。计算区间头部仍缺失的行业、财务和权重值保持 NULL，不用未来数据回填。

事件可以发生在非交易日，但引用的事件行不会增加原面板的行域。未来事件不回填过去，`lookforward` 不扩展输出日期。引用缺失与真实 0 不混淆；同一证券/基础字段/日期有多条记录时明确报错。`@` 是固定证券引用的保留分隔符，只允许一个且两侧非空，不用它命名普通字段或派生列。

`build_factor_source(data, codes, factors, dates, start_time, end_time)` 内部以 `default` / `fixed_code` 两个分支构造数据，已删除 `seed_factors` 参数及全部历史补值逻辑；新增引用类型只扩展类型分发和对应构造器，不修改现有 DSL 算符。字段分类仍定义在原来的 Workers 中，查询编译直接复用已有常量，不另建字段目录。

## 多元回归

六个算符共用 `fields={"target": ..., "controls": [...]}`，每个结果仍是一列数值，不输出数组或矩阵：

| 类型 | op | 结果 | params |
| --- | --- | --- | --- |
| TS | `controls.rolling_alpha` | 当前窗口截距 | `window`, `min_periods=None`, `intercept=True` |
| TS | `controls.rolling_beta` | 当前窗口指定解释变量系数 | 同上，另有 `index=0` |
| TS | `controls.rolling_residual` | 当前观测在当前窗口拟合下的残差 | 同 alpha |
| CS | `controls.alpha` | 当前截面截距，广播到共同有效行 | `intercept=True` |
| CS | `controls.beta` | 当前截面指定解释变量系数，广播到共同有效行 | `intercept=True`, `index=0` |
| CS | `controls.residual` | 当前截面每个共同有效观测的残差 | `intercept=True` |

`controls` 按列表顺序输入，可混合连续数值与 BOOL、STRING、SYMBOL 分类变量。分类变量只用当前窗口/截面的共同有效样本独热编码，类别升序排列并删除首类；NULL 不成为一个类别。数值 NULL、NaN、正负无穷以及分类 NULL 的行共同排除，不补值。

`beta.index` 从 0 起算，指删除基准类别后的展开列，不包含截距；先按控制变量原顺序，再按分类值升序展开。数值常量列保留位置且系数为 0；只有一个有效类别的分类列不占位置；不存在的索引输出 NULL。分类类别变化会改变该索引含义，不使用未来类别来固定展开位置。正常拟合使用 SVD 伪逆，秩亏时取最小范数最小二乘解。

TS 按证券、日期排序，`on` 先筛选观测序列，`window` 按筛选后的行数计数；窗口内缺失行仍占位置，不跳过缺失向前凑样本。`min_periods` 为最少共同有效样本数，默认等于 `window`。不够时所有结果为 NULL；足够时，即使当前行缺失也可输出 alpha/beta，但当天 residual 为 NULL。`on=false/NULL` 行在恢复面板位置后仍为 NULL。

沿用原截面中性化的退化规则：没有有效控制列、单样本或有效样本数不大于活动控制列数加截距项数时，返回去均值回归，即 `alpha=avg(y)`、已有系数位置 `beta=0`、`residual=y-avg(y)`；这一退化规则也适用于 `intercept=False`。正常无截距回归的 alpha 为 0。CS 无效行的全部输出为 NULL。

```python
derivatives = {
    "market_return": {
        "type": "TS", "op": "unary.pct_change",
        "fields": {"col": "close@000852.SH"}, "params": {"periods": 1},
    },
    "daily_return": {
        "type": "TS", "op": "unary.pct_change",
        "fields": {"col": "close_hfq"}, "params": {"periods": 1},
    },
    "daily_residual": {
        "type": "TS", "op": "controls.rolling_residual",
        "fields": {"target": "daily_return", "controls": ["market_return"]},
        "params": {"window": 63, "min_periods": 63, "intercept": True},
    },
    "residual_volatility": {
        "type": "TS", "op": "unary.rolling_std",
        "fields": {"col": "daily_residual"},
        "params": {"window": 63, "min_periods": 63},
    },
}
```

上例统计的是每日各自滚动拟合的当天残差序列，而不是用当天系数重新计算当前窗口全部历史残差。需用 `lookback` 显式覆盖收益、回归和后续统计的预热区间；不要把预热 NULL 填 0。相同输入、窗口、有效样本要求、截距和 `on` 的 TS alpha/beta/residual 共用拟合结果；既有 `binary.rolling_alpha/beta/residual` 不变。

各公开 DOS 函数直接接收原始 `target, controls` 和对应参数：`ts_controls_rolling_alpha/residual(target, controls, window, min_periods, intercept)`，beta 末尾另加 `index`；CS 省略窗口参数。`controls` 是等行数、有序控制列的表。内部拟合结果不会作为公开算符输入。旧截面中性化名称已删除，不提供兼容别名；`controls.residual` 不自动去极值、标准化，也不能替代应用的完整因子预处理。

## 命令行

```bash
uv sync
uv run query compile --output /tmp/query.dos
uv run query workers --list-workers
uv run query workers daily daily-basic adj-factor
uv run query workers index-daily --index-code 000300.SH --start-date 2026-01-01 --end-date 2026-01-31 --dry-run
uv run query workers index-weight --index-code 000300.SH
uv run query workers all --end-date 2026-10-09
```

`python -m query` 提供相同命令。Workers 保留原分页、重试、限流、数据库增量水位、覆盖回抓和结构化结果行为。
`--dry-run` 抓取及校验但不创建 writer、不写库；`--overwrite` 忽略增量水位并追加相同键的最新值，不先删除旧记录。

库导入不读取 `.env`，CLI `workers` 在启动时读取当前目录 `.env`。配置：

- `DOLPHINDB_ENDPOINTS`：逗号分隔的 host:port，兼容旧 `DOLPHIN_HOST` / `DOLPHIN_PORT`。
- 查询账号：`DOLPHINDB_USERNAME` / `DOLPHINDB_PASSWORD`，兼容 `DOLPHIN_RUNTIME_USERNAME` / `DOLPHIN_RUNTIME_PASSWORD`。
- 写入账号：`DOLPHINDB_WORKER_USERNAME` / `DOLPHINDB_WORKER_PASSWORD`，兼容 `DOLPHIN_WORKER_USERNAME` / `DOLPHIN_WORKER_PASSWORD`；不会退回查询账号。
- `DOLPHIN_CORE_DATABASE` / `DOLPHIN_CORE_TABLE`：指定因子窄表，默认 `dfs://CoreData` / `coreTable`。
- `TUSHARE_TOKEN`、`INDEX_CODES`、`DATA_START_DATE`：采集来源及默认范围。

独立数据更新命令不会在导入或测试时执行，不修改任何下游应用的环境。
