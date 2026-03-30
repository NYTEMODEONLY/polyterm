"""Tests for WhaleTracker and InsiderDetector"""

import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch

from polyterm.core.whale_tracker import WhaleTracker, InsiderDetector
from polyterm.db.models import Wallet, Trade, Alert


class TestWhaleTracker:
    """Tests for WhaleTracker core functionality"""

    @pytest.fixture
    def mock_db(self):
        db = Mock()
        db.get_wallet.return_value = None
        db.insert_trade.return_value = None
        db.upsert_wallet.return_value = None
        db.insert_alert.return_value = None
        return db

    @pytest.fixture
    def mock_clob(self):
        clob = Mock()
        clob.subscribe_to_trades = AsyncMock()
        clob.listen_for_trades = AsyncMock()
        return clob

    @pytest.fixture
    def tracker(self, mock_db, mock_clob):
        return WhaleTracker(
            database=mock_db,
            clob_client=mock_clob,
            min_whale_trade=10000,
        )

    @pytest.fixture
    def sample_trade_data(self):
        return {
            'maker_address': '0xWhale123',
            'taker_address': '0xTaker456',
            'price': 0.65,
            'size': 100,
            'market': 'market-abc',
            'market_slug': 'will-btc-reach-100k',
            'side': 'BUY',
            'outcome': 'YES',
            'timestamp': 1700000000,
            'transactionHash': '0xtx123',
        }

    # --- process_trade tests ---

    @pytest.mark.asyncio
    async def test_process_trade_creates_trade_record(self, tracker, mock_db, sample_trade_data):
        """process_trade returns a Trade and inserts into DB"""
        trade = await tracker.process_trade(sample_trade_data)
        assert trade is not None
        assert trade.wallet_address == '0xWhale123'
        assert trade.price == 0.65
        assert trade.size == 100
        assert trade.notional == 65.0
        assert trade.side == 'BUY'
        assert trade.market_id == 'market-abc'
        mock_db.insert_trade.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_trade_uses_taker_if_no_maker(self, tracker, mock_db):
        """Falls back to taker_address when maker is empty"""
        data = {
            'maker_address': '',
            'taker_address': '0xTaker789',
            'price': 0.50,
            'size': 200,
            'market': 'market-xyz',
        }
        trade = await tracker.process_trade(data)
        assert trade.wallet_address == '0xTaker789'

    @pytest.mark.asyncio
    async def test_process_trade_skips_if_no_wallet(self, tracker):
        """Returns None when no wallet address available"""
        data = {'price': 0.50, 'size': 100}
        trade = await tracker.process_trade(data)
        assert trade is None

    @pytest.mark.asyncio
    async def test_process_trade_updates_recent_trades_cache(self, tracker, sample_trade_data):
        """Appends to recent_trades in-memory cache"""
        assert len(tracker.recent_trades) == 0
        await tracker.process_trade(sample_trade_data)
        assert len(tracker.recent_trades) == 1

    @pytest.mark.asyncio
    async def test_process_trade_trims_cache_at_max(self, tracker, sample_trade_data):
        """Cache is trimmed when it exceeds max_recent_trades"""
        tracker.max_recent_trades = 3
        for i in range(5):
            data = dict(sample_trade_data)
            data['transactionHash'] = f'0xtx{i}'
            await tracker.process_trade(data)
        assert len(tracker.recent_trades) == 3

    @pytest.mark.asyncio
    async def test_process_trade_timestamp_int(self, tracker, sample_trade_data):
        """Handles integer timestamp"""
        sample_trade_data['timestamp'] = 1700000000
        trade = await tracker.process_trade(sample_trade_data)
        assert trade.timestamp.year >= 2023

    @pytest.mark.asyncio
    async def test_process_trade_timestamp_string(self, tracker, sample_trade_data):
        """Handles ISO string timestamp"""
        sample_trade_data['timestamp'] = '2024-01-15T12:00:00Z'
        trade = await tracker.process_trade(sample_trade_data)
        assert trade.timestamp.year == 2024

    @pytest.mark.asyncio
    async def test_process_trade_timestamp_missing(self, tracker, sample_trade_data):
        """Uses current time when timestamp is missing"""
        del sample_trade_data['timestamp']
        trade = await tracker.process_trade(sample_trade_data)
        assert trade.timestamp is not None

    # --- _update_wallet tests ---

    @pytest.mark.asyncio
    async def test_update_wallet_creates_new_wallet(self, tracker, mock_db, sample_trade_data):
        """Creates new wallet if not in DB"""
        mock_db.get_wallet.return_value = None
        await tracker.process_trade(sample_trade_data)
        mock_db.upsert_wallet.assert_called_once()
        wallet = mock_db.upsert_wallet.call_args[0][0]
        assert wallet.address == '0xWhale123'
        assert wallet.total_trades == 1

    @pytest.mark.asyncio
    async def test_update_wallet_increments_existing(self, tracker, mock_db, sample_trade_data):
        """Updates existing wallet stats"""
        existing = Wallet(
            address='0xWhale123',
            first_seen=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_trades=5,
            total_volume=5000.0,
        )
        mock_db.get_wallet.return_value = existing
        await tracker.process_trade(sample_trade_data)
        wallet = mock_db.upsert_wallet.call_args[0][0]
        assert wallet.total_trades == 6
        assert wallet.total_volume == 5065.0  # 5000 + 65

    @pytest.mark.asyncio
    async def test_update_wallet_tracks_largest_trade(self, tracker, mock_db, sample_trade_data):
        """Updates largest_trade when new trade exceeds it"""
        existing = Wallet(
            address='0xWhale123',
            first_seen=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_trades=1,
            total_volume=50.0,
            largest_trade=50.0,
        )
        mock_db.get_wallet.return_value = existing
        await tracker.process_trade(sample_trade_data)
        wallet = mock_db.upsert_wallet.call_args[0][0]
        assert wallet.largest_trade == 65.0

    @pytest.mark.asyncio
    async def test_update_wallet_tracks_favorite_markets(self, tracker, mock_db, sample_trade_data):
        """Adds market to favorite_markets list"""
        mock_db.get_wallet.return_value = None
        await tracker.process_trade(sample_trade_data)
        wallet = mock_db.upsert_wallet.call_args[0][0]
        assert 'market-abc' in wallet.favorite_markets

    @pytest.mark.asyncio
    async def test_update_wallet_auto_tags_whale(self, tracker, mock_db):
        """Auto-tags wallet as 'whale' when volume >= 100k"""
        existing = Wallet(
            address='0xBigWhale',
            first_seen=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_trades=50,
            total_volume=99950.0,
        )
        mock_db.get_wallet.return_value = existing
        data = {
            'maker_address': '0xBigWhale',
            'price': 0.50,
            'size': 200,
            'market': 'm1',
        }
        await tracker.process_trade(data)
        wallet = mock_db.upsert_wallet.call_args[0][0]
        assert 'whale' in wallet.tags

    @pytest.mark.asyncio
    async def test_update_wallet_caches_in_memory(self, tracker, mock_db, sample_trade_data):
        """Wallet is cached in active_wallets dict"""
        await tracker.process_trade(sample_trade_data)
        assert '0xWhale123' in tracker.active_wallets

    # --- Whale detection & callbacks ---

    @pytest.mark.asyncio
    async def test_whale_trade_triggers_alert(self, tracker, mock_db):
        """Whale trade (notional >= min_whale_trade) creates an alert"""
        data = {
            'maker_address': '0xBigSpender',
            'price': 0.50,
            'size': 25000,  # notional = 12500
            'market': 'm1',
        }
        await tracker.process_trade(data)
        # insert_alert called for whale alert
        calls = [c for c in mock_db.insert_alert.call_args_list
                 if c[0][0].alert_type == 'whale']
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_whale_callback_fires(self, tracker, mock_db):
        """Sync whale callback is invoked on whale trade"""
        callback = Mock()
        tracker.add_whale_callback(callback)
        data = {
            'maker_address': '0xBigSpender',
            'price': 0.50,
            'size': 25000,
            'market': 'm1',
        }
        await tracker.process_trade(data)
        callback.assert_called_once()
        trade_arg, wallet_arg = callback.call_args[0]
        assert isinstance(trade_arg, Trade)
        assert isinstance(wallet_arg, Wallet)

    @pytest.mark.asyncio
    async def test_whale_async_callback_fires(self, tracker, mock_db):
        """Async whale callback is awaited on whale trade"""
        callback = AsyncMock()
        tracker.add_whale_callback(callback)
        data = {
            'maker_address': '0xBigSpender',
            'price': 0.50,
            'size': 25000,
            'market': 'm1',
        }
        await tracker.process_trade(data)
        callback.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_whale_callback_error_does_not_crash(self, tracker, mock_db):
        """Callback exception is caught, processing continues"""
        callback = Mock(side_effect=RuntimeError("boom"))
        tracker.add_whale_callback(callback)
        data = {
            'maker_address': '0xBigSpender',
            'price': 0.50,
            'size': 25000,
            'market': 'm1',
        }
        trade = await tracker.process_trade(data)
        assert trade is not None  # didn't crash

    @pytest.mark.asyncio
    async def test_small_trade_no_whale_alert(self, tracker, mock_db, sample_trade_data):
        """Trade below threshold does NOT trigger whale alert"""
        await tracker.process_trade(sample_trade_data)  # notional=65
        whale_alerts = [c for c in mock_db.insert_alert.call_args_list
                        if c[0][0].alert_type == 'whale']
        assert len(whale_alerts) == 0

    # --- Smart money detection ---

    @pytest.mark.asyncio
    async def test_smart_money_callback_fires(self, tracker, mock_db):
        """Smart money callback fires when wallet qualifies"""
        existing = Wallet(
            address='0xSmart',
            first_seen=datetime(2024, 1, 1, tzinfo=timezone.utc),
            total_trades=10,
            total_volume=50000.0,
            win_rate=0.80,
        )
        mock_db.get_wallet.return_value = existing
        callback = Mock()
        tracker.add_smart_money_callback(callback)
        data = {
            'maker_address': '0xSmart',
            'price': 0.50,
            'size': 100,
            'market': 'm1',
        }
        await tracker.process_trade(data)
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_smart_money_no_callback(self, tracker, mock_db, sample_trade_data):
        """Non-smart money wallet doesn't trigger smart money callback"""
        callback = Mock()
        tracker.add_smart_money_callback(callback)
        await tracker.process_trade(sample_trade_data)
        callback.assert_not_called()

    # --- start_monitoring ---

    @pytest.mark.asyncio
    async def test_start_monitoring_subscribes_and_listens(self, tracker, mock_clob):
        """start_monitoring wires subscribe + listen"""
        await tracker.start_monitoring(['slug-a', 'slug-b'])
        mock_clob.subscribe_to_trades.assert_awaited_once()
        slugs_arg = mock_clob.subscribe_to_trades.call_args[0][0]
        assert slugs_arg == ['slug-a', 'slug-b']
        mock_clob.listen_for_trades.assert_awaited_once()

    # --- start_monitoring with fallback ---

    @pytest.mark.asyncio
    async def test_start_monitoring_falls_back_to_rest_on_ws_error(self, tracker, mock_clob):
        """Falls back to REST polling when on_error callback fires"""
        # Make listen_for_trades invoke the on_error callback
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("WebSocket permanently failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)
        mock_clob.get_recent_trades = Mock(return_value=[])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Stop monitoring after first poll iteration
            async def stop_after_sleep(seconds):
                tracker.stop_monitoring()

            mock_sleep.side_effect = stop_after_sleep
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # Should have attempted REST polling
        mock_clob.get_recent_trades.assert_called()

    @pytest.mark.asyncio
    async def test_start_monitoring_falls_back_on_subscribe_exception(self, tracker, mock_clob):
        """Falls back to REST polling when subscribe raises"""
        mock_clob.subscribe_to_trades = AsyncMock(side_effect=Exception("connect failed"))
        mock_clob.get_recent_trades = Mock(return_value=[])

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            async def stop_after_sleep(seconds):
                tracker.stop_monitoring()

            mock_sleep.side_effect = stop_after_sleep
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        mock_clob.get_recent_trades.assert_called()

    @pytest.mark.asyncio
    async def test_rest_polling_processes_trades(self, tracker, mock_clob, mock_db):
        """REST polling processes trade data through process_trade"""
        mock_clob.listen_for_trades = AsyncMock()  # Exits cleanly (no error)
        # But we simulate ws_failed by making on_error fire
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)
        mock_clob.get_recent_trades = Mock(return_value=[
            {
                "maker_address": "0xWhale",
                "price": 0.50,
                "size": 100,
                "market": "m1",
                "transactionHash": "0xtx1",
            },
            {
                "maker_address": "0xWhale2",
                "price": 0.60,
                "size": 200,
                "market": "m1",
                "transactionHash": "0xtx2",
            },
        ])

        poll_count = 0

        async def stop_after_poll(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 1:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_poll):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # Both trades should have been processed
        assert mock_db.insert_trade.call_count == 2

    @pytest.mark.asyncio
    async def test_rest_polling_deduplicates_by_tx_hash(self, tracker, mock_clob, mock_db):
        """REST polling skips trades with already-seen tx hashes"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)

        trade = {
            "maker_address": "0xWhale",
            "price": 0.50,
            "size": 100,
            "market": "m1",
            "transactionHash": "0xSameTx",
        }
        # Return same trade on both poll iterations
        mock_clob.get_recent_trades = Mock(return_value=[trade])

        poll_count = 0

        async def stop_after_two(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 2:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_two):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # Trade should only be processed once despite appearing in both polls
        assert mock_db.insert_trade.call_count == 1

    @pytest.mark.asyncio
    async def test_rest_polling_handles_api_error_gracefully(self, tracker, mock_clob, mock_db):
        """REST polling continues after individual API call failures"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)
        mock_clob.get_recent_trades = Mock(side_effect=Exception("API error"))

        poll_count = 0

        async def stop_after_two(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 2:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_two):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # Should not crash, just keep polling
        assert mock_db.insert_trade.call_count == 0

    def test_stop_monitoring_sets_flag(self, tracker):
        """stop_monitoring sets _monitoring to False"""
        tracker._monitoring = True
        tracker.stop_monitoring()
        assert tracker._monitoring is False

    @pytest.mark.asyncio
    async def test_start_monitoring_sets_monitoring_flag(self, tracker, mock_clob):
        """start_monitoring sets _monitoring to True"""
        assert tracker._monitoring is False
        await tracker.start_monitoring(["slug-a"])
        assert tracker._monitoring is True

    @pytest.mark.asyncio
    async def test_rest_polling_caps_seen_set(self, tracker, mock_clob, mock_db):
        """REST polling clears seen_tx_hashes when exceeding MAX_SEEN"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)

        # Generate unique trades to fill the seen set
        call_idx = [0]

        def make_trades(slug, limit=50):
            trades = []
            for i in range(limit):
                trades.append({
                    "maker_address": "0xWhale",
                    "price": 0.50,
                    "size": 100,
                    "market": "m1",
                    "transactionHash": f"0xtx_{call_idx[0]}_{i}",
                })
            call_idx[0] += 1
            return trades

        mock_clob.get_recent_trades = Mock(side_effect=make_trades)

        poll_count = 0

        async def stop_after_polls(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 3:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_polls):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # All trades should be processed (no deduplication across clears)
        assert mock_db.insert_trade.call_count >= 100

    # --- REST polling edge cases ---

    @pytest.mark.asyncio
    async def test_rest_polling_partial_slug_failure(self, tracker, mock_clob, mock_db):
        """REST polling continues with other slugs when one slug fails"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)

        call_idx = [0]

        def get_trades(slug, limit=50):
            call_idx[0] += 1
            if slug == "slug-fail":
                raise Exception("API timeout for this slug")
            return [{
                "maker_address": "0xWhale",
                "price": 0.50,
                "size": 100,
                "market": "m1",
                "transactionHash": f"0xtx_{call_idx[0]}",
            }]

        mock_clob.get_recent_trades = Mock(side_effect=get_trades)

        poll_count = 0

        async def stop_after_poll(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 1:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_poll):
            await tracker.start_monitoring(["slug-ok", "slug-fail"], poll_interval=1.0)

        # slug-ok trades should have been processed despite slug-fail errors
        assert mock_db.insert_trade.call_count >= 1

    @pytest.mark.asyncio
    async def test_rest_polling_with_none_market_slugs(self, tracker, mock_clob, mock_db):
        """REST polling uses empty string slug when market_slugs is None"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)
        mock_clob.get_recent_trades = Mock(return_value=[{
            "maker_address": "0xWhale",
            "price": 0.50,
            "size": 100,
            "market": "m1",
            "transactionHash": "0xtx1",
        }])

        poll_count = 0

        async def stop_after_poll(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 1:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_poll):
            await tracker.start_monitoring(None, poll_interval=1.0)

        # Should have polled with empty string slug
        mock_clob.get_recent_trades.assert_called()
        assert mock_db.insert_trade.call_count == 1

    @pytest.mark.asyncio
    async def test_rest_polling_trade_without_tx_hash(self, tracker, mock_clob, mock_db):
        """REST polling processes trades that have no transactionHash"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)
        mock_clob.get_recent_trades = Mock(return_value=[
            {
                "maker_address": "0xWhale",
                "price": 0.50,
                "size": 100,
                "market": "m1",
                # No transactionHash or tx_hash
            },
            {
                "maker_address": "0xWhale",
                "price": 0.50,
                "size": 100,
                "market": "m1",
                # Same trade without hash - can't deduplicate
            },
        ])

        poll_count = 0

        async def stop_after_poll(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 1:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_after_poll):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # Both trades processed (no hash means no dedup)
        assert mock_db.insert_trade.call_count == 2

    @pytest.mark.asyncio
    async def test_start_monitoring_ws_success_no_rest_fallback(self, tracker, mock_clob, mock_db):
        """When WS succeeds (no on_error), REST fallback is not triggered"""
        # listen_for_trades returns cleanly without invoking on_error
        mock_clob.listen_for_trades = AsyncMock()
        mock_clob.get_recent_trades = Mock(return_value=[])

        await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # REST polling should NOT have been called
        mock_clob.get_recent_trades.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_monitoring_can_restart_after_stop(self, tracker, mock_clob, mock_db):
        """start_monitoring can be called again after stop_monitoring"""
        async def listen_with_error(**kwargs):
            on_error = kwargs.get("on_error")
            if on_error:
                on_error(Exception("failed"))

        mock_clob.listen_for_trades = AsyncMock(side_effect=listen_with_error)
        mock_clob.get_recent_trades = Mock(return_value=[])

        # First run
        poll_count = 0

        async def stop_first(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 1:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_first):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        assert tracker._monitoring is False

        # Second run should work
        poll_count = 0

        async def stop_second(seconds):
            nonlocal poll_count
            poll_count += 1
            if poll_count >= 1:
                tracker.stop_monitoring()

        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=stop_second):
            await tracker.start_monitoring(["slug-a"], poll_interval=1.0)

        # _monitoring was set to True during second run, then False on stop
        assert tracker._monitoring is False

    # --- Leaderboard & query methods ---

    def test_get_whale_leaderboard(self, tracker, mock_db):
        """Delegates to db.get_whale_wallets"""
        mock_db.get_whale_wallets.return_value = [Mock(), Mock()]
        result = tracker.get_whale_leaderboard(limit=5)
        mock_db.get_whale_wallets.assert_called_once_with(min_volume=10000)
        assert len(result) == 2

    def test_get_smart_money_leaderboard(self, tracker, mock_db):
        """Delegates to db.get_smart_money_wallets"""
        mock_db.get_smart_money_wallets.return_value = [Mock()]
        result = tracker.get_smart_money_leaderboard(limit=10)
        mock_db.get_smart_money_wallets.assert_called_once_with(
            min_win_rate=0.70, min_trades=10
        )

    def test_get_recent_whale_trades(self, tracker, mock_db):
        mock_db.get_large_trades.return_value = []
        tracker.get_recent_whale_trades(hours=12)
        mock_db.get_large_trades.assert_called_once_with(min_notional=10000, hours=12)

    def test_get_wallet_profile(self, tracker, mock_db):
        mock_db.get_wallet_stats.return_value = {'address': '0x1'}
        result = tracker.get_wallet_profile('0x1')
        assert result['address'] == '0x1'

    def test_track_wallet(self, tracker, mock_db):
        tracker.track_wallet('0xAddr', tag='vip')
        mock_db.add_wallet_tag.assert_called_once_with('0xAddr', 'vip')

    def test_untrack_wallet(self, tracker, mock_db):
        tracker.untrack_wallet('0xAddr', tag='vip')
        mock_db.remove_wallet_tag.assert_called_once_with('0xAddr', 'vip')

    def test_get_tracked_wallets(self, tracker, mock_db):
        w1 = Wallet(address='0x1', first_seen=datetime.now(), tags=['tracked'])
        w2 = Wallet(address='0x2', first_seen=datetime.now(), tags=[])
        mock_db.get_all_wallets.return_value = [w1, w2]
        result = tracker.get_tracked_wallets()
        assert len(result) == 1
        assert result[0].address == '0x1'


