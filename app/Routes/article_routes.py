from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from app.database import get_db
from app.models import Article, SavedArticle, User
from app.utils.auth import get_current_user
import uuid
from datetime import datetime
from app.analytics.posthog_client import track_event

router = APIRouter()

# ✅ Save article
@router.post("/save/{slug}")
async def save_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # get article by slug
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # check if already saved
    result = await db.execute(
        select(SavedArticle).where(
            SavedArticle.user_id == current_user.id,
            SavedArticle.article_id == article.id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"status": "already_saved"}

    saved = SavedArticle(
        id=uuid.uuid4(),
        user_id=current_user.id,
        article_id=article.id,
        created_at=datetime.utcnow(),
    )
    db.add(saved)
    article.save_count += 1  # ✅ increment global counter
    await db.commit()
    track_event(str(current_user.id), "article_saved", {"slug": slug})

    return {"status": "saved", "save_count": article.save_count}


# ✅ Get saved articles for current user
@router.get("/saved")
async def get_saved_articles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # join to fetch metadata
    result = await db.execute(
        select(Article)
        .join(SavedArticle, SavedArticle.article_id == Article.id)
        .where(SavedArticle.user_id == current_user.id)
    )
    articles = result.scalars().all()

    return {
        "saved": [
            {
                "slug": a.slug,
                "title": a.title,
                "excerpt": a.excerpt,
                "read_count": a.read_count,
                "save_count": a.save_count,
            }
            for a in articles
        ]
    }


# ✅ Unsave article
@router.delete("/save/{slug}")
async def unsave_article(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # delete the SavedArticle entry
    q = await db.execute(
        select(SavedArticle).where(
            SavedArticle.user_id == current_user.id,
            SavedArticle.article_id == article.id,
        )
    )
    saved = q.scalar_one_or_none()
    if not saved:
        raise HTTPException(status_code=404, detail="Not saved")

    await db.delete(saved)
    article.save_count = max(0, article.save_count - 1)  # ✅ decrement safely
    await db.commit()
    track_event(str(current_user.id), "article_unsaved", {"slug": slug})

    return {"status": "removed", "save_count": article.save_count}


# ✅ Check if current user saved a specific article
@router.get("/saved/{slug}")
async def is_article_saved(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    q = await db.execute(
        select(SavedArticle).where(
            SavedArticle.user_id == current_user.id,
            SavedArticle.article_id == article.id,
        )
    )
    saved = q.scalar_one_or_none()

    return {"isSaved": bool(saved)}

# ✅ Get top read articles
@router.get("/top")
async def get_top_articles(
    limit: int = 3,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Article).order_by(Article.read_count.desc()).limit(limit)
    )
    articles = result.scalars().all()

    return [
        {
            "slug": a.slug,
            "title": a.title,
            "excerpt": a.excerpt,
            "read_count": a.read_count,
            "save_count": a.save_count,
        }
        for a in articles
    ]

@router.post("/{slug}/read")
async def increment_article_read(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Article).where(Article.slug == slug))
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(404, "Article not found")

    article.read_count += 1
    article.updated_at = datetime.utcnow()
    await db.commit()
    track_event(None, "article_read", {"slug": slug})
    return {"slug": slug, "read_count": article.read_count}
