# 自主创建的skills or workflow

目的：完成scb的工作

## ZhaiShuai_skill

这是根据赵老师平常的工作态度和工作情况撰写的skill

主要是为了模仿赵老师的工作方式来解决问题。

## autonomous-driving-temporal-safety-analysis

面向 CARLA/Apollo 自动驾驶实验的 TCPS-PA Diagnostic Protocol v2。它把六层方法实现为可执行的 Claim–Evidence 推理系统：先检查证据类型、前置 claim、反证与 defeater，再决定每层 verdict、置信度上限和允许使用的结论语言；同时强制区分 observed/data 与 model/predicted 结果。

- 源码目录：`autonomous-driving-temporal-safety-analysis/`
- 可安装包：`autonomous-driving-temporal-safety-analysis/dist/autonomous-driving-temporal-safety-analysis.skill`
- 主要能力：原始日志与 Trace 审计、Apollo record 解析数据画像、Claim Graph、Evidence Ledger、Defeater Ledger、语义 argument validation、墙钟速度积分、deadline/debt 证据资格审计和受约束的碰撞归因
- 关键口径：主响应距离统一使用 `t1→t2` 墙钟速度梯形积分；模型/回溯 deadline 不得伪装成独立需求，碰撞 run 不使用模型补齐完整观测停车距离
