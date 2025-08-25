"""
Unit tests for database configuration and connection management.

This module contains tests for the database configuration, connection pooling,
health checks, and migration utilities.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from config.database import (
    DatabaseConfig,
    get_db_session,
    get_async_db_session,
    get_async_db_session_dependency,
    DatabaseHealthCheck,
    DatabaseMigrationHelper,
    execute_raw_query,
    get_database_stats,
    db_config
)
from config.settings import Settings


class TestDatabaseConfig:
    """Test cases for DatabaseConfig class."""
    
    @patch('config.database.get_settings')
    def test_database_url_property(self, mock_get_settings):
        """Test database URL property construction."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_get_settings.return_value = mock_settings
        
        config = DatabaseConfig()
        expected_url = "postgresql://testuser:testpass@localhost:5432/testdb"
        assert config.database_url == expected_url
    
    @patch('config.database.get_settings')
    def test_async_database_url_property(self, mock_get_settings):
        """Test async database URL property construction."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_get_settings.return_value = mock_settings
        
        config = DatabaseConfig()
        expected_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        assert config.async_database_url == expected_url
    
    @patch('config.database.get_settings')
    @patch('config.database.create_engine')
    def test_get_engine(self, mock_create_engine, mock_get_settings):
        """Test engine creation and caching."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.db_echo = False
        mock_get_settings.return_value = mock_settings
        
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        config = DatabaseConfig()
        
        # First call should create engine
        engine1 = config.get_engine()
        assert engine1 == mock_engine
        mock_create_engine.assert_called_once()
        
        # Second call should return cached engine
        engine2 = config.get_engine()
        assert engine2 == mock_engine
        assert mock_create_engine.call_count == 1  # Should not be called again
    
    @patch('config.database.get_settings')
    @patch('config.database.create_async_engine')
    def test_get_async_engine(self, mock_create_async_engine, mock_get_settings):
        """Test async engine creation and caching."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.db_echo = False
        mock_get_settings.return_value = mock_settings
        
        mock_async_engine = Mock()
        mock_create_async_engine.return_value = mock_async_engine
        
        config = DatabaseConfig()
        
        # First call should create async engine
        engine1 = config.get_async_engine()
        assert engine1 == mock_async_engine
        mock_create_async_engine.assert_called_once()
        
        # Second call should return cached engine
        engine2 = config.get_async_engine()
        assert engine2 == mock_async_engine
        assert mock_create_async_engine.call_count == 1  # Should not be called again
    
    @patch('config.database.get_settings')
    @patch('config.database.sessionmaker')
    def test_get_session_factory(self, mock_sessionmaker, mock_get_settings):
        """Test session factory creation and caching."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.db_echo = False
        mock_get_settings.return_value = mock_settings
        
        mock_factory = Mock()
        mock_sessionmaker.return_value = mock_factory
        
        config = DatabaseConfig()
        
        # Mock the engine
        with patch.object(config, 'get_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_get_engine.return_value = mock_engine
            
            # First call should create factory
            factory1 = config.get_session_factory()
            assert factory1 == mock_factory
            mock_sessionmaker.assert_called_once()
            
            # Second call should return cached factory
            factory2 = config.get_session_factory()
            assert factory2 == mock_factory
            assert mock_sessionmaker.call_count == 1  # Should not be called again
    
    @patch('config.database.get_settings')
    @patch('config.database.async_sessionmaker')
    def test_get_async_session_factory(self, mock_async_sessionmaker, mock_get_settings):
        """Test async session factory creation and caching."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.db_echo = False
        mock_get_settings.return_value = mock_settings
        
        mock_factory = Mock()
        mock_async_sessionmaker.return_value = mock_factory
        
        config = DatabaseConfig()
        
        # Mock the async engine
        with patch.object(config, 'get_async_engine') as mock_get_async_engine:
            mock_async_engine = Mock()
            mock_get_async_engine.return_value = mock_async_engine
            
            # First call should create factory
            factory1 = config.get_async_session_factory()
            assert factory1 == mock_factory
            mock_async_sessionmaker.assert_called_once()
            
            # Second call should return cached factory
            factory2 = config.get_async_session_factory()
            assert factory2 == mock_factory
            assert mock_async_sessionmaker.call_count == 1  # Should not be called again
    
    @pytest.mark.asyncio
    async def test_create_tables(self):
        """Test table creation."""
        config = DatabaseConfig()
        
        # Mock the async engine and connection
        mock_async_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_async_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch.object(config, 'get_async_engine', return_value=mock_async_engine):
            await config.create_tables()
            
            # Verify that run_sync was called on the connection
            mock_conn.run_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_drop_tables(self):
        """Test table dropping."""
        config = DatabaseConfig()
        
        # Mock the async engine and connection
        mock_async_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_async_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch.object(config, 'get_async_engine', return_value=mock_async_engine):
            await config.drop_tables()
            
            # Verify that run_sync was called on the connection
            mock_conn.run_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_connection_success(self):
        """Test successful connection check."""
        config = DatabaseConfig()
        
        # Mock the async engine and connection
        mock_async_engine = AsyncMock()
        mock_conn = AsyncMock()
        mock_async_engine.begin.return_value.__aenter__.return_value = mock_conn
        
        with patch.object(config, 'get_async_engine', return_value=mock_async_engine):
            result = await config.check_connection()
            assert result is True
            mock_conn.execute.assert_called_once_with("SELECT 1")
    
    @pytest.mark.asyncio
    async def test_check_connection_failure(self):
        """Test failed connection check."""
        config = DatabaseConfig()
        
        # Mock the async engine to raise an exception
        mock_async_engine = AsyncMock()
        mock_async_engine.begin.side_effect = OperationalError("Connection failed", None, None)
        
        with patch.object(config, 'get_async_engine', return_value=mock_async_engine):
            result = await config.check_connection()
            assert result is False
    
    def test_close_connections(self):
        """Test connection cleanup."""
        config = DatabaseConfig()
        
        # Mock engines
        mock_engine = Mock()
        mock_async_engine = AsyncMock()
        
        config._engine = mock_engine
        config._async_engine = mock_async_engine
        
        with patch('asyncio.create_task') as mock_create_task:
            config.close_connections()
            
            # Verify engines are disposed
            mock_engine.dispose.assert_called_once()
            mock_create_task.assert_called_once()


class TestSessionManagement:
    """Test cases for session management functions."""
    
    def test_get_db_session(self):
        """Test synchronous session dependency."""
        # Mock the session factory and session
        mock_session = Mock()
        mock_factory = Mock()
        mock_factory.return_value = mock_session
        
        with patch.object(db_config, 'get_session_factory', return_value=mock_factory):
            # Test the generator
            session_gen = get_db_session()
            session = next(session_gen)
            
            assert session == mock_session
            
            # Test cleanup
            try:
                next(session_gen)
            except StopIteration:
                pass
            
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_async_db_session(self):
        """Test async session context manager."""
        # Mock the async session factory and session
        mock_session = AsyncMock()
        mock_factory = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None
        
        with patch.object(db_config, 'get_async_session_factory', return_value=mock_factory):
            async with get_async_db_session() as session:
                assert session == mock_session
    
    @pytest.mark.asyncio
    async def test_get_async_db_session_dependency(self):
        """Test async session dependency for FastAPI."""
        # Mock the async session
        mock_session = AsyncMock()
        
        with patch('config.database.get_async_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            # Test the async generator
            session_gen = get_async_db_session_dependency()
            session = await session_gen.__anext__()
            
            assert session == mock_session


class TestDatabaseHealthCheck:
    """Test cases for DatabaseHealthCheck class."""
    
    @pytest.mark.asyncio
    async def test_check_database_health_success(self):
        """Test successful database health check."""
        # Mock successful connection check
        with patch.object(db_config, 'check_connection', return_value=True):
            # Mock engine and pool
            mock_pool = Mock()
            mock_pool.size.return_value = 10
            mock_pool.checkedin.return_value = 8
            mock_pool.checkedout.return_value = 2
            mock_pool.overflow.return_value = 0
            mock_pool.invalid.return_value = 0
            
            mock_engine = Mock()
            mock_engine.pool = mock_pool
            
            with patch.object(db_config, 'get_async_engine', return_value=mock_engine):
                # Mock session and query result
                mock_session = AsyncMock()
                mock_result = Mock()
                mock_result.scalar.return_value = 42
                mock_session.execute.return_value = mock_result
                
                with patch('config.database.get_async_db_session') as mock_get_session:
                    mock_get_session.return_value.__aenter__.return_value = mock_session
                    mock_get_session.return_value.__aexit__.return_value = None
                    
                    health_status = await DatabaseHealthCheck.check_database_health()
                    
                    assert health_status["database_connected"] is True
                    assert health_status["connection_pool_status"]["pool_size"] == 10
                    assert health_status["connection_pool_status"]["checked_in"] == 8
                    assert health_status["connection_pool_status"]["checked_out"] == 2
                    assert health_status["query_performance"]["total_jobs"] == 42
                    assert "test_query_time_ms" in health_status["query_performance"]
                    assert health_status["error_message"] is None
    
    @pytest.mark.asyncio
    async def test_check_database_health_failure(self):
        """Test failed database health check."""
        # Mock failed connection check
        with patch.object(db_config, 'check_connection', return_value=False):
            health_status = await DatabaseHealthCheck.check_database_health()
            
            assert health_status["database_connected"] is False
            assert health_status["connection_pool_status"] == {}
            assert health_status["query_performance"] == {}
            assert health_status["error_message"] is None
    
    @pytest.mark.asyncio
    async def test_check_database_health_exception(self):
        """Test database health check with exception."""
        # Mock connection check to raise exception
        with patch.object(db_config, 'check_connection', side_effect=Exception("Test error")):
            health_status = await DatabaseHealthCheck.check_database_health()
            
            assert health_status["database_connected"] is False
            assert health_status["error_message"] == "Test error"


class TestDatabaseMigrationHelper:
    """Test cases for DatabaseMigrationHelper class."""
    
    @pytest.mark.asyncio
    async def test_initialize_database(self):
        """Test database initialization."""
        with patch.object(db_config, 'create_tables') as mock_create_tables:
            await DatabaseMigrationHelper.initialize_database()
            mock_create_tables.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_database_failure(self):
        """Test database initialization failure."""
        with patch.object(db_config, 'create_tables', side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                await DatabaseMigrationHelper.initialize_database()
    
    @pytest.mark.asyncio
    async def test_reset_database(self):
        """Test database reset."""
        with patch.object(db_config, 'drop_tables') as mock_drop_tables, \
             patch.object(db_config, 'create_tables') as mock_create_tables:
            
            await DatabaseMigrationHelper.reset_database()
            
            mock_drop_tables.assert_called_once()
            mock_create_tables.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_database_failure(self):
        """Test database reset failure."""
        with patch.object(db_config, 'drop_tables', side_effect=Exception("Reset failed")):
            with pytest.raises(Exception, match="Reset failed"):
                await DatabaseMigrationHelper.reset_database()
    
    @pytest.mark.asyncio
    async def test_backup_database(self):
        """Test database backup placeholder."""
        # This is just a placeholder test since the actual implementation
        # would depend on specific backup requirements
        await DatabaseMigrationHelper.backup_database("/tmp/backup.sql")
        # No assertions needed as it's just a placeholder


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    @pytest.mark.asyncio
    async def test_execute_raw_query(self):
        """Test raw query execution."""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [("result1",), ("result2",)]
        mock_session.execute.return_value = mock_result
        
        with patch('config.database.get_async_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            results = await execute_raw_query("SELECT * FROM test_table", {"param": "value"})
            
            assert results == [("result1",), ("result2",)]
            mock_session.execute.assert_called_once_with("SELECT * FROM test_table", {"param": "value"})
    
    @pytest.mark.asyncio
    async def test_execute_raw_query_no_params(self):
        """Test raw query execution without parameters."""
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [("result",)]
        mock_session.execute.return_value = mock_result
        
        with patch('config.database.get_async_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            results = await execute_raw_query("SELECT 1")
            
            assert results == [("result",)]
            mock_session.execute.assert_called_once_with("SELECT 1", {})
    
    @pytest.mark.asyncio
    async def test_get_database_stats_success(self):
        """Test successful database stats retrieval."""
        mock_session = AsyncMock()
        
        # Mock results for table counts
        table_results = [Mock(), Mock(), Mock(), Mock()]
        table_results[0].scalar.return_value = 10  # scraping_jobs
        table_results[1].scalar.return_value = 50  # scraped_data
        table_results[2].scalar.return_value = 25  # job_logs
        table_results[3].scalar.return_value = 100  # system_metrics
        
        # Mock result for database size
        size_result = Mock()
        size_result.scalar.return_value = "10 MB"
        
        mock_session.execute.side_effect = table_results + [size_result]
        
        with patch('config.database.get_async_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None
            
            stats = await get_database_stats()
            
            assert stats["scraping_jobs_count"] == 10
            assert stats["scraped_data_count"] == 50
            assert stats["job_logs_count"] == 25
            assert stats["system_metrics_count"] == 100
            assert stats["database_size"] == "10 MB"
            assert "error" not in stats
    
    @pytest.mark.asyncio
    async def test_get_database_stats_failure(self):
        """Test database stats retrieval failure."""
        with patch('config.database.get_async_db_session', side_effect=Exception("DB Error")):
            stats = await get_database_stats()
            
            assert "error" in stats
            assert stats["error"] == "DB Error"


class TestEngineEventListeners:
    """Test cases for engine event listeners."""
    
    @patch('config.database.get_settings')
    def test_setup_engine_events(self, mock_get_settings):
        """Test that engine event listeners are set up correctly."""
        mock_settings = Mock()
        mock_settings.db_user = "testuser"
        mock_settings.db_password = "testpass"
        mock_settings.db_host = "localhost"
        mock_settings.db_port = 5432
        mock_settings.db_name = "testdb"
        mock_settings.db_pool_size = 10
        mock_settings.db_max_overflow = 20
        mock_settings.db_echo = False
        mock_get_settings.return_value = mock_settings
        
        with patch('config.database.create_engine') as mock_create_engine, \
             patch('config.database.event') as mock_event:
            
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            
            config = DatabaseConfig()
            config.get_engine()
            
            # Verify that event listeners were set up
            assert mock_event.listens_for.call_count >= 2  # At least connect and checkout events