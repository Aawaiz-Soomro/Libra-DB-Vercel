from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from . import db
from .models import Book, Booking, Category, Rating, User

bp = Blueprint("library", __name__)


def current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def current_role() -> str | None:
    user = current_user()
    if user:
        return user.role
    return None


def current_member() -> User | None:
    user = current_user()
    if not user or user.role != "member":
        return None
    return user


def require_role(role: str):
    user = current_user()
    if not user or user.role != role:
        flash("Please log in to access that portal.", "warning")
        return redirect(url_for("library.login", next=request.path))
    if not user.approved:
        session.clear()
        flash("Your account is awaiting librarian approval.", "warning")
        return redirect(url_for("library.login"))
    return None


@bp.app_context_processor
def inject_globals():
    return {
        "active_role": current_role(),
        "active_member": current_member(),
        "active_user": current_user(),
    }


def get_form_value(field_name: str, cast=str, default=None):
    value = request.form.get(field_name)
    if value is None or value == "":
        return default
    return cast(value)


@bp.route("/")
def index():
    # First touch should land on auth; if already signed in, route to the right portal.
    role = current_role()

    if role == "librarian":
        return redirect(url_for("library.admin_portal"))
    if role == "member":
        return redirect(url_for("library.member_portal"))

    return redirect(url_for("library.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        action = request.form.get("action", "login")

        if action == "register":
            name = get_form_value("name")
            email = get_form_value("email")
            password = get_form_value("password")
            if not all([name, email, password]):
                flash("Please provide name, email, and password to register.", "warning")
                return redirect(url_for("library.login"))

            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash("An account with that email already exists. Please log in.", "info")
                return redirect(url_for("library.login"))

            user = User(name=name, email=email, role="member", approved=False)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Registration submitted. A librarian must approve your account.", "success")
            return redirect(url_for("library.login"))

        email = get_form_value("email")
        password = get_form_value("password")

        if not email or not password:
            flash("Enter both email and password to sign in.", "warning")
            return redirect(url_for("library.login"))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid credentials. Please try again.", "danger")
            return redirect(url_for("library.login"))

        if not user.approved:
            flash("Your account is awaiting librarian approval.", "warning")
            return redirect(url_for("library.login"))

        session.clear()
        session["role"] = user.role
        session["user_id"] = user.id
        flash("Welcome back!", "success")
        next_page = request.args.get("next")
        if user.role == "librarian":
            return redirect(next_page or url_for("library.admin_portal"))
        return redirect(next_page or url_for("library.member_portal"))

    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("library.login"))


@bp.route("/admin")
def admin_portal():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    pending_users = User.query.filter_by(role="member", approved=False).count()
    pending_bookings = Booking.query.filter_by(approved=False).count()
    book_count = Book.query.count()
    user_count = User.query.count()
    booking_count = Booking.query.count()
    rating_count = Rating.query.count()

    recent_books = Book.query.order_by(Book.created_at.desc()).limit(5)
    active_bookings = (
        Booking.query.filter_by(returned=False, approved=True)
        .order_by(Booking.start_date.desc())
        .limit(5)
    )

    return render_template(
        "admin/dashboard.html",
        book_count=book_count,
        user_count=user_count,
        booking_count=booking_count,
        rating_count=rating_count,
        recent_books=recent_books,
        active_bookings=active_bookings,
        pending_users=pending_users,
        pending_bookings=pending_bookings,
    )


@bp.route("/member")
def member_portal():
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    member = current_member()
    open_bookings = (
        Booking.query.filter_by(user_id=member.id, returned=False)
        .order_by(Booking.start_date.desc())
        .limit(5)
    )
    recent_ratings = (
        Rating.query.filter_by(user_id=member.id)
        .order_by(Rating.created_at.desc())
        .limit(3)
    )
    suggested_books = Book.query.order_by(Book.created_at.desc()).limit(4)

    return render_template(
        "member/dashboard.html",
        member=member,
        open_bookings=open_bookings,
        recent_ratings=recent_ratings,
        suggested_books=suggested_books,
    )


@bp.route("/portfolio")
def portfolio():
    hero = {
        "name": "Avery Quinn",
        "roles": ["CS Student", "Creative Coder", "Full-Stack Dev"],
        "tagline": "Design-forward developer crafting ultra-fast experiences.",
        "bio": (
            "I'm a computer science student obsessed with building polished, human-centered interfaces "
            "and performant systems. Here's a snapshot of the playground where I experiment with "
            "motion, micro-interactions, and emerging tech."
        ),
        "cta_primary": {"label": "Download Résumé", "url": "#"},
        "cta_secondary": {"label": "Let's Talk", "url": "#contact"},
    }

    stats = [
        {"label": "Projects", "value": "24", "detail": "concept-to-launch"},
        {"label": "Hackathons", "value": "12", "detail": "global podium finishes"},
        {"label": "Coffee", "value": "∞", "detail": "fueling late-night builds"},
    ]

    projects = [
        {
            "title": "NeuroEdge Studio",
            "subtitle": "Realtime AI dashboard for the creative industry",
            "description": "Designed a cinematic data canvas with GPU-accelerated visuals, sub-100ms interactions, and adaptive layouts.",
            "tags": ["WebGL", "FastAPI", "WebSockets", "UX"],
            "image": "https://images.unsplash.com/photo-1483478550801-ceba5fe50e8e?auto=format&fit=crop&w=1200&q=80",
            "link": "#",
        },
        {
            "title": "Pulseboard",
            "subtitle": "Low-latency ops board for campus mobility",
            "description": "Built an offline-first PWA with predictive routing, gradient theming, and tactile micro-interactions.",
            "tags": ["TypeScript", "PWA", "GraphQL", "Design Systems"],
            "image": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?auto=format&fit=crop&w=1200&q=80",
            "link": "#",
        },
        {
            "title": "Aurora Compiler",
            "subtitle": "DSL + compiler toolkit for shader artists",
            "description": "Created a playful syntax, VS Code extension, and visual debugger that transforms creative coding workflows.",
            "tags": ["Rust", "Compilers", "VS Code", "DX"],
            "image": "https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1200&q=80",
            "link": "#",
        },
    ]

    experiences = [
        {
            "role": "Product Engineering Intern",
            "company": "Nova Labs",
            "timeframe": "2023 — Present",
            "summary": "Prototyped motion-heavy dashboards and shipped production-ready React + Flask surfaces.",
            "highlights": [
                "Cut render times by 38% via memoized data flows",
                "Partnered with design to build a living design system",
            ],
        },
        {
            "role": "Research Fellow",
            "company": "Human-Computer Interaction Lab",
            "timeframe": "2022 — 2023",
            "summary": "Explored tangible interfaces and spatial computing for inclusive education.",
            "highlights": [
                "Co-authored paper on adaptive haptics",
                "Built AR storytelling toolkit adopted by 4 classrooms",
            ],
        },
        {
            "role": "Freelance Creative Technologist",
            "company": "Self-Initiated",
            "timeframe": "Ongoing",
            "summary": "Partner with early-stage founders to transform sketches into launch-ready experiences.",
            "highlights": [
                "End-to-end delivery of 7 branded microsites",
                "Integrated analytics + A/B testing for rapid learning",
            ],
        },
    ]

    skill_groups = [
        {"title": "Core Stack", "stack": ["Python", "TypeScript", "Rust", "Go", "SQL", "GraphQL"]},
        {"title": "Frameworks", "stack": ["React", "Next.js", "Flask", "FastAPI", "Tailwind", "Framer Motion"]},
        {"title": "Tooling", "stack": ["Figma", "Notion", "Blender", "Docker", "AWS", "Vite"]},
    ]

    spotlights = [
        {
            "title": "Current focus",
            "description": "Building ambient computing prototypes that blur the line between physical and digital worlds.",
        },
        {
            "title": "Recent win",
            "description": "Led a team of 4 to sweep a 48-hour hackathon with an adaptive transit assistant.",
        },
        {
            "title": "What's next",
            "description": "Exploring generative UI systems + compiler-assisted design workflows.",
        },
    ]

    contact = {
        "email": "hello@avery.codes",
        "location": "Remote • Earth",
        "availability": "Open for internships, freelance collaborations, and research labs",
    }

    return render_template(
        "portfolio.html",
        hero=hero,
        stats=stats,
        projects=projects,
        experiences=experiences,
        skill_groups=skill_groups,
        spotlights=spotlights,
        contact=contact,
    )


@bp.route("/books")
def books():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    category_id = request.args.get("category", type=int)
    categories = Category.query.all()

    if category_id:
        book_list = Book.query.filter_by(category_id=category_id).all()
    else:
        book_list = Book.query.all()

    return render_template(
        "books/list.html",
        books=book_list,
        categories=categories,
        selected_category=category_id,
    )


@bp.route("/books/create", methods=["GET", "POST"])
def create_book():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    categories = Category.query.all()

    if request.method == "POST":
        book = Book(
            title=get_form_value("title"),
            author=get_form_value("author"),
            isbn=get_form_value("isbn"),
            description=get_form_value("description"),
            category_id=get_form_value("category_id", int),
            copies_total=get_form_value("copies_total", int, 1),
            copies_available=get_form_value("copies_available", int, 1),
        )
        db.session.add(book)
        db.session.commit()
        flash("Book created successfully", "success")
        return redirect(url_for("library.books"))

    return render_template("books/form.html", categories=categories)


@bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def edit_book(book_id: int):
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    book = Book.query.get_or_404(book_id)
    categories = Category.query.all()

    if request.method == "POST":
        book.title = get_form_value("title")
        book.author = get_form_value("author")
        book.isbn = get_form_value("isbn")
        book.description = get_form_value("description")
        book.category_id = get_form_value("category_id", int)
        book.copies_total = get_form_value("copies_total", int)
        book.copies_available = get_form_value("copies_available", int)
        db.session.commit()
        flash("Book updated successfully", "success")
        return redirect(url_for("library.books"))

    return render_template("books/form.html", book=book, categories=categories)


@bp.route("/books/<int:book_id>/delete", methods=["POST"])
def delete_book(book_id: int):
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash("Book deleted", "info")
    return redirect(url_for("library.books"))


@bp.route("/users")
def users():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    return render_template("users/list.html", users=User.query.all())


@bp.route("/users/create", methods=["GET", "POST"])
def create_user():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        password = get_form_value("password")
        if not password:
            flash("Password is required for new accounts.", "warning")
            return redirect(url_for("library.create_user"))

        user = User(
            name=get_form_value("name"),
            email=get_form_value("email"),
            role=get_form_value("role", default="member"),
            approved=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("User created", "success")
        return redirect(url_for("library.users"))

    return render_template("users/form.html")


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id: int):
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted", "info")
    return redirect(url_for("library.users"))


@bp.route("/users/<int:user_id>/approve", methods=["POST"])
def approve_user(user_id: int):
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    user = User.query.get_or_404(user_id)
    if user.role != "member":
        flash("Only member accounts require approval.", "info")
        return redirect(url_for("library.users"))

    if user.approved:
        flash("User already approved.", "info")
        return redirect(url_for("library.users"))

    user.approved = True
    db.session.commit()
    flash(f"{user.name} approved.", "success")
    return redirect(url_for("library.users"))


@bp.route("/bookings")
def bookings():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    bookings_list = Booking.query.order_by(Booking.start_date.desc()).all()
    return render_template("bookings/list.html", bookings=bookings_list)


@bp.route("/bookings/create", methods=["GET", "POST"])
def create_booking():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    users = User.query.filter_by(role="member", approved=True).order_by(User.name).all()
    books = Book.query.all()

    if request.method == "POST":
        book_id = get_form_value("book_id", int)
        book = Book.query.get_or_404(book_id)
        if book.copies_available < 1:
            flash("No copies available for that book.", "warning")
            return redirect(url_for("library.create_booking"))

        user_id = get_form_value("user_id", int)
        member = User.query.get_or_404(user_id)
        if member.role != "member" or not member.approved:
            flash("Select an approved member account.", "warning")
            return redirect(url_for("library.create_booking"))

        booking = Booking(
            user_id=user_id,
            book_id=book_id,
            start_date=get_form_value("start_date", lambda v: date.fromisoformat(v)),
            end_date=get_form_value("end_date", lambda v: date.fromisoformat(v)),
            approved=True,
            return_requested=False,
            returned=False,
            fine_amount=0,
        )
        book.copies_available -= 1
        db.session.add(booking)
        db.session.commit()
        flash("Booking created", "success")
        return redirect(url_for("library.bookings"))

    return render_template("bookings/form.html", users=users, books=books)


@bp.route("/bookings/<int:booking_id>/return", methods=["POST"])
def return_booking(booking_id: int):
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    booking = Booking.query.get_or_404(booking_id)
    if booking.approved and (booking.return_requested or not booking.returned):
        booking.returned = True
        booking.return_requested = False
        booking.returned_at = date.today()
        days_overdue = max((booking.returned_at - booking.end_date).days, 0)
        booking.fine_amount = days_overdue * 100
        booking.book.copies_available += 1
        db.session.commit()
        if booking.fine_amount:
            flash(f"Return confirmed. Fine: Rs {booking.fine_amount}.", "warning")
        else:
            flash("Return confirmed.", "success")
    return redirect(url_for("library.bookings"))


@bp.route("/bookings/<int:booking_id>/approve", methods=["POST"])
def approve_booking(booking_id: int):
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    booking = Booking.query.get_or_404(booking_id)
    if booking.approved:
        flash("Booking already approved.", "info")
        return redirect(url_for("library.bookings"))

    if booking.book.copies_available < 1:
        flash("No copies available to approve this booking.", "warning")
        return redirect(url_for("library.bookings"))

    booking.approved = True
    booking.book.copies_available -= 1
    db.session.commit()
    flash("Booking approved.", "success")
    return redirect(url_for("library.bookings"))


@bp.route("/ratings")
def ratings():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    rating_list = Rating.query.order_by(Rating.created_at.desc()).all()
    return render_template("ratings/list.html", ratings=rating_list)


@bp.route("/ratings/create", methods=["GET", "POST"])
def create_rating():
    redirect_response = require_role("librarian")
    if redirect_response:
        return redirect_response

    users = User.query.all()
    books = Book.query.all()
    if request.method == "POST":
        rating = Rating(
            user_id=get_form_value("user_id", int),
            book_id=get_form_value("book_id", int),
            score=get_form_value("score", int),
            comment=get_form_value("comment"),
        )
        db.session.add(rating)
        db.session.commit()
        flash("Rating submitted", "success")
        return redirect(url_for("library.ratings"))

    return render_template("ratings/form.html", users=users, books=books)


@bp.route("/member/books")
def member_books():
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    category_id = request.args.get("category", type=int)
    categories = Category.query.all()

    if category_id:
        book_list = Book.query.filter_by(category_id=category_id).all()
    else:
        book_list = Book.query.all()

    return render_template(
        "member/books.html",
        books=book_list,
        categories=categories,
        selected_category=category_id,
    )


@bp.route("/member/books/<int:book_id>/reviews")
def member_book_reviews(book_id: int):
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    book = Book.query.get_or_404(book_id)
    ratings = (
        Rating.query.filter_by(book_id=book.id)
        .order_by(Rating.created_at.desc())
        .all()
    )
    return render_template("member/book_reviews.html", book=book, ratings=ratings)


@bp.route("/member/bookings")
def member_bookings():
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    member = current_member()
    bookings_list = Booking.query.filter_by(user_id=member.id).order_by(Booking.start_date.desc()).all()
    return render_template("member/bookings.html", bookings=bookings_list, member=member)


@bp.route("/member/bookings/new", methods=["GET", "POST"])
def member_create_booking():
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    member = current_member()
    books = Book.query.all()
    selected_book_id = request.args.get("book_id", type=int)
    today = date.today()

    if request.method == "POST":
        book_id = get_form_value("book_id", int)
        start_raw = request.form.get("start_date")
        end_raw = request.form.get("end_date")

        if not book_id:
            flash("Select a book to continue.", "warning")
            return redirect(url_for("library.member_create_booking"))

        book = Book.query.get(book_id)
        if not book:
            flash("Selected book was not found.", "danger")
            return redirect(url_for("library.member_create_booking"))

        if book.copies_available < 1:
            flash("No copies available right now. Please pick another title.", "warning")
            return redirect(url_for("library.member_create_booking", book_id=book_id))

        try:
            start_date = date.fromisoformat(start_raw)
            end_date = date.fromisoformat(end_raw)
        except Exception:
            flash("Provide valid start and end dates.", "warning")
            return redirect(url_for("library.member_create_booking", book_id=book_id))

        if start_date < today:
            flash("Start date cannot be in the past.", "warning")
            return redirect(url_for("library.member_create_booking", book_id=book_id))
        if end_date < start_date:
            flash("End date cannot be before the start date.", "warning")
            return redirect(url_for("library.member_create_booking", book_id=book_id))

        booking = Booking(
            user_id=member.id,
            book_id=book_id,
            start_date=start_date,
            end_date=end_date,
            approved=False,
            return_requested=False,
            returned=False,
            fine_amount=0,
        )
        db.session.add(booking)
        db.session.commit()
        flash("Booking request submitted. A librarian must approve it.", "success")
        return redirect(url_for("library.member_bookings"))

    return render_template(
        "member/booking_form.html",
        books=books,
        member=member,
        selected_book_id=selected_book_id,
        min_date=today.isoformat(),
        default_end=(today + timedelta(days=7)).isoformat(),
    )


@bp.route("/member/bookings/<int:booking_id>/return", methods=["POST"])
def member_return_booking(booking_id: int):
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    member = current_member()
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != member.id:
        flash("That booking does not belong to you.", "danger")
        return redirect(url_for("library.member_bookings"))

    if not booking.approved:
        flash("This booking is still awaiting librarian approval.", "warning")
        return redirect(url_for("library.member_bookings"))

    if booking.return_requested:
        flash("Return already requested. A librarian will confirm it.", "info")
        return redirect(url_for("library.member_bookings"))

    if not booking.returned:
        booking.return_requested = True
        db.session.commit()
        flash("Return requested. A librarian must confirm it.", "success")

    return redirect(url_for("library.member_bookings"))


@bp.route("/member/ratings")
def member_ratings():
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    member = current_member()
    rating_list = (
        Rating.query.filter_by(user_id=member.id)
        .order_by(Rating.created_at.desc())
        .all()
    )
    return render_template("member/ratings.html", ratings=rating_list, member=member)


@bp.route("/member/ratings/new", methods=["GET", "POST"])
def member_create_rating():
    redirect_response = require_role("member")
    if redirect_response:
        return redirect_response

    member = current_member()
    books = Book.query.all()
    selected_book_id = request.args.get("book_id", type=int)

    if request.method == "POST":
        rating = Rating(
            user_id=member.id,
            book_id=get_form_value("book_id", int),
            score=get_form_value("score", int),
            comment=get_form_value("comment"),
        )
        db.session.add(rating)
        db.session.commit()
        flash("Thanks for rating!", "success")
        return redirect(url_for("library.member_ratings"))

    return render_template(
        "member/rating_form.html",
        books=books,
        member=member,
        selected_book_id=selected_book_id,
    )
