"""Publish Forge Pro — campaigns, scheduler, publishing queue (UI-first, no live integrations)."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict

from core import db, new_id, now_iso

router = APIRouter(prefix="/api", tags=["publish"])

PLATFORMS = ["youtube", "facebook", "instagram", "tiktok", "linkedin", "x"]


class Campaign(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: Optional[str] = None
    name: str
    goal: str = ""
    color: str = "#6D3BFF"
    status: str = "active"
    created_at: str = Field(default_factory=now_iso)


class CampaignCreate(BaseModel):
    name: str
    goal: str = ""
    color: str = "#6D3BFF"
    project_id: Optional[str] = None


class Post(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=new_id)
    project_id: Optional[str] = None
    campaign_id: Optional[str] = None
    title: str
    content: str = ""
    platforms: List[str] = Field(default_factory=list)
    scheduled_at: str = ""       # ISO datetime
    status: str = "scheduled"    # draft | scheduled | queued | published
    created_at: str = Field(default_factory=now_iso)


class PostCreate(BaseModel):
    title: str
    content: str = ""
    platforms: List[str] = Field(default_factory=list)
    scheduled_at: str = ""
    campaign_id: Optional[str] = None
    project_id: Optional[str] = None
    status: str = "scheduled"


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    platforms: Optional[List[str]] = None
    scheduled_at: Optional[str] = None
    campaign_id: Optional[str] = None
    status: Optional[str] = None


@router.get("/publish/platforms")
async def platforms():
    return PLATFORMS


# Campaigns
@router.get("/publish/campaigns", response_model=List[Campaign])
async def list_campaigns():
    return await db.campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("/publish/campaigns", response_model=Campaign)
async def create_campaign(body: CampaignCreate):
    c = Campaign(**body.model_dump())
    await db.campaigns.insert_one(c.model_dump())
    return c


@router.delete("/publish/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str):
    await db.campaigns.delete_one({"id": campaign_id})
    await db.posts.update_many({"campaign_id": campaign_id}, {"$set": {"campaign_id": None}})
    return {"ok": True}


# Posts / queue / calendar
@router.get("/publish/posts", response_model=List[Post])
async def list_posts(status: Optional[str] = None):
    query = {"status": status} if status else {}
    return await db.posts.find(query, {"_id": 0}).sort("scheduled_at", 1).to_list(2000)


@router.post("/publish/posts", response_model=Post)
async def create_post(body: PostCreate):
    p = Post(**body.model_dump())
    await db.posts.insert_one(p.model_dump())
    return p


@router.put("/publish/posts/{post_id}", response_model=Post)
async def update_post(post_id: str, body: PostUpdate):
    updates = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    res = await db.posts.update_one({"id": post_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Post not found")
    return await db.posts.find_one({"id": post_id}, {"_id": 0})


@router.delete("/publish/posts/{post_id}")
async def delete_post(post_id: str):
    await db.posts.delete_one({"id": post_id})
    return {"ok": True}
