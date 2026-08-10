from dataclasses import dataclass, field


_TABLE_ALIASES = {
    "forum_messages": ("forum_chat_messages",),
    "forum_sessions": ("forum_chat_sessions",),
    "posts": ("post",),
    "users": ("user_mgmt",),
}


@dataclass(frozen=True)
class ExperimentSchema:
    """
    Introspected database schema for YSocial microblogging/forum experiments.

    The adapter keeps table discovery and capability checks in one place so the
    data handler can work across closely related experiment variants.
    """

    tables: frozenset[str]
    columns: dict[str, frozenset[str]] = field(default_factory=dict)

    def has_table(self, *table_names):
        return any(table_name in self.tables for table_name in table_names)

    def has_column(self, table_name, column_name):
        return column_name in self.columns.get(table_name, frozenset())

    def resolve_table(self, table_name):
        candidates = (table_name,) + _TABLE_ALIASES.get(table_name, ())
        for candidate in candidates:
            if candidate in self.tables:
                return candidate
        raise KeyError(f"Table '{table_name}' is not available in this dataset.")

    def supports_feature(self, feature_name):
        feature_name = feature_name.lower()

        feature_checks = {
            "microblog": lambda: self.has_table("post"),
            "forum": lambda: self.has_table("forum_chat_messages", "forum_chat_sessions"),
            "users": lambda: self.has_table("user_mgmt"),
            "posts": lambda: self.has_table("post"),
            "threads": lambda: self.has_table("post")
            and self.has_column("post", "comment_to")
            and self.has_column("post", "thread_id"),
            "follow_network": lambda: self.has_table("follow"),
            "reactions": lambda: self.has_table("reactions"),
            "recommendations": lambda: self.has_table("recommendations"),
            "mentions": lambda: self.has_table("mentions"),
            "hashtags": lambda: self.has_table("hashtags") and self.has_table("post_hashtags"),
            "topics": lambda: self.has_table("interests") and self.has_table("post_topics"),
            "sentiment": lambda: self.has_table("post_sentiment"),
            "toxicity": lambda: self.has_table("post_toxicity"),
            "emotions": lambda: self.has_table("emotions") and self.has_table("post_emotions"),
            "forum_sessions": lambda: self.has_table("forum_chat_sessions"),
            "forum_messages": lambda: self.has_table("forum_chat_messages"),
            "moderation": lambda: self.has_table("reported", "sys_messages"),
        }

        if feature_name not in feature_checks:
            raise KeyError(f"Unknown feature '{feature_name}'.")

        return feature_checks[feature_name]()

    def describe(self):
        return {
            "tables": sorted(self.tables),
            "columns": {name: sorted(cols) for name, cols in self.columns.items()},
            "features": {
                feature: self.supports_feature(feature)
                for feature in (
                    "microblog",
                    "forum",
                    "users",
                    "posts",
                    "threads",
                    "follow_network",
                    "reactions",
                    "recommendations",
                    "mentions",
                    "hashtags",
                    "topics",
                    "sentiment",
                    "toxicity",
                    "emotions",
                    "forum_sessions",
                    "forum_messages",
                    "moderation",
                )
            },
        }
