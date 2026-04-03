# Similar Screen

> Find markets related to one you are watching.

## Overview

The Similar screen helps users discover markets that are related to a given market. It supports three match types: topic-based similarity, category-based similarity, or both combined. This is useful for finding correlated markets or alternative betting opportunities.

## Access

- **Menu shortcut**: `sml`, `similar`
- **Menu path**: Page 2 (Similar)

## What It Shows

After prompting for a market name and match type, it displays a list of similar markets. The user selects from three match modes:

1. **All** -- matches by both topic and category
2. **Topic only** -- matches by topic/subject similarity
3. **Category only** -- matches by market category

## Navigation / Keyboard Shortcuts

- `1` / `2` / `3` -- select match type (all, topic, category)
- Leaving the market prompt empty returns to the menu

## CLI Command

```bash
polyterm similar "<market name>" --type <all|topic|category>
```

## Data Sources

- Gamma REST API (market listings, categories, topics)

## Related Screens

- [search_screen](../screens/search_screen.md) -- advanced market search with filters
- [sentiment_screen](../screens/sentiment_screen.md) -- sentiment analysis for discovered markets
