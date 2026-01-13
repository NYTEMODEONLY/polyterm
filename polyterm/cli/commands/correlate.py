"""Market Correlation - Find related and correlated markets"""

import click
from datetime import datetime
from difflib import SequenceMatcher
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", "search_term", default=None, help="Market to find correlations for")
@click.option("--limit", "-l", default=10, help="Number of correlated markets to show")
@click.option("--min-score", default=0.3, help="Minimum correlation score (0-1)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def correlate(ctx, search_term, limit, min_score, interactive, output_format):
    """Find correlated and related markets

    Discovers markets that may move together based on:
    - Topic similarity (title/question matching)
    - Category overlap
    - Time-based variants (same event, different dates)
    - Inverse relationships (opposite outcomes)

    Examples:
        polyterm correlate -m "bitcoin"           # Find BTC-related markets
        polyterm correlate -m "election" -l 20   # More results
        polyterm correlate --interactive         # Interactive selection
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        search_term = Prompt.ask("[cyan]Search for market[/cyan]", default="")

    if not search_term:
        console.print("[yellow]Please specify a market with -m or use --interactive[/yellow]")
        return

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
            progress.add_task("Finding correlated markets...", total=None)

            # Find the source market
            source_markets = gamma_client.search_markets(search_term, limit=1)

            if not source_markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
                else:
                    console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
                return

            source = source_markets[0]
            source_id = source.get('id', source.get('condition_id', ''))
            source_title = source.get('question', source.get('title', ''))
            source_category = source.get('category', source.get('market_type', ''))

            # Extract key terms from the source market
            key_terms = _extract_key_terms(source_title)

            # Search for related markets using key terms
            related_markets = []
            seen_ids = {source_id}

            # Search by different strategies
            for term in key_terms[:5]:  # Top 5 key terms
                results = gamma_client.search_markets(term, limit=30)
                for m in results:
                    m_id = m.get('id', m.get('condition_id', ''))
                    if m_id not in seen_ids:
                        seen_ids.add(m_id)
                        related_markets.append(m)

            # Score and rank correlations
            correlations = []
            for market in related_markets:
                score_data = _calculate_correlation_score(source, market)
                if score_data['total_score'] >= min_score:
                    correlations.append({
                        'market': market,
                        'score': score_data,
                    })

            # Sort by score
            correlations.sort(key=lambda x: x['score']['total_score'], reverse=True)
            correlations = correlations[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'source_market': {
                    'id': source_id,
                    'title': source_title,
                    'category': source_category,
                },
                'correlations': [{
                    'market_id': c['market'].get('id', c['market'].get('condition_id', '')),
                    'title': c['market'].get('question', c['market'].get('title', '')),
                    'score': c['score']['total_score'],
                    'relationship': c['score']['relationship'],
                    'reasons': c['score']['reasons'],
                } for c in correlations],
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]Correlated Markets[/bold]\n[dim]{source_title[:70]}...[/dim]" if len(source_title) > 70 else f"[bold]Correlated Markets[/bold]\n[dim]{source_title}[/dim]", border_style="cyan"))
        console.print()

        if not correlations:
            console.print("[yellow]No strongly correlated markets found.[/yellow]")
            console.print("[dim]Try lowering --min-score or using different search terms.[/dim]")
            return

        # Group by relationship type
        positive = [c for c in correlations if c['score']['relationship'] == 'positive']
        inverse = [c for c in correlations if c['score']['relationship'] == 'inverse']
        time_variant = [c for c in correlations if c['score']['relationship'] == 'time_variant']
        related = [c for c in correlations if c['score']['relationship'] == 'related']

        # Display positive correlations
        if positive:
            console.print("[bold green]Positively Correlated[/bold green] [dim](move together)[/dim]")
            _display_correlation_table(console, positive)
            console.print()

        # Display inverse correlations
        if inverse:
            console.print("[bold red]Inversely Correlated[/bold red] [dim](move opposite)[/dim]")
            _display_correlation_table(console, inverse)
            console.print()

        # Display time variants
        if time_variant:
            console.print("[bold yellow]Time Variants[/bold yellow] [dim](same event, different dates)[/dim]")
            _display_correlation_table(console, time_variant)
            console.print()

        # Display related
        if related:
            console.print("[bold cyan]Related Markets[/bold cyan] [dim](similar topic)[/dim]")
            _display_correlation_table(console, related)
            console.print()

        # Trading implications
        console.print("[bold]Trading Implications:[/bold]")
        console.print()
        if positive:
            console.print("[green]+[/green] Positively correlated markets can be used to double exposure")
        if inverse:
            console.print("[red]-[/red] Inverse markets are good for hedging your position")
        if time_variant:
            console.print("[yellow]~[/yellow] Time variants show the term structure of probability")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _extract_key_terms(title: str) -> list:
    """Extract key searchable terms from a title"""
    # Common words to exclude
    stop_words = {
        'will', 'the', 'be', 'is', 'are', 'was', 'were', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'a', 'an', 'and', 'or',
        'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
        'as', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'under', 'again', 'further', 'then', 'once',
        'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
        'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'can',
        'should', 'now', 'what', 'which', 'who', 'whom', 'this', 'that',
        'these', 'those', 'am', 'any', 'yes', 'no', 'over', 'up', 'down',
    }

    # Clean and split
    import re
    words = re.findall(r'\b[a-zA-Z0-9]+\b', title.lower())

    # Filter and score by length (longer = more specific)
    key_terms = [w for w in words if w not in stop_words and len(w) > 2]

    # Prioritize longer words (more specific)
    key_terms.sort(key=len, reverse=True)

    # Also look for multi-word phrases
    phrases = []

    # Look for capitalized phrases in original
    caps_pattern = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', title)
    phrases.extend(caps_pattern)

    # Look for quoted phrases
    quoted = re.findall(r'"([^"]+)"', title)
    phrases.extend(quoted)

    return phrases + key_terms


def _calculate_correlation_score(source: dict, target: dict) -> dict:
    """Calculate correlation score between two markets"""
    source_title = source.get('question', source.get('title', '')).lower()
    target_title = target.get('question', target.get('title', '')).lower()

    source_category = source.get('category', '').lower()
    target_category = target.get('category', '').lower()

    reasons = []
    scores = []

    # 1. Title similarity
    title_sim = SequenceMatcher(None, source_title, target_title).ratio()
    if title_sim > 0.5:
        scores.append(title_sim * 0.4)  # Weight: 40%
        reasons.append(f"Title similarity: {title_sim:.0%}")

    # 2. Category match
    if source_category and target_category and source_category == target_category:
        scores.append(0.2)  # Weight: 20%
        reasons.append(f"Same category: {source_category}")

    # 3. Key term overlap
    source_terms = set(_extract_key_terms(source_title)[:10])
    target_terms = set(_extract_key_terms(target_title)[:10])

    if source_terms and target_terms:
        overlap = len(source_terms & target_terms)
        term_score = overlap / max(len(source_terms), len(target_terms))
        if term_score > 0:
            scores.append(term_score * 0.3)  # Weight: 30%
            common = source_terms & target_terms
            if common:
                reasons.append(f"Shared terms: {', '.join(list(common)[:3])}")

    # 4. Check for time variants (dates in titles)
    import re
    source_dates = re.findall(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|20\d{2}|q[1-4])\b', source_title, re.I)
    target_dates = re.findall(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|20\d{2}|q[1-4])\b', target_title, re.I)

    # 5. Check for inverse relationship
    inverse_pairs = [
        ('yes', 'no'), ('win', 'lose'), ('above', 'below'),
        ('over', 'under'), ('more', 'less'), ('increase', 'decrease'),
        ('rise', 'fall'), ('up', 'down'), ('higher', 'lower'),
    ]

    is_inverse = False
    for pair in inverse_pairs:
        if (pair[0] in source_title and pair[1] in target_title) or \
           (pair[1] in source_title and pair[0] in target_title):
            is_inverse = True
            break

    # Determine relationship type
    relationship = 'related'
    if is_inverse:
        relationship = 'inverse'
        scores.append(0.1)
        reasons.append("Inverse relationship detected")
    elif source_dates and target_dates and source_dates != target_dates:
        # Same topic, different dates
        title_no_dates = re.sub(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|20\d{2}|q[1-4])\b', '', source_title, flags=re.I)
        target_no_dates = re.sub(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|20\d{2}|q[1-4])\b', '', target_title, flags=re.I)
        if SequenceMatcher(None, title_no_dates, target_no_dates).ratio() > 0.7:
            relationship = 'time_variant'
            scores.append(0.15)
            reasons.append(f"Same event, different timeframes")
    elif title_sim > 0.6:
        relationship = 'positive'

    total_score = sum(scores) if scores else 0

    return {
        'total_score': min(1.0, total_score),
        'relationship': relationship,
        'reasons': reasons,
    }


def _display_correlation_table(console: Console, correlations: list):
    """Display correlation results table"""
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Score", width=6, justify="center")
    table.add_column("Market", max_width=55)
    table.add_column("Price", width=8, justify="center")

    for corr in correlations[:8]:
        market = corr['market']
        score = corr['score']['total_score']

        title = market.get('question', market.get('title', ''))[:53]

        # Get price
        price = _get_price(market)
        price_str = f"{price:.0%}" if price else "-"

        # Score color
        if score >= 0.7:
            score_str = f"[green]{score:.0%}[/green]"
        elif score >= 0.5:
            score_str = f"[yellow]{score:.0%}[/yellow]"
        else:
            score_str = f"[dim]{score:.0%}[/dim]"

        table.add_row(score_str, title, price_str)

    console.print(table)


def _get_price(market: dict) -> float:
    """Get current market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0))
