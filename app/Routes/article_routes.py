from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import SavedArticle, User
from app.utils.auth import get_current_user
import uuid
from fastapi import Body

router = APIRouter()

# ✅ Save article
@router.post("/save/{slug}")
async def save_article(
    slug: str,
    payload: dict = Body(...),  # ✅ expect { title, excerpt }
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(SavedArticle).where(
            SavedArticle.user_id == current_user.id,
            SavedArticle.article_slug == slug
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"status": "already_saved"}

    saved = SavedArticle(
        id=uuid.uuid4(),
        user_id=current_user.id,
        article_slug=slug,
        title=payload.get("title"),
        excerpt=payload.get("excerpt"),
    )
    db.add(saved)
    await db.commit()
    return {"status": "saved"}


# ✅ Get saved articles
@router.get("/saved")
async def get_saved_articles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(SavedArticle).where(SavedArticle.user_id == current_user.id)
    )
    saved = result.scalars().all()

    return {
        "saved": [
            {
                "slug": s.article_slug,
                "title": s.title,
                "excerpt": s.excerpt,
            }
            for s in saved
        ]
    }


# ✅ Unsave article
@router.delete("/save/{slug}")
async def unsave_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(SavedArticle).where(
            SavedArticle.user_id == current_user.id,
            SavedArticle.article_slug == slug
        )
    )
    saved = result.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Not saved")

    await db.delete(saved)
    await db.commit()
    return {"status": "removed"}

@router.get("/saved/{slug}")
async def is_article_saved(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(SavedArticle).where(
            SavedArticle.user_id == current_user.id,
            SavedArticle.article_slug == slug,
        )
    )
    saved = result.scalar_one_or_none()
    return {"isSaved": bool(saved)}   # ✅ simple boolean response
