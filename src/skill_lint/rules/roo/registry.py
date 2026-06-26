"""Import all Roo rule modules to trigger @register decorators.

Import this module anywhere you need the full RULE_REGISTRY populated.
"""

import skill_lint.rules.roo.frontmatter_rules  # noqa: F401
import skill_lint.rules.roo.description_rules  # noqa: F401
import skill_lint.rules.roo.body_rules  # noqa: F401
import skill_lint.rules.roo.cross_skill_rules  # noqa: F401
