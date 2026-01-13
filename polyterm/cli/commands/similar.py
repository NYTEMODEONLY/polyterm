"""Similar Markets - Find related markets for diversification or hedging"""

import click
import re
from collections import Counter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=True)
@click.option("--limit", "-l", default=10, help="Number of similar markets to show")
@click.option("--type", "-t", "match_type", type=click.Choice(["topic", "category", "all"]), default="all", help="Similarity type")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def similar(ctx, market_search, limit, match_type, output_format):
    """Find markets similar to a given market

    Useful for:
    - Diversification (find related bets)
    - Hedging (find correlated markets)
    - Discovery (explore related topics)

    Examples:
        polyterm similar "bitcoin"              # Find markets like bitcoin
        polyterm similar "trump" --type topic   # Topic-based similarity
        polyterm similar "election" --limit 20  # More results
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Finding similar markets...", total=None)

            # Find the source market
            source_markets = gamma_client.search_markets(market_search, limit=1)

            if not source_markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Market not found'})
                else:
                    console.print(f"[yellow]Market '{market_search}' not found.[/yellow]")
                return

            source = source_markets[0]
            source_title = source.get('question', source.get('title', ''))
            source_category = source.get('category', 'Unknown')
            source_id = source.get('id', source.get('condition_id', ''))

            # Extract keywords from source
            keywords = _extract_keywords(source_title)

            # Get candidate markets
            all_markets = gamma_client.get_markets(limit=200, active=True)

            # Score similarity
            scored = []
            for market in all_markets:
                market_id = market.get('id', market.get('condition_id', ''))
                if market_id == source_id:
                    continue

                score = _calculate_similarity(source, market, keywords, match_type)
                if score > 0:
                    scored.append({
                        'market': market,
                        'score': score,
                        'match_reasons': _get_match_reasons(source, market, keywords),
                    })

            # Sort by score
            scored.sort(key=lambda x: x['score'], reverse=True)
            results = scored[:limit]

    finally:
        gamma_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'source': {
                'title': source_title,
                'category': source_category,
            },
            'similar': [{
                'title': r['market'].get('question', r['market'].get('title', '')),
                'score': r['score'],
                'reasons': r['match_reasons'],
            } for r in results],
        })
        return

    # Display results
    console.print()
    console.print(Panel(f"[bold]Markets Similar To[/bold]\n{source_title[:60]}", border_style="cyan"))
    console.print()

    console.print(f"[dim]Category: {source_category} | Keywords: {', '.join(keywords[:5])}[/dim]")
    console.print()

    if not results:
        console.print("[yellow]No similar markets found.[/yellow]")
        console.print("[dim]Try a different market or broader search term.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Market", max_width=45)
    table.add_column("Match", width=8, justify="center")
    table.add_column("Price", width=8, justify="center")
    table.add_column("Why Similar", max_width=25)

    for r in results:
        market = r['market']
        title = market.get('question', market.get('title', ''))[:43]
        price = _get_price(market)
        score = r['score']

        # Match quality indicator
        if score >= 70:
            match_str = f"[green]{score}%[/green]"
        elif score >= 40:
            match_str = f"[yellow]{score}%[/yellow]"
        else:
            match_str = f"[dim]{score}%[/dim]"

        reasons = ', '.join(r['match_reasons'][:2])

        table.add_row(title, match_str, f"{price:.0%}", reasons)

    console.print(table)
    console.print()
    console.print(f"[dim]{len(results)} similar markets found[/dim]")
    console.print()

    # Suggestions
    if results:
        console.print("[bold]Suggestions:[/bold]")
        top = results[0]
        console.print(f"  [green]+[/green] Most similar: {top['market'].get('question', '')[:50]}")

        # Find one in different category for diversification
        for r in results:
            if r['market'].get('category') != source_category:
                console.print(f"  [cyan]~[/cyan] For diversification: {r['market'].get('question', '')[:45]}")
                break

        console.print()


def _extract_keywords(title: str) -> list:
    """Extract meaningful keywords from a market title"""
    # Remove common words
    stop_words = {
        'will', 'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have',
        'for', 'not', 'on', 'with', 'as', 'do', 'at', 'this', 'but', 'by',
        'from', 'or', 'an', 'what', 'all', 'were', 'when', 'we', 'there',
        'can', 'has', 'more', 'if', 'no', 'out', 'so', 'up', 'into', 'than',
        'its', 'about', 'who', 'which', 'their', 'any', 'before', 'after',
        'during', 'between', 'under', 'over', 'above', 'below', 'is', 'are',
        'was', 'been', 'being', 'it', 'he', 'she', 'they', 'him', 'her',
        'yes', 'no', '2024', '2025', '2026',
    }

    # Tokenize and clean
    words = re.findall(r'\b[a-zA-Z]+\b', title.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    # Count and return most common
    counts = Counter(keywords)
    return [word for word, _ in counts.most_common(10)]


def _calculate_similarity(source: dict, target: dict, keywords: list, match_type: str) -> int:
    """Calculate similarity score between two markets"""
    score = 0

    source_title = source.get('question', source.get('title', '')).lower()
    target_title = target.get('question', target.get('title', '')).lower()
    source_category = source.get('category', '')
    target_category = target.get('category', '')

    # Category match (if matching by category or all)
    if match_type in ['category', 'all']:
        if source_category and target_category:
            if source_category == target_category:
                score += 30

    # Keyword matches (if matching by topic or all)
    if match_type in ['topic', 'all']:
        keyword_matches = sum(1 for k in keywords if k in target_title)
        score += min(50, keyword_matches * 15)

        # Bonus for exact phrase matches
        for k in keywords:
            if k in target_title and k in source_title:
                score += 5

    # Title similarity (Jaccard-like)
    source_words = set(re.findall(r'\b[a-zA-Z]+\b', source_title))
    target_words = set(re.findall(r'\b[a-zA-Z]+\b', target_title))

    if source_words and target_words:
        intersection = len(source_words & target_words)
        union = len(source_words | target_words)
        jaccard = intersection / union if union > 0 else 0
        score += int(jaccard * 30)

    return min(100, score)


def _get_match_reasons(source: dict, target: dict, keywords: list) -> list:
    """Get reasons why markets are similar"""
    reasons = []

    source_title = source.get('question', source.get('title', '')).lower()
    target_title = target.get('question', target.get('title', '')).lower()

    # Category match
    if source.get('category') == target.get('category') and source.get('category'):
        reasons.append(f"Same category")

    # Keyword matches
    matched_keywords = [k for k in keywords if k in target_title]
    if matched_keywords:
        reasons.append(f"Keywords: {', '.join(matched_keywords[:3])}")

    # Common entities (capitalized words that appear in both)
    source_entities = set(re.findall(r'\b[A-Z][a-z]+\b', source.get('question', '')))
    target_entities = set(re.findall(r'\b[A-Z][a-z]+\b', target.get('question', '')))
    common_entities = source_entities & target_entities

    if common_entities:
        reasons.append(f"Same: {', '.join(list(common_entities)[:2])}")

    return reasons if reasons else ['Topic similarity']


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            import json
            prices = market['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))
