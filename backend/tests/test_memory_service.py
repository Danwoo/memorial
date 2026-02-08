"""
Unit Tests for Memory Service
Example test file demonstrating testing patterns with DI
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from app.services.memory_service import MemoryService
from app.schemas.memory import MemoryInDB, SourceType


class TestMemoryService:
    """Test cases for MemoryService"""
    
    @pytest.fixture
    def mock_memory_repo(self):
        """Create mock MemoryRepository"""
        repo = MagicMock()
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_user = AsyncMock()
        repo.update_status = AsyncMock()
        repo.delete = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_vector_repo(self):
        """Create mock VectorRepository"""
        repo = MagicMock()
        repo.save_embedding = AsyncMock()
        repo.similarity_search = AsyncMock()
        return repo
    
    @pytest.fixture
    def mock_graph_repo(self):
        """Create mock GraphRepository"""
        repo = MagicMock()
        repo.is_connected = True
        repo.save_entities = AsyncMock()
        repo.save_relations = AsyncMock()
        return repo
    
    @pytest.fixture
    def memory_service(self, mock_memory_repo, mock_vector_repo, mock_graph_repo):
        """Create MemoryService with mocked dependencies"""
        return MemoryService(mock_memory_repo, mock_vector_repo, mock_graph_repo)
    
    @pytest.mark.asyncio
    async def test_create_memory_success(self, memory_service, mock_memory_repo, mock_vector_repo):
        """Test successful memory creation"""
        # Arrange
        user_id = UUID("00000000-0000-0000-0000-000000000001")
        expected_memory = MemoryInDB(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            user_id=user_id,
            title="Test Memory",
            content="Test content",
            source_type="NOTE",
            status="processing",
            created_at=None,
            updated_at=None
        )
        mock_memory_repo.create.return_value = expected_memory
        
        # Act
        result = await memory_service.create_memory(
            user_id=user_id,
            title="Test Memory",
            content="Test content",
            source_type="NOTE"
        )
        
        # Assert
        assert result.id == expected_memory.id
        assert result.title == "Test Memory"
        mock_memory_repo.create.assert_called_once()
        mock_vector_repo.save_embedding.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_memory_found(self, memory_service, mock_memory_repo):
        """Test getting existing memory"""
        # Arrange
        memory_id = UUID("00000000-0000-0000-0000-000000000002")
        user_id = UUID("00000000-0000-0000-0000-000000000001")
        expected_memory = MemoryInDB(
            id=memory_id,
            user_id=user_id,
            title="Test Memory",
            content="Test content",
            source_type="NOTE",
            status="completed",
            created_at=None,
            updated_at=None
        )
        mock_memory_repo.get_by_id.return_value = expected_memory
        
        # Act
        result = await memory_service.get_memory(memory_id, user_id)
        
        # Assert
        assert result is not None
        assert result.id == memory_id
        mock_memory_repo.get_by_id.assert_called_once_with(memory_id, user_id)
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, memory_service, mock_memory_repo):
        """Test getting non-existent memory"""
        # Arrange
        mock_memory_repo.get_by_id.return_value = None
        
        # Act
        result = await memory_service.get_memory(
            UUID("00000000-0000-0000-0000-000000000099"),
            UUID("00000000-0000-0000-0000-000000000001")
        )
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_list_memories(self, memory_service, mock_memory_repo):
        """Test listing memories with pagination"""
        # Arrange
        user_id = UUID("00000000-0000-0000-0000-000000000001")
        expected_memories = [
            MemoryInDB(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                user_id=user_id,
                title="Memory 1",
                content="Content 1",
                source_type="NOTE",
                status="completed",
                created_at=None,
                updated_at=None
            )
        ]
        mock_memory_repo.get_by_user.return_value = (expected_memories, 1)
        
        # Act
        items, total = await memory_service.list_memories(user_id, page=1, limit=20)
        
        # Assert
        assert len(items) == 1
        assert total == 1
        mock_memory_repo.get_by_user.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_memory_success(self, memory_service, mock_memory_repo):
        """Test successful memory deletion"""
        # Arrange
        mock_memory_repo.delete.return_value = True
        
        # Act
        result = await memory_service.delete_memory(
            UUID("00000000-0000-0000-0000-000000000002"),
            UUID("00000000-0000-0000-0000-000000000001")
        )
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_update_after_processing_with_graph(
        self, 
        memory_service, 
        mock_memory_repo, 
        mock_graph_repo
    ):
        """Test updating memory after Librarian processing with graph data"""
        # Arrange
        memory_id = UUID("00000000-0000-0000-0000-000000000002")
        mock_memory_repo.update_status.return_value = True
        
        entities = [{"name": "Python", "type": "Technology"}]
        relations = [{"source": "Python", "target": "Programming", "type": "IS_A"}]
        
        # Act
        result = await memory_service.update_memory_after_processing(
            memory_id=memory_id,
            summary="Test summary",
            tags=["python", "programming"],
            entities=entities,
            relations=relations
        )
        
        # Assert
        assert result is True
        mock_memory_repo.update_status.assert_called_once()
        mock_graph_repo.save_entities.assert_called_once()
        mock_graph_repo.save_relations.assert_called_once()
