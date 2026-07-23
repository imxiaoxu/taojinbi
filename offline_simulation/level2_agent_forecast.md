# Level 2 Agent 离线挽回预测

## 一、历史目标人群

- 五表原始记录行数：{'event_log.csv': 40250, 'game_behavior_log.csv': 8874, 'intervention_test.csv': 2000, 'user_profile.csv': 7000, 'version_exposure.csv': 7000}
- `standard` Level 2 启动用户：295
- `standard` Level 2 完成用户：145
- 历史基线通过率：49.15%
- `standard` Level 2 至少一次失败用户：210
- `standard` Level 2 第二次及以上失败用户：84
- `standard` Level 2 退出用户：150

## 二、情景估算

预测明细见 `level2_agent_forecast.csv`。以首次 Level 2 失败的 210 名用户为例：

- 使用 `tutorial_popup` 的历史 PSM-DID 游戏完成效应 `+16.30pp`，对应预计新增完成约 **34.2 人**。
- 使用 `game_difficulty_reduced` 的历史 PSM-DID 游戏完成效应 `+23.05pp`，对应预计新增完成约 **48.4 人**。
- 对已经发生的 150 名 Level 2 退出用户，若仅将降难度效应作间接换算，则同一历史窗口约为 **33.5 至 35.6 名**潜在可挽回完成用户，中心估计 **34.6 名**。

## 三、解释边界

1. 上述数字是“干预效应 x 历史可触达人群”的**情景规划值**，不是已证明的 Agent 线上收益。
2. `intervention_test.csv` 的 PSM-DID 对象是历史干预用户，并非 `standard` Level 2 失败用户；外推需要由新 A/B 验证。
3. 教程、切换 Guided Mode、降难度在 Agent 计划中不可将 uplift 相加，否则会重复计量。首期应把它们作为不同策略臂或由 Agent 选择的联合策略，使用整体 Agent vs Holdout 的 ITT 衡量。
4. 当前原始游戏表仅代表 treatment 内游戏用户，不能从该表推断版本层的因果效果。

## 四、样本量

见 `level2_sample_size.csv`。按历史基线、双主比较 Bonferroni 校正（双侧 alpha=0.025）和 80% power，检测 5pp 提升约需每组 1898 名完整用户、三组共 5694 名。
