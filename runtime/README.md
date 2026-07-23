# Local Agent Runtime

本目录包含Week6离线回放所需的本地Agent Mock运行时，不依赖相邻Week5目录。

| 文件 | 用途 |
|---|---|
| `agent_workflow_mock.py` | Feature、Memory、Guardrail、Scene、Planning、Tool和Eval的本地Mock实现 |
| `build_raw_table_replay.py` | 从包内合成五表抽取六类场景并执行脱敏抽样回放 |

运行抽样回放：

```bash
python3 runtime/build_raw_table_replay.py
```

运行时只使用Python标准库，不调用真实淘金币业务接口。
