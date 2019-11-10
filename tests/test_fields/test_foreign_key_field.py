import cacheorm as co
import pytest

from .test_models import TestModel


class User(TestModel):
    username = co.StringField()
    sub_user = co.ForeignKeyField("self", null=True, object_id_name="sub")


class Article(TestModel):
    author = co.ForeignKeyField(User)
    content = co.StringField()


def test_create():
    sam = User.create(username="sam")
    assert sam.sub is None
    assert sam.sub_user is None
    bob = User.create(username="bob")

    # access attributes of foreign key field after creation
    # does not trigger extra query
    with Article.mock_backend_method("get") as m:
        article = Article.insert(content="sam article", author=sam).execute()
        assert "sam" == article.author.username
        assert 0 == m.call_count

    # set to an integer in which case a query will occur
    with Article.mock_backend_method("get") as m:
        article = Article.insert(content="bob article", author=bob.id).execute()
        assert "bob" == article.author.username
        assert 1 == m.call_count

    # set the ID accessor directly
    with Article.mock_backend_method("get") as m:
        article = Article.insert(
            content="bob another article", author_id=bob.id
        ).execute()
        assert "bob" == article.author.username
        assert 1 == m.call_count


def test_query():
    sam = User.insert(username="sam").execute()
    article = Article.insert(content="sam article", author=sam).execute()
    with Article.mock_backend_method("get") as m:
        article_db = Article.get_by_id(article.id)
        assert sam.id == article_db.author_id
        assert 1 == m.call_count
        assert sam.username == article_db.author.username
        assert 2 == m.call_count
        with pytest.raises(AttributeError):
            _ = article_db.author.invalid
    with pytest.raises(AttributeError):
        _ = Article.author.invalid
    with pytest.raises(User.DoesNotExist):
        article = Article(content="non author")
        _ = article.author


def test_specify_object_id_name():
    with pytest.raises(ValueError):

        class T(TestModel):
            user = co.ForeignKeyField(User, object_id_name="user")

    sam1 = User.create(username="sam1")
    sam2 = User.create(username="sam2", sub_user=sam1)
    sam1_cache = User.get_by_id(sam1.id)
    assert sam1_cache.id == sam2.sub
    assert sam1.username == sam2.sub_user.username


class Like(TestModel):
    liker = co.ForeignKeyField(User)
    article = co.ForeignKeyField(Article)
    mark = co.StringField(default="")

    class Meta:
        primary_key = co.CompositeKey("liker", "article")


def test_composite_key_contain_foreign_key_fields():
    sam = User.create(username="sam")
    bob = User.create(username="bob")
    article = Article.create(content="sam article", author=sam)
    likes = Like.insert_many(
        {"liker": sam, "article": article, "mark": "myself"},
        {"liker_id": bob.id, "article": article.id},
    ).execute()
    assert likes[0].mark == Like.get_by_id((sam, article)).mark
    deleted = Like.delete(like=bob, article_id=article.id).execute()
    assert deleted is True
    with pytest.raises(Like.DoesNotExist):
        Like.get_by_id((sam.id, article))
    Like.set_by_id((sam, article), {"mark": "ohhhho"})
