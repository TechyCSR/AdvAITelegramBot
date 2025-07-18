import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import logging
from database import user_db

logger = logging.getLogger(__name__)

@dataclass
class VideoAnalytics:
    """Analytics data for video generation."""
    request_id: str
    user_id: int
    prompt: str
    quality: str
    aspect_ratio: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    generation_time: Optional[float] = None
    tokens_used: int = 0
    enhanced_prompt: Optional[str] = None
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    views: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoAnalytics':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        datetime_fields = ['created_at', 'started_at', 'completed_at']
        for field in datetime_fields:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)

class VideoAnalyticsManager:
    """Manage video generation analytics and insights."""
    
    def __init__(self):
        self.collection_name = "video_analytics"
    
    def get_analytics_collection(self):
        """Get the analytics MongoDB collection."""
        try:
            return user_db.get_database()[self.collection_name]
        except Exception as e:
            logger.error(f"Failed to get analytics collection: {e}")
            return None
    
    async def record_generation_start(self, request_id: str, user_id: int, prompt: str, 
                                    quality: str, aspect_ratio: str, tokens_used: int) -> bool:
        """Record the start of video generation."""
        try:
            analytics = VideoAnalytics(
                request_id=request_id,
                user_id=user_id,
                prompt=prompt,
                quality=quality,
                aspect_ratio=aspect_ratio,
                status="started",
                created_at=datetime.now(),
                started_at=datetime.now(),
                tokens_used=tokens_used
            )
            
            collection = self.get_analytics_collection()
            if collection:
                collection.insert_one(analytics.to_dict())
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to record generation start: {e}")
            return False
    
    async def record_generation_completion(self, request_id: str, generation_time: float, 
                                         file_size: Optional[int] = None, 
                                         enhanced_prompt: Optional[str] = None) -> bool:
        """Record the completion of video generation."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return False
            
            update_data = {
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "generation_time": generation_time
            }
            
            if file_size:
                update_data["file_size"] = file_size
            if enhanced_prompt:
                update_data["enhanced_prompt"] = enhanced_prompt
            
            result = collection.update_one(
                {"request_id": request_id},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to record generation completion: {e}")
            return False
    
    async def record_generation_failure(self, request_id: str, error_message: str) -> bool:
        """Record a failed video generation."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return False
            
            result = collection.update_one(
                {"request_id": request_id},
                {"$set": {
                    "status": "failed",
                    "completed_at": datetime.now().isoformat(),
                    "error_message": error_message
                }}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to record generation failure: {e}")
            return False
    
    async def increment_video_views(self, request_id: str) -> bool:
        """Increment view count for a video."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return False
            
            result = collection.update_one(
                {"request_id": request_id},
                {"$inc": {"views": 1}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to increment video views: {e}")
            return False
    
    async def get_user_analytics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics for a user."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return {}
            
            # Date range
            start_date = datetime.now() - timedelta(days=days)
            
            # Aggregate user data
            pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "created_at": {"$gte": start_date.isoformat()}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "completed_videos": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                        "failed_videos": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        },
                        "total_tokens_used": {"$sum": "$tokens_used"},
                        "total_generation_time": {"$sum": "$generation_time"},
                        "total_views": {"$sum": "$views"},
                        "avg_generation_time": {"$avg": "$generation_time"},
                        "quality_breakdown": {
                            "$push": "$quality"
                        }
                    }
                }
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if not result:
                return {
                    "total_requests": 0,
                    "completed_videos": 0,
                    "failed_videos": 0,
                    "success_rate": 0,
                    "total_tokens_used": 0,
                    "total_generation_time": 0,
                    "avg_generation_time": 0,
                    "total_views": 0,
                    "quality_breakdown": {},
                    "recent_requests": []
                }
            
            data = result[0]
            
            # Calculate success rate
            total_requests = data.get("total_requests", 0)
            completed_videos = data.get("completed_videos", 0)
            success_rate = (completed_videos / total_requests * 100) if total_requests > 0 else 0
            
            # Quality breakdown
            quality_counts = {}
            for quality in data.get("quality_breakdown", []):
                quality_counts[quality] = quality_counts.get(quality, 0) + 1
            
            # Get recent requests
            recent_requests = list(collection.find(
                {"user_id": user_id},
                sort=[("created_at", -1)],
                limit=10
            ))
            
            return {
                "total_requests": total_requests,
                "completed_videos": completed_videos,
                "failed_videos": data.get("failed_videos", 0),
                "success_rate": round(success_rate, 1),
                "total_tokens_used": data.get("total_tokens_used", 0),
                "total_generation_time": round(data.get("total_generation_time", 0), 1),
                "avg_generation_time": round(data.get("avg_generation_time", 0), 1),
                "total_views": data.get("total_views", 0),
                "quality_breakdown": quality_counts,
                "recent_requests": recent_requests
            }
            
        except Exception as e:
            logger.error(f"Failed to get user analytics: {e}")
            return {}
    
    async def get_global_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get global platform analytics."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return {}
            
            start_date = datetime.now() - timedelta(days=days)
            
            pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": start_date.isoformat()}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_requests": {"$sum": 1},
                        "unique_users": {"$addToSet": "$user_id"},
                        "completed_videos": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                        "failed_videos": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        },
                        "total_tokens_used": {"$sum": "$tokens_used"},
                        "total_generation_time": {"$sum": "$generation_time"},
                        "total_views": {"$sum": "$views"},
                        "avg_generation_time": {"$avg": "$generation_time"},
                        "quality_breakdown": {"$push": "$quality"},
                        "aspect_ratio_breakdown": {"$push": "$aspect_ratio"}
                    }
                },
                {
                    "$project": {
                        "total_requests": 1,
                        "unique_users_count": {"$size": "$unique_users"},
                        "completed_videos": 1,
                        "failed_videos": 1,
                        "total_tokens_used": 1,
                        "total_generation_time": 1,
                        "total_views": 1,
                        "avg_generation_time": 1,
                        "quality_breakdown": 1,
                        "aspect_ratio_breakdown": 1
                    }
                }
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if not result:
                return {}
            
            data = result[0]
            
            # Calculate additional metrics
            total_requests = data.get("total_requests", 0)
            completed_videos = data.get("completed_videos", 0)
            success_rate = (completed_videos / total_requests * 100) if total_requests > 0 else 0
            
            # Quality breakdown
            quality_counts = {}
            for quality in data.get("quality_breakdown", []):
                quality_counts[quality] = quality_counts.get(quality, 0) + 1
            
            # Aspect ratio breakdown
            ratio_counts = {}
            for ratio in data.get("aspect_ratio_breakdown", []):
                ratio_counts[ratio] = ratio_counts.get(ratio, 0) + 1
            
            return {
                "total_requests": total_requests,
                "unique_users": data.get("unique_users_count", 0),
                "completed_videos": completed_videos,
                "failed_videos": data.get("failed_videos", 0),
                "success_rate": round(success_rate, 1),
                "total_tokens_used": data.get("total_tokens_used", 0),
                "total_generation_time": round(data.get("total_generation_time", 0), 1),
                "avg_generation_time": round(data.get("avg_generation_time", 0), 1),
                "total_views": data.get("total_views", 0),
                "quality_breakdown": quality_counts,
                "aspect_ratio_breakdown": ratio_counts
            }
            
        except Exception as e:
            logger.error(f"Failed to get global analytics: {e}")
            return {}
    
    async def get_popular_prompts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular prompts based on success and views."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return []
            
            pipeline = [
                {
                    "$match": {
                        "status": "completed",
                        "prompt": {"$exists": True, "$ne": ""}
                    }
                },
                {
                    "$group": {
                        "_id": "$prompt",
                        "count": {"$sum": 1},
                        "total_views": {"$sum": "$views"},
                        "avg_generation_time": {"$avg": "$generation_time"},
                        "qualities_used": {"$push": "$quality"}
                    }
                },
                {
                    "$sort": {
                        "count": -1,
                        "total_views": -1
                    }
                },
                {
                    "$limit": limit
                }
            ]
            
            results = list(collection.aggregate(pipeline))
            
            popular_prompts = []
            for result in results:
                popular_prompts.append({
                    "prompt": result["_id"],
                    "usage_count": result["count"],
                    "total_views": result["total_views"],
                    "avg_generation_time": round(result["avg_generation_time"], 1),
                    "most_used_quality": max(set(result["qualities_used"]), 
                                           key=result["qualities_used"].count)
                })
            
            return popular_prompts
            
        except Exception as e:
            logger.error(f"Failed to get popular prompts: {e}")
            return []
    
    async def get_performance_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get performance trends over time."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return {}
            
            start_date = datetime.now() - timedelta(days=days)
            
            pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": start_date.isoformat()},
                        "status": "completed"
                    }
                },
                {
                    "$project": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": {"$dateFromString": {"dateString": "$created_at"}}
                            }
                        },
                        "generation_time": 1,
                        "quality": 1
                    }
                },
                {
                    "$group": {
                        "_id": "$date",
                        "count": {"$sum": 1},
                        "avg_generation_time": {"$avg": "$generation_time"},
                        "quality_breakdown": {"$push": "$quality"}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            results = list(collection.aggregate(pipeline))
            
            trends = {
                "daily_counts": [],
                "daily_avg_times": [],
                "dates": []
            }
            
            for result in results:
                trends["dates"].append(result["_id"])
                trends["daily_counts"].append(result["count"])
                trends["daily_avg_times"].append(round(result["avg_generation_time"], 1))
            
            return trends
            
        except Exception as e:
            logger.error(f"Failed to get performance trends: {e}")
            return {}
    
    async def get_user_leaderboard(self, metric: str = "completed_videos", limit: int = 10) -> List[Dict[str, Any]]:
        """Get user leaderboard based on various metrics."""
        try:
            collection = self.get_analytics_collection()
            if not collection:
                return []
            
            # Define aggregation based on metric
            if metric == "completed_videos":
                match_stage = {"status": "completed"}
                group_field = {"$sum": 1}
            elif metric == "tokens_used":
                match_stage = {}
                group_field = {"$sum": "$tokens_used"}
            elif metric == "total_views":
                match_stage = {"status": "completed"}
                group_field = {"$sum": "$views"}
            else:
                return []
            
            pipeline = [
                {"$match": match_stage},
                {
                    "$group": {
                        "_id": "$user_id",
                        "value": group_field,
                        "last_activity": {"$max": "$created_at"}
                    }
                },
                {"$sort": {"value": -1}},
                {"$limit": limit}
            ]
            
            results = list(collection.aggregate(pipeline))
            
            leaderboard = []
            for i, result in enumerate(results, 1):
                leaderboard.append({
                    "rank": i,
                    "user_id": result["_id"],
                    "value": result["value"],
                    "last_activity": result["last_activity"]
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Failed to get user leaderboard: {e}")
            return []

# Global analytics manager instance
analytics_manager = VideoAnalyticsManager()

# Convenience functions
async def record_generation_start(request_id: str, user_id: int, prompt: str, 
                                quality: str, aspect_ratio: str, tokens_used: int) -> bool:
    """Record the start of video generation."""
    return await analytics_manager.record_generation_start(
        request_id, user_id, prompt, quality, aspect_ratio, tokens_used
    )

async def record_generation_completion(request_id: str, generation_time: float, 
                                     file_size: Optional[int] = None, 
                                     enhanced_prompt: Optional[str] = None) -> bool:
    """Record the completion of video generation."""
    return await analytics_manager.record_generation_completion(
        request_id, generation_time, file_size, enhanced_prompt
    )

async def record_generation_failure(request_id: str, error_message: str) -> bool:
    """Record a failed video generation."""
    return await analytics_manager.record_generation_failure(request_id, error_message)

async def get_user_analytics(user_id: int, days: int = 30) -> Dict[str, Any]:
    """Get comprehensive analytics for a user."""
    return await analytics_manager.get_user_analytics(user_id, days)

async def get_global_analytics(days: int = 7) -> Dict[str, Any]:
    """Get global platform analytics."""
    return await analytics_manager.get_global_analytics(days)

async def increment_video_views(request_id: str) -> bool:
    """Increment view count for a video."""
    return await analytics_manager.increment_video_views(request_id)