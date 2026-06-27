p = r'E:\Projects\simgameworld\backend\src\pack\loader.py'
c = open(p, encoding='utf-8').read()

# Add validate_rule_set
c = c.replace(
    '    def _load_meta(self, pack_dir: Path) -> MetaYaml:',
    '    def _validate_rule_set(self, rule_set: str) -> None:\n        if rule_set not in {"dnd_5e_srd"}:\n            raise ValueError(f"Unsupported: {rule_set}")\n\n    def _load_meta(self, pack_dir: Path) -> MetaYaml:'
)

# Add pump_lore + validate to load()
c = c.replace(
    '        meta = self._load_meta(pack_dir)\n\n        return WorldState(',
    '        meta = self._load_meta(pack_dir)\n        self._validate_rule_set(meta.rule_set)\n        self.pump_lore(pack_dir, pack_name)\n\n        return WorldState('
)

open(p, 'w', encoding='utf-8', newline='\n').write(c)

# Verify
c2 = open(p, encoding='utf-8').read()
print('Has pump_lore in load:', 'pump_lore(pack_dir' in c2)
print('Has validate_rule_set:', '_validate_rule_set' in c2)
