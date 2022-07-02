# 数据分析流程

## 数据获取

1. 获取当前用户1000场比赛的id
2. match_history中包含比赛id和胜负情况
3. 根据比赛id获取己方玩家的summon_id
4. 根据summon_id获取该场比赛前20场的战绩信息
5. 当前用户每场比赛记录一条数据，数据内容为

```json
[
    {
        match_id: int,
        win: bool,
        members: [
            {
                summon1_id: [{kill: int ...}],
                summon2_id: [{kill: int ...}],
            }
        ]
    }
]
```
