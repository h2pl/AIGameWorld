# P4-1 D20 规则库

## 定位

`src/rules/dnd_rules.py` — 纯数值函数库，零外部依赖（不看 State/LLM/DB）。
Engine 层引用它做确定性裁决：`from src.rules.dnd_rules import attack_roll, damage_roll`

## 函数清单

| 函数 | 签名 | 公式 |
|------|------|------|
| `roll_d20` | `() -> int` | `random.randint(1, 20)` |
| `resolve_check` | `(bonus: int, dc: int) -> CheckResult` | `1d20 + bonus vs dc` |
| `attack_roll` | `(atk_bonus: int) -> AttackResult` | 同 check，但 nat20/nat1 有特殊语义 |
| `damage_roll` | `(dice_str: str) -> int` | 解析 "2d6+3" 等 |
| `calculate_ac` | `(base: int, dex: int, shield: int=0, armor_type: str="light") -> int` | 按护甲类型限制敏捷 |
| `roll_initiative` | `(dex_mod: int) -> int` | `1d20 + dex_mod` |
| `saving_throw` | `(attr_mod: int, prof: int, dc: int) -> CheckResult` | `1d20 + attr_mod + prof vs dc` |
| `with_advantage` | `() -> int` | `max(2d20)` |
| `with_disadvantage` | `() -> int` | `min(2d20)` |

## 数据类型（dataclass）

```python
@dataclass
class CheckResult:
    success: bool
    roll: int
    bonus: int
    dc: int
    total: int
    is_critical: bool = False  # nat20
    is_fumble: bool = False    # nat1

@dataclass
class AttackResult(CheckResult):
    damage: int = 0
```

## 护栏

- nat20: 必定成功（Attack 时重击，damage_dice 翻倍）
- nat1: 必定失败
- 骰子结果 1-20 范围内
- 伤害骰负数保护（最小 0）

## 测试标准

- 掷 D20 1000 次全在 1-20 范围
- nat20 无论 DC 多高必定成功
- nat1 无论 DC 多低必定失败
- 伤害骰解析正确（含空格/+号/多骰）
- AC 计算中甲 dex 上限+2、重甲 dex 不参与
