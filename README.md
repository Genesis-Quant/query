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
