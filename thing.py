import nbtlib


class RelaxedParser(nbtlib.Parser):
    def collect_tokens_until(self, token_type):
        while True:
            try:
                yield from super().collect_tokens_until(token_type)
                return
            except nbtlib.InvalidLiteral as exc:
                if exc.args[1].startswith("Expected comma"):
                    yield self.current_token


snbt = """
{
	version: 13
	default_reward_team: false
	default_consume_items: false
	default_autoclaim_rewards: "disabled"
	default_quest_shape: "circle"
	default_quest_disable_jei: false
	emergency_items_cooldown: 300
	drop_loot_crates: false
	loot_crate_no_drop: {
		passive: 4000
		monster: 600
		boss: 0
	}
	disable_gui: false
	grid_scale: 0.5d
	pause_game: false
	lock_message: ""
}
"""

print(RelaxedParser(nbtlib.tokenize(snbt)).parse())
