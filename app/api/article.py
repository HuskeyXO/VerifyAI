from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.article import Article
from app.models.source import Source
from app.schemas.article import ArticleCreate, ArticleResponse

router = APIRouter(
    prefix="/articles",
    tags=["Articles"]
)

@router.post("/", response_model=ArticleResponse, status_code=status.HTTP_201_CREATED)
def create_source(article: ArticleCreate, db: Session = Depends(get_db)):


    source = ( db.query(Source).filter(Source.id == article.source_id).first() )

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="source not found"
        )


    new_article = Article(
        source_id = article.source_id,
        title = article.title,
        url = article.url,
        author = article.author,
        content = article.content,
        published_at = article.published_at

    )

    db.add(new_article)
    db.commit()
    db.refresh(new_article)

    return new_article
