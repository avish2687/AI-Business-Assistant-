from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from app.services.ai_service import (
    generate_marketing_content,
    generate_business_plan_section,
    analyze_competitors,
    generate_social_media_posts,
)

router = APIRouter()


# --- Request / Response Models ---

class MarketingRequest(BaseModel):
    business_type: str = Field(..., example="online bakery", description="Type of business")
    goal: str = Field(..., example="increase online sales by 30%", description="Marketing goal")

class MarketingResponse(BaseModel):
    response: str

class BusinessPlanRequest(BaseModel):
    business_type: str = Field(..., example="SaaS startup")
    section: str = Field(..., example="Executive Summary", description="Section of business plan")
    context: Optional[str] = Field("", example="B2B HR software targeting SMEs")

class CompetitorRequest(BaseModel):
    business_type: str = Field(..., example="fitness app")
    market: str = Field(..., example="India tier-2 cities")

class SocialMediaRequest(BaseModel):
    business_type: str = Field(..., example="handmade jewelry store")
    platform: str = Field(..., example="Instagram", description="Platform: Instagram, Twitter, LinkedIn")
    topic: str = Field(..., example="Diwali sale announcement")
    count: int = Field(3, ge=1, le=5)


# --- Endpoints ---

@router.post("/generate-content", response_model=MarketingResponse)
def generate_content(req: MarketingRequest):
    """Generate marketing content (headline, pitch, CTAs) for a business."""
    try:
        result = generate_marketing_content(req.business_type, req.goal)
        return {"response": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/business-plan")
def business_plan_section(req: BusinessPlanRequest):
    """Generate a specific section of a business plan."""
    try:
        result = generate_business_plan_section(req.business_type, req.section, req.context)
        return {"section": req.section, "content": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitor-analysis")
def competitor_analysis(req: CompetitorRequest):
    """Analyze competitors for a given business and market."""
    try:
        result = analyze_competitors(req.business_type, req.market)
        return {"business_type": req.business_type, "market": req.market, "analysis": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/social-media-posts")
def social_media(req: SocialMediaRequest):
    """Generate social media posts for a business."""
    try:
        posts = generate_social_media_posts(
            req.business_type, req.platform, req.topic, req.count
        )
        return {"platform": req.platform, "posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
