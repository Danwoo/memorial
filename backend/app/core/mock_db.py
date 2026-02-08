"""
Mock Supabase Client for Local Testing
Mimics the interface of supabase-py client
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from uuid import uuid4

# In-memory storage
MOCK_DATA = {
    "memories": [],
    "chat_sessions": []
}

class MockResponse:
    def __init__(self, data: Any, count: int = 0):
        self.data = data
        self.count = count

class MockQueryBuilder:
    def __init__(self, table: str, data: List[Dict]):
        self.table = table
        self.current_data = data
        self.filters = []
        self.limit_val = None
        self.offset_val = 0
        self.order_by = None
    
    def select(self, columns: str = "*", count: Optional[str] = None):
        return self
        
    def insert(self, data: Dict):
        # Simulate ID generation and timestamp
        if "id" not in data:
            data["id"] = str(uuid4())
        
        # Add to global store
        MOCK_DATA[self.table].append(data)
        
        # Return the inserted data
        return MockResponse(data=[data])
        
    def update(self, data: Dict):
        self.update_data = data
        return self
        
    def delete(self):
        self.is_delete = True
        return self
        
    def eq(self, column: str, value: Any):
        self.filters.append((column, value))
        return self
        
    def or_(self, query: str):
        # Simple mock support for OR: just ignore for MVP test
        return self
        
    def order(self, column: str, desc: bool = False):
        self.order_by = (column, desc)
        return self
        
    def range(self, start: int, end: int):
        self.offset_val = start
        self.limit_val = end - start + 1
        return self
        
    def single(self):
        self.is_single = True
        return self
        
    def execute(self):
        filtered = self.current_data
        
        # Apply filters (AND logic)
        for col, val in self.filters:
            filtered = [item for item in filtered if str(item.get(col)) == str(val)]
            
        # Apply update
        if hasattr(self, 'update_data'):
            for item in filtered:
                item.update(self.update_data)
            return MockResponse(data=filtered)
            
        # Apply delete
        if hasattr(self, 'is_delete'):
            # Remove from global store
            MOCK_DATA[self.table] = [item for item in MOCK_DATA[self.table] if item not in filtered]
            return MockResponse(data=filtered)
            
        # Apply sorting
        if self.order_by:
            col, desc = self.order_by
            # Simple string sort
            filtered.sort(key=lambda x: str(x.get(col, "")), reverse=desc)
            
        # Apply pagination
        total = len(filtered)
        if self.limit_val:
            filtered = filtered[self.offset_val : self.offset_val + self.limit_val]
            
        # Apply single
        if hasattr(self, 'is_single'):
            data = filtered[0] if filtered else None
            return MockResponse(data=data)
            
        return MockResponse(data=filtered, count=total)

class MockClient:
    def __init__(self, url: str, key: str):
        self.supabase_url = url
        self.supabase_key = key
        
    def table(self, name: str):
        if name not in MOCK_DATA:
            MOCK_DATA[name] = []
        return MockQueryBuilder(name, MOCK_DATA[name])

    def rpc(self, func_name: str, params: Dict):
        """
        Mock RPC call. 
        For match_memories, return dummy similarity search results.
        """
        if func_name == "match_memories":
            # Return checks from stored memories
            # Just return last 3 memories as 'similar'
            memories = MOCK_DATA.get("memories", [])
            # Sort by created_at (simple mock)
            results = sorted(memories, key=lambda x: x.get("created_at", ""), reverse=True)[:3]
            
            # Add similarity score
            for m in results:
                m["similarity"] = 0.95
                
            return MockQueryBuilder("memories", results)
            
        return MockQueryBuilder("unknown", [])

print("WARNING: Using Mock Supabase Client for Testing")
