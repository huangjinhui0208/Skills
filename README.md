# 自主创建的skills or workflow

目的：完成scb的工作

## ZhaiShuai_skill

这是根据赵老师平常的工作态度和工作情况撰写的skill

主要是为了模仿赵老师的工作方式来解决问题。

## autonomous-driving-temporal-safety-analysis

面向 CARLA/Apollo 自动驾驶实验的“时间正确性—物理安全传播”分析 skill。它按照六层方法组织延迟注入、时序退化、因果响应、动态 deadline、距离传播和物理安全结局，并强制区分 observed/data 与 model/predicted 结果。

- 源码目录：`autonomous-driving-temporal-safety-analysis/`
- 可安装包：`autonomous-driving-temporal-safety-analysis/dist/autonomous-driving-temporal-safety-analysis.skill`
- 主要能力：原始日志与 Trace 审计、Apollo record 解析数据画像、墙钟速度积分、动态 deadline、timing slack、distance debt、制动余量及碰撞归因
- 关键口径：主响应距离统一使用 `t1→t2` 墙钟速度梯形积分；碰撞 run 不使用模型补齐完整观测停车距离
