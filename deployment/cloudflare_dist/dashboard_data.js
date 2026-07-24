window.DASHBOARD_DATA = {
  meta: { version: 'offline-baseline-v1', generated_at: '2026-07-16', raw_files: ['event_log.csv', 'game_behavior_log.csv', 'intervention_test.csv', 'user_profile.csv', 'version_exposure.csv'] },
  kpis: [
    { label:'standard Level 2 基线通过率', value:'49.15%', desc:'145 / 295 名启动用户', tone:'warning' },
    { label:'Level 2 至少一次失败用户', value:'210', desc:'首期 Agent 可触达人群', tone:'negative' },
    { label:'Level 2 立即退出用户', value:'150', desc:'历史窗口内 standard 模式', tone:'negative' },
    { label:'首期实验样本量', value:'5,694', desc:'检测 5pp 提升，三组总入组', tone:'' }
  ],
  level2_flow: [
    {label:'Level 2 启动',users:295,note:'standard 模式',color:'#1e63a9'},
    {label:'Level 2 通过',users:145,note:'通过率 49.15%',color:'#2f8a57'},
    {label:'至少一次失败',users:210,note:'失败率 71.19%',color:'#c3484b'},
    {label:'第二次及以上失败',users:84,note:'Agent 重点触发层',color:'#d88816'},
    {label:'Level 2 退出',users:150,note:'退出用户',color:'#c3484b'},
    {label:'历史游戏完成',users:117,note:'standard overall',color:'#0f9ba8'}
  ],
  variants: [
    {name:'guided_mode',completion:70.67,exit:29.33,color:'green'},
    {name:'easy_mode',completion:36.00,exit:64.00,color:'cyan'},
    {name:'standard',completion:29.25,exit:70.75,color:'red'}
  ],
  monitor: [
    {metric:'入组用户数与 1:1:1 分流',grain:'小时 / 按 strata',rule:'SRM p < 0.01 暂停扩量'},
    {metric:'Level 2 通过率',grain:'日 / 成熟 24h 队列',rule:'Agent vs Holdout 主指标；目标 +5pp'},
    {metric:'游戏完成率',grain:'日 / 成熟 24h 队列',rule:'Agent 不能低于固定规则组'},
    {metric:'即时退出率',grain:'日 / 入组后 10 分钟',rule:'较 Holdout 恶化 > 3pp 暂停'},
    {metric:'Dify P95 与工具失败率',grain:'5 分钟',rule:'P95 > 1.5s 或失败率 > 1% 告警'},
    {metric:'7 日留存 / 加购 / 下单',grain:'日 / 成熟 7 天队列',rule:'次指标；不提前解读未成熟队列'}
  ],
  forecast: [
    {scenario:'首次失败后教程',eligible:210,effect:16.30,low:33.1,high:35.3},
    {scenario:'首次失败后降难度',eligible:210,effect:23.05,low:46.9,high:49.9},
    {scenario:'第二次失败后降难度',eligible:84,effect:23.05,low:18.8,high:19.9},
    {scenario:'退出用户间接换算',eligible:150,effect:23.05,low:33.5,high:35.6}
  ],
  roi: [
    {strategy:'首次失败后教程',eligible:210,orderEffect:8.71,incrementalOrders:18.3,grossContribution:146.4,variableCost:105.0,roi:39.4,breakEvenFixedCost:41.4},
    {strategy:'首次失败后降难度',eligible:210,orderEffect:12.61,incrementalOrders:26.5,grossContribution:211.8,variableCost:105.0,roi:101.7,breakEvenFixedCost:106.8}
  ],
  monitor_runbook: [
    {alert:'分流异常 / SRM p < 0.01',check:'入组事件量、去重、固定分桶',owner:'前端 / 实验平台 / 数据',action:'暂停扩量并对账',recovery:'连续 2 小时恢复且 p >= 0.01'},
    {alert:'前端展示失败率 > 0.5%',check:'Backend 响应、Schema、组件和展示回执',owner:'前端 / 后端',action:'切换静态提示',recovery:'连续 2 个窗口低于 0.5%'},
    {alert:'Dify P95 > 1.5s',check:'Proxy、Workflow 节点和模型耗时',owner:'Agent / 后端',action:'超时终止并静态兜底',recovery:'P95 <= 1.5s 且超时率 < 1%'},
    {alert:'Dify 返回格式不合法',check:'workflow_version、原始响应、JSON Schema',owner:'Agent / 后端',action:'拒绝非法动作并兜底',recovery:'计划校验通过率 >= 99.5%'},
    {alert:'工具失败率 > 1%',check:'action_type、error_code、幂等键和限流',owner:'后端 / 业务服务',action:'受控重试或 pending',recovery:'失败率 <= 1%，重复执行率为 0'},
    {alert:'核心效果或护栏恶化',check:'成熟队列、数据完整性、策略和游戏版本',owner:'数据 / Agent / 游戏产品',action:'降流或暂停 Agent',recovery:'护栏恢复且根因复核通过'},
    {alert:'指标为 0 / 突增 / 完全一致',check:'ODS-DWD-宽表-BI 四层对账',owner:'数据 / BI',action:'标记数据异常，禁止解读',recovery:'三层对账误差 < 0.5%'},
    {alert:'T+7 指标未更新',check:'成熟队列、调度、Join 和分区',owner:'数据',action:'标记未成熟或延迟',recovery:'成熟人数与入组台账一致'}
  ],
  readiness: [
    {item:'A/B 分组、样本量、成功与停止规则',status:'已完成',state:'ready',next:'在实验平台创建 coin_game_level2_agent_v1 并锁定分桶'},
    {item:'前端事件与 trace_id 规范',status:'设计完成',state:'ready',next:'前端实现、联调和事件完整率验收'},
    {item:'Dify / Backend 决策与工具执行',status:'接口已定义',state:'pending',next:'接入生产 Proxy、业务工具、幂等与 fallback'},
    {item:'数仓与实验宽表',status:'字段已定义',state:'pending',next:'建表、T+1/T+7 回填、配置 BI 数据集'},
    {item:'实时 Agent / A-B 数据',status:'尚未产生',state:'blocked',next:'需完成灰度发布后由真实事件流填充'}
  ]
};