class TestInsiderDetector:
    """Tests for InsiderDetector scoring and analysis"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def detector(self, mock_db):
        return InsiderDetector(database=mock_db)

    def _make_wallet(self, **kwargs):
        defaults = dict(
            address='0xTest',
            first_seen=datetime.now(timezone.utc) - timedelta(days=365),
            total_trades=50,
            total_volume=10000.0,
            win_rate=0.50,
            avg_position_size=200.0,
            tags=[],
            risk_score=0,
        )
        defaults.update(kwargs)
        return Wallet(**defaults)

    # --- calculate_insider_score ---

    def test_score_brand_new_wallet(self, detector):
        """Brand new wallet (< 1 day) gets 25 age points"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(hours=6)
        )
        score = detector.calculate_insider_score(wallet)
        assert score >= 25

    def test_score_old_wallet_low_risk(self, detector):
        """Old wallet with normal activity scores low"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(days=365),
            avg_position_size=200,
            win_rate=0.50,
            total_trades=100,
            total_volume=20000,
        )
        score = detector.calculate_insider_score(wallet)
        assert score < 40  # low risk

    def test_score_high_position_size(self, detector):
        """Large avg position size adds points"""
        wallet = self._make_wallet(avg_position_size=60000)
        score = detector.calculate_insider_score(wallet)
        assert score >= 25

    def test_score_high_win_rate_with_enough_trades(self, detector):
        """High win rate with 5+ trades adds points"""
        wallet = self._make_wallet(win_rate=0.96, total_trades=10)
        score = detector.calculate_insider_score(wallet)
        assert score >= 25

    def test_score_high_win_rate_too_few_trades(self, detector):
        """High win rate with < 5 trades gets no win rate bonus"""
        wallet = self._make_wallet(win_rate=0.99, total_trades=3)
        score = detector.calculate_insider_score(wallet)
        # Should NOT include the 25 for win rate
        assert score < 25 or score == 0  # only age/position/pattern can contribute

    def test_score_few_trades_high_volume_pattern(self, detector):
        """Few trades + high volume triggers pattern detection"""
        wallet = self._make_wallet(total_trades=5, total_volume=60000)
        score = detector.calculate_insider_score(wallet)
        assert score >= 15

    def test_score_capped_at_100(self, detector):
        """Score never exceeds 100"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_position_size=100000,
            win_rate=0.99,
            total_trades=8,
            total_volume=200000,
        )
        score = detector.calculate_insider_score(wallet)
        assert score <= 100

    def test_score_max_suspicious_wallet(self, detector):
        """All risk factors present yields high score"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_position_size=100000,
            win_rate=0.99,
            total_trades=8,
            total_volume=200000,
        )
        score = detector.calculate_insider_score(wallet)
        assert score >= 70  # high risk

    # --- analyze_wallet ---

    def test_analyze_wallet_risk_levels(self, detector):
        """Risk levels are correctly assigned"""
        # High risk
        wallet_high = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_position_size=100000,
            win_rate=0.99,
            total_trades=8,
            total_volume=200000,
        )
        result = detector.analyze_wallet(wallet_high)
        assert result['risk_level'] == 'high'

        # Low risk
        wallet_low = self._make_wallet()
        result_low = detector.analyze_wallet(wallet_low)
        assert result_low['risk_level'] == 'low'

    def test_analyze_wallet_returns_risk_factors(self, detector):
        """Analysis includes human-readable risk factors"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(days=2),
            avg_position_size=30000,
            win_rate=0.90,
            total_trades=8,
            total_volume=60000,
        )
        result = detector.analyze_wallet(wallet)
        assert len(result['risk_factors']) > 0
        assert result['address'] == '0xTest'
        assert 'total_trades' in result
        assert 'total_volume' in result

    # --- get_suspicious_wallets ---

    def test_get_suspicious_wallets_filters_by_score(self, detector, mock_db):
        """Only returns wallets above threshold"""
        w_high = self._make_wallet(
            address='0xSus',
            first_seen=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_position_size=100000,
            win_rate=0.99,
            total_trades=8,
            total_volume=200000,
        )
        w_low = self._make_wallet(address='0xClean')
        mock_db.get_all_wallets.return_value = [w_high, w_low]
        result = detector.get_suspicious_wallets(min_score=70)
        assert len(result) >= 1
        assert all(r['risk_score'] >= 70 for r in result)

    def test_get_suspicious_wallets_sorted_by_score(self, detector, mock_db):
        """Results sorted descending by risk_score"""
        w1 = self._make_wallet(
            address='0xA',
            first_seen=datetime.now(timezone.utc) - timedelta(hours=1),
            avg_position_size=100000,
            win_rate=0.99,
            total_trades=8,
            total_volume=200000,
        )
        w2 = self._make_wallet(
            address='0xB',
            first_seen=datetime.now(timezone.utc) - timedelta(days=3),
            avg_position_size=60000,
            win_rate=0.96,
            total_trades=6,
            total_volume=100000,
        )
        mock_db.get_all_wallets.return_value = [w2, w1]
        result = detector.get_suspicious_wallets(min_score=40)
        if len(result) >= 2:
            assert result[0]['risk_score'] >= result[1]['risk_score']

    # --- flag_wallet_as_suspicious ---

    def test_flag_wallet_creates_alert(self, detector, mock_db):
        """Flagging wallet inserts alert and tags wallet"""
        wallet = self._make_wallet(risk_score=50)
        mock_db.get_wallet.return_value = wallet
        detector.flag_wallet_as_suspicious('0xTest')
        mock_db.add_wallet_tag.assert_called_once_with('0xTest', 'insider_suspect')
        mock_db.insert_alert.assert_called_once()
        alert = mock_db.insert_alert.call_args[0][0]
        assert alert.alert_type == 'insider_suspect'
        assert wallet.risk_score >= 70  # raised to min 70

    def test_flag_wallet_noop_if_not_found(self, detector, mock_db):
        """Flagging unknown wallet does nothing"""
        mock_db.get_wallet.return_value = None
        detector.flag_wallet_as_suspicious('0xUnknown')
        mock_db.insert_alert.assert_not_called()

    # --- check_trade_for_insider_signals ---

    def test_check_fresh_wallet_large_bet(self, detector):
        """Fresh wallet + large bet triggers insider signal"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(days=1),
            total_trades=2,
        )
        trade = Trade(
            market_id='m1',
            wallet_address='0xTest',
            notional=15000,
            side='BUY',
        )
        alert = detector.check_trade_for_insider_signals(trade, wallet)
        assert alert is not None
        assert alert.alert_type == 'insider_signal'
        assert 'Fresh wallet with large bet' in alert.message

    def test_check_first_trade_huge(self, detector):
        """First trade >= $25k triggers signal"""
        wallet = self._make_wallet(total_trades=1)
        trade = Trade(
            market_id='m1',
            wallet_address='0xTest',
            notional=30000,
        )
        alert = detector.check_trade_for_insider_signals(trade, wallet)
        assert alert is not None
        assert 'First trade is $25k+' in alert.message

    def test_check_high_win_rate_signal(self, detector):
        """High win rate wallet triggers signal"""
        wallet = self._make_wallet(win_rate=0.95, total_trades=20)
        trade = Trade(
            market_id='m1',
            wallet_address='0xTest',
            notional=5000,
        )
        alert = detector.check_trade_for_insider_signals(trade, wallet)
        assert alert is not None
        assert 'High win rate' in alert.message

    def test_check_no_signals_normal_trade(self, detector):
        """Normal trade returns None"""
        wallet = self._make_wallet()
        trade = Trade(
            market_id='m1',
            wallet_address='0xTest',
            notional=500,
        )
        alert = detector.check_trade_for_insider_signals(trade, wallet)
        assert alert is None

    def test_check_severity_capped(self, detector):
        """Combined signal severity doesn't exceed 100"""
        wallet = self._make_wallet(
            first_seen=datetime.now(timezone.utc) - timedelta(hours=1),
            total_trades=1,
            win_rate=0.95,
        )
        trade = Trade(
            market_id='m1',
            wallet_address='0xTest',
            notional=30000,
        )
        alert = detector.check_trade_for_insider_signals(trade, wallet)
        assert alert is not None
        assert alert.severity <= 100
