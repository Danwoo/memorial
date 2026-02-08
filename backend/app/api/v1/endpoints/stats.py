"""
Statistics API Endpoints
Dashboard data for analytics and insights
"""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta

from app.core.supabase import get_supabase_client
from app.schemas.stats import (
    OverviewStats,
    ActivityData,
    SourceStats,
    TagStats,
    StatsOverviewResponse,
)

router = APIRouter(prefix="/stats", tags=["stats"])


# ========================================
# Endpoints
# ========================================
@router.get("/overview", response_model=StatsOverviewResponse)
async def get_overview_stats():
    """
    Get comprehensive statistics overview for the dashboard.
    """
    db = get_supabase_client()
    
    # Get all memories
    all_memories = db.table("memories").select("id, source_type, created_at, tags").execute()
    memories = all_memories.data or []
    
    total = len(memories)
    
    # Calculate date ranges
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Count by time period
    this_week = 0
    this_month = 0
    day_counts = {}
    source_counts = {"WEB": 0, "PDF": 0, "NOTE": 0}
    tag_counts = {}
    
    for m in memories:
        created_at_str = m.get("created_at", "")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                
                if created_at >= week_ago:
                    this_week += 1
                if created_at >= month_ago:
                    this_month += 1
                
                # Group by day for activity
                day_key = created_at.strftime("%Y-%m-%d")
                day_counts[day_key] = day_counts.get(day_key, 0) + 1
            except Exception:
                pass
        
        # Source type counts
        source_type = m.get("source_type", "NOTE")
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        
        # Tag counts
        tags = m.get("tags") or []
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Find most active day
    most_active_day = None
    if day_counts:
        most_active_day = max(day_counts, key=day_counts.get)
    
    # Build recent activity (last 7 days)
    recent_activity = []
    for i in range(7):
        day = now - timedelta(days=i)
        day_key = day.strftime("%Y-%m-%d")
        recent_activity.append(ActivityData(
            date=day_key,
            count=day_counts.get(day_key, 0)
        ))
    recent_activity.reverse()
    
    # Build source stats
    sources = []
    for src, count in source_counts.items():
        percentage = (count / total * 100) if total > 0 else 0
        sources.append(SourceStats(
            source_type=src,
            count=count,
            percentage=round(percentage, 1)
        ))
    
    # Build top tags (top 10)
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_tags = [TagStats(tag=t[0], count=t[1]) for t in sorted_tags]
    
    return StatsOverviewResponse(
        overview=OverviewStats(
            total_memories=total,
            total_this_week=this_week,
            total_this_month=this_month,
            most_active_day=most_active_day
        ),
        recent_activity=recent_activity,
        sources=sources,
        top_tags=top_tags
    )


@router.get("/activity")
async def get_activity_data(
    range: str = Query("7d", description="Time range: 7d, 30d, 90d")
):
    """
    Get daily activity data for a specific time range.
    """
    db = get_supabase_client()
    
    days_map = {"7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(range, 7)
    
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Query memories in range
    memories = db.table("memories")\
        .select("created_at")\
        .gte("created_at", start_date.isoformat())\
        .execute()
    
    # Group by day
    day_counts = {}
    for i in range(days):
        day = now - timedelta(days=i)
        day_counts[day.strftime("%Y-%m-%d")] = 0
    
    for m in memories.data or []:
        created_at_str = m.get("created_at", "")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                day_key = created_at.strftime("%Y-%m-%d")
                if day_key in day_counts:
                    day_counts[day_key] += 1
            except Exception:
                pass
    
    # Sort by date
    sorted_data = sorted(day_counts.items())
    return [{"date": d[0], "count": d[1]} for d in sorted_data]


@router.get("/timeline")
async def get_timeline_data(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get memories grouped by date for timeline view.
    """
    db = get_supabase_client()
    
    offset = (page - 1) * limit
    
    # Query memories with pagination, ordered by date
    result = db.table("memories")\
        .select("id, title, summary, source_type, created_at, tags")\
        .order("created_at", desc=True)\
        .range(offset, offset + limit - 1)\
        .execute()
    
    memories = result.data or []
    
    # Group by date
    grouped = {}
    for m in memories:
        created_at_str = m.get("created_at", "")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
                day_key = created_at.strftime("%Y-%m-%d")
                if day_key not in grouped:
                    grouped[day_key] = []
                grouped[day_key].append(m)
            except Exception:
                pass
    
    # Convert to list format
    timeline = [
        {"date": date, "memories": items}
        for date, items in sorted(grouped.items(), reverse=True)
    ]
    
    return {
        "page": page,
        "limit": limit,
        "timeline": timeline,
        "has_more": len(memories) == limit
    }
