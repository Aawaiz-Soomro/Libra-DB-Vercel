from datetime import date, timedelta

from . import db
from .models import Book, Booking, Category, Rating, User


def _ensure_category(name: str) -> Category:
    category = Category.query.filter_by(name=name).first()
    if category:
        return category
    category = Category(name=name)
    db.session.add(category)
    return category


def _ensure_user(name: str, email: str, role: str, password: str, approved: bool) -> User:
    user = User.query.filter_by(email=email).first()
    if user:
        # Backfill password/role/approval if an old record exists
        if not user.password_hash:
            user.set_password(password)
        if user.role != role:
            user.role = role
        if approved and not user.approved:
            user.approved = True
        return user

    user = User(name=name, email=email, role=role, approved=approved)
    user.set_password(password)
    db.session.add(user)
    return user


def _ensure_book(**kwargs) -> Book:
    isbn = kwargs["isbn"]
    book = Book.query.filter_by(isbn=isbn).first()
    if book:
        # Update copies if needed to avoid zeroing out availability
        book.copies_total = max(book.copies_total, kwargs.get("copies_total", book.copies_total))
        book.copies_available = max(
            book.copies_available,
            kwargs.get("copies_available", book.copies_available),
        )
        return book

    book = Book(**kwargs)
    db.session.add(book)
    return book


def seed_database() -> None:
    """Insert demo data without creating duplicates."""
    fiction = _ensure_category("Fiction")
    science = _ensure_category("Science")
    history = _ensure_category("History")
    db.session.flush()

    librarian = _ensure_user(
        name="Libby Librarian",
        email="librarian@example.com",
        role="librarian",
        password="admin123",
        approved=True,
    )
    alice = _ensure_user(
        name="Alice Johnson",
        email="alice@example.com",
        role="member",
        password="password123",
        approved=True,
    )
    bob = _ensure_user(
        name="Bob Smith",
        email="bob@example.com",
        role="member",
        password="password123",
        approved=True,
    )
    carol = _ensure_user(
        name="Carol Perez",
        email="carol@example.com",
        role="member",
        password="password123",
        approved=True,
    )
    db.session.flush()

    clean_code = _ensure_book(
        title="Clean Code",
        author="Robert C. Martin",
        isbn="9780132350884",
        description="Handbook of agile software craftsmanship.",
        category=science,
        copies_total=4,
        copies_available=4,
    )
    nineteen_eighty_four = _ensure_book(
        title="1984",
        author="George Orwell",
        isbn="9780451524935",
        description="Dystopian social science fiction novel.",
        category=fiction,
        copies_total=3,
        copies_available=3,
    )
    sapiens = _ensure_book(
        title="Sapiens",
        author="Yuval Noah Harari",
        isbn="9780062316097",
        description="Brief history of humankind.",
        category=history,
        copies_total=2,
        copies_available=2,
    )
    db.session.flush()

    if not Booking.query.filter_by(user_id=alice.id, book_id=clean_code.id).first():
        booking = Booking(
            user=alice,
            book=clean_code,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=7),
            approved=True,
            return_requested=False,
            returned=False,
            fine_amount=0,
        )
        clean_code.copies_available = max(clean_code.copies_available - 1, 0)
        db.session.add(booking)

    if not Rating.query.filter_by(user_id=alice.id, book_id=clean_code.id).first():
        db.session.add(Rating(user=alice, book=clean_code, score=5, comment="Great reference!"))
    if not Rating.query.filter_by(user_id=bob.id, book_id=nineteen_eighty_four.id).first():
        db.session.add(Rating(user=bob, book=nineteen_eighty_four, score=4, comment="A classic."))
    if not Rating.query.filter_by(user_id=carol.id, book_id=sapiens.id).first():
        db.session.add(Rating(user=carol, book=sapiens, score=5, comment="Eye opening."))

    db.session.commit()
    print("Seed data inserted or refreshed.")
