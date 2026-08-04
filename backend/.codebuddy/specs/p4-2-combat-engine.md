# P4-2 Combat Engine

## 定位

`src/engine/combat/combat.py` — 回合制战斗引擎，引用 `src/rules/dnd_rules.py` 做骰子裁决。

## 流程

```
1. 先攻排序 → 每人掷 1d20 + dex_mod，从高到低排序
2. 回合循环：
   a. 按先攻顺序，每人攻击一名对方队伍成员
   b. 命中判定 → attack_roll(atk_bonus, target.ac, damage_dice)
   c. 命中 → target.hp -= damage
   d. HP <= 0 → 死亡，移除
   e. 一方全灭 → 战斗结束
3. 返回 winner + survivors + combat_log
```

## Schema

```python
class CombatParticipant(BaseModel):
    name: str
    team: str       # "party" | "enemy"
    hp: int
    max_hp: int
    ac: int
    atk_bonus: int
    damage_dice: str
    dex_mod: int
```

## 护栏

- 空参与者 → 直接返回
- 单方战斗 → 直接判定 winner
- HP 不低于 0
- 每轮日志记录攻击细节

## 测试

- 空参与者 → winner=None
- 2v2 战斗直到一方全灭
- 先攻排序正确
- 高 AC 角色难被命中
- 重击伤害翻倍
